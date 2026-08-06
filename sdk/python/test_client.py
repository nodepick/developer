import unittest
from unittest.mock import patch, MagicMock
import httpx
from nodepick import NodePickClient, NodepickMCPClient

class TestNodepickClient(unittest.TestCase):
    @patch("httpx.Client")
    def test_node_create_returns_immediately(self, mock_client_cls):
        # Setup mocks
        mock_client = mock_client_cls.return_value
        
        mock_post_resp = MagicMock()
        mock_post_resp.json.return_value = {"vm": {"id": "vm-123"}}
        mock_post_resp.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_post_resp
        
        client = NodePickClient(api_key="test-key")
        
        node = client.node_create()
        
        self.assertEqual(node["id"], "vm-123")
        self.assertEqual(mock_client.post.call_count, 1)
        call_args = mock_client.post.call_args
        self.assertEqual(call_args[0][0], "/api/v1/nodes")
        payload = call_args[1]["json"]
        self.assertEqual(payload["memory"], 512 * 1024 * 1024)
        self.assertEqual(payload["cpu"], 1)
        self.assertEqual(payload["networkType"], "private")
        mock_client.get.assert_not_called()
        client.close()

    @patch("httpx.Client")
    def test_node_wait_polls_with_jitter_until_running(self, mock_client_cls):
        mock_client = mock_client_cls.return_value
        
        mock_get_resp_pending = MagicMock()
        mock_get_resp_pending.json.return_value = {
            "vm": {"id": "vm-123"},
            "vmm": {"state": "Creating"}
        }
        mock_get_resp_pending.raise_for_status = MagicMock()
        
        mock_get_resp_running = MagicMock()
        mock_get_resp_running.json.return_value = {
            "vm": {"id": "vm-123"},
            "vmm": {"state": "Running"}
        }
        mock_get_resp_running.raise_for_status = MagicMock()
        
        mock_client.get.side_effect = [
            mock_get_resp_pending,
            mock_get_resp_running
        ]
        
        client = NodePickClient(api_key="test-key")
        
        with patch("time.sleep", MagicMock()) as mock_sleep:
            progress = list(client.node_wait(["vm-123"], delay=1.0))
            self.assertEqual(progress, [("vm-123", 1, 1)])
            self.assertEqual(mock_client.get.call_count, 2)
            mock_sleep.assert_any_call(1.0)
            
        client.close()

    @patch("httpx.Client")
    def test_node_delete_polls_until_gone(self, mock_client_cls):
        # Setup mocks
        mock_client = mock_client_cls.return_value
        
        mock_delete_resp = MagicMock()
        mock_delete_resp.json.return_value = {"status": "deleting"}
        mock_delete_resp.raise_for_status = MagicMock()
        
        mock_get_resp_still = MagicMock()
        mock_get_resp_still.status_code = 200
        
        mock_get_resp_deleted = MagicMock()
        mock_get_resp_deleted.status_code = 502
        
        mock_client.delete.return_value = mock_delete_resp
        mock_client.get.side_effect = [
            mock_get_resp_still,
            mock_get_resp_deleted
        ]
        
        client = NodePickClient(api_key="test-key")
        
        # Act
        with patch.object(client, "node_list", return_value=[]), patch("time.sleep", MagicMock()) as mock_sleep:
            res = client.node_delete("vm-123")
            
            # Assert
            self.assertEqual(res["status"], "deleting")
            mock_client.delete.assert_called_once_with("/api/v1/nodes/vm-123")
            self.assertEqual(mock_client.get.call_count, 2)
            mock_sleep.assert_called_once_with(1.0)
            
        client.close()

    @patch("httpx.Client")
    def test_mcp_client_creation(self, mock_client_cls):
        client = NodePickClient(api_key="test-key")
        mock_details = {
            "connect": {
                "nmcpUrl": "https://lax1-mg1.entic.net:10010",
                "nmcpApiKey": "secret-mcp-key"
            }
        }
        with patch.object(client, "node_get_details", return_value=mock_details):
            mcp_client = client.mcp("node-123")
            self.assertIsInstance(mcp_client, NodepickMCPClient)
            self.assertEqual(mcp_client.url, "https://lax1-mg1.entic.net:10010")
            self.assertEqual(mcp_client.api_key, "secret-mcp-key")
        client.close()

    @patch("httpx.Client")
    def test_aliases(self, mock_client_cls):
        client = NodePickClient(api_key="test-key")
        self.assertEqual(client.create_node, client.node_create)
        self.assertEqual(client.list_nodes, client.node_list)
        self.assertEqual(client.wait_for_nodes, client.node_wait)
        self.assertEqual(client.get_node_details, client.node_get_details)
        self.assertEqual(client.delete_node, client.node_delete)
        self.assertEqual(client.shutdown_node, client.node_shutdown)
        self.assertEqual(client.reboot_node, client.node_reboot)
        client.close()

if __name__ == "__main__":
    unittest.main()
