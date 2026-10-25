#!/usr/bin/env python3
import json
import os
import time
import urllib.request
from datetime import datetime, timezone

MESH_CONFIG = "agent-mesh.json"
OUTPUT_DIR = "public"
STATUS_FILE = os.path.join(OUTPUT_DIR, "mesh_status.json")

def check_endpoint(url: str, timeout: int = 10) -> dict:
    start = time.perf_counter()
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "AgentMeshSentinel/2.0 (Automated Network Health Check)"}
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

    if not os.path.exists(MESH_CONFIG):
        print(f"Config {MESH_CONFIG} not found.")
        return

    with open(MESH_CONFIG, "r", encoding="utf-8") as f:
        config = json.load(f)

    health_report = {
        "network": config.get("network_name"),
        "audited_at_utc": now_iso,
        "total_wires": len(config.get("wires", [])),
        "results": []
    }

    healthy_count = 0

    for wire in config.get("wires", []):
        feed_url = wire["primary_feed"]
        check = check_endpoint(feed_url)
        if check["status"] == "HEALTHY":
            healthy_count += 1

        health_report["results"].append({
            "name": wire["name"],
            "cluster": wire["cluster"],
            "target_agent": wire["target_agent"],
            "primary_feed": feed_url,
            "health": check
        })

    health_report["summary"] = {
        "healthy_wires": healthy_count,
        "unhealthy_wires": len(config.get("wires", [])) - healthy_count,
        "availability_pct": round((healthy_count / len(config.get("wires", []))) * 100, 1) if config.get("wires") else 0
    }

    # Write JSON health artifact
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(health_report, f, indent=2)

    # Append status summary to public/llms.txt
    llms_path = os.path.join(OUTPUT_DIR, "llms.txt")
    if os.path.exists(llms_path):
        with open(llms_path, "r", encoding="utf-8") as f:
            content = f.read()

        status_block = [
            "",
            "## Federated Wire Mesh Status",
            f"> Audit Time: {now_iso}",
            f"> Active Network Health: {health_report['summary']['healthy_wires']}/{health_report['summary']['total_wires']} Wires Operational ({health_report['summary']['availability_pct']}%)",
            ""
        ]
        for w in health_report["results"]:
            h = w["health"]
            icon = "ONLINE" if h["status"] == "HEALTHY" else "OFFLINE"
            status_block.append(f"- **{w['name']}** [{icon}]: {h.get('latency_ms', 0)}ms | Feed: `{w['primary_feed']}`")

        with open(llms_path, "w", encoding="utf-8") as f:
            f.write(content + "\n".join(status_block) + "\n")

if __name__ == "__main__":
    run()
