import sys

from .repl import MiniGitRepl


def main() -> None:
    """`python -m mini_git` 실행 시 호출되는 모듈 진입점이다."""
    MiniGitRepl(sys.stdin, sys.stdout).run()


if __name__ == "__main__":
    main()
