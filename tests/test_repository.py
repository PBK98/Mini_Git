import unittest
from io import StringIO
from unittest.mock import patch

from mini_git import CommitObject, MiniGit, MiniGitRepository
from mini_git.errors import (
    AppError,
    EnvError,
    ReplExit,
    RuntimeError,
)
from mini_git.repl import MiniGitRepl


def make_commit(
    commit_hash: str,
    parents: tuple[str, ...] = (),
    author: str = "Alice",
    timestamp: str = "2026-01-01 00:00:00",
) -> CommitObject:
    """그래프 알고리즘 테스트에 사용할 커밋 객체를 만든다."""
    return CommitObject(
        commit_hash=commit_hash,
        message=commit_hash,
        author=author,
        timestamp=timestamp,
        parents=parents,
        branch="main",
    )


class MiniGitRepositoryTest(unittest.TestCase):
    def test_commit_hashes_are_unique_in_session(self):
        repo = MiniGitRepository()
        repo.init("Alice")

        first_hash = repo.commit("same message").commit_hash
        second_hash = repo.commit("same message").commit_hash

        self.assertNotEqual(first_hash, second_hash)

    @patch("mini_git.repository.datetime")
    def test_commit_hashes_remain_unique_after_reinitialization(self, datetime_mock):
        datetime_mock.now.return_value.strftime.return_value = "2026-01-01 00:00:00"
        repo = MiniGitRepository()
        repo.init("Alice")
        first_hash = repo.commit("same message").commit_hash

        repo.init("Alice")
        second_hash = repo.commit("same message").commit_hash

        self.assertNotEqual(first_hash, second_hash)
        self.assertEqual(len(repo.commits), 2)

    def test_reinitialization_changes_author_without_deleting_repository_data(self):
        repo = MiniGitRepository()
        repo.init("Alice")
        alice_commit = repo.commit("Alice commit")
        repo.create_branch("feature")
        repo.switch("feature")

        result = repo.init("Bob")
        bob_commit = repo.commit("Bob commit")

        self.assertEqual(
            result,
            [
                "Repository already initialized.",
                "Current branch: feature",
                "Current user: Bob",
            ],
        )
        self.assertIn(alice_commit.commit_hash, repo.commits)
        self.assertEqual(bob_commit.author, "Bob")
        self.assertEqual(bob_commit.parents, (alice_commit.commit_hash,))
        self.assertEqual(repo.current_branch, "feature")
        self.assertEqual(repo.branches["main"], alice_commit.commit_hash)

    def test_current_user_returns_the_latest_initialized_user(self):
        repo = MiniGitRepository()
        repo.init("Alice")
        repo.init("Bob")

        self.assertEqual(repo.current_user(), ["Current user: Bob"])

    def test_topological_sort_returns_parent_before_child(self):
        repo = MiniGitRepository()
        repo.init("Alice")

        first_hash = repo.commit("first").commit_hash
        second_hash = repo.commit("second").commit_hash

        sorted_hashes = [commit.commit_hash for commit in repo.sorted_commits()]

        self.assertLess(sorted_hashes.index(first_hash), sorted_hashes.index(second_hash))

    def test_shortest_path_does_not_choose_a_longer_lexicographical_path(self):
        repo = MiniGitRepository()
        repo.init("Alice")
        repo.commits = {
            "s": make_commit("s"),
            "a": make_commit("a", ("s",)),
            "z": make_commit("z", ("s", "a")),
        }
        repo.children["s"] = ["z", "a"]
        repo.children["a"] = ["z"]

        path = repo.shortest_path("s", "z")

        self.assertEqual(path, ["s", "z"])

    def test_shortest_path_chooses_lexicographically_smallest_equal_path(self):
        repo = MiniGitRepository()
        repo.init("Alice")
        repo.commits = {
            "s": make_commit("s"),
            "b": make_commit("b", ("s",)),
            "c": make_commit("c", ("s",)),
            "z": make_commit("z", ("b", "c")),
        }
        repo.children["s"] = ["c", "b"]
        repo.children["b"] = ["z"]
        repo.children["c"] = ["z"]

        path = repo.shortest_path("s", "z")

        self.assertEqual(path, ["s", "b", "z"])

    def test_shortest_path_returns_none_for_disconnected_commits(self):
        repo = MiniGitRepository()
        repo.init("Alice")
        repo.commits = {
            "left": make_commit("left"),
            "right": make_commit("right"),
        }

        self.assertIsNone(repo.shortest_path("left", "right"))

    def test_ancestors_returns_every_reachable_parent_once(self):
        repo = MiniGitRepository()
        repo.init("Alice")
        repo.commits = {
            "root": make_commit("root"),
            "left": make_commit("left", ("root",)),
            "right": make_commit("right", ("root",)),
            "merge": make_commit("merge", ("left", "right")),
        }

        ancestors = repo.ancestors("merge")

        self.assertEqual(
            {commit.commit_hash for commit in ancestors},
            {"root", "left", "right"},
        )

    def test_log_sort_options_use_the_requested_fields(self):
        repo = MiniGitRepository()
        repo.init("Alice")
        first = make_commit("first", author="Charlie", timestamp="2026-01-02 00:00:00")
        second = make_commit("second", author="Alice", timestamp="2026-01-03 00:00:00")
        third = make_commit("third", author="Bob", timestamp="2026-01-01 00:00:00")
        repo.commits = {
            first.commit_hash: first,
            second.commit_hash: second,
            third.commit_hash: third,
        }

        by_date = [commit.commit_hash for commit in repo.log("date")]
        by_author = [commit.commit_hash for commit in repo.log("author")]

        self.assertEqual(by_date, ["third", "first", "second"])
        self.assertEqual(by_author, ["second", "third", "first"])

    def test_commit_parents_are_immutable(self):
        repo = MiniGitRepository()
        repo.init("Alice")

        commit = repo.commit("first")

        self.assertIsInstance(commit.parents, tuple)


