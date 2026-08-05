import sys

from .errors import EnvError, ReplExit, RuntimeError
from .repl import MiniGitRepl


def main() -> None:
    """`python -m mini_git` 실행 시 호출되는 모듈 진입점이다."""
    try:
        exit_code = MiniGitRepl(sys.stdin, sys.stdout).run()
    except KeyboardInterrupt:
        exit_code = ReplExit.keyboard_interrupt().handle(sys.stdout)
    except EOFError:
        exit_code = ReplExit.eof().handle(sys.stdout)
    except OSError as error:
        exit_code = EnvError.io_failed(error).handle(sys.stdout)
    except BaseException as error:
        exit_code = RuntimeError.unexpected_exception(error).handle(sys.stdout)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
