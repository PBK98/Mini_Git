import sys

from .errors import handler_error
from .repl import MiniGitRepl


def main() -> None:
    """`python -m mini_git` 실행 시 호출되는 모듈 진입점이다."""
    try:
        MiniGitRepl(sys.stdin, sys.stdout).run()
    except BaseException as error:
        handler_error(error, sys.stdout)


if __name__ == "__main__":
    main()
