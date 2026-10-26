#!/usr/bin/env python3
import json
import os
import time
import urllib.request
from datetime import datetime, timezone

POSSIBLE_CONFIG_PATHS = [
    "agent-mesh.json",
    "public/agent-mesh.json"
]
OUTPUT_DIR = "public"
STATUS_FILE = os.path.join(OUTPUT_DIR, "mesh_status.json")

def check_endpoint(url: str, timeout: int = 10) -> dict:
    start = time.perf_counter()
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "AgentMeshSentinel/4.0 (Autonomous Health Auditor)"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
            raw_data = resp.read()
            return {
                "status": "HEALTHY",
                "http_code": resp.status,
                "latency_ms": elapsed_ms,
                "payload_bytes": len(raw_data)
            }
    except Exception as e:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
        return {
            "status": "UNREACHABLE",
            "http_code": getattr(e, "code", 0),
            "latency_ms": elapsed_ms,
            "error": str(e)
        }

def run():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    now_iso = datetime.now(timezone.utc).isoformat()

    config_path = None
    for p in POSSIBLE_CONFIG_PATHS:
        if os.path.exists(p):
            config_path = p
            break

    config = {}
    if config_path:
        with open(config_path, "r", encoding="utf-8") as f:
            try:
                config = json.load(f)
            except Exception as e:
                print(f"Warning: Failed to parse {config_path}: {e}")
    else:
        print("Warning: agent-mesh.json not found in root or public/. Generating baseline status.")

    flat_wires = []
    clusters = config.get("clusters", {})
    if isinstance(clusters, dict) and clusters:
        for cluster_name, wire_list in clusters.items():
            for w in wire_list:
                w["cluster"] = cluster_name
                flat_wires.append(w)
    elif "wires" in config:
        flat_wires = config.get("wires", [])

    health_report = {
        "network": config.get("network_name", "Autonomous Agent Mesh"),
        "audited_at_utc": now_iso,
        "total_wires": len(flat_wires),
        "results": []
    }

    healthy_count = 0
    for wire in flat_wires:
        feed_url = wire.get("primary_feed") or wire.get("feed")
        if not feed_url:
            continue
        check = check_endpoint(feed_url)
        if check["status"] == "HEALTHY":
            healthy_count += 1

        health_report["results"].append({
            "name": wire.get("name"),
            "cluster": wire.get("cluster", "general"),
            "primary_feed": feed_url,
            "health": check
        })

    health_report["summary"] = {
        "healthy_wires": healthy_count,
        "unhealthy_wires": len(flat_wires) - healthy_count,
        "availability_pct": round((healthy_count / len(flat_wires)) * 100, 1) if flat_wires else 0.0
    }

    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(health_report, f, indent=2)

if __name__ == "__main__":
    run()
