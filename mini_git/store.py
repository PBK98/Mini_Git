from __future__ import annotations

import hashlib
from typing import Protocol


class StoredObject(Protocol):
    def serialize(self) -> str:
        ...


class ObjectStore:
    def __init__(self) -> None:
        self._objects: dict[str, StoredObject] = {}

    def save_content_object(self, obj: StoredObject) -> str:
        object_hash = self._hash(obj.serialize())
        self._objects.setdefault(object_hash, obj)
        return object_hash

    def save_with_hash(self, object_hash: str, obj: StoredObject) -> None:
        if object_hash in self._objects:
            raise ValueError(f"duplicated object hash: {object_hash}")
        self._objects[object_hash] = obj

    def get(self, object_hash: str) -> StoredObject:
        return self._objects[object_hash]

    def contains(self, object_hash: str) -> bool:
        return object_hash in self._objects

    def items(self) -> list[tuple[str, StoredObject]]:
        return list(self._objects.items())

    @staticmethod
    def _hash(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()
