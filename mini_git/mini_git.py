from __future__ import annotations

import shlex

from .errors import AppError, RuntimeError
from .objects import Blob, CommitObject, Directory
from .repository import MiniGitRepository


class MiniGitResult:
    """명령 실행 결과와 REPL 종료 여부를 함께 담는다."""

    def __init__(self, lines: list[str] | None = None, should_exit: bool = False) -> None:
        self.lines = lines or []
        self.should_exit = should_exit


class MiniGit:
    """MiniGit 명령을 파싱하고 실제 저장소 기능을 실행한다."""

    def __init__(self) -> None:
        self.repo = MiniGitRepository()
        self.working_tree: dict[str, str] = {}

    def execute(self, line: str) -> MiniGitResult:
        """한 줄 명령을 실행하고 출력할 문자열 목록을 반환한다."""
        if not line:
            return MiniGitResult()

        try:
            args = shlex.split(line)
        except ValueError as error:
            raise AppError.command_parse_failed(str(error)) from error

        command = args[0]
        command_args = args[1:]

        if command in {"exit", "quit"}:
            return MiniGitResult(["bye"], should_exit=True)
        if command == "help":
            return MiniGitResult(self._help())
        if command == "add":
            return MiniGitResult(self._add(command_args))
        if command == "remove":
            return MiniGitResult(self._remove(command_args))
        if command == "status":
            return MiniGitResult(self._status())
        if command == "commit":
            return MiniGitResult(self._commit(command_args))
        if command == "log":
            return MiniGitResult(self._log())
        if command == "objects":
            return MiniGitResult(self._objects())
        if command == "show":
            return MiniGitResult(self._show(command_args))

        raise AppError.unknown_repl_command(command)

    def _help(self) -> list[str]:
        """지원하는 MiniGit 명령어를 반환한다."""
        return [
            "commands:",
            "  add <path> <content>      add or update a file in the working tree",
            "  remove <path>             remove a file from the working tree",
            "  status                    show working tree files and HEAD",
            "  commit <message>          create a commit from the working tree",
            "  log                       show commits in topological order",
            "  objects                   show stored object hashes",
            "  show <hash>               show one stored object",
            "  help                      show this help",
            "  exit                      leave the REPL",
        ]

    def _add(self, args: list[str]) -> list[str]:
        """메모리 작업 트리에 파일 하나를 추가하거나 수정한다."""
        if len(args) < 2:
            raise AppError.invalid_command_usage("add <path> <content>")

        path = args[0]
        content = " ".join(args[1:])
        self.working_tree[path] = content
        return [f"added {path}"]

    def _remove(self, args: list[str]) -> list[str]:
        """작업 트리에서 파일 경로 하나를 제거한다."""
        if len(args) != 1:
            raise AppError.invalid_command_usage("remove <path>")

        path = args[0]

        if path not in self.working_tree:
            raise AppError.working_tree_path_not_found(path)

        del self.working_tree[path]
        return [f"removed {path}"]

    def _status(self) -> list[str]:
        """HEAD와 현재 작업 트리에 있는 파일 목록을 반환한다."""
        head = self.repo.head_hash[:8] if self.repo.head_hash is not None else "None"
        lines = [f"HEAD: {head}"]

        if not self.working_tree:
            lines.append("working tree is empty")
            return lines

        lines.append("working tree:")
        for path in sorted(self.working_tree):
            lines.append(f"- {path}")

        return lines

    def _commit(self, args: list[str]) -> list[str]:
        """현재 작업 트리 스냅샷으로 커밋을 만든다."""
        if not args:
            raise AppError.invalid_command_usage("commit <message>")

        if not self.working_tree:
            raise AppError.empty_working_tree_commit()

        message = " ".join(args)
        commit_hash = self.repo.commit(dict(self.working_tree), message)
        return [f"committed {commit_hash}"]

    def _log(self) -> list[str]:
        """부모가 자식보다 먼저 나오는 위상 정렬 순서로 커밋을 반환한다."""
        commits = self.repo.sorted_commits()

        if not commits:
            return ["no commits"]

        lines: list[str] = []
        for commit in commits:
            parent = commit.parent_hash[:8] if commit.parent_hash is not None else "None"
            lines.append(
                f"{commit.commit_hash[:8]} parent={parent} root={commit.root_hash[:8]} {commit.message}"
            )
        return lines

    def _objects(self) -> list[str]:
        """저장된 객체 해시와 객체 타입을 반환한다."""
        objects = self.repo.object_store.items()

        if not objects:
            return ["no objects"]

        lines: list[str] = []
        for object_hash, obj in objects:
            object_type = getattr(obj, "object_type", "unknown")
            lines.append(f"{object_hash[:8]} {object_type}")
        return lines

    def _show(self, args: list[str]) -> list[str]:
        """전체 해시 또는 유일한 해시 prefix로 객체 하나를 반환한다."""
        if len(args) != 1:
            raise AppError.invalid_command_usage("show <hash>")

        object_hash = self._resolve_hash(args[0])

        if object_hash is None:
            raise AppError.object_hash_not_found(args[0])

        obj = self.repo.object_store.get(object_hash)

        if isinstance(obj, Blob):
            return ["type: blob", obj.content]
        if isinstance(obj, Directory):
            lines = ["type: directory"]
            for name, child_hash in sorted(obj.entries.items()):
                lines.append(f"{name} -> {child_hash}")
            return lines
        if isinstance(obj, CommitObject):
            parent = obj.parent_hash if obj.parent_hash is not None else "None"
            return [
                "type: commit",
                f"hash: {obj.commit_hash}",
                f"parent: {parent}",
                f"root: {obj.root_hash}",
                f"message: {obj.message}",
            ]

        return [obj.serialize()]

    def _resolve_hash(self, prefix: str) -> str | None:
        """show 명령에서 전체 해시와 유일한 prefix를 모두 허용한다."""
        matches = [
            object_hash
            for object_hash, _ in self.repo.object_store.items()
            if object_hash.startswith(prefix)
        ]

        if len(matches) > 1:
            raise RuntimeError.ambiguous_object_hash(prefix)

        if len(matches) == 1:
            return matches[0]

        return prefix if self.repo.object_store.contains(prefix) else None
