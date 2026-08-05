from __future__ import annotations

import hashlib
import heapq
from collections import defaultdict, deque

from .errors import RuntimeError
from .objects import Blob, CommitObject, Directory
from .store import ObjectStore


class MiniGitRepository:
    """객체, 커밋, HEAD, 커밋 그래프 정렬을 함께 관리한다."""

    def __init__(self) -> None:
        self.object_store = ObjectStore()
        # 커밋 해시로 CommitObject를 바로 찾기 위한 맵이다.
        self.commits: dict[str, CommitObject] = {}
        # 위상 정렬에서 자식 커밋을 빠르게 찾기 위한 역방향 인덱스다.
        self.children: dict[str | None, list[str]] = defaultdict(list)
        self.head_hash: str | None = None
        # 커밋 해시는 세션 안에서 유일해야 하므로 커밋마다 카운터를 사용한다.
        self._commit_counter = 0

    def commit(self, files: dict[str, str], message: str) -> str:
        """작업 트리 스냅샷을 저장하고 HEAD 위치에 새 커밋을 만든다."""
        root_hash = self._save_directory(files)
        parent_hash = self.head_hash
        commit_hash = self._create_commit_hash(root_hash, parent_hash, message)
        commit = CommitObject(
            root_hash=root_hash,
            parent_hash=parent_hash,
            message=message,
            commit_hash=commit_hash,
        )

        self.object_store.save_with_hash(commit_hash, commit)
        self.commits[commit_hash] = commit
        # 커밋은 부모를 가리키므로, 자식 조회는 별도 인덱스로 관리한다.
        self.children[parent_hash].append(commit_hash)
        self.head_hash = commit_hash
        return commit_hash

    def get_commit(self, commit_hash: str) -> CommitObject:
        """커밋 해시맵에서 CommitObject를 반환한다."""
        return self.commits[commit_hash]

    def sorted_commits(self) -> list[CommitObject]:
        """모든 부모 커밋이 자식보다 먼저 나오도록 커밋을 반환한다."""
        indegree: dict[str, int] = {commit_hash: 0 for commit_hash in self.commits}

        # 부모가 있는 커밋은 부모 커밋 하나에 의존한다.
        for commit_hash, commit in self.commits.items():
            if commit.parent_hash is not None:
                indegree[commit_hash] += 1

        # Kahn 위상 정렬은 부모가 없는 커밋부터 시작한다.
        ready = deque(
            commit_hash
            for commit_hash, degree in indegree.items()
            if degree == 0
        )
        result: list[CommitObject] = []

        while ready:
            commit_hash = ready.popleft()
            result.append(self.commits[commit_hash])

            # 부모가 결과에 추가되면 자식의 남은 의존성 수를 줄인다.
            for child_hash in self.children.get(commit_hash, []):
                indegree[child_hash] -= 1
                if indegree[child_hash] == 0:
                    ready.append(child_hash)

        if len(result) != len(self.commits):
            raise RuntimeError.cyclic_commit_graph()

        return result

    def sorted_commits_by_hash(self) -> list[CommitObject]:
        """동시에 처리 가능한 커밋이 여러 개일 때 heap을 쓰는 위상 정렬이다."""
        indegree: dict[str, int] = {commit_hash: 0 for commit_hash in self.commits}

        for commit_hash, commit in self.commits.items():
            if commit.parent_hash is not None:
                indegree[commit_hash] += 1

        ready = [
            commit_hash
            for commit_hash, degree in indegree.items()
            if degree == 0
        ]
        heapq.heapify(ready)
        result: list[CommitObject] = []

        while ready:
            commit_hash = heapq.heappop(ready)
            result.append(self.commits[commit_hash])

            for child_hash in self.children.get(commit_hash, []):
                indegree[child_hash] -= 1
                if indegree[child_hash] == 0:
                    heapq.heappush(ready, child_hash)

        if len(result) != len(self.commits):
            raise RuntimeError.cyclic_commit_graph()

        return result

    def _save_directory(self, files: dict[str, str]) -> str:
        """각 파일을 Blob으로 저장한 뒤 루트 Directory를 저장한다."""
        entries: dict[str, str] = {}

        for file_name, content in files.items():
            blob_hash = self.object_store.save_content_object(Blob(content))
            entries[file_name] = blob_hash

        return self.object_store.save_content_object(Directory(entries))

    def _create_commit_hash(
        self,
        root_hash: str,
        parent_hash: str | None,
        message: str,
    ) -> str:
        """커밋 데이터와 카운터를 사용해 세션 내 고유 커밋 해시를 만든다."""
        while True:
            source = "\n".join(
                [
                    "commit",
                    f"counter:{self._commit_counter}",
                    f"parent:{parent_hash or ''}",
                    f"root:{root_hash}",
                    f"message:{message}",
                ]
            )
            self._commit_counter += 1
            commit_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()

            if commit_hash not in self.commits and not self.object_store.contains(commit_hash):
                return commit_hash
