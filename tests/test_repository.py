import unittest
from io import StringIO

from mini_git import Blob, Directory, MiniGit, MiniGitRepository
from mini_git.errors import (
    AppError,
    EnvError,
    RuntimeError,
    handler_error,
)
from mini_git.repl import MiniGitRepl


class MiniGitRepositoryTest(unittest.TestCase):
    def test_blob_hash_is_content_based(self):
        repo = MiniGitRepository()

        first_hash = repo.object_store.save_content_object(Blob("hello"))
        second_hash = repo.object_store.save_content_object(Blob("hello"))

        self.assertEqual(first_hash, second_hash)

    def test_directory_maps_file_name_to_blob_hash(self):
        repo = MiniGitRepository()
        blob_hash = repo.object_store.save_content_object(Blob("hello"))
        directory = Directory({"hello.txt": blob_hash})

        directory_hash = repo.object_store.save_content_object(directory)
        saved_directory = repo.object_store.get(directory_hash)

        self.assertEqual(saved_directory, directory)

    def test_commit_hashes_are_unique_in_session(self):
        repo = MiniGitRepository()

        first_hash = repo.commit({"a.txt": "same"}, "same message")
        second_hash = repo.commit({"a.txt": "same"}, "same message")

        self.assertNotEqual(first_hash, second_hash)

    def test_topological_sort_returns_parent_before_child(self):
        repo = MiniGitRepository()

        first_hash = repo.commit({"a.txt": "1"}, "first")
        second_hash = repo.commit({"a.txt": "2"}, "second")

        sorted_hashes = [commit.commit_hash for commit in repo.sorted_commits()]

        self.assertLess(sorted_hashes.index(first_hash), sorted_hashes.index(second_hash))


class MiniGitCommandTest(unittest.TestCase):
    def test_minigit_executes_add_commit_and_log(self):
        app = MiniGit()

        add_result = app.execute("add README.md hello")
        commit_result = app.execute("commit first")
        log_result = app.execute("log")

        self.assertEqual(add_result.lines, ["added README.md"])
        self.assertEqual(len(commit_result.lines), 1)
        self.assertIn("committed ", commit_result.lines[0])
        self.assertIn("parent=None", log_result.lines[0])

    def test_minigit_exit_result_marks_repl_exit(self):
        app = MiniGit()

        result = app.execute("exit")

        self.assertEqual(result.lines, ["bye"])
        self.assertTrue(result.should_exit)


class MiniGitReplTest(unittest.TestCase):
    def test_repl_add_commit_and_log(self):
        input_stream = StringIO(
            "\n".join(
                [
                    "add README.md hello",
                    "commit first",
                    "log",
                    "exit",
                ]
            )
        )
        output_stream = StringIO()

        exit_code = MiniGitRepl(input_stream, output_stream).run()

        output = output_stream.getvalue()

        self.assertIn("added README.md", output)
        self.assertIn("committed ", output)
        self.assertIn("parent=None", output)
        self.assertIn("first", output)
        self.assertIn("bye", output)
        self.assertEqual(exit_code, 0)

    def test_repl_treats_empty_readline_as_eof_error(self):
        output_stream = StringIO()

        exit_code = MiniGitRepl(StringIO(), output_stream).run()

        self.assertIn("env error: unexpected end of input", output_stream.getvalue())
        self.assertEqual(exit_code, 1)

    def test_repl_routes_errors_to_handler_error(self):
        input_stream = StringIO("commit\nexit\n")
        output_stream = StringIO()

        exit_code = MiniGitRepl(input_stream, output_stream).run()

        output = output_stream.getvalue()

        self.assertIn("app error: usage: commit <message>", output)
        self.assertIn("bye", output)
        self.assertEqual(exit_code, 2)

    def test_repl_routes_keyboard_interrupt_to_handler_error(self):
        class InterruptInput:
            def readline(self):
                raise KeyboardInterrupt

        output_stream = StringIO()

        exit_code = MiniGitRepl(InterruptInput(), output_stream).run()

        self.assertIn("env error: interrupted by user", output_stream.getvalue())
        self.assertEqual(exit_code, 130)

    def test_repl_returns_1_for_eof_error(self):
        class EofInput:
            def readline(self):
                raise EOFError

        output_stream = StringIO()

        exit_code = MiniGitRepl(EofInput(), output_stream).run()

        self.assertIn("env error: unexpected end of input", output_stream.getvalue())
        self.assertEqual(exit_code, 1)

    def test_repl_routes_unexpected_error_to_handler_error(self):
        repl = MiniGitRepl(StringIO(), StringIO())

        repl.app.execute = lambda line: (_ for _ in ()).throw(ValueError("boom"))
        repl.input_stream = StringIO("explode\nexit\n")
        exit_code = repl.run()

        self.assertIn(
            "runtime error: unexpected ValueError: boom",
            repl.output_stream.getvalue(),
        )
        self.assertEqual(exit_code, 1)

    def test_repl_routes_ambiguous_hash_to_handler_error(self):
        repl = MiniGitRepl(StringIO("show abc\nexit\n"), StringIO())
        repl.app.repo.object_store._objects["abc111"] = Blob("one")
        repl.app.repo.object_store._objects["abc222"] = Blob("two")

        exit_code = repl.run()

        self.assertIn(
            "runtime error: ambiguous object hash: abc",
            repl.output_stream.getvalue(),
        )
        self.assertEqual(exit_code, 1)


