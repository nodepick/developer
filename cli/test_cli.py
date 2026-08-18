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

    def test_version(self):
        result = runner.invoke(app, ["--version"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("nodepick CLI version 0.1.0", result.output)

    def test_version_short(self):
        result = runner.invoke(app, ["-v"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("nodepick CLI version 0.1.0", result.output)

    def test_node_help(self):
        result = runner.invoke(app, ["node", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Manage Compute Nodes", result.output)

    def test_node_get_help(self):
        result = runner.invoke(app, ["node", "get", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Get details of a specific node", result.output)

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
        self.assertIn("configure", result.output)
        self.assertIn("clear", result.output)
        self.assertIn("test", result.output)

    def test_auth_configure_help(self):
        result = runner.invoke(app, ["auth", "configure", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("API key", result.output)

    def test_auth_clear_help(self):
        result = runner.invoke(app, ["auth", "clear", "--help"])
        self.assertEqual(result.exit_code, 0)

    def test_auth_test_help(self):
        result = runner.invoke(app, ["auth", "test", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Test API access", result.output)

    def test_auth_configure_interactive(self):
        result = runner.invoke(app, ["auth", "configure"], input="test_api_key_123\n")
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Credentials configured", result.output)

    def test_ai_help(self):
        result = runner.invoke(app, ["--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("[BETA]", result.output)
        self.assertIn("ai", result.output)

        ai_result = runner.invoke(app, ["ai", "--help"])
        self.assertEqual(ai_result.exit_code, 0)
        self.assertIn("[BETA]", ai_result.output)
        self.assertIn("mcp", ai_result.output)

    def test_ai_mcp_help(self):
        result = runner.invoke(app, ["ai", "mcp", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("configure", result.output)

    def test_ai_mcp_configure_help(self):
        result = runner.invoke(app, ["ai", "mcp", "configure", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("agent", result.output)
        self.assertIn("supported: antigravity", result.output)
        self.assertIn("nodes", result.output)

    def test_ai_mcp_configure_unsupported_agent(self):
        result = runner.invoke(app, ["ai", "mcp", "configure", "unsupported-agent", "dev"])
        self.assertEqual(result.exit_code, 1)
        self.assertIn("Unsupported agent", result.output)

    def test_ai_mcp_configure_single_node(self):
        from unittest.mock import patch, MagicMock
        import tempfile
        import json

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            mock_client = MagicMock()
            mock_client.node_get_details.return_value = {
                "vm_uuid": "116e7171-7cbe-4797-bd92-dac551d8883e",
                "display_name": "dev",
                "connect": {
                    "mcpUrl": "https://lax1-mg1.entic.net:10010",
                    "mcpApiKey": "mcp-secret-key-123"
                }
            }

            with patch("nodepick_cli.commands.ai.get_client", return_value=mock_client), \
                 patch("pathlib.Path.home", return_value=tmppath):
                result = runner.invoke(app, ["ai", "mcp", "configure", "antigravity", "dev"])
                self.assertEqual(result.exit_code, 0)
                self.assertIn("Configured MCP server 'dev'", result.output)
                self.assertIn("Successfully configured 1 MCP server(s)", result.output)

                # Verify files were created and updated with correct MCP config (HTTP stream, TLS verification disabled)
                mcp_config_file = tmppath / ".gemini" / "config" / "mcp_config.json"
                self.assertTrue(mcp_config_file.exists())
                with open(mcp_config_file, "r") as f:
                    cfg = json.load(f)
                    self.assertIn("dev", cfg["mcpServers"])
                    self.assertEqual(cfg["mcpServers"]["dev"]["url"], "https://lax1-mg1.entic.net:10010")
                    self.assertEqual(cfg["mcpServers"]["dev"]["serverUrl"], "https://lax1-mg1.entic.net:10010")
                    self.assertEqual(cfg["mcpServers"]["dev"]["type"], "http")
                    self.assertEqual(cfg["mcpServers"]["dev"]["transport"], "http")
                    self.assertTrue(cfg["mcpServers"]["dev"]["insecure"])
                    self.assertTrue(cfg["mcpServers"]["dev"]["insecureSkipVerify"])
                    self.assertFalse(cfg["mcpServers"]["dev"]["rejectUnauthorized"])
                    self.assertFalse(cfg["mcpServers"]["dev"]["verify"])
                    self.assertTrue(cfg["mcpServers"]["dev"]["tls"]["insecure"])
                    self.assertEqual(cfg["mcpServers"]["dev"]["headers"]["X-API-Key"], "mcp-secret-key-123")

    def test_ai_mcp_configure_multiple_nodes(self):
        from unittest.mock import patch, MagicMock
        import tempfile
        import json

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            mock_client = MagicMock()

            def mock_get_details(node_id):
                if node_id == "dev":
                    return {
                        "display_name": "dev",
                        "connect": {"mcpUrl": "https://lax1-mg1.entic.net:10010", "mcpApiKey": "key-dev"}
                    }
                elif node_id == "prod":
                    return {
                        "display_name": "prod",
                        "connect": {"mcpUrl": "https://fmt1-sr3.entic.net:10010", "mcpApiKey": "key-prod"}
                    }
                return {}

            mock_client.node_get_details.side_effect = mock_get_details

            with patch("nodepick_cli.commands.ai.get_client", return_value=mock_client), \
                 patch("pathlib.Path.home", return_value=tmppath):
                result = runner.invoke(app, ["ai", "mcp", "configure", "antigravity", "dev", "prod"])
                self.assertEqual(result.exit_code, 0)
                self.assertIn("Configured MCP server 'dev'", result.output)
                self.assertIn("Configured MCP server 'prod'", result.output)
                self.assertIn("Successfully configured 2 MCP server(s)", result.output)

                settings_file = tmppath / ".gemini" / "settings.json"
                with open(settings_file, "r") as f:
                    cfg = json.load(f)
                    self.assertIn("dev", cfg["mcpServers"])
                    self.assertIn("prod", cfg["mcpServers"])

    def test_ai_mcp_configure_all_nodes(self):
        from unittest.mock import patch, MagicMock
        import tempfile
        import json

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            mock_client = MagicMock()
            mock_client.node_list.return_value = [
                {"vm_uuid": "node-1", "display_name": "node-1"},
                {"vm_uuid": "node-2", "display_name": "node-2"},
            ]
            mock_client.node_get_details.side_effect = lambda n: {
                "display_name": n,
                "connect": {"mcpUrl": f"https://{n}.entic.net:10010"}
            }

            with patch("nodepick_cli.commands.ai.get_client", return_value=mock_client), \
                 patch("pathlib.Path.home", return_value=tmppath):
                result = runner.invoke(app, ["ai", "mcp", "configure", "antigravity"])
                self.assertEqual(result.exit_code, 0)
                self.assertIn("Successfully configured 2 MCP server(s)", result.output)


if __name__ == "__main__":
    unittest.main()


