import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from typer.testing import CliRunner
from nodepick_cli.main import app

runner = CliRunner()

class TestCliCommands(unittest.TestCase):
    def test_help(self):
        result = runner.invoke(app, ["--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Nodepick CLI", result.output)
        self.assertIn("node", result.output)
        self.assertIn("auth", result.output)

    def test_node_help(self):
        result = runner.invoke(app, ["node", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Manage micro-VM compute nodes", result.output)

    def test_ssh_help(self):
        result = runner.invoke(app, ["ssh", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Manage developer SSH public keys", result.output)

    def test_ssh_add_help(self):
        result = runner.invoke(app, ["ssh", "add", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Add an SSH public key", result.output)

    def test_auth_help(self):
        result = runner.invoke(app, ["auth", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("save", result.output)
        self.assertIn("clear", result.output)
        self.assertIn("test", result.output)

    def test_auth_save_help(self):
        result = runner.invoke(app, ["auth", "save", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("API key", result.output)

    def test_auth_clear_help(self):
        result = runner.invoke(app, ["auth", "clear", "--help"])
        self.assertEqual(result.exit_code, 0)

    def test_auth_test_help(self):
        result = runner.invoke(app, ["auth", "test", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Test API access", result.output)


if __name__ == "__main__":
    unittest.main()
