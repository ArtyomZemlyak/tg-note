"""
Agent Registry
Registry pattern for agent types (Open/Closed Principle)
Allows adding new agent types without modifying existing code
"""

from typing import Callable, Dict, Optional, Type
from loguru import logger

from .base_agent import BaseAgent


class AgentRegistry:
    """
    Registry for agent types
    
    Follows Open/Closed Principle:
    - Open for extension (can register new agent types)
    - Closed for modification (no need to modify this class)
    """
    
    def __init__(self):
        self._agents: Dict[str, Type[BaseAgent]] = {}
        self._factories: Dict[str, Callable] = {}
        
    def register(
        self,
        name: str,
        agent_class: Optional[Type[BaseAgent]] = None,
        factory: Optional[Callable] = None
    ) -> None:
        """
        Register an agent type
        
        Args:
            name: Agent type name
            agent_class: Agent class (if using simple instantiation)
            factory: Factory function (if using custom instantiation logic)
        
        Raises:
            ValueError: If neither agent_class nor factory is provided
        """
        if agent_class is None and factory is None:
            raise ValueError("Either agent_class or factory must be provided")
        
        if agent_class:
            self._agents[name] = agent_class
            logger.debug(f"Registered agent type: {name} -> {agent_class.__name__}")
        
        if factory:
            self._factories[name] = factory
            logger.debug(f"Registered agent factory: {name}")
    
    def create(self, name: str, config: Optional[Dict] = None) -> BaseAgent:
        """
        Create an agent instance
        
        Args:
            name: Agent type name
            config: Configuration dictionary
        
        Returns:
            Agent instance
        
        Raises:
            ValueError: If agent type is not registered
        """
        config = config or {}
        
        # Check if custom factory exists
        if name in self._factories:
            return self._factories[name](config)
        
        # Use simple class instantiation
        if name in self._agents:
            return self._agents[name](config=config)
        
        # Agent type not found
        available = list(set(list(self._agents.keys()) + list(self._factories.keys())))
        raise ValueError(
            f"Unknown agent type: {name}. "
            f"Available types: {available}"
        )
    
    def is_registered(self, name: str) -> bool:
        """
        Check if agent type is registered
        
        Args:
            name: Agent type name
        
        Returns:
            True if registered
        """
        return name in self._agents or name in self._factories
    
    def get_available_types(self) -> list[str]:
        """
        Get list of available agent types
        
        Returns:
            List of agent type names
        """
        return list(set(list(self._agents.keys()) + list(self._factories.keys())))


# Global registry instance
_global_registry = AgentRegistry()


def get_registry() -> AgentRegistry:
    """Get the global agent registry"""
    return _global_registry


def register_agent(
    name: str,
    agent_class: Optional[Type[BaseAgent]] = None,
    factory: Optional[Callable] = None
) -> None:
    """
    Register an agent type in the global registry
    
    Args:
        name: Agent type name
        agent_class: Agent class
        factory: Factory function
    """
    _global_registry.register(name, agent_class, factory)
