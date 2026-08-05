from __future__ import annotations

import hashlib
from typing import Protocol

from .errors import RuntimeError


class StoredObject(Protocol):
    """안정적인 저장 문자열로 변환할 수 있는 객체의 규칙이다."""

    def serialize(self) -> str:
        ...


class ObjectStore:
    """모든 객체를 해시 주소로 저장하는 메모리 기반 해시맵이다."""

    def __init__(self) -> None:
        self._objects: dict[str, StoredObject] = {}

    def save_content_object(self, obj: StoredObject) -> str:
        """직렬화된 내용만으로 해시를 계산하는 객체를 저장한다."""
        object_hash = self._hash(obj.serialize())
        self._objects.setdefault(object_hash, obj)
        return object_hash

    def save_with_hash(self, object_hash: str, obj: StoredObject) -> None:
        """이미 생성된 고유 해시를 가진 객체를 저장한다."""
        if object_hash in self._objects:
            raise RuntimeError.duplicate_object_hash(object_hash)
        self._objects[object_hash] = obj

    def get(self, object_hash: str) -> StoredObject:
        """해시로 객체를 찾고, 없으면 RuntimeError로 변환한다."""
        try:
            return self._objects[object_hash]
        except KeyError as error:
            raise RuntimeError.stored_object_not_found(object_hash) from error

    def contains(self, object_hash: str) -> bool:
        """해당 해시가 이미 저장소에서 사용 중인지 확인한다."""
        return object_hash in self._objects

    def items(self) -> list[tuple[str, StoredObject]]:
        """목록 출력과 해시 조회에 사용할 모든 해시/객체 쌍을 반환한다."""
        return list(self._objects.items())

    @staticmethod
    def _hash(value: str) -> str:
        """SHA-256으로 안정적인 객체 주소를 만든다."""
        return hashlib.sha256(value.encode("utf-8")).hexdigest()
