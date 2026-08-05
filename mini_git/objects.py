from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


ObjectType = Literal["blob", "directory", "commit"]


@dataclass(frozen=True)
class Blob:
    """파일 내용만 저장한다. 파일 이름은 Directory가 관리한다."""

    content: str

    @property
    def object_type(self) -> ObjectType:
        return "blob"

    def serialize(self) -> str:
        """내용 기반 해시에 사용할 안정적인 문자열 표현을 만든다."""
        return f"blob\n{self.content}"


@dataclass(frozen=True)
class Directory:
    """파일명 또는 디렉터리명을 저장된 객체 해시와 연결한다."""

    entries: dict[str, str] = field(default_factory=dict)

    @property
    def object_type(self) -> ObjectType:
        return "directory"

    def serialize(self) -> str:
        """같은 디렉터리 구조가 항상 같은 해시를 만들도록 항목을 정렬한다."""
        lines = ["directory"]
        for name, object_hash in sorted(self.entries.items()):
            lines.append(f"{name}:{object_hash}")
        return "\n".join(lines)


@dataclass(frozen=True)
class CommitObject:
    """저장된 한 시점의 프로젝트 상태와 부모 커밋을 나타낸다."""

    root_hash: str
    parent_hash: str | None
    message: str
    commit_hash: str

    @property
    def object_type(self) -> ObjectType:
        return "commit"

    def serialize(self) -> str:
        """커밋 히스토리를 복원할 수 있도록 root와 parent 연결을 포함한다."""
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