class ErrorHandlerTest(unittest.TestCase):
    def test_handler_error_delegates_app_error_message(self):
        output_stream = StringIO()

        exit_code = handler_error(AppError("sample"), output_stream)

        self.assertEqual(output_stream.getvalue(), "app error: sample\n")
        self.assertEqual(exit_code, 1)

    def test_handler_error_delegates_runtime_error_message(self):
        output_stream = StringIO()

        exit_code = handler_error(RuntimeError("sample"), output_stream)

        self.assertEqual(output_stream.getvalue(), "runtime error: sample\n")
        self.assertEqual(exit_code, 1)

    def test_handler_error_delegates_env_error_message(self):
        output_stream = StringIO()

        exit_code = handler_error(EnvError("sample"), output_stream)

        self.assertEqual(output_stream.getvalue(), "env error: sample\n")
        self.assertEqual(exit_code, 1)

    def test_handler_error_converts_unknown_exception_to_runtime_error(self):
        output_stream = StringIO()

        exit_code = handler_error(ValueError("bad value"), output_stream)

        self.assertEqual(
            output_stream.getvalue(),
            "runtime error: unexpected ValueError: bad value\n",
        )
        self.assertEqual(exit_code, 1)

    def test_handler_error_converts_os_error_to_env_error(self):
        output_stream = StringIO()

        exit_code = handler_error(OSError("stream failed"), output_stream)

        self.assertEqual(output_stream.getvalue(), "env error: io failed: stream failed\n")
        self.assertEqual(exit_code, 1)

    def test_handler_error_returns_1_for_eof_error(self):
        output_stream = StringIO()

        exit_code = handler_error(EOFError(), output_stream)

        self.assertEqual(output_stream.getvalue(), "env error: unexpected end of input\n")
        self.assertEqual(exit_code, 1)

    def test_error_classes_create_common_messages_with_methods(self):
        usage_error = AppError.invalid_command_usage("commit <message>")

        self.assertEqual(usage_error.format_message(), "app error: usage: commit <message>")
        self.assertEqual(usage_error.exit_code, 2)
        self.assertEqual(
            RuntimeError.cyclic_commit_graph().format_message(),
            "runtime error: commit graph has a cycle",
        )
        keyboard_error = EnvError.keyboard_interrupt()

        self.assertEqual(keyboard_error.format_message(), "env error: interrupted by user")
        self.assertEqual(keyboard_error.exit_code, 130)


if __name__ == "__main__":
    unittest.main()
