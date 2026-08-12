from __future__ import annotations

import hashlib
from collections import defaultdict, deque
from datetime import datetime

from .errors import AppError, RuntimeError
from .objects import CommitObject


class MiniGitRepository:
    """브랜치, HEAD, 커밋 그래프, 검색 인덱스를 함께 관리한다."""

    def __init__(self) -> None:
        self.commits: dict[str, CommitObject] = {}
        self.children: dict[str, list[str]] = defaultdict(list)
        self.branches: dict[str, str | None] = {}
        self.current_branch: str | None = None
        self.current_author: str | None = None
        self.keyword_index: dict[str, list[str]] = defaultdict(list)
        self.author_index: dict[str, list[str]] = defaultdict(list)
        self._commit_counter = 0
        self._issued_hashes: set[str] = set()

    def init(self, user_name: str) -> list[str]:
        """저장소를 처음 만들거나 기존 저장소의 현재 사용자를 변경한다."""
        if self.current_branch is not None:
            self.current_author = user_name
            return [
                "Repository already initialized.",
                f"Current branch: {self.current_branch}",
                f"Current user: {user_name}",
            ]

        self.commits = {}
        self.children = defaultdict(list)
        self.branches = {"main": None}
        self.current_branch = "main"
        self.current_author = user_name
        self.keyword_index = defaultdict(list)
        self.author_index = defaultdict(list)

        return [
            "Initialized repository.",
            "Current branch: main",
            f"Current user: {user_name}",
        ]

    def create_branch(self, branch_name: str) -> list[str]:
        """현재 HEAD를 가리키는 새 브랜치를 만든다."""
        self._require_initialized()

        if branch_name in self.branches:
            raise AppError.branch_already_exists(branch_name)

        head_hash = self._head_hash()
        if head_hash is None:
            raise AppError.branch_requires_commit()

        self.branches[branch_name] = head_hash
        return [f"Created branch: {branch_name}"]

    def list_branches(self) -> list[str]:
        """생성된 브랜치와 현재 브랜치를 표시한다."""
        self._require_initialized()
        lines = ["Branches:"]

        for branch_name in self.branches:
            marker = "*" if branch_name == self.current_branch else " "
            lines.append(f"{marker} {branch_name}")

        return lines

    def current_user(self) -> list[str]:
        """현재 커밋 작성자로 설정된 사용자를 반환한다."""
        self._require_initialized()
        return [f"Current user: {self._current_author_name()}"]

    def switch(self, branch_name: str) -> list[str]:
        """현재 브랜치를 지정한 브랜치로 변경한다."""
        self._require_initialized()

        if branch_name not in self.branches:
            raise AppError.unknown_branch(branch_name)

        self.current_branch = branch_name
        return [f"Switched to branch: {branch_name}"]

    def commit(self, message: str) -> CommitObject:
        """현재 HEAD를 부모로 하는 새 커밋을 만든다."""
        self._require_initialized()

        branch_name = self._current_branch_name()
        author = self._current_author_name()
        parent_hash = self.branches[branch_name]
        parents = (parent_hash,) if parent_hash is not None else ()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        commit_hash = self._create_commit_hash(message, author, timestamp, parents)
        commit = CommitObject(
            commit_hash=commit_hash,
            message=message,
            author=author,
            timestamp=timestamp,
            parents=parents,
            branch=branch_name,
        )

        self.commits[commit_hash] = commit
        self.branches[branch_name] = commit_hash

        for parent in parents:
            self.children[parent].append(commit_hash)

        self._index_commit(commit)
        return commit

    def log(self, sort_by: str | None = None) -> list[CommitObject]:
        """커밋 로그를 기본 위상 정렬 또는 지정 기준 정렬로 반환한다."""
        self._require_initialized()

        if sort_by is None:
            return self.sorted_commits()
        if sort_by == "date":
            return self._sort_commits_by_date()
        if sort_by == "author":
            return self._sort_commits_by_author()
        raise AppError.invalid_sort_option(sort_by)

    def ancestors(self, commit_hash: str) -> list[CommitObject]:
        """지정한 커밋에서 도달 가능한 모든 조상 커밋을 반환한다."""
        resolved_hash = self.resolve_commit_hash(commit_hash)
        visited: set[str] = set()
        result: list[CommitObject] = []
        ready = deque(self.commits[resolved_hash].parents)

        while ready:
            parent_hash = ready.popleft()
            if parent_hash in visited:
                continue
            visited.add(parent_hash)
            parent = self.commits[parent_hash]
            result.append(parent)
            for grand_parent_hash in parent.parents:
                ready.append(grand_parent_hash)

        return result

    def search_keyword(self, keyword: str) -> list[CommitObject]:
        """커밋 메시지 키워드 역색인으로 검색한다."""
        self._require_initialized()

        normalized_keyword = " ".join(keyword.lower().split())
        tokens = normalized_keyword.split()

        if not tokens:
            return []

        candidate_hashes = self.keyword_index.get(tokens[0], [])

        for token in tokens[1:]:
            token_hashes = self.keyword_index.get(token, [])
            if len(token_hashes) < len(candidate_hashes):
                candidate_hashes = token_hashes

        token_hash_sets: list[set[str]] = []
        for token in tokens:
            token_hash_sets.append(set(self.keyword_index.get(token, [])))

        matches: list[str] = []
        for commit_hash in candidate_hashes:
            if not self._is_in_every_index(commit_hash, token_hash_sets):
                continue

            commit = self.commits[commit_hash]
            normalized_message = " ".join(commit.message.lower().split())
            if normalized_keyword in normalized_message:
                matches.append(commit_hash)

        return self._commits_from_hashes(matches)

    def search_author(self, author: str) -> list[CommitObject]:
        """작성자 역색인으로 검색한다."""
        self._require_initialized()
        hashes = self.author_index.get(author, [])
        return self._commits_from_hashes(hashes)

    def shortest_path(self, start_hash: str, end_hash: str) -> list[str] | None:
        """부모-자식 연결을 무방향 간선으로 보고 최단 경로를 찾는다."""
        start = self.resolve_commit_hash(start_hash)
        end = self.resolve_commit_hash(end_hash)

        if start == end:
            return [start]

        # 목적지까지의 거리를 먼저 구하면 최단 경로에 포함될 이웃만 고를 수 있다.
        ready = deque([end])
        distance_to_end = {end: 0}

        while ready:
            current = ready.popleft()

            for neighbor in self._neighbors(current):
                if neighbor in distance_to_end:
                    continue
                distance_to_end[neighbor] = distance_to_end[current] + 1
                ready.append(neighbor)

        if start not in distance_to_end:
            return None

        path = [start]
        current = start

        while current != end:
            next_distance = distance_to_end[current] - 1
            next_commit: str | None = None

            for neighbor in self._neighbors(current):
                if distance_to_end.get(neighbor) != next_distance:
                    continue
                if next_commit is None or neighbor < next_commit:
                    next_commit = neighbor

            if next_commit is None:
                raise RuntimeError.shortest_path_reconstruction_failed()

            path.append(next_commit)
            current = next_commit

        return path

    def sorted_commits(self) -> list[CommitObject]:
        """모든 부모 커밋이 자식보다 먼저 나오도록 커밋을 반환한다."""
        self._require_initialized()
        indegree: dict[str, int] = {}

        for commit_hash, commit in self.commits.items():
            indegree[commit_hash] = len(commit.parents)

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
            raise RuntimeError.cyclic_commit_graph()

        return result

    def resolve_commit_hash(self, prefix: str) -> str:
        """전체 커밋 해시 또는 유일한 prefix를 실제 커밋 해시로 변환한다."""
        self._require_initialized()
        matches = [
            commit_hash
            for commit_hash in self.commits
            if commit_hash.startswith(prefix)
        ]

        if len(matches) > 1:
            raise RuntimeError.ambiguous_commit_hash(prefix)
        if len(matches) == 1:
            return matches[0]
        raise AppError.unknown_commit(prefix)

    def _require_initialized(self) -> None:
        """INIT 전 명령 실행을 막는다."""
        if self.current_branch is None or self.current_author is None:
            raise AppError.repository_not_initialized()

    def _head_hash(self) -> str | None:
        """현재 브랜치가 가리키는 HEAD 해시를 반환한다."""
        if self.current_branch is None:
            return None
        return self.branches[self.current_branch]

    def _current_branch_name(self) -> str:
        """초기화된 현재 브랜치 이름을 반환한다."""
        if self.current_branch is None:
            raise AppError.repository_not_initialized()
        return self.current_branch

    def _current_author_name(self) -> str:
        """초기화된 현재 작성자 이름을 반환한다."""
        if self.current_author is None:
            raise AppError.repository_not_initialized()
        return self.current_author

    def _create_commit_hash(
        self,
        message: str,
        author: str,
        timestamp: str,
        parents: tuple[str, ...],
    ) -> str:
        """커밋 데이터와 카운터를 사용해 세션 내 고유 커밋 해시를 만든다."""
        while True:
            source = "\n".join(
                [
                    "commit",
                    f"counter:{self._commit_counter}",
                    f"message:{message}",
                    f"author:{author}",
                    f"timestamp:{timestamp}",
                    f"parents:{','.join(parents)}",
                ]
            )
            self._commit_counter += 1
            commit_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()

            if commit_hash not in self._issued_hashes:
                self._issued_hashes.add(commit_hash)
                return commit_hash

    def _index_commit(self, commit: CommitObject) -> None:
        """작성자와 메시지 키워드 역색인을 갱신한다."""
        self.author_index[commit.author].append(commit.commit_hash)

        for token in commit.message.split():
            keyword = token.lower()
            if commit.commit_hash not in self.keyword_index[keyword]:
                self.keyword_index[keyword].append(commit.commit_hash)

    def _commits_from_hashes(self, hashes: list[str]) -> list[CommitObject]:
        """해시 목록을 CommitObject 목록으로 변환한다."""
        commits: list[CommitObject] = []
        for commit_hash in hashes:
            commits.append(self.commits[commit_hash])
        return commits

    def _is_in_every_index(
        self,
        commit_hash: str,
        indexes: list[set[str]],
    ) -> bool:
        """커밋 해시가 모든 키워드 인덱스에 포함되는지 확인한다."""
        for index in indexes:
            if commit_hash not in index:
                return False
        return True

    def _sort_commits_by_date(self) -> list[CommitObject]:
        """표준 정렬 API 없이 timestamp 기준으로 커밋을 정렬한다."""
        return self._insertion_sort(self._commit_values(), "timestamp")

    def _sort_commits_by_author(self) -> list[CommitObject]:
        """표준 정렬 API 없이 author 기준으로 커밋을 정렬한다."""
        return self._insertion_sort(self._commit_values(), "author")

    def _commit_values(self) -> list[CommitObject]:
        """커밋 해시맵의 값을 리스트로 복사한다."""
        values: list[CommitObject] = []
        for commit in self.commits.values():
            values.append(commit)
        return values

    def _insertion_sort(self, commits: list[CommitObject], field_name: str) -> list[CommitObject]:
        """간단한 삽입 정렬로 커밋 목록을 정렬한다."""
        for index in range(1, len(commits)):
            current = commits[index]
            position = index - 1

            while position >= 0 and self._comes_after(commits[position], current, field_name):
                commits[position + 1] = commits[position]
                position -= 1

            commits[position + 1] = current

        return commits

    def _comes_after(
        self,
        left: CommitObject,
        right: CommitObject,
        field_name: str,
    ) -> bool:
        """정렬 기준과 해시 tie-breaker로 두 커밋의 순서를 비교한다."""
        left_value = getattr(left, field_name)
        right_value = getattr(right, field_name)

        if left_value == right_value:
            return left.commit_hash > right.commit_hash
        return left_value > right_value

    def _neighbors(self, commit_hash: str) -> list[str]:
        """PATH 탐색에 사용할 부모와 자식 이웃 목록을 반환한다."""
        neighbors: list[str] = []
        commit = self.commits[commit_hash]

        for parent_hash in commit.parents:
            neighbors.append(parent_hash)
        for child_hash in self.children.get(commit_hash, []):
            neighbors.append(child_hash)

        return neighbors