class MiniGitCommandTest(unittest.TestCase):
    def test_minigit_executes_init_commit_branch_switch_and_log(self):
        app = MiniGit()

        init_result = app.execute("init Alice")
        commit_result = app.execute("commit first")
        branch_result = app.execute("branch feature")
        switch_result = app.execute("switch feature")
        log_result = app.execute("log")

        self.assertIn("Initialized repository.", init_result.lines)
        self.assertEqual(len(commit_result.lines), 1)
        self.assertIn("[main ", commit_result.lines[0])
        self.assertEqual(branch_result.lines, ["Created branch: feature"])
        self.assertEqual(switch_result.lines, ["Switched to branch: feature"])
        self.assertIn("commit ", log_result.lines[0])
        self.assertIn("[main]", log_result.lines[0])

    def test_whoiam_shows_the_current_user_after_user_change(self):
        app = MiniGit()
        app.execute("init Alice")
        alice_result = app.execute("WHOIAM")
        app.execute("init Bob")
        bob_result = app.execute("whoiam")

        self.assertEqual(alice_result.lines, ["Current user: Alice"])
        self.assertEqual(bob_result.lines, ["Current user: Bob"])

    def test_whoiam_requires_init_and_rejects_arguments(self):
        app = MiniGit()

        with self.assertRaises(AppError) as uninitialized_context:
            app.execute("whoiam")
        self.assertEqual(
            uninitialized_context.exception.message,
            "repository is not initialized",
        )

        app.execute("init Alice")
        with self.assertRaises(AppError) as args_context:
            app.execute("whoiam Alice")
        self.assertEqual(args_context.exception.message, "usage: whoiam")

    def test_branch_lists_all_branches_and_marks_the_current_branch(self):
        app = MiniGit()
        app.execute("init Alice")
        app.execute("commit first")
        app.execute("branch feature")

        main_result = app.execute("branch")
        app.execute("switch feature")
        feature_result = app.execute("branch")

        self.assertEqual(main_result.lines, ["Branches:", "* main", "  feature"])
        self.assertEqual(feature_result.lines, ["Branches:", "  main", "* feature"])

    def test_branch_list_requires_init(self):
        app = MiniGit()

        with self.assertRaises(AppError) as context:
            app.execute("branch")

        self.assertEqual(context.exception.message, "repository is not initialized")

    def test_minigit_searches_by_keyword_and_author(self):
        app = MiniGit()

        app.execute("init Alice")
        app.execute('commit "Initial commit"')
        app.execute('commit "Add login feature"')

        keyword_result = app.execute("search login")
        author_result = app.execute("search --author=Alice")

        self.assertIn("Found 1 commit:", keyword_result.lines[0])
        self.assertIn("Add login feature", keyword_result.lines[1])
        self.assertIn("Found 2 commits:", author_result.lines[0])

    def test_sorted_logs_include_commits_from_every_initialized_user(self):
        app = MiniGit()
        app.execute("init Alice")
        app.execute("commit Alice-work")
        app.execute("init Bob")
        app.execute("commit Bob-work")

        date_result = app.execute("log --sort-by=date")
        author_result = app.execute("log --sort-by=author")
        author_headers = [
            line for line in author_result.lines if line.startswith("commit ")
        ]

        self.assertTrue(any("(Alice," in line for line in date_result.lines))
        self.assertTrue(any("(Bob," in line for line in date_result.lines))
        self.assertEqual(len(author_headers), 2)
        self.assertIn("(Alice,", author_headers[0])
        self.assertIn("(Bob,", author_headers[1])

    def test_author_search_uses_the_init_user_name(self):
        app = MiniGit()
        app.execute("init test")
        app.execute("commit first")

        author_result = app.execute("search --author=test")
        branch_name_result = app.execute("search --author=main")

        self.assertEqual(author_result.lines[0], "Found 1 commit:")
        self.assertEqual(branch_name_result.lines, ["Found 0 commits:"])

    def test_search_rejects_an_unknown_option(self):
        app = MiniGit()
        app.execute("init test")
        app.execute("commit first")

        with self.assertRaises(AppError) as context:
            app.execute("search --autor=test")

        self.assertEqual(
            context.exception.message,
            "usage: search <keyword> | search --author=<name>",
        )

    def test_minigit_searches_a_quoted_multiword_keyword(self):
        app = MiniGit()
        app.execute("init Alice")
        app.execute('commit "Add login feature"')
        app.execute('commit "Move login button"')

        result = app.execute('search "login feature"')

        self.assertEqual(result.lines[0], "Found 1 commit:")
        self.assertIn("Add login feature", result.lines[1])

    def test_minigit_supports_case_insensitive_commands_and_spaced_author(self):
        app = MiniGit()

        app.execute('INIT "Alice Smith"')
        app.execute('CoMmIt "Initial commit"')
        result = app.execute('SeArCh --author="Alice Smith"')

        self.assertEqual(result.lines[0], "Found 1 commit:")

    def test_repository_commands_require_init(self):
        app = MiniGit()

        for command in ("log", "search login", "path abc def", "ancestors abc"):
            with self.subTest(command=command):
                with self.assertRaises(AppError) as context:
                    app.execute(command)
                self.assertEqual(
                    context.exception.message,
                    "repository is not initialized",
                )

    def test_empty_string_arguments_are_rejected(self):
        app = MiniGit()
        commands = (
            'init ""',
            'branch ""',
            'switch ""',
            'commit ""',
            'path "" abc',
            'ancestors ""',
            'search ""',
            'search --author=""',
            "help extra",
            "exit extra",
        )

        for command in commands:
            with self.subTest(command=command):
                with self.assertRaises(AppError):
                    app.execute(command)

    def test_branch_requires_an_existing_head_commit(self):
        app = MiniGit()
        app.execute("init Alice")

        with self.assertRaises(AppError) as context:
            app.execute("branch feature")

        self.assertEqual(
            context.exception.message,
            "cannot create branch before first commit",
        )

    def test_minigit_finds_path_and_ancestors(self):
        app = MiniGit()

        app.execute("init Alice")
        first = app.repo.commit("first")
        second = app.repo.commit("second")

        path_result = app.execute(f"path {first.commit_hash[:6]} {second.commit_hash[:6]}")
        ancestors_result = app.execute(f"ancestors {second.commit_hash[:6]}")

        self.assertIn("Path:", path_result.lines[0])
        self.assertIn(first.commit_hash[:6], path_result.lines[0])
        self.assertIn(second.commit_hash[:6], path_result.lines[0])
        self.assertIn("Ancestors:", ancestors_result.lines[0])
        self.assertIn(first.message, ancestors_result.lines[1])

    def test_minigit_exit_result_marks_repl_exit(self):
        app = MiniGit()

        exit_result = app.execute("exit")
        quit_result = app.execute("quit")

        self.assertEqual(exit_result.lines, ["bye"])
        self.assertTrue(exit_result.should_exit)
        self.assertEqual(quit_result.lines, ["bye"])
        self.assertTrue(quit_result.should_exit)

    def test_exit_and_quit_use_the_same_dispatch_handler(self):
        app = MiniGit()

        self.assertIs(
            app._command_handlers["exit"],
            app._command_handlers["quit"],
        )


