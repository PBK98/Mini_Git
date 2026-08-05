from __future__ import annotations

import sys
from typing import TextIO


class AppError(Exception):
    """REPL 명령이나 사용자에게 보이는 앱 규칙에서 발생하는 에러다."""

    def __init__(self, message: str, exit_code: int = 1) -> None:
        super().__init__(message)
        self.message = message
        self.exit_code = exit_code

    @classmethod
    def command_parse_failed(cls, message: str) -> AppError:
        """입력을 명령어 인자로 나눌 수 없을 때 사용한다."""
        return cls(f"could not parse command: {message}", exit_code=2)

    @classmethod
    def unknown_repl_command(cls, command: str) -> AppError:
        """REPL이 지원하지 않는 명령어를 입력했을 때 사용한다."""
        return cls(f"unknown command: {command}", exit_code=2)

    @classmethod
    def invalid_command_usage(cls, command_usage: str) -> AppError:
        """알려진 명령어의 인자가 부족하거나 잘못됐을 때 사용한다."""
        return cls(f"usage: {command_usage}", exit_code=2)

    @classmethod
    def repository_not_initialized(cls) -> AppError:
        """INIT 전 저장소 기능을 실행했을 때 사용한다."""
        return cls("repository is not initialized")

    @classmethod
    def branch_already_exists(cls, branch_name: str) -> AppError:
        """이미 존재하는 브랜치를 만들려고 할 때 사용한다."""
        return cls(f"branch already exists: {branch_name}")

    @classmethod
    def branch_requires_commit(cls) -> AppError:
        """첫 커밋 전에 브랜치를 만들려고 할 때 사용한다."""
        return cls("cannot create branch before first commit")

    @classmethod
    def unknown_branch(cls, branch_name: str) -> AppError:
        """존재하지 않는 브랜치를 참조했을 때 사용한다."""
        return cls(f"unknown branch: {branch_name}")

    @classmethod
    def unknown_commit(cls, commit_hash: str) -> AppError:
        """존재하지 않는 커밋 해시를 참조했을 때 사용한다."""
        return cls(f"unknown commit: {commit_hash}")

    @classmethod
    def invalid_sort_option(cls, sort_by: str) -> AppError:
        """지원하지 않는 로그 정렬 옵션을 입력했을 때 사용한다."""
        return cls(f"invalid sort option: {sort_by}", exit_code=2)

    def format_message(self) -> str:
        """AppError 출력 메시지를 만든다."""
        return f"app error: {self.message}"

    def handle(self, output_stream: TextIO) -> int:
        """앱 규칙 에러 메시지를 출력하고 종료 코드를 반환한다."""
        _write_message(self.format_message(), output_stream)
        return self.exit_code


class RuntimeError(Exception):
    """저장소 내부 상태나 알고리즘 실행 중 발생하는 에러다."""

    def __init__(self, message: str, exit_code: int = 1) -> None:
        super().__init__(message)
        self.message = message
        self.exit_code = exit_code

    @classmethod
    def ambiguous_commit_hash(cls, commit_hash: str) -> RuntimeError:
        """커밋 해시 prefix가 둘 이상의 커밋과 일치할 때 사용한다."""
        return cls(f"ambiguous commit hash: {commit_hash}")

    @classmethod
    def cyclic_commit_graph(cls) -> RuntimeError:
        """위상 정렬 중 커밋 그래프의 순환을 발견했을 때 사용한다."""
        return cls("commit graph has a cycle")

    @classmethod
    def shortest_path_reconstruction_failed(cls) -> RuntimeError:
        """계산된 거리 정보로 최단 경로를 복원할 수 없을 때 사용한다."""
        return cls("failed to reconstruct shortest path")

    @classmethod
    def unexpected_exception(cls, error: BaseException) -> RuntimeError:
        """미리 분류하지 못한 예외가 발생했을 때 사용한다."""
        error_name = type(error).__name__
        message = str(error) or error_name
        return cls(f"unexpected {error_name}: {message}")

    def format_message(self) -> str:
        """RuntimeError 출력 메시지를 만든다."""
        return f"runtime error: {self.message}"

    def handle(self, output_stream: TextIO) -> int:
        """런타임 에러 메시지를 출력하고 종료 코드를 반환한다."""
        _write_message(self.format_message(), output_stream)
        return self.exit_code


class ReplExit(Exception):
    """REPL 입력 흐름이 종료될 때 발생하는 제어 흐름이다."""

    def __init__(self, message: str, exit_code: int) -> None:
        super().__init__(message)
        self.message = message
        self.exit_code = exit_code

    @classmethod
    def keyboard_interrupt(cls) -> ReplExit:
        """사용자가 Ctrl-C로 REPL 실행을 중단했을 때 사용한다."""
        return cls("interrupted by user", exit_code=130)

    @classmethod
    def eof(cls) -> ReplExit:
        """입력 스트림이 EOF에 도달했을 때 사용한다."""
        return cls("unexpected end of input", exit_code=1)

    def format_message(self) -> str:
        """ReplExit 출력 메시지를 만든다."""
        return f"repl exit: {self.message}"

    def handle(self, output_stream: TextIO) -> int:
        """REPL 종료 메시지를 출력하고 종료 코드를 반환한다."""
        _write_message(self.format_message(), output_stream)
        return self.exit_code


class EnvError(Exception):
    """실행 환경 때문에 발생하는 에러다."""

    def __init__(self, message: str, exit_code: int = 1) -> None:
        super().__init__(message)
        self.message = message
        self.exit_code = exit_code

    @classmethod
    def io_failed(cls, error: OSError) -> EnvError:
        """입력 또는 출력 스트림에서 I/O 에러가 발생했을 때 사용한다."""
        return cls(f"io failed: {error}")

    def format_message(self) -> str:
        """EnvError 출력 메시지를 만든다."""
        return f"env error: {self.message}"

    def handle(self, output_stream: TextIO) -> int:
        """환경 에러 메시지를 출력하고 종료 코드를 반환한다."""
        _write_message(self.format_message(), output_stream)
        return self.exit_code


def _write_message(message: str, output_stream: TextIO) -> None:
    """기본 출력이 실패하면 stderr로 한 번 더 출력한다."""
    try:
        print(message, file=output_stream)
    except BaseException:
        try:
            print(message, file=sys.stderr)
        except BaseException:
            pass
