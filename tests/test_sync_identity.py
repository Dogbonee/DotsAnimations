import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


class SyncIdentityTest(unittest.TestCase):
    def test_commit_uses_gilbot_even_with_different_caller_identity(self):
        script = Path(__file__).resolve().parents[1] / "sync.py"
        env = {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_AUTHOR_NAME": "Caller",
            "GIT_AUTHOR_EMAIL": "caller@example.com",
            "GIT_COMMITTER_NAME": "Caller",
            "GIT_COMMITTER_EMAIL": "caller@example.com",
        }
        with tempfile.TemporaryDirectory() as repo, patch.dict(os.environ, env):
            spec = importlib.util.spec_from_file_location("dots_sync", script)
            assert spec is not None and spec.loader is not None
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            subprocess.run(["git", "init", "-q", repo], check=True)
            result = module.run("git -c commit.gpgsign=false commit --allow-empty -m identity-test", cwd=repo)
            self.assertIsNotNone(result, "Commit must succeed without caller Git configuration")
            identity = subprocess.check_output(
                ["git", "log", "-1", "--format=%an <%ae>|%cn <%ce>"], cwd=repo, text=True
            ).strip()
            self.assertEqual(identity, "Gilbot <gilbert@example.com>|Gilbot <gilbert@example.com>")


if __name__ == "__main__":
    unittest.main()