class MiniGitReplTest(unittest.TestCase):
    def test_repl_init_commit_and_log(self):
        input_stream = StringIO(
            "\n".join(
                [
                    "init Alice",
                    "commit first",
                    "log",
                    "exit",
                ]
            )
        )
        output_stream = StringIO()

        exit_code = MiniGitRepl(input_stream, output_stream).run()

        output = output_stream.getvalue()

        self.assertIn("Initialized repository.", output)
        self.assertIn("[main ", output)
        self.assertIn("commit ", output)
        self.assertIn("first", output)
        self.assertIn("bye", output)
        self.assertEqual(exit_code, 0)

    def test_repl_routes_empty_readline_to_repl_exit(self):
        output_stream = StringIO()

        exit_code = MiniGitRepl(StringIO(), output_stream).run()

        self.assertIn("repl exit: unexpected end of input", output_stream.getvalue())
        self.assertEqual(exit_code, 1)

    def test_repl_handles_app_error(self):
        input_stream = StringIO("commit\nexit\n")
        output_stream = StringIO()

        exit_code = MiniGitRepl(input_stream, output_stream).run()

        output = output_stream.getvalue()

        self.assertIn("app error: usage: commit <message>", output)
        self.assertIn("bye", output)
        self.assertEqual(exit_code, 2)

    def test_repl_routes_keyboard_interrupt_to_repl_exit(self):
        class InterruptInput:
            def readline(self):
                raise KeyboardInterrupt

        output_stream = StringIO()

        exit_code = MiniGitRepl(InterruptInput(), output_stream).run()

        self.assertIn("repl exit: interrupted by user", output_stream.getvalue())
        self.assertEqual(exit_code, 130)

    def test_repl_routes_eof_error_to_repl_exit(self):
        class EofInput:
            def readline(self):
                raise EOFError

        output_stream = StringIO()

        exit_code = MiniGitRepl(EofInput(), output_stream).run()

        self.assertIn("repl exit: unexpected end of input", output_stream.getvalue())
        self.assertEqual(exit_code, 1)

    def test_repl_handles_unexpected_error(self):
        repl = MiniGitRepl(StringIO(), StringIO())

        repl.app.execute = lambda line: (_ for _ in ()).throw(ValueError("boom"))
        repl.input_stream = StringIO("explode\nexit\n")
        exit_code = repl.run()

        self.assertIn(
            "runtime error: unexpected ValueError: boom",
            repl.output_stream.getvalue(),
        )
        self.assertEqual(exit_code, 1)

    def test_repl_handles_ambiguous_hash_error(self):
        repl = MiniGitRepl(StringIO("path abc abc111\nexit\n"), StringIO())
        repl.app.repo.init("Alice")
        repl.app.repo.commits["abc111"] = repl.app.repo.commit("one")
        repl.app.repo.commits["abc222"] = repl.app.repo.commit("two")

        exit_code = repl.run()

        self.assertIn(
            "runtime error: ambiguous commit hash: abc",
            repl.output_stream.getvalue(),
        )
        self.assertEqual(exit_code, 1)


