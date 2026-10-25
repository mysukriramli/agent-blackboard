#!/usr/bin/env python3
import os
import json
import urllib.request
from datetime import datetime, timezone

TARGET_REPO = "mysukriramli/agent-blackboard"
BLACKBOARD_ISSUE_NUM = 1

def dispatch_bounty(task_id: str, title: str, instructions: str, wire_name: str, payload_data: dict = None):
    """Pushes a verified high-urgency bounty task directly into the central agent blackboard."""
    token = os.getenv("MESH_BOT_TOKEN") or os.getenv("GITHUB_TOKEN")
    if not token:
        print("Notice: No GitHub Token available for bounty dispatch.")
        return

    now_iso = datetime.now(timezone.utc).isoformat()
    structured_task = {
        "task_id": f"{wire_name}_{task_id}_{datetime.now(timezone.utc).strftime('%Y%m%d')}",
        "title": title,
        "status": "open",
        "created_by": wire_name,
        "dispatched_at_utc": now_iso,
        "instructions": instructions,
        "context_payload": payload_data or {},
        "solution_artifact_url": None
    }

    comment_body = (
        f"### 🤖 Autonomous Bounty Dispatch: `{title}`\n\n"
        f"**Originating Wire**: `{wire_name}`  \n"
        f"**Timestamp**: `{now_iso}`\n\n"
        f"```json\n{json.dumps(structured_task, indent=2)}\n```\n"
    )

    url = f"https://api.github.com/repos/{TARGET_REPO}/issues/{BLACKBOARD_ISSUE_NUM}/comments"
    req = urllib.request.Request(
        url,
        data=json.dumps({"body": comment_body}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": f"MeshBountyBroker/{wire_name}",
            "Content-Type": "application/json"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status in (200, 201):
                print(f"Successfully dispatched bounty {task_id} to {TARGET_REPO}")
    except Exception as e:
        print(f"Bounty dispatch failed ({task_id}): {e}")

if __name__ == "__main__":
    # Example standalone invocation
    import sys
    if len(sys.argv) >= 5:
        dispatch_bounty(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        print("Usage: python mesh_bounty_broker.py <task_id> <title> <instructions> <wire_name>")
