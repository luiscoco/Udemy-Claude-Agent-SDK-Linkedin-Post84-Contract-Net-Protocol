"""Run the local tests with python -m unittest discover -v."""
import asyncio
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from runtime import Agent, contained_path, temporary_workspace
from workflow import run

ROOT = Path(__file__).resolve().parent


class PracticalTests(unittest.TestCase):
    def test_workflow_domain_invariants(self):
        with temporary_workspace(prefix="practical-test-") as directory:
            workspace = Path(directory).resolve()
            self.assertTrue(workspace.is_relative_to(Path(tempfile.gettempdir()).resolve()))
            root = workspace / "application"
            shutil.copytree(ROOT, root, ignore=shutil.ignore_patterns("outputs", "state", ".venv", "__pycache__", ".git"))
            output = workspace / "output"
            output.mkdir()
            data = json.loads((root / "data/input.json").read_text(encoding="utf8"))
            agent = Agent(root, output)
            result = asyncio.run(run(agent, data))
            self.assertEqual(result['winner']['contractor'], 'a')
            self.assertEqual(result['status'], 'completed')

    def test_workspace_traversal_is_rejected(self):
        with self.assertRaises(ValueError):
            contained_path(ROOT, "../outside.txt")


if __name__ == "__main__":
    unittest.main()
