import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from typer.testing import CliRunner
from nodepick_cli.main import app
from nodepick_cli import __version__

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
        self.assertIn(f"nodepick CLI version {__version__}", result.output)

    def test_version_short(self):
        result = runner.invoke(app, ["-v"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn(f"nodepick CLI version {__version__}", result.output)

    def test_node_help(self):
        result = runner.invoke(app, ["node", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Manage Compute Nodes", result.output)

    def test_node_get_help(self):
        result = runner.invoke(app, ["node", "get", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Get details of a specific node", result.output)

    def test_node_delete_not_found(self):
        from unittest.mock import patch, MagicMock
        mock_client = MagicMock()
        mock_client.node_delete.side_effect = ValueError("Node not found: 'dev'")
        with patch("nodepick_cli.commands.node.get_client", return_value=mock_client):
            result = runner.invoke(app, ["node", "delete", "dev"])
            self.assertEqual(result.exit_code, 1)
            self.assertIn("Node not found", result.output)

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

    def test_auth_test_success(self):
        from unittest.mock import patch, MagicMock
        mock_client = MagicMock()
        mock_client.get_me.return_value = {
            "user": {"id": "user-123", "email": "anil@nodepick.ai"},
            "org": {"id": "org-456", "name": "anilj's Org"}
        }
        with patch("nodepick_cli.auth.login._get_api_key_with_source", return_value=("test-key", "env var")), \
             patch("nodepick_cli.auth.login.get_base_url", return_value="https://api.nodepick.ai"), \
             patch("nodepick.NodePickClient", return_value=mock_client):
            result = runner.invoke(app, ["auth", "test"])
            self.assertEqual(result.exit_code, 0)
            self.assertIn("API access OK", result.output)
            self.assertIn("API URL: https://api.nodepick.ai", result.output)
            self.assertIn("User: user-123", result.output)
            self.assertIn("Organization: org-456", result.output)

    def test_auth_configure_no_api_key_flag(self):
        result = runner.invoke(app, ["auth", "configure", "--api-key", "secret123"])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("No such option", result.output)

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
        self.assertIn("--insecure", result.output)
        self.assertIn("--delete", result.output)

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

                # Verify files were created and updated with secure MCP config (HTTPS verification enabled by default)
                mcp_config_file = tmppath / ".gemini" / "config" / "mcp_config.json"
                self.assertTrue(mcp_config_file.exists())
                with open(mcp_config_file, "r") as f:
                    cfg = json.load(f)
                    self.assertIn("dev", cfg["mcpServers"])
                    self.assertEqual(cfg["mcpServers"]["dev"]["url"], "https://lax1-mg1.entic.net:10010")
                    self.assertEqual(cfg["mcpServers"]["dev"]["serverUrl"], "https://lax1-mg1.entic.net:10010")
                    self.assertEqual(cfg["mcpServers"]["dev"]["type"], "http")
                    self.assertEqual(cfg["mcpServers"]["dev"]["transport"], "http")
                    self.assertNotIn("insecure", cfg["mcpServers"]["dev"])
                    self.assertNotIn("tls", cfg["mcpServers"]["dev"])
                    self.assertEqual(cfg["mcpServers"]["dev"]["headers"]["X-API-Key"], "mcp-secret-key-123")

    def test_ai_mcp_configure_insecure(self):
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
                result = runner.invoke(app, ["ai", "mcp", "configure", "antigravity", "dev", "--insecure"])
                self.assertEqual(result.exit_code, 0)
                self.assertIn("Configured MCP server 'dev'", result.output)
                self.assertIn("Successfully configured 1 MCP server(s)", result.output)

                mcp_config_file = tmppath / ".gemini" / "config" / "mcp_config.json"
                self.assertTrue(mcp_config_file.exists())
                with open(mcp_config_file, "r") as f:
                    cfg = json.load(f)
                    self.assertIn("dev", cfg["mcpServers"])
                    self.assertTrue(cfg["mcpServers"]["dev"]["insecure"])
                    self.assertTrue(cfg["mcpServers"]["dev"]["insecureSkipVerify"])
                    self.assertFalse(cfg["mcpServers"]["dev"]["rejectUnauthorized"])
                    self.assertFalse(cfg["mcpServers"]["dev"]["verify"])
                    self.assertTrue(cfg["mcpServers"]["dev"]["tls"]["insecure"])

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

    def test_ai_mcp_configure_delete_specific_node(self):
        from unittest.mock import patch
        import tempfile
        import json

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            mcp_config_file = tmppath / ".gemini" / "config" / "mcp_config.json"
            mcp_config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(mcp_config_file, "w") as f:
                json.dump({
                    "mcpServers": {
                        "dev": {"url": "https://dev.entic.net:10010"},
                        "prod": {"url": "https://prod.entic.net:10010"}
                    }
                }, f)

            with patch("pathlib.Path.home", return_value=tmppath):
                result = runner.invoke(app, ["ai", "mcp", "configure", "antigravity", "dev", "--delete"])
                self.assertEqual(result.exit_code, 0)
                self.assertIn("Removed MCP server configuration 'dev'", result.output)
                self.assertIn("Successfully removed 1 MCP server configuration(s)", result.output)

                with open(mcp_config_file, "r") as f:
                    cfg = json.load(f)
                    self.assertNotIn("dev", cfg["mcpServers"])
                    self.assertIn("prod", cfg["mcpServers"])

    def test_ai_mcp_configure_delete_all(self):
        from unittest.mock import patch
        import tempfile
        import json

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            mcp_config_file = tmppath / ".gemini" / "config" / "mcp_config.json"
            mcp_config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(mcp_config_file, "w") as f:
                json.dump({
                    "mcpServers": {
                        "dev": {"url": "https://dev.entic.net:10010"},
                        "prod": {"url": "https://prod.entic.net:10010"}
                    }
                }, f)

            with patch("pathlib.Path.home", return_value=tmppath):
                result = runner.invoke(app, ["ai", "mcp", "configure", "antigravity", "-d"])
                self.assertEqual(result.exit_code, 0)
                self.assertIn("Successfully removed 2 MCP server configuration(s)", result.output)

                with open(mcp_config_file, "r") as f:
                    cfg = json.load(f)
                    self.assertEqual(cfg["mcpServers"], {})


    def test_network_help(self):
        result = runner.invoke(app, ["network", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("list", result.output)
        self.assertIn("create", result.output)
        self.assertIn("get", result.output)
        self.assertIn("delete", result.output)

    def test_network_list(self):
        from unittest.mock import patch, MagicMock
        mock_client = MagicMock()
        mock_client.vpc_list.return_value = [
            {"id": "vpc-1", "name": "prod-net", "subnet": "10.0.1.0/24", "region": "fmt1", "enableOutboundNat": True}
        ]
        with patch("nodepick_cli.commands.network.get_client", return_value=mock_client):
            result = runner.invoke(app, ["network", "list"])
            self.assertEqual(result.exit_code, 0)
            self.assertIn("vpc-1", result.output)
            self.assertIn("prod-net", result.output)
            self.assertIn("10.0.1.0/24", result.output)
            # Verify AZ column is not present
            self.assertNotIn(" AZ ", result.output)

    def test_network_create(self):
        from unittest.mock import patch, MagicMock
        mock_client = MagicMock()
        mock_client.vpc_create.return_value = {"id": "vpc-new-123", "name": "devnet"}
        with patch("nodepick_cli.commands.network.get_client", return_value=mock_client):
            result = runner.invoke(app, ["network", "create", "devnet", "--region", "fmt1"])
            self.assertEqual(result.exit_code, 0)
            self.assertIn("VPC network created successfully", result.output)
            self.assertIn("vpc-new-123", result.output)
            mock_client.vpc_create.assert_called_once_with(
                name="devnet",
                region="fmt1",
                description=None,
                enable_outbound_nat=True,
            )

            # Verify --az option is no longer supported
            result_az = runner.invoke(app, ["network", "create", "devnet", "--region", "fmt1", "--az", "zone1"])
            self.assertNotEqual(result_az.exit_code, 0)
            self.assertIn("No such option: --az", result_az.output)

    def test_network_get(self):
        from unittest.mock import patch, MagicMock
        mock_client = MagicMock()
        mock_client.vpc_get.return_value = {
            "id": "vpc-123",
            "name": "devnet",
            "subnet": "10.0.1.0/24",
            "vni": 1001,
            "region": "fmt1"
        }
        with patch("nodepick_cli.commands.network.get_client", return_value=mock_client):
            result = runner.invoke(app, ["network", "get", "vpc-123"])
            self.assertEqual(result.exit_code, 0)
            self.assertIn("vpc-123", result.output)
            self.assertIn("devnet", result.output)

    def test_network_delete(self):
        from unittest.mock import patch, MagicMock
        mock_client = MagicMock()
        mock_client.vpc_delete.return_value = {"deleted": True}
        with patch("nodepick_cli.commands.network.get_client", return_value=mock_client):
            result = runner.invoke(app, ["network", "delete", "vpc-123"])
            self.assertEqual(result.exit_code, 0)
            self.assertIn("VPC network vpc-123 deleted", result.output)

    def test_node_find_command(self):
        from unittest.mock import patch, MagicMock
        mock_client = MagicMock()
        mock_client.find_compute.return_value = [
            {
                "id": "host-1",
                "region": "fmt1",
                "datacenter": "facility-1",
                "memory_gb": 32,
                "storage_gb": 500,
                "cpu": {"cores": 16},
                "requested_cpu": 2,
                "requested_memory_gb": 4,
                "requested_storage_gb": 50,
                "pricing": {
                    "hourly": "0.0150",
                    "monthly": "10.95",
                    "currency": "USD"
                }
            }
        ]
        with patch("nodepick_cli.commands.node.get_client", return_value=mock_client):
            # Test 'np node find'
            result = runner.invoke(app, ["node", "find", "-c", "2", "-m", "4", "-s", "50", "-p", "50"], env={"COLUMNS": "160"})
            self.assertEqual(result.exit_code, 0)
            # Verify required columns are present in output:
            # host id, region, datacenter, ram, disk, cpu, price-per-hour, price-per-month
            self.assertIn("Host ID", result.output)
            self.assertIn("Region", result.output)
            self.assertIn("Datacenter", result.output)
            self.assertIn("RAM (GB)", result.output)
            self.assertIn("Disk (GB)", result.output)
            self.assertIn("CPU (Cores)", result.output)
            self.assertIn("Price/hr ($)", result.output)
            self.assertIn("Price/mo ($)", result.output)
            self.assertIn("host-1", result.output)
            self.assertIn("fmt1", result.output)
            self.assertIn("facility-1", result.output)
            self.assertIn("$0.0150", result.output)
            self.assertIn("$10.95", result.output)

            # Verify requested values (4, 50, 2) are displayed, NOT host capacity (32, 500, 16)
            self.assertIn("4", result.output)
            self.assertIn("50", result.output)
            self.assertIn("2", result.output)

            # Test shortcut 'np find'
            res_shortcut = runner.invoke(app, ["find", "-c", "2", "-m", "4", "-s", "50"], env={"COLUMNS": "160"})
            self.assertEqual(res_shortcut.exit_code, 0)
            self.assertIn("Host ID", res_shortcut.output)
            self.assertIn("$0.0150", res_shortcut.output)

    def test_node_create_with_vpc_and_no_network_flag(self):
        from unittest.mock import patch, MagicMock
        mock_client = MagicMock()
        mock_client.node_create.return_value = {"vm_uuid": "node-new-123"}
        with patch("nodepick_cli.commands.node.get_client", return_value=mock_client):
            # 1. Create with --vpc (verifies default memory is 1 GB / value of 1)
            result = runner.invoke(app, ["node", "create", "--name", "my-node", "--vpc", "devnet"])
            self.assertEqual(result.exit_code, 0)
            self.assertIn("Node created successfully", result.output)
            mock_client.node_create.assert_called_once_with(
                memory=1,
                cpu=1,
                display_name="my-node",
                storage_gb=None,
                vpc="devnet",
            )

            # 2. Create with custom --memory 2
            mock_client.node_create.reset_mock()
            result_mem = runner.invoke(app, ["node", "create", "--name", "my-node-2", "--memory", "2"])
            self.assertEqual(result_mem.exit_code, 0)
            mock_client.node_create.assert_called_once_with(
                memory=2,
                cpu=1,
                display_name="my-node-2",
                storage_gb=None,
                vpc=None,
            )

            # 3. Verify --network option no longer exists
            result_invalid = runner.invoke(app, ["node", "create", "--network", "public"])
            self.assertNotEqual(result_invalid.exit_code, 0)
            self.assertIn("No such option: --network", result_invalid.output)

            # 4. Verify min constraints in CLI (cpu >= 1, memory >= 1 GB, storage >= 10 GB)
            res_bad_cpu = runner.invoke(app, ["node", "create", "--cpu", "0"])
            self.assertNotEqual(res_bad_cpu.exit_code, 0)

            res_bad_mem = runner.invoke(app, ["node", "create", "--memory", "0"])
            self.assertNotEqual(res_bad_mem.exit_code, 0)

            res_bad_storage = runner.invoke(app, ["node", "create", "--storage", "5"])
            self.assertNotEqual(res_bad_storage.exit_code, 0)

    def test_node_attach_and_detach_ip_ipv4(self):
        from unittest.mock import patch, MagicMock
        mock_client = MagicMock()
        mock_client.node_attach_ip.return_value = {"status": "attached", "ip": "1.2.3.4/26", "ipVersion": 4}
        mock_client.node_detach_ip.return_value = {"status": "detached"}
        with patch("nodepick_cli.commands.node.get_client", return_value=mock_client):
            # Standard: np node attach-ip dev
            res1 = runner.invoke(app, ["node", "attach-ip", "dev"])
            self.assertEqual(res1.exit_code, 0)
            self.assertIn("Public IPv4 attached to node dev", res1.output)
            self.assertIn("1.2.3.4/26", res1.output)
            mock_client.node_attach_ip.assert_called_with("dev", ip="auto")

            # Inverted: np node dev attach-ip
            res2 = runner.invoke(app, ["node", "dev", "attach-ip"])
            self.assertEqual(res2.exit_code, 0)
            self.assertIn("Public IPv4 attached to node dev", res2.output)

            # Specific IPv4: np node attach-ip dev --ip 1.2.3.4
            res_spec = runner.invoke(app, ["node", "attach-ip", "dev", "--ip", "1.2.3.4"])
            self.assertEqual(res_spec.exit_code, 0)
            mock_client.node_attach_ip.assert_called_with("dev", ip="1.2.3.4")

            # Detach: np node detach-ip dev and np node dev detach-ip
            res3 = runner.invoke(app, ["node", "detach-ip", "dev"])
            self.assertEqual(res3.exit_code, 0)
            self.assertIn("Public IPv4 detached from node dev", res3.output)

            res4 = runner.invoke(app, ["node", "dev", "detach-ip"])
            self.assertEqual(res4.exit_code, 0)
            self.assertIn("Public IPv4 detached from node dev", res4.output)

    def test_node_attach_and_detach_ip_ipv6(self):
        from unittest.mock import patch, MagicMock
        mock_client = MagicMock()
        mock_client.node_attach_ip.return_value = {"status": "attached", "ip": "2001:470::1/64", "ipVersion": 6}
        mock_client.node_detach_ip.return_value = {"status": "detached"}
        mock_client.node_get_details.return_value = {
            "connect": {"publicIpv6": "2001:470::1/64"}
        }
        with patch("nodepick_cli.commands.node.get_client", return_value=mock_client):
            # Standard with --ip auto-ipv6: np node attach-ip dev --ip auto-ipv6
            res1 = runner.invoke(app, ["node", "attach-ip", "dev", "--ip", "auto-ipv6"])
            self.assertEqual(res1.exit_code, 0)
            self.assertIn("Public IPv6 attached to node dev", res1.output)
            mock_client.node_attach_ip.assert_called_with("dev", ip="auto-ipv6")

            # Inverted with --ip ipv6: np node dev attach-ip --ip ipv6
            res2 = runner.invoke(app, ["node", "dev", "attach-ip", "--ip", "ipv6"])
            self.assertEqual(res2.exit_code, 0)
            self.assertIn("Public IPv6 attached to node dev", res2.output)

            # Auto-detected IPv6 address string: np node attach-ip dev --ip 2001:470::1
            res_addr = runner.invoke(app, ["node", "attach-ip", "dev", "--ip", "2001:470::1"])
            self.assertEqual(res_addr.exit_code, 0)
            mock_client.node_attach_ip.assert_called_with("dev", ip="2001:470::1")

            # Verify --ipv6 is no longer an option on attach-ip
            res_no_opt = runner.invoke(app, ["node", "attach-ip", "dev", "--ipv6"])
            self.assertNotEqual(res_no_opt.exit_code, 0)
            self.assertIn("No such option: --ipv6", res_no_opt.output)

            # Detach IPv6: np node detach-ip dev --ipv6 and np node dev detach-ip --ipv6
            res3 = runner.invoke(app, ["node", "detach-ip", "dev", "--ipv6"])
            self.assertEqual(res3.exit_code, 0)
            self.assertIn("Public IPv6 detached from node dev", res3.output)

            res4 = runner.invoke(app, ["node", "dev", "detach-ip", "--ipv6"])
            self.assertEqual(res4.exit_code, 0)
            self.assertIn("Public IPv6 detached from node dev", res4.output)


if __name__ == "__main__":
    unittest.main()


