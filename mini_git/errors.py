from __future__ import annotations

from typing import TextIO


class AppError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    @classmethod
    def command_parse_failed(cls, message: str) -> AppError:
        return cls(f"could not parse command: {message}")

    @classmethod
    def unknown_repl_command(cls, command: str) -> AppError:
        return cls(f"unknown command: {command}")

    @classmethod
    def invalid_command_usage(cls, command_usage: str) -> AppError:
        return cls(f"usage: {command_usage}")

    @classmethod
    def working_tree_path_not_found(cls, target: str) -> AppError:
        return cls(f"not found: {target}")

    @classmethod
    def object_hash_not_found(cls, object_hash: str) -> AppError:
        return cls(f"not found: {object_hash}")

    @classmethod
    def empty_working_tree_commit(cls) -> AppError:
        return cls("nothing to commit")

    def format_message(self) -> str:
        return f"app error: {self.message}"


class RuntimeError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    @classmethod
    def ambiguous_object_hash(cls, object_hash: str) -> RuntimeError:
        return cls(f"ambiguous object hash: {object_hash}")

    @classmethod
    def duplicate_object_hash(cls, object_hash: str) -> RuntimeError:
        return cls(f"duplicated object hash: {object_hash}")

    @classmethod
    def stored_object_not_found(cls, object_hash: str) -> RuntimeError:
        return cls(f"object not found: {object_hash}")

    @classmethod
    def cyclic_commit_graph(cls) -> RuntimeError:
        return cls("commit graph has a cycle")

    def format_message(self) -> str:
        return f"runtime error: {self.message}"


class EnvError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    @classmethod
    def keyboard_interrupt(cls) -> EnvError:
        return cls("interrupted by user")

    def format_message(self) -> str:
        return f"env error: {self.message}"


HandledError = AppError | RuntimeError | EnvError


class HandlerError:
    def __call__(self, error: HandledError, output_stream: TextIO) -> None:
        print(error.format_message(), file=output_stream)


handler_error = HandlerError()