class ErrorClassTest(unittest.TestCase):
    def test_app_error_handles_its_message(self):
        output_stream = StringIO()

        exit_code = AppError("sample").handle(output_stream)

        self.assertEqual(output_stream.getvalue(), "app error: sample\n")
        self.assertEqual(exit_code, 1)

    def test_runtime_error_handles_its_message(self):
        output_stream = StringIO()

        exit_code = RuntimeError("sample").handle(output_stream)

        self.assertEqual(output_stream.getvalue(), "runtime error: sample\n")
        self.assertEqual(exit_code, 1)

    def test_env_error_handles_its_message(self):
        output_stream = StringIO()

        exit_code = EnvError("sample").handle(output_stream)

        self.assertEqual(output_stream.getvalue(), "env error: sample\n")
        self.assertEqual(exit_code, 1)

    def test_runtime_error_handles_converted_unexpected_error(self):
        output_stream = StringIO()

        error = RuntimeError.unexpected_exception(ValueError("bad value"))
        exit_code = error.handle(output_stream)

        self.assertEqual(
            output_stream.getvalue(),
            "runtime error: unexpected ValueError: bad value\n",
        )
        self.assertEqual(exit_code, 1)

    def test_env_error_handles_converted_os_error(self):
        output_stream = StringIO()

        error = EnvError.io_failed(OSError("stream failed"))
        exit_code = error.handle(output_stream)

        self.assertEqual(output_stream.getvalue(), "env error: io failed: stream failed\n")
        self.assertEqual(exit_code, 1)

    def test_repl_exit_handles_keyboard_interrupt(self):
        output_stream = StringIO()

        exit_code = ReplExit.keyboard_interrupt().handle(output_stream)

        self.assertEqual(output_stream.getvalue(), "repl exit: interrupted by user\n")
        self.assertEqual(exit_code, 130)

    def test_repl_exit_handles_eof(self):
        output_stream = StringIO()

        exit_code = ReplExit.eof().handle(output_stream)

        self.assertEqual(output_stream.getvalue(), "repl exit: unexpected end of input\n")
        self.assertEqual(exit_code, 1)

    def test_error_classes_create_common_messages_with_methods(self):
        usage_error = AppError.invalid_command_usage("commit <message>")

        self.assertEqual(usage_error.format_message(), "app error: usage: commit <message>")
        self.assertEqual(usage_error.exit_code, 2)
        self.assertEqual(
            RuntimeError.cyclic_commit_graph().format_message(),
            "runtime error: commit graph has a cycle",
        )
        repl_exit = ReplExit.keyboard_interrupt()

        self.assertEqual(repl_exit.format_message(), "repl exit: interrupted by user")
        self.assertEqual(repl_exit.exit_code, 130)

        env_error = EnvError.io_failed(OSError("disk failed"))

        self.assertEqual(env_error.format_message(), "env error: io failed: disk failed")
        self.assertEqual(env_error.exit_code, 1)


if __name__ == "__main__":
    unittest.main()
