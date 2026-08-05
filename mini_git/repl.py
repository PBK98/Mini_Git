from __future__ import annotations

from typing import TextIO

from .errors import AppError, EnvError, ReplExit, RuntimeError
from .mini_git import MiniGit


PROMPT = "mini-git> "


class MiniGitRepl:
    """입력 스트림과 출력 스트림을 연결하는 REPL 환경이다."""

    def __init__(
        self,
        input_stream: TextIO,
        output_stream: TextIO,
    ) -> None:
        self.input_stream = input_stream
        self.output_stream = output_stream
        self.app = MiniGit()
        self._running = True

    def run(self) -> int:
        """EOF, Ctrl-C, exit, quit가 나올 때까지 명령을 읽는다."""
        self._write("Mini Git REPL. Type 'help' for commands.")
        exit_code = 0

        while self._running:
            try:
                self._write_prompt()
                line = self.input_stream.readline()

                if line == "":
                    # readline()은 Ctrl-D/EOF를 예외가 아니라 빈 문자열로 알려준다.
                    raise ReplExit.eof()

                result = self.app.execute(line.strip())
                self._write_lines(result.lines)
                self._running = not result.should_exit
            except (AppError, RuntimeError) as error:
                exit_code = error.handle(self.output_stream)
            except ReplExit as error:
                self._write("")
                exit_code = error.handle(self.output_stream)
                self._running = False
            except KeyboardInterrupt:
                self._write("")
                exit_code = ReplExit.keyboard_interrupt().handle(self.output_stream)
                self._running = False
            except EOFError:
                self._write("")
                exit_code = ReplExit.eof().handle(self.output_stream)
                self._running = False
            except OSError as error:
                exit_code = EnvError.io_failed(error).handle(self.output_stream)
                self._running = False
            except EnvError as error:
                exit_code = error.handle(self.output_stream)
                self._running = False
            except BaseException as error:
                exit_code = RuntimeError.unexpected_exception(error).handle(
                    self.output_stream
                )
                self._running = False

        return exit_code

    def _write(self, value: str) -> None:
        """설정된 출력 스트림에 한 줄을 쓴다."""
        print(value, file=self.output_stream)

    def _write_lines(self, lines: list[str]) -> None:
        """명령 실행 결과를 REPL 출력 스트림에 순서대로 쓴다."""
        for line in lines:
            self._write(line)

    def _write_prompt(self) -> None:
        """줄바꿈 없이 프롬프트를 출력한다."""
        print(PROMPT, end="", file=self.output_stream, flush=True)
