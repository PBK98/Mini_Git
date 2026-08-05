from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


ObjectType = Literal["commit"]


@dataclass(frozen=True)
class CommitObject:
    """커밋 그래프의 한 노드에 필요한 메타데이터와 부모 연결을 나타낸다."""

    commit_hash: str
    message: str
    author: str
    timestamp: str
    parents: tuple[str, ...]
    branch: str

    @property
    def object_type(self) -> ObjectType:
        return "commit"

    def serialize(self) -> str:
        """커밋 메타데이터를 문자열로 변환한다."""
        parent_text = ",".join(self.parents)
        return "\n".join(
            [
                "commit",
                f"hash:{self.commit_hash}",
                f"message:{self.message}",
                f"author:{self.author}",
                f"timestamp:{self.timestamp}",
                f"parents:{parent_text}",
                f"branch:{self.branch}",
            ]
        )
