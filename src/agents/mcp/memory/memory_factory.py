"""
Memory Storage Factory

Factory for creating appropriate memory storage instances based on configuration.
Follows the Factory Pattern and Dependency Inversion Principle.
"""

from pathlib import Path
from typing import Optional

from loguru import logger

from .memory_base import BaseMemoryStorage
from .memory_json_storage import JsonMemoryStorage
from .memory_mem_agent_storage import MemAgentStorage
from .memory_vector_storage import VectorBasedMemoryStorage


class MemoryStorageFactory:
    """
    Factory for creating memory storage instances

    This factory creates the appropriate storage implementation based on
    the storage type configuration, following SOLID principles:
    - Single Responsibility: Only responsible for creating storage instances
    - Open/Closed: Can be extended with new storage types without modification
    - Dependency Inversion: Returns abstract BaseMemoryStorage interface
    """

    # Registry of available storage types
    STORAGE_TYPES = {
        "json": JsonMemoryStorage,
        "vector": VectorBasedMemoryStorage,
        "mem-agent": MemAgentStorage,
    }

    @classmethod
    def create(
        cls, storage_type: str, data_dir: Path, model_name: Optional[str] = None, backend: Optional[str] = None, **kwargs
    ) -> BaseMemoryStorage:
        """
        Create a memory storage instance

        Args:
            storage_type: Type of storage ("json", "vector", or "mem-agent")
            data_dir: Directory for storing memory data
            model_name: Model name for vector-based storage or mem-agent (optional)
            backend: Backend for model execution ("auto", "vllm", "mlx", "transformers") (optional)
            **kwargs: Additional arguments for specific storage implementations
                     For mem-agent: max_tool_turns (int)

        Returns:
            Memory storage instance

        Raises:
            ValueError: If storage_type is unknown
            ImportError: If required dependencies for storage type are missing
        """
        storage_type = storage_type.lower()

        if storage_type not in cls.STORAGE_TYPES:
            available = ", ".join(cls.STORAGE_TYPES.keys())
            raise ValueError(
                f"Unknown storage type: '{storage_type}'. " f"Available types: {available}"
            )

        storage_class = cls.STORAGE_TYPES[storage_type]

        try:
            # Create storage instance with appropriate parameters
            if storage_type == "json":
                storage = storage_class(data_dir=data_dir)
                logger.info(f"[MemoryStorageFactory] Created JsonMemoryStorage at {data_dir}")

            elif storage_type == "vector":
                # Vector-based storage requires model_name
                if model_name is None:
                    raise ValueError("model_name is required for vector-based storage")
                storage = storage_class(data_dir=data_dir, model_name=model_name)
                logger.info(
                    f"[MemoryStorageFactory] Created VectorBasedMemoryStorage "
                    f"with model '{model_name}' at {data_dir}"
                )

            elif storage_type == "mem-agent":
                # Mem-agent storage with LLM-based memory management
                # Derive use_vllm from backend parameter
                # backend can be: "auto", "vllm", "mlx", "transformers"
                # use_vllm=True means use vLLM backend, False means use OpenRouter/auto-detection
                if backend is None:
                    backend = "auto"
                
                # Only set use_vllm=True if backend is explicitly "vllm"
                # For "auto", "mlx", "transformers", use_vllm=False and let the agent auto-detect
                use_vllm = (backend.lower() == "vllm")
                
                max_tool_turns = kwargs.get("max_tool_turns", 20)
                storage = storage_class(
                    data_dir=data_dir,
                    model=model_name,  # Model name for mem-agent
                    use_vllm=use_vllm,
                    max_tool_turns=max_tool_turns,
                )
                logger.info(
                    f"[MemoryStorageFactory] Created MemAgentStorage "
                    f"with model '{model_name or 'default'}', backend={backend}, use_vllm={use_vllm} at {data_dir}"
                )

            else:
                # Fallback for future storage types
                storage = storage_class(data_dir=data_dir, **kwargs)
                logger.info(
                    f"[MemoryStorageFactory] Created {storage_class.__name__} at {data_dir}"
                )

            return storage

        except ImportError as e:
            logger.error(
                f"[MemoryStorageFactory] Failed to create {storage_type} storage: {e}. "
                f"Missing dependencies?"
            )
            raise
        except Exception as e:
            logger.error(f"[MemoryStorageFactory] Failed to create {storage_type} storage: {e}")
            raise

    @classmethod
    def register_storage_type(cls, name: str, storage_class: type) -> None:
        """
        Register a new storage type

        Allows extending the factory with custom storage implementations
        without modifying the factory code (Open/Closed Principle).

        Args:
            name: Name for the storage type
            storage_class: Storage class (must inherit from BaseMemoryStorage)

        Raises:
            TypeError: If storage_class doesn't inherit from BaseMemoryStorage
        """
        if not issubclass(storage_class, BaseMemoryStorage):
            raise TypeError(
                f"Storage class must inherit from BaseMemoryStorage, "
                f"got {storage_class.__name__}"
            )

        cls.STORAGE_TYPES[name.lower()] = storage_class
        logger.info(f"[MemoryStorageFactory] Registered new storage type: {name}")

    @classmethod
    def list_available_types(cls) -> list[str]:
        """
        List all available storage types

        Returns:
            List of storage type names
        """
        return list(cls.STORAGE_TYPES.keys())


def create_memory_storage(
    storage_type: str, data_dir: Path, model_name: Optional[str] = None, backend: Optional[str] = None, **kwargs
) -> BaseMemoryStorage:
    """
    Convenience function for creating memory storage

    This is a simplified interface to the factory for common use cases.

    Args:
        storage_type: Type of storage ("json", "vector", or "mem-agent")
        data_dir: Directory for storing memory data
        model_name: Model name for vector-based storage or mem-agent (optional)
        backend: Backend for model execution ("auto", "vllm", "mlx", "transformers") (optional)
        **kwargs: Additional arguments for specific storage implementations

    Returns:
        Memory storage instance
    """
    return MemoryStorageFactory.create(
        storage_type=storage_type, data_dir=data_dir, model_name=model_name, backend=backend, **kwargs
    )
