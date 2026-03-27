"""Base repository interface for data storage."""

import abc
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class Repository(abc.ABC, Generic[T]):
    """Abstract base class for repositories."""

    @abc.abstractmethod
    def create(self, entity: T) -> T:
        """Create a new entity."""

    @abc.abstractmethod
    def get(self, id: str) -> T | None:  # noqa: A002
        """Get an entity by ID."""

    @abc.abstractmethod
    def get_all(self) -> list[T]:
        """Get all entities."""

    @abc.abstractmethod
    def update(self, entity: T) -> T:
        """Update an entity."""

    @abc.abstractmethod
    def delete(self, id: str) -> None:  # noqa: A002
        """Delete an entity by ID."""

    @abc.abstractmethod
    def search(self, **kwargs: Any) -> list[T]:
        """Search for entities based on criteria."""
