from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


ObjectType = Literal["blob", "directory", "commit"]


@dataclass(frozen=True)
class Blob:
    content: str

    @property
    def object_type(self) -> ObjectType:
        return "blob"

    def serialize(self) -> str:
        return f"blob\n{self.content}"


@dataclass(frozen=True)
class Directory:
    entries: dict[str, str] = field(default_factory=dict)

    @property
    def object_type(self) -> ObjectType:
        return "directory"

    def serialize(self) -> str:
        lines = ["directory"]
        for name, object_hash in sorted(self.entries.items()):
            lines.append(f"{name}:{object_hash}")
        return "\n".join(lines)


@dataclass(frozen=True)
class CommitObject:
    root_hash: str
    parent_hash: str | None
    message: str
    commit_hash: str

    @property
    def object_type(self) -> ObjectType:
        return "commit"

    def serialize(self) -> str:
        parent = self.parent_hash if self.parent_hash is not None else ""
        return "\n".join(
            [
                "commit",
                f"hash:{self.commit_hash}",
                f"parent:{parent}",
                f"root:{self.root_hash}",
                f"message:{self.message}",
            ]
        )
