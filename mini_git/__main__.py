import sys

from .repl import MiniGitRepl


def main() -> None:
    MiniGitRepl(sys.stdin, sys.stdout).run()


if __name__ == "__main__":
    main()
