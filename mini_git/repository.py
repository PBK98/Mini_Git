from __future__ import annotations

import hashlib
import heapq
from collections import defaultdict, deque

from .objects import Blob, CommitObject, Directory
from .store import ObjectStore


class MiniGitRepository:
    def __init__(self) -> None:
        self.object_store = ObjectStore()
        self.commits: dict[str, CommitObject] = {}
        self.children: dict[str | None, list[str]] = defaultdict(list)
        self.head_hash: str | None = None
        self._commit_counter = 0

    def commit(self, files: dict[str, str], message: str) -> str:
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
        self.children[parent_hash].append(commit_hash)
        self.head_hash = commit_hash
        return commit_hash

    def get_commit(self, commit_hash: str) -> CommitObject:
        return self.commits[commit_hash]

    def sorted_commits(self) -> list[CommitObject]:
        indegree: dict[str, int] = {commit_hash: 0 for commit_hash in self.commits}

        for commit_hash, commit in self.commits.items():
            if commit.parent_hash is not None:
                indegree[commit_hash] += 1

        ready = deque(
            commit_hash
            for commit_hash, degree in indegree.items()
            if degree == 0
        )
        result: list[CommitObject] = []

        while ready:
            commit_hash = ready.popleft()
            result.append(self.commits[commit_hash])

            for child_hash in self.children.get(commit_hash, []):
                indegree[child_hash] -= 1
                if indegree[child_hash] == 0:
                    ready.append(child_hash)

        if len(result) != len(self.commits):
            raise ValueError("commit graph has a cycle")

        return result

    def sorted_commits_by_hash(self) -> list[CommitObject]:
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
            raise ValueError("commit graph has a cycle")

        return result

    def _save_directory(self, files: dict[str, str]) -> str:
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
