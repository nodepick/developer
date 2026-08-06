import os
import time
import sys
import argparse
import httpx
from concurrent.futures import ThreadPoolExecutor

from nodepick import NodePickClient

def create_single_node(client: NodePickClient, index: int):
    start_time = time.time()
    try:
        node = client.node_create()
        create_duration = time.time() - start_time
        return (node, create_duration, index)
    except httpx.HTTPStatusError as e:
        print(f"\nFailed to create node n{index}: {e} - Response: {e.response.text}", file=sys.stderr)
        return (None, time.time() - start_time, index)
    except Exception as e:
        print(f"\nFailed to create node n{index}: {e}", file=sys.stderr)
        return (None, time.time() - start_time, index)

def create_nodes_parallel(client: NodePickClient, num_nodes: int):
    """Creates multiple nodes in parallel using a ThreadPoolExecutor."""
    with ThreadPoolExecutor(max_workers=num_nodes) as executor:
        futures = [executor.submit(create_single_node, client, i + 1) for i in range(num_nodes)]
        results = [future.result() for future in futures]
    return results

def main():
    parser = argparse.ArgumentParser(description="Nodepick Python SDK node deployment example.")
    parser.add_argument("-q", "--quiet", action="store_true", help="Enable quiet output mode.")
    args, _ = parser.parse_known_args()

    quiet = args.quiet or os.getenv("QUIET", "").lower() in ("1", "true", "yes")

    api_key = os.getenv("NODEPICK_API_KEY")
    if not api_key:
        raise RuntimeError("Set the NODEPICK_API_KEY environment variable before running this script.")

    client = NodePickClient(
        api_key=api_key,
        base_url=os.getenv("NODEPICK_BASE_URL", "http://localhost:3000"),
    )

    # Number of nodes we want to spin up
    num_nodes = 1

    with client:
        results = create_nodes_parallel(client, num_nodes)
        finish_create_time = time.time()

        node_data = {}
        for node, create_dur, idx in results:
            if node and node.get("id"):
                node_id = node["id"]
                node_data[node_id] = {
                    "index": idx,
                    "label": f"n{idx}",
                    "create_sec": max(1, int(round(create_dur))),
                    "finish_create_time": finish_create_time,
                }

        node_ids = list(node_data.keys())

        if node_ids:
            for node_id, completed, total in client.node_wait(node_ids):
                now = time.time()
                info = node_data[node_id]
                boot_dur = max(1, int(round(now - info["finish_create_time"])))
                info["boot_sec"] = boot_dur

        if quiet:
            print(f"{len(node_data)} nodes created.")
        else:
            sorted_nodes = sorted(node_data.values(), key=lambda x: x["index"])
            for i, info in enumerate(sorted_nodes):
                lbl = info["label"]
                c_s = f"{info['create_sec']}s"
                b_s = f"{info.get('boot_sec', 0)}s"
                if i == 0:
                    print(f"{lbl}: {c_s} {b_s} ({c_s} to create, {b_s} to boot and show it is running)")
                else:
                    print(f"{lbl}: {c_s} {b_s}")

if __name__ == "__main__":
    main()


