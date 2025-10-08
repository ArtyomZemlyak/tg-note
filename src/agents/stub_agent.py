"""
Stub Agent
Simple placeholder agent for MVP testing
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
from loguru import logger

from .base_agent import BaseAgent, KBStructure


class StubAgent(BaseAgent):
    """
    Stub agent for MVP - minimal processing and formatting
    
    Note: This agent uses MCP mem-agent HTTP server for memory storage,
    allowing it to record and retrieve processing history.
    """
    
    def __init__(self, config: Optional[Dict] = None, kb_root_path: Optional[Path] = None):
        """
        Initialize StubAgent with MCP memory support
        
        Args:
            config: Configuration dictionary
            kb_root_path: Root path for knowledge base (for mem-agent)
        """
        super().__init__(config)
        self.kb_root_path = kb_root_path or Path("./knowledge_base")
        
        # Initialize MCP memory client
        self._init_mcp_memory()
    
    def _init_mcp_memory(self) -> None:
        """Initialize MCP memory agent client"""
        try:
            from .mcp.memory_agent_tool import MemoryStoreTool
            from .tools.base_tool import ToolContext
            
            # Create tool context
            ctx = ToolContext(
                kb_root_path=self.kb_root_path,
                base_agent_class=BaseAgent,
            )
            
            # Create memory store tool
            self.memory_tool = MemoryStoreTool()
            self.memory_tool.enable()
            self.memory_context = ctx
            
            logger.info("[StubAgent] MCP memory agent initialized")
        except Exception as e:
            logger.warning(f"[StubAgent] Failed to initialize MCP memory: {e}")
            self.memory_tool = None
            self.memory_context = None
    
    async def _store_in_memory(self, content: str, tags: list = None) -> None:
        """
        Store content in MCP memory
        
        Args:
            content: Content to store
            tags: Optional tags
        """
        if not self.memory_tool or not self.memory_context:
            logger.debug("[StubAgent] Memory tool not available, skipping storage")
            return
        
        try:
            await self.memory_tool.execute(
                {"content": content, "tags": tags or []},
                self.memory_context
            )
            logger.debug(f"[StubAgent] Stored content in memory: {content[:50]}...")
        except Exception as e:
            logger.warning(f"[StubAgent] Failed to store in memory: {e}")
    
    async def process(self, content: Dict) -> Dict:
        """
        Process content with minimal formatting
        
        Args:
            content: Content dictionary
        
        Returns:
            Processed content with markdown formatting and KB structure
        """
        if not self.validate_input(content):
            raise ValueError("Invalid input content")
        
        text = content.get("text", "")
        urls = content.get("urls", [])
        
        # Create basic markdown structure
        markdown_content = self._format_markdown(text, urls)
        
        # Generate metadata
        metadata = {
            "processed_at": datetime.now().isoformat(),
            "agent": "StubAgent",
            "version": "0.3.0"
        }
        
        # Determine KB structure (simple heuristic for stub)
        kb_structure = self._determine_kb_structure(text, urls)
        
        # Store processing result in memory
        title = BaseAgent.generate_title(text)
        memory_note = f"Processed content: {title}\nCategory: {kb_structure.category}"
        await self._store_in_memory(memory_note, tags=["stub_agent", kb_structure.category])
        
        return {
            "markdown": markdown_content,
            "metadata": metadata,
            "title": title,
            "kb_structure": kb_structure
        }
    
    def validate_input(self, content: Dict) -> bool:
        """
        Validate input content
        
        Args:
            content: Content to validate
        
        Returns:
            True if valid, False otherwise
        """
        return isinstance(content, dict) and "text" in content
    
    def _format_markdown(self, text: str, urls: list) -> str:
        """
        Format content as markdown
        
        Args:
            text: Main text content
            urls: List of URLs
        
        Returns:
            Formatted markdown string
        """
        lines = [
            "# Content Note",
            "",
            "## Content",
            "",
            text,
            ""
        ]
        
        if urls:
            lines.extend([
                "## Links",
                ""
            ])
            for url in urls:
                lines.append(f"- {url}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _determine_kb_structure(self, text: str, urls: list) -> KBStructure:
        """
        Determine KB structure based on content (simple heuristic for stub)
        
        Args:
            text: Content text
            urls: List of URLs
        
        Returns:
            KBStructure object
        """
        text_lower = text.lower()
        
        # Simple keyword-based categorization
        if any(keyword in text_lower for keyword in ["ai", "artificial intelligence", "machine learning", "neural network", "llm", "gpt"]):
            return KBStructure(category="ai", subcategory="machine-learning", tags=["ai"])
        elif any(keyword in text_lower for keyword in ["biology", "gene", "dna", "protein", "cell"]):
            return KBStructure(category="biology", tags=["biology"])
        elif any(keyword in text_lower for keyword in ["physics", "quantum", "particle", "relativity"]):
            return KBStructure(category="physics", tags=["physics"])
        elif any(keyword in text_lower for keyword in ["programming", "code", "software", "python", "javascript"]):
            return KBStructure(category="tech", subcategory="programming", tags=["programming"])
        else:
            # Default category
            return KBStructure(category="general", tags=["uncategorized"])