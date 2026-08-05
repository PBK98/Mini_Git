import unittest

from mini_git import Blob, Directory, MiniGitRepository


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


if __name__ == "__main__":
    unittest.main()
