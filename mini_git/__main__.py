from .repository import MiniGitRepository


def main() -> None:
    repo = MiniGitRepository()

    first = repo.commit(
        {"README.md": "Mini Git project\n"},
        "first commit",
    )
    second = repo.commit(
        {
            "README.md": "Mini Git project\n",
            "app.py": "print('hello')\n",
        },
        "add app.py",
    )

    print(f"first commit: {first}")
    print(f"second commit: {second}")
    print()
    print("topological order:")

    for commit in repo.sorted_commits():
        parent = commit.parent_hash or "None"
        print(f"- {commit.commit_hash[:8]} parent={parent[:8]} message={commit.message}")


if __name__ == "__main__":
    main()
