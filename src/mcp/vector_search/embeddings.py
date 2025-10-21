"""
Embedding Models
Supports multiple embedding backends: sentence-transformers, OpenAI API, Infinity API
"""

import hashlib
import json
from abc import ABC, abstractmethod
from typing import List, Optional

from loguru import logger


class BaseEmbedder(ABC):
    """Base class for embedding models"""

    def __init__(self, model_name: str):
        self.model_name = model_name

    @abstractmethod
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of texts

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors
        """
        pass

    @abstractmethod
    async def embed_query(self, query: str) -> List[float]:
        """
        Embed a single query

        Args:
            query: Query text to embed

        Returns:
            Embedding vector
        """
        pass

    @abstractmethod
    def get_dimension(self) -> int:
        """Get the dimension of embeddings"""
        pass

    def get_model_hash(self) -> str:
        """Get a hash identifying the model configuration"""
        config = {"model_type": self.__class__.__name__, "model_name": self.model_name}
        config_str = json.dumps(config, sort_keys=True)
        return hashlib.md5(config_str.encode()).hexdigest()


class SentenceTransformerEmbedder(BaseEmbedder):
    """Local sentence-transformers embeddings"""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize sentence-transformers model

        Args:
            model_name: HuggingFace model name (default: all-MiniLM-L6-v2)
        """
        super().__init__(model_name)
        self._model = None
        self._dimension: Optional[int] = None

    def _load_model(self):
        """Lazy load the model"""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                logger.info(f"Loading sentence-transformer model: {self.model_name}")
                self._model = SentenceTransformer(self.model_name)
                # Get dimension from first embedding
                test_emb = self._model.encode(["test"], show_progress_bar=False)
                self._dimension = len(test_emb[0])
                logger.info(f"Model loaded. Dimension: {self._dimension}")
            except ImportError:
                raise ImportError(
                    "sentence-transformers not installed. "
                    "Install with: pip install sentence-transformers"
                )

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts"""
        self._load_model()
        assert self._model is not None, "Model should be loaded"

        logger.debug(f"Embedding {len(texts)} texts with sentence-transformers")
        embeddings = self._model.encode(
            texts, show_progress_bar=len(texts) > 10, convert_to_numpy=True
        )
        result: List[List[float]] = embeddings.tolist()
        return result

    async def embed_query(self, query: str) -> List[float]:
        """Embed a single query"""
        embeddings = await self.embed_texts([query])
        return embeddings[0]

    def get_dimension(self) -> int:
        """Get embedding dimension"""
        if self._dimension is None:
            self._load_model()
        assert self._dimension is not None, "Dimension should be set after loading model"
        return self._dimension


class OpenAIEmbedder(BaseEmbedder):
    """OpenAI API embeddings"""

    # Dimension mapping for known models
    DIMENSIONS = {
        "text-embedding-ada-002": 1536,
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
    }

    def __init__(
        self,
        model_name: str = "text-embedding-ada-002",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        """
        Initialize OpenAI embeddings

        Args:
            model_name: OpenAI model name
            api_key: OpenAI API key (or set OPENAI_API_KEY env var)
            base_url: Custom API base URL
        """
        super().__init__(model_name)
        self.api_key = api_key
        self.base_url = base_url
        self._client = None
        # If model is known, use mapped dimension; otherwise determine dynamically later
        self._dimension: Optional[int] = self.DIMENSIONS.get(model_name)

    def _get_client(self):
        """Lazy load OpenAI client"""
        if self._client is None:
            try:
                from openai import AsyncOpenAI

                logger.info(f"Initializing OpenAI client for model: {self.model_name}")
                self._client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
            except ImportError:
                raise ImportError("openai not installed. " "Install with: pip install openai")
        return self._client

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts"""
        client = self._get_client()

        logger.debug(f"Embedding {len(texts)} texts with OpenAI")

        # OpenAI has a limit on batch size, process in chunks
        batch_size = 100
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            response = await client.embeddings.create(model=self.model_name, input=batch)
            embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(embeddings)

        # Set dimension from first embedding if not yet known
        if self._dimension is None and all_embeddings:
            self._dimension = len(all_embeddings[0])
            logger.info(f"Determined OpenAI embedding dimension from response: {self._dimension}")

        return all_embeddings

    async def embed_query(self, query: str) -> List[float]:
        """Embed a single query"""
        embeddings = await self.embed_texts([query])
        return embeddings[0]

    def get_dimension(self) -> int:
        """Get embedding dimension"""
        # If we already know it (known model mapping or previously probed), return it
        if self._dimension is not None:
            return self._dimension

        # Try to probe synchronously via HTTP (no dependency on openai package)
        try:
            import urllib.error
            import urllib.request

            url_base = self.base_url or "https://api.openai.com/v1"
            url = f"{url_base.rstrip('/')}/embeddings"
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            payload = {
                "model": self.model_name,
                "input": ["__dimension_probe__"],
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            embeddings = [item.get("embedding", []) for item in data.get("data", [])]
            if embeddings and isinstance(embeddings[0], list):
                self._dimension = len(embeddings[0])
                logger.info(f"Determined OpenAI embedding dimension dynamically: {self._dimension}")
                return self._dimension
        except Exception as e:
            logger.warning(f"Failed to determine OpenAI embedding dimension dynamically: {e}")

        # If we cannot determine dimension, raise to avoid mismatched vector store creation
        raise RuntimeError(
            "Unable to determine OpenAI embedding dimension; ensure API connectivity or use a known model."
        )


class InfinityEmbedder(BaseEmbedder):
    """Infinity API embeddings (https://github.com/michaelfeil/infinity)"""

    def __init__(
        self, model_name: str, api_url: str = "http://localhost:7997", api_key: Optional[str] = None
    ):
        """
        Initialize Infinity API embeddings

        Args:
            model_name: Model name configured in Infinity
            api_url: Infinity API URL
            api_key: API key if authentication is enabled
        """
        super().__init__(model_name)
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self._dimension: Optional[int] = None

    def _determine_dimension_sync(self) -> int:
        """Determine embedding dimension synchronously using embed_texts function.

        Uses a lightweight single-text embedding request to avoid assumptions about
        the /models schema. This leverages the existing embed_texts method for consistency.
        """
        import asyncio

        # Use embed_texts to get dimension from a probe text
        probe_text = "__dimension_probe__"

        # Run the async embed_texts method synchronously
        try:
            # Try to get the current event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're in an async context, we need to use a different approach
                # Fall back to direct HTTP request for consistency
                return self._determine_dimension_direct_http()
            else:
                # We can run the async method
                embeddings = loop.run_until_complete(self.embed_texts([probe_text]))
        except RuntimeError:
            # No event loop or can't run in current context, fall back to direct HTTP
            return self._determine_dimension_direct_http()

        if not embeddings or not isinstance(embeddings[0], list):
            raise RuntimeError("Infinity API returned unexpected response for dimension probe")
        return len(embeddings[0])

    def _determine_dimension_direct_http(self) -> int:
        """Fallback method for determining dimension via direct HTTP request.

        Used when async context is not available for embed_texts.
        """
        import urllib.error
        import urllib.request

        url = f"{self.api_url}/embeddings"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {"model": self.model_name, "input": ["__dimension_probe__"]}

        req = urllib.request.Request(
            url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        embeddings = [item.get("embedding", []) for item in data.get("data", [])]
        if not embeddings or not isinstance(embeddings[0], list):
            raise RuntimeError("Infinity API returned unexpected response for dimension probe")
        return len(embeddings[0])

    async def _make_request(self, texts: List[str]) -> List[List[float]]:
        """Make request to Infinity API"""
        import aiohttp

        url = f"{self.api_url}/embeddings"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {"model": self.model_name, "input": texts}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(
                        f"Infinity API error (status {response.status}): {error_text}"
                    )

                data = await response.json()
                embeddings = [item["embedding"] for item in data["data"]]

                # Set dimension from first embedding
                if self._dimension is None and embeddings:
                    self._dimension = len(embeddings[0])

                return embeddings

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts"""
        logger.debug(f"Embedding {len(texts)} texts with Infinity API")
        return await self._make_request(texts)

    async def embed_query(self, query: str) -> List[float]:
        """Embed a single query"""
        embeddings = await self.embed_texts([query])
        return embeddings[0]

    def get_dimension(self) -> int:
        """Get embedding dimension"""
        if self._dimension is None:
            try:
                self._dimension = self._determine_dimension_sync()
                logger.info(
                    f"Determined Infinity embedding dimension dynamically: {self._dimension}"
                )
            except Exception as e:
                raise RuntimeError(f"Failed to determine Infinity embedding dimension: {e}")
        return self._dimension
