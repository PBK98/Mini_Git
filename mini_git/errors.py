from __future__ import annotations

from typing import TextIO


class AppError(Exception):
    """REPL 명령이나 사용자에게 보이는 앱 규칙에서 발생하는 에러다."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    @classmethod
    def command_parse_failed(cls, message: str) -> AppError:
        """입력을 명령어 인자로 나눌 수 없을 때 사용한다."""
        return cls(f"could not parse command: {message}")

    @classmethod
    def unknown_repl_command(cls, command: str) -> AppError:
        """REPL이 지원하지 않는 명령어를 입력했을 때 사용한다."""
        return cls(f"unknown command: {command}")

    @classmethod
    def invalid_command_usage(cls, command_usage: str) -> AppError:
        """알려진 명령어의 인자가 부족하거나 잘못됐을 때 사용한다."""
        return cls(f"usage: {command_usage}")

    @classmethod
    def working_tree_path_not_found(cls, target: str) -> AppError:
        """작업 트리에 없는 경로를 참조했을 때 사용한다."""
        return cls(f"not found: {target}")

    @classmethod
    def object_hash_not_found(cls, object_hash: str) -> AppError:
        """존재하지 않는 객체 해시나 prefix를 참조했을 때 사용한다."""
        return cls(f"not found: {object_hash}")

    @classmethod
    def empty_working_tree_commit(cls) -> AppError:
        """작업 트리가 비어 있는데 커밋하려고 할 때 사용한다."""
        return cls("nothing to commit")

    def format_message(self) -> str:
        return f"app error: {self.message}"


class RuntimeError(Exception):
    """저장소나 객체 저장소의 내부 상태에서 발생하는 에러다."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    @classmethod
    def ambiguous_object_hash(cls, object_hash: str) -> RuntimeError:
        """해시 prefix가 둘 이상의 저장 객체와 일치할 때 사용한다."""
        return cls(f"ambiguous object hash: {object_hash}")

    @classmethod
    def duplicate_object_hash(cls, object_hash: str) -> RuntimeError:
        """생성된 해시가 이미 객체 저장소에 있을 때 사용한다."""
        return cls(f"duplicated object hash: {object_hash}")

    @classmethod
    def stored_object_not_found(cls, object_hash: str) -> RuntimeError:
        """내부 조회에서 없는 저장 객체를 불러오려고 할 때 사용한다."""
        return cls(f"object not found: {object_hash}")

    @classmethod
    def cyclic_commit_graph(cls) -> RuntimeError:
        """위상 정렬 중 커밋 그래프의 순환을 발견했을 때 사용한다."""
        return cls("commit graph has a cycle")

    def format_message(self) -> str:
        return f"runtime error: {self.message}"


class EnvError(Exception):
    """실행 환경 때문에 발생하는 에러다."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    @classmethod
    def keyboard_interrupt(cls) -> EnvError:
        """사용자가 Ctrl-C로 REPL을 중단했을 때 사용한다."""
        return cls("interrupted by user")

    def format_message(self) -> str:
        return f"env error: {self.message}"


HandledError = AppError | RuntimeError | EnvError


class HandlerError:
    """처리 가능한 모든 에러의 단일 출력 경계다."""

    def __call__(self, error: HandledError, output_stream: TextIO) -> None:
        print(error.format_message(), file=output_stream)


handler_error = HandlerError()
