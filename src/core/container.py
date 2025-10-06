"""
Dependency Injection Container
Provides a simple DI container for managing dependencies and services
"""

from typing import Any, Callable, Dict, Optional, Type, TypeVar
from loguru import logger


T = TypeVar('T')


class Container:
    """Simple dependency injection container"""
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._singletons: Dict[str, Any] = {}
        
    def register(self, name: str, factory: Callable, singleton: bool = True) -> None:
        """
        Register a service factory
        
        Args:
            name: Service name
            factory: Factory function that creates the service
            singleton: If True, only one instance will be created
        """
        self._factories[name] = factory
        if singleton:
            self._singletons[name] = None
        logger.debug(f"Registered service: {name} (singleton={singleton})")
    
    def register_instance(self, name: str, instance: Any) -> None:
        """
        Register a service instance directly
        
        Args:
            name: Service name
            instance: Service instance
        """
        self._services[name] = instance
        logger.debug(f"Registered instance: {name}")
    
    def get(self, name: str) -> Any:
        """
        Get a service by name
        
        Args:
            name: Service name
        
        Returns:
            Service instance
        
        Raises:
            KeyError: If service is not registered
        """
        # Check if already instantiated
        if name in self._services:
            return self._services[name]
        
        # Check if singleton already created
        if name in self._singletons and self._singletons[name] is not None:
            return self._singletons[name]
        
        # Check if factory exists
        if name not in self._factories:
            raise KeyError(f"Service '{name}' not registered in container")
        
        # Create instance using factory
        factory = self._factories[name]
        instance = factory(self)
        
        # Store if singleton
        if name in self._singletons:
            self._singletons[name] = instance
            self._services[name] = instance
        
        return instance
    
    def has(self, name: str) -> bool:
        """
        Check if service is registered
        
        Args:
            name: Service name
        
        Returns:
            True if service is registered
        """
        return name in self._services or name in self._factories
    
    def clear(self) -> None:
        """Clear all registered services (useful for testing)"""
        self._services.clear()
        self._factories.clear()
        self._singletons.clear()
        logger.debug("Container cleared")


# Global container instance
_container = Container()


def get_container() -> Container:
    """Get the global container instance"""
    return _container


def register_service(name: str, factory: Callable, singleton: bool = True) -> None:
    """
    Register a service in the global container
    
    Args:
        name: Service name
        factory: Factory function
        singleton: If True, only one instance will be created
    """
    _container.register(name, factory, singleton)


def get_service(name: str) -> Any:
    """
    Get a service from the global container
    
    Args:
        name: Service name
    
    Returns:
        Service instance
    """
    return _container.get(name)
