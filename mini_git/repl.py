from __future__ import annotations

import shlex
from typing import TextIO

from .errors import (
    AppError,
    EnvError,
    RuntimeError,
    handler_error,
)
from .objects import Blob, CommitObject, Directory
from .repository import MiniGitRepository


PROMPT = "mini-git> "


class MiniGitRepl:
    def __init__(
        self,
        input_stream: TextIO,
        output_stream: TextIO,
    ) -> None:
        self.input_stream = input_stream
        self.output_stream = output_stream
        self.repo = MiniGitRepository()
        self.working_tree: dict[str, str] = {}
        self._running = True

    def run(self) -> None:
        self._write("Mini Git REPL. Type 'help' for commands.")

        while self._running:
            try:
                self._write_prompt()
                line = self.input_stream.readline()
            except KeyboardInterrupt:
                self._write("")
                handler_error(EnvError.keyboard_interrupt(), self.output_stream)
                self._running = False
                break

            if line == "":
                self._write("")
                break

            try:
                self.execute(line.strip())
            except (AppError, RuntimeError, EnvError) as error:
                handler_error(error, self.output_stream)

    def execute(self, line: str) -> None:
        if not line:
            return

        try:
            args = shlex.split(line)
        except ValueError as error:
            raise AppError.command_parse_failed(str(error)) from error

        command = args[0]
        command_args = args[1:]

        if command in {"exit", "quit"}:
            self._running = False
            self._write("bye")
        elif command == "help":
            self._help()
        elif command == "add":
            self._add(command_args)
        elif command == "remove":
            self._remove(command_args)
        elif command == "status":
            self._status()
        elif command == "commit":
            self._commit(command_args)
        elif command == "log":
            self._log()
        elif command == "objects":
            self._objects()
        elif command == "show":
            self._show(command_args)
        else:
            raise AppError.unknown_repl_command(command)

    def _help(self) -> None:
        self._write(
            "\n".join(
                [
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
            )
        )

    def _add(self, args: list[str]) -> None:
        if len(args) < 2:
            raise AppError.invalid_command_usage("add <path> <content>")

        path = args[0]
        content = " ".join(args[1:])
        self.working_tree[path] = content
        self._write(f"added {path}")

    def _remove(self, args: list[str]) -> None:
        if len(args) != 1:
            raise AppError.invalid_command_usage("remove <path>")

        path = args[0]

        if path not in self.working_tree:
            raise AppError.working_tree_path_not_found(path)

        del self.working_tree[path]
        self._write(f"removed {path}")

    def _status(self) -> None:
        head = self.repo.head_hash[:8] if self.repo.head_hash is not None else "None"
        self._write(f"HEAD: {head}")

        if not self.working_tree:
            self._write("working tree is empty")
            return

        self._write("working tree:")
        for path in sorted(self.working_tree):
            self._write(f"- {path}")

    def _commit(self, args: list[str]) -> None:
        if not args:
            raise AppError.invalid_command_usage("commit <message>")

        if not self.working_tree:
            raise AppError.empty_working_tree_commit()

        message = " ".join(args)
        commit_hash = self.repo.commit(dict(self.working_tree), message)
        self._write(f"committed {commit_hash}")

    def _log(self) -> None:
        commits = self.repo.sorted_commits()

        if not commits:
            self._write("no commits")
            return

        for commit in commits:
            parent = commit.parent_hash[:8] if commit.parent_hash is not None else "None"
            self._write(
                f"{commit.commit_hash[:8]} parent={parent} root={commit.root_hash[:8]} {commit.message}"
            )

    def _objects(self) -> None:
        objects = self.repo.object_store.items()

        if not objects:
            self._write("no objects")
            return

        for object_hash, obj in objects:
            object_type = getattr(obj, "object_type", "unknown")
            self._write(f"{object_hash[:8]} {object_type}")

    def _show(self, args: list[str]) -> None:
        if len(args) != 1:
            raise AppError.invalid_command_usage("show <hash>")

        object_hash = self._resolve_hash(args[0])

        if object_hash is None:
            raise AppError.object_hash_not_found(args[0])

        obj = self.repo.object_store.get(object_hash)

        if isinstance(obj, Blob):
            self._write("type: blob")
            self._write(obj.content)
        elif isinstance(obj, Directory):
            self._write("type: directory")
            for name, child_hash in sorted(obj.entries.items()):
                self._write(f"{name} -> {child_hash}")
        elif isinstance(obj, CommitObject):
            parent = obj.parent_hash if obj.parent_hash is not None else "None"
            self._write("type: commit")
            self._write(f"hash: {obj.commit_hash}")
            self._write(f"parent: {parent}")
            self._write(f"root: {obj.root_hash}")
            self._write(f"message: {obj.message}")
        else:
            self._write(obj.serialize())

    def _resolve_hash(self, prefix: str) -> str | None:
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

    def _write(self, value: str) -> None:
        print(value, file=self.output_stream)

    def _write_prompt(self) -> None:
        print(PROMPT, end="", file=self.output_stream, flush=True)
