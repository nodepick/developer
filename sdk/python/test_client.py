import unittest
from unittest.mock import patch, MagicMock
import httpx
from nodepick import NodePickClient, NodepickMCPClient

class TestNodepickClient(unittest.TestCase):
    @patch("httpx.Client")
    def test_node_create_with_explicit_host_bypasses_discovery(self, mock_client_cls):
        # Setup mocks
        mock_client = mock_client_cls.return_value
        
        mock_post_resp = MagicMock()
        mock_post_resp.json.return_value = {"vm": {"id": "vm-123"}}
        mock_post_resp.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_post_resp
        
        client = NodePickClient(api_key="test-key")
        
        node = client.node_create(system_id="custom-host-id")
        
        self.assertEqual(node["id"], "vm-123")
        self.assertEqual(mock_client.post.call_count, 1)
        call_args = mock_client.post.call_args
        self.assertEqual(call_args[0][0], "/api/v1/nodes")
        payload = call_args[1]["json"]
        self.assertEqual(payload["memory"], 512 * 1024 * 1024)
        self.assertEqual(payload["cpu"], 1)
        self.assertEqual(payload["networkType"], "private")
        self.assertEqual(payload["systemId"], "custom-host-id")
        mock_client.get.assert_not_called()
        client.close()

    @patch("httpx.Client")
    def test_node_create_auto_picks_cheapest_smallest_host(self, mock_client_cls):
        mock_client = mock_client_cls.return_value

        # Mock GET /api/v1/compute with two candidate hosts
        mock_get_resp = MagicMock()
        mock_get_resp.json.return_value = {
            "hosts": [
                {
                    "id": "expensive-big-host",
                    "region": "us-west-1",
                    "cpu": {"cores": 64},
                    "memory_gb": 128,
                    "pricing": {
                        "vcpu_micros_per_hour": 10000,
                        "ram_gib_micros_per_hour": 5000,
                        "storage_gib_micros_per_hour": 100,
                    }
                },
                {
                    "id": "cheapest-small-host",
                    "region": "fmt1",
                    "cpu": {"cores": 16},
                    "memory_gb": 32,
                    "pricing": {
                        "vcpu_micros_per_hour": 2000,
                        "ram_gib_micros_per_hour": 1500,
                        "storage_gib_micros_per_hour": 50,
                    }
                }
            ]
        }
        mock_get_resp.raise_for_status = MagicMock()
        mock_client.get.return_value = mock_get_resp

        mock_post_resp = MagicMock()
        mock_post_resp.json.return_value = {"vm": {"id": "vm-auto-123"}}
        mock_post_resp.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_post_resp

        client = NodePickClient(api_key="test-key")
        node = client.node_create(cpu=2, memory=1024 * 1024 * 1024)

        self.assertEqual(node["id"], "vm-auto-123")
        self.assertEqual(mock_client.get.call_count, 1)
        compute_call = mock_client.get.call_args
        self.assertEqual(compute_call[0][0], "/api/v1/compute")
        self.assertEqual(compute_call[1]["params"]["status"], "active")

        # Verify cheapest-small-host was selected and pinned as systemId
        post_payload = mock_client.post.call_args[1]["json"]
        self.assertEqual(post_payload["systemId"], "cheapest-small-host")
        self.assertEqual(post_payload["region"], "fmt1")
        client.close()

    @patch("httpx.Client")
    def test_node_create_with_vpc_resolution(self, mock_client_cls):
        mock_client = mock_client_cls.return_value

        # Mock GET /api/v1/networking to resolve VPC name
        mock_vpc_resp = MagicMock()
        mock_vpc_resp.json.return_value = {
            "networks": [
                {"id": "vpc-uuid-456", "name": "production-net"}
            ]
        }
        mock_vpc_resp.raise_for_status = MagicMock()
        mock_client.get.return_value = mock_vpc_resp

        mock_post_resp = MagicMock()
        mock_post_resp.json.return_value = {"vm": {"id": "vm-vpc-123"}}
        mock_post_resp.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_post_resp

        client = NodePickClient(api_key="test-key")

        # 1. Using vpc name string
        client.node_create(vpc="production-net", system_id="host-1")
        post_payload = mock_client.post.call_args[1]["json"]
        self.assertEqual(post_payload["networkId"], "vpc-uuid-456")

        # 2. Using direct UUID string
        client.node_create(network_id="a90f1e84-180b-4866-9aa2-947ca793a39e", system_id="host-1")
        post_payload = mock_client.post.call_args[1]["json"]
        self.assertEqual(post_payload["networkId"], "a90f1e84-180b-4866-9aa2-947ca793a39e")

        # 3. Using dict object
        client.node_create(vpc={"id": "vpc-dict-789"}, system_id="host-1")
        post_payload = mock_client.post.call_args[1]["json"]
        self.assertEqual(post_payload["networkId"], "vpc-dict-789")

        client.close()

    @patch("httpx.Client")
    def test_find_compute_filtering_and_pricing(self, mock_client_cls):
        mock_client = mock_client_cls.return_value

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "hosts": [
                {
                    "id": "host-cheap",
                    "region": "fmt1",
                    "cpu": {"cores": 16},
                    "memory_gb": 32,
                    "pricing": {
                        "vcpu_micros_per_hour": 2000,
                        "ram_gib_micros_per_hour": 1500,
                        "storage_gib_micros_per_hour": 50,
                    }
                },
                {
                    "id": "host-expensive",
                    "region": "fmt1",
                    "cpu": {"cores": 32},
                    "memory_gb": 64,
                    "pricing": {
                        "vcpu_micros_per_hour": 100000,
                        "ram_gib_micros_per_hour": 100000,
                        "storage_gib_micros_per_hour": 10000,
                    }
                }
            ]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_client.get.return_value = mock_resp

        client = NodePickClient(api_key="test-key")

        # Query with max_price filter (USD/month)
        hosts = client.find_compute(
            min_cpu=2,
            min_memory_gb=4.0,
            min_storage_gb=20,
            max_price=20.0,
            region="fmt1",
            status="active"
        )

        self.assertEqual(len(hosts), 1)
        self.assertEqual(hosts[0]["id"], "host-cheap")
        self.assertTrue(hosts[0]["estimated_monthly_cost_usd"] < 20.0)
        self.assertAlmostEqual(hosts[0]["estimated_monthly_cost_usd"], 8.03, places=2)

        get_params = mock_client.get.call_args[1]["params"]
        self.assertEqual(get_params["min_cpu"], 2)
        self.assertEqual(get_params["min_memory_gb"], 4.0)
        self.assertEqual(get_params["min_storage_gb"], 20)
        self.assertEqual(get_params["region"], "fmt1")
        self.assertEqual(get_params["status"], "active")

        client.close()

    @patch("httpx.Client")
    def test_node_attach_and_detach_ip(self, mock_client_cls):
        mock_client = mock_client_cls.return_value

        mock_post_resp = MagicMock()
        mock_post_resp.json.return_value = {
            "status": "attached",
            "ip": "184.105.163.137/26",
            "ipVersion": 4,
            "billed": True
        }
        mock_post_resp.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_post_resp

        mock_del_resp = MagicMock()
        mock_del_resp.json.return_value = {"status": "detached"}
        mock_del_resp.raise_for_status = MagicMock()
        mock_client.delete.return_value = mock_del_resp

        client = NodePickClient(api_key="test-key")

        with patch.object(client, "node_list", return_value=[{"vm_uuid": "node-uuid-123"}]):
            # Attach default auto
            attach_res = client.node_attach_ip("node-uuid-123")
            self.assertEqual(attach_res["status"], "attached")
            self.assertEqual(attach_res["ipVersion"], 4)
            mock_client.post.assert_called_once_with(
                "/api/v1/nodes/node-uuid-123/network/ip",
                json={"ip": "auto"}
            )

            # Attach auto-ipv6
            client.node_attach_ip("node-uuid-123", ip="auto-ipv6")
            self.assertEqual(mock_client.post.call_args[1]["json"], {"ip": "auto-ipv6"})

            # Detach IP
            detach_res = client.node_detach_ip("node-uuid-123")
            self.assertEqual(detach_res["status"], "detached")
            mock_client.delete.assert_called_once_with(
                "/api/v1/nodes/node-uuid-123/network/ip",
                params=None
            )

        client.close()

    @patch("httpx.Client")
    def test_vpc_crud(self, mock_client_cls):
        mock_client = mock_client_cls.return_value

        mock_create_resp = MagicMock()
        mock_create_resp.json.return_value = {
            "network": {
                "id": "vpc-1",
                "name": "devnet",
                "subnet": "10.0.1.0/24"
            }
        }
        mock_create_resp.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_create_resp

        mock_list_resp = MagicMock()
        mock_list_resp.json.return_value = {
            "networks": [
                {"id": "vpc-1", "name": "devnet"}
            ]
        }
        mock_list_resp.raise_for_status = MagicMock()

        mock_get_resp = MagicMock()
        mock_get_resp.json.return_value = {
            "network": {"id": "vpc-1", "name": "devnet"}
        }
        mock_get_resp.raise_for_status = MagicMock()

        mock_del_resp = MagicMock()
        mock_del_resp.json.return_value = {"deleted": True}
        mock_del_resp.raise_for_status = MagicMock()
        mock_client.delete.return_value = mock_del_resp

        client = NodePickClient(api_key="test-key")

        # Create
        created = client.vpc_create(name="devnet", region="fmt1")
        self.assertEqual(created["name"], "devnet")
        mock_client.post.assert_called_once()
        self.assertEqual(mock_client.post.call_args[0][0], "/api/v1/networking")
        self.assertEqual(mock_client.post.call_args[1]["json"]["name"], "devnet")

        def mock_get_handler(url, **kwargs):
            if url == "/api/v1/networking":
                return mock_list_resp
            return mock_get_resp

        mock_client.get.side_effect = mock_get_handler

        # List
        vpcs = client.vpc_list()
        self.assertEqual(len(vpcs), 1)
        self.assertEqual(vpcs[0]["id"], "vpc-1")

        # Get
        vpc = client.vpc_get("vpc-1")
        self.assertEqual(vpc["id"], "vpc-1")

        # Delete
        deleted = client.vpc_delete("vpc-1")
        self.assertTrue(deleted["deleted"])
        mock_client.delete.assert_called_once_with("/api/v1/networking/vpc-1")

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
        with patch.object(client, "node_list", return_value=[{"vm_uuid": "vm-123"}]), patch("time.sleep", MagicMock()) as mock_sleep:
            res = client.node_delete("vm-123")
            
            # Assert
            self.assertEqual(res["status"], "deleting")
            mock_client.delete.assert_called_once_with("/api/v1/nodes/vm-123")
            self.assertEqual(mock_client.get.call_count, 2)
            mock_sleep.assert_called_once_with(1.0)
            
        client.close()

    @patch("httpx.Client")
    def test_node_not_found_raises_error(self, mock_client_cls):
        client = NodePickClient(api_key="test-key")
        with patch.object(client, "node_list", return_value=[{"display_name": "other-node", "vm_uuid": "uuid-999"}]):
            with self.assertRaises(ValueError) as ctx:
                client.node_delete("dev")
            self.assertIn("Node not found", str(ctx.exception))
        client.close()

    @patch("httpx.Client")
    def test_mcp_client_creation(self, mock_client_cls):
        client = NodePickClient(api_key="test-key")
        mock_details = {
            "connect": {
                "mcpUrl": "https://fmt1-sr3.entic.net:10010",
                "mcpApiKey": "secret-mcp-key"
            }
        }
        with patch.object(client, "node_get_details", return_value=mock_details):
            mcp_client = client.mcp("node-123")
            self.assertIsInstance(mcp_client, NodepickMCPClient)
            self.assertEqual(mcp_client.url, "https://fmt1-sr3.entic.net:10010")
            self.assertEqual(mcp_client.api_key, "secret-mcp-key")
        client.close()

if __name__ == "__main__":
    unittest.main()
