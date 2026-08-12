from __future__ import annotations

import shlex

from .errors import AppError
from .objects import CommitObject
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

    def execute(self, line: str) -> MiniGitResult:
        """한 줄 명령을 실행하고 출력할 문자열 목록을 반환한다."""
        if not line:
            return MiniGitResult()

        try:
            args = shlex.split(line)
        except ValueError as error:
            raise AppError.command_parse_failed(str(error)) from error

        command = args[0].lower()
        command_args = args[1:]

        if command in {"exit", "quit"}:
            if command_args:
                raise AppError.invalid_command_usage(command)
            return MiniGitResult(["bye"], should_exit=True)
        if command == "help":
            if command_args:
                raise AppError.invalid_command_usage("help")
            return MiniGitResult(self._help())
        if command == "init":
            return MiniGitResult(self._init(command_args))
        if command == "whoiam":
            return MiniGitResult(self._whoiam(command_args))
        if command == "branch":
            return MiniGitResult(self._branch(command_args))
        if command == "switch":
            return MiniGitResult(self._switch(command_args))
        if command == "commit":
            return MiniGitResult(self._commit(command_args))
        if command == "log":
            return MiniGitResult(self._log(command_args))
        if command == "path":
            return MiniGitResult(self._path(command_args))
        if command == "ancestors":
            return MiniGitResult(self._ancestors(command_args))
        if command == "search":
            return MiniGitResult(self._search(command_args))

        raise AppError.unknown_repl_command(args[0])

    def _help(self) -> list[str]:
        """지원하는 MiniGit 명령어를 반환한다."""
        return [
            "commands:",
            "  init <user_name>              initialize repository",
            "  whoiam                        show current user",
            "  branch                        list branches and show current branch",
            "  branch <branch_name>          create branch at current HEAD",
            "  switch <branch_name>          switch current branch",
            "  commit <message>              create commit from current HEAD",
            "  log                           show commits in topological order",
            "  log --sort-by=date|author     show sorted commits",
            "  path <commit1> <commit2>      show shortest path",
            "  ancestors <commit_hash>       show ancestor commits",
            "  search <keyword>              search commits by message keyword",
            "  search --author=<name>        search commits by author",
            "  help                          show this help",
            "  exit                          leave the REPL",
        ]

    def _init(self, args: list[str]) -> list[str]:
        """저장소를 초기화한다."""
        if len(args) != 1 or not args[0].strip():
            raise AppError.invalid_command_usage("init <user_name>")
        return self.repo.init(args[0])

    def _whoiam(self, args: list[str]) -> list[str]:
        """현재 커밋 작성자를 출력한다."""
        if args:
            raise AppError.invalid_command_usage("whoiam")
        return self.repo.current_user()

    def _branch(self, args: list[str]) -> list[str]:
        """브랜치 목록을 출력하거나 새 브랜치를 생성한다."""
        if not args:
            return self.repo.list_branches()
        if len(args) != 1 or not args[0].strip():
            raise AppError.invalid_command_usage("branch [<branch_name>]")
        return self.repo.create_branch(args[0])

    def _switch(self, args: list[str]) -> list[str]:
        """현재 브랜치를 변경한다."""
        if len(args) != 1 or not args[0].strip():
            raise AppError.invalid_command_usage("switch <branch_name>")
        return self.repo.switch(args[0])

    def _commit(self, args: list[str]) -> list[str]:
        """커밋을 생성한다."""
        message = " ".join(args)
        if not message.strip():
            raise AppError.invalid_command_usage("commit <message>")

        commit = self.repo.commit(message)
        return [f"[{commit.branch} {self._short_hash(commit.commit_hash)}] {commit.message}"]

    def _log(self, args: list[str]) -> list[str]:
        """커밋 로그를 출력 형식으로 변환한다."""
        sort_by = self._parse_log_sort_option(args)
        commits = self.repo.log(sort_by)
        return self._format_commit_list(commits, include_branch=sort_by is None)

    def _path(self, args: list[str]) -> list[str]:
        """두 커밋 사이의 최단 경로를 출력한다."""
        if len(args) != 2 or not args[0].strip() or not args[1].strip():
            raise AppError.invalid_command_usage("path <commit1> <commit2>")

        path = self.repo.shortest_path(args[0], args[1])
        if path is None:
            return ["No path"]

        return [f"Path: {self._format_path(path)}"]

    def _ancestors(self, args: list[str]) -> list[str]:
        """특정 커밋의 모든 조상을 출력한다."""
        if len(args) != 1 or not args[0].strip():
            raise AppError.invalid_command_usage("ancestors <commit_hash>")

        ancestors = self.repo.ancestors(args[0])

        if not ancestors:
            return ["No ancestors"]

        lines = ["Ancestors:"]
        for commit in ancestors:
            lines.append(f"- {self._short_hash(commit.commit_hash)}: {commit.message}")
        return lines

    def _search(self, args: list[str]) -> list[str]:
        """키워드 또는 작성자 기준으로 커밋을 검색한다."""
        if len(args) != 1 or not args[0].strip():
            raise AppError.invalid_command_usage("search <keyword> | search --author=<name>")

        if args[0].startswith("--author="):
            author = args[0][len("--author="):]
            if not author.strip():
                raise AppError.invalid_command_usage("search --author=<name>")
            commits = self.repo.search_author(author)
        elif args[0].startswith("--"):
            raise AppError.invalid_command_usage(
                "search <keyword> | search --author=<name>"
            )
        else:
            commits = self.repo.search_keyword(args[0])

        if not commits:
            return ["Found 0 commits:"]

        lines = [f"Found {len(commits)} commit:" if len(commits) == 1 else f"Found {len(commits)} commits:"]
        for commit in commits:
            lines.append(f"- {self._short_hash(commit.commit_hash)}: {commit.message}")
        return lines

    def _parse_log_sort_option(self, args: list[str]) -> str | None:
        """LOG 명령의 정렬 옵션을 해석한다."""
        if not args:
            return None
        if len(args) != 1 or not args[0].startswith("--sort-by="):
            raise AppError.invalid_command_usage("log [--sort-by=date|author]")

        sort_by = args[0][len("--sort-by="):]

        if sort_by not in {"date", "author"}:
            raise AppError.invalid_sort_option(sort_by)

        return sort_by

    def _format_commit_list(
        self,
        commits: list[CommitObject],
        include_branch: bool,
    ) -> list[str]:
        """커밋 목록을 LOG 출력 문자열로 변환한다."""
        if not commits:
            return ["no commits"]

        lines: list[str] = []

        for commit in commits:
            branch_text = f" [{commit.branch}]" if include_branch else ""
            lines.append(
                f"commit {self._short_hash(commit.commit_hash)} "
                f"({commit.author}, {commit.timestamp}){branch_text}"
            )
            lines.append(commit.message)

        return lines

    def _format_path(self, path: list[str]) -> str:
        """경로 해시 목록을 짧은 해시 문자열로 변환한다."""
        short_path: list[str] = []

        for commit_hash in path:
            short_path.append(self._short_hash(commit_hash))

        return " -> ".join(short_path)

    def _short_hash(self, commit_hash: str) -> str:
        """화면 출력에 사용할 짧은 커밋 해시를 만든다."""
        return commit_hash[:6]
