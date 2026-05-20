# Model Context Protocol (MCP)

*Phase 1, chapter 5.1 — the protocol that lets an LLM call your tools instead of just reading what you paste at it.*

> ⭐ Star this repo if you find it useful.

> This chapter is the foundation. For a full deep-dive — auth, transports, production servers in Go — see **[MCP for DevOps](/02-mcp-for-devops/00-toc.md)**.

---

## The Problem MCP Solves

Last year I built an internal tool that let our team ask Claude questions about our AWS account. It worked by giving Claude a list of `aws` CLI commands in the prompt and letting it suggest one. We'd copy the suggestion, run it, paste the output back, and ask the follow-up.

It was useful. It was also stupid. The model knew what command to run. The shell knew how to run it. We were the JSON-RPC layer in between, by hand.

That's the gap MCP closes. The Model Context Protocol is a standard for letting an LLM call tools and read resources on the other side of a process boundary. The model says "run `describe_instances`" and a server actually runs it. No copy-paste, no humans-as-API-glue.

By the end of this chapter you'll have:

- A working MCP server in Python that exposes EC2 operations
- A clear mental model of resources, tools, and prompts
- Claude Desktop and VS Code Copilot both talking to your server
- Enough understanding to build MCP servers for whatever your team needs

---

## What MCP Actually Is

MCP is a small JSON-RPC protocol that runs over stdio or HTTP. It defines three things a server can expose to a client:

- **Resources** — read-only data the model can fetch by URI. Logs, configs, files, query results.
- **Tools** — functions the model can call with structured arguments. The verbs.
- **Prompts** — reusable prompt templates the user (not the model) can invoke.

The client — Claude Desktop, VS Code Copilot, your custom app — handles the LLM. The server handles your systems. Neither knows what the other looks like internally; they just speak the protocol.

```
┌──────────────────┐   JSON-RPC over stdio/HTTP   ┌──────────────────┐
│   MCP Client     │ ◀──────────────────────────▶ │   MCP Server     │
│ (Claude Desktop, │                              │ (Your code:      │
│  VS Code, …)     │   tools/list, tools/call,    │  EC2, k8s, RDS…) │
│                  │   resources/read, …          │                  │
└──────────────────┘                              └──────────────────┘
        │                                                  │
        ▼                                                  ▼
       LLM                                          External systems
```

The win is composability. Once a tool is exposed via MCP, every MCP-aware client can use it. You write the EC2 server once. It works in Claude Desktop, in Copilot, in Cursor, in your own agent loop.

---

## MCP vs. Function Calling vs. REST

People ask this constantly. Short version:

- **REST API** — your service exposes endpoints. The LLM has no idea they exist.
- **Function calling** — you describe functions in the LLM provider's format (OpenAI tools, Anthropic tools). The LLM picks one. You run it. Provider-specific.
- **MCP** — same idea as function calling, but standardized across providers and clients. The server is reusable.

If you're building one LLM app that calls one set of functions, function calling is fine. If you're exposing the same operations to multiple LLM apps, multiple teams, or both, write an MCP server.

---

## Setting Up

The official Python SDK is on PyPI as `mcp`. It includes `FastMCP`, a decorator-based API that hides most of the boilerplate.

```bash
pip install "mcp[cli]>=1.2" "boto3>=1.34" "pydantic>=2.7"
```

Configure AWS however you normally do:

```bash
aws configure   # or use AWS_PROFILE and an SSO config
```

Permissions for the server (read-only and start/stop only — never grant `ec2:TerminateInstances` to anything an LLM can reach):

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "ec2:DescribeInstances",
      "ec2:DescribeInstanceStatus",
      "ec2:DescribeVpcs",
      "ec2:StartInstances",
      "ec2:StopInstances",
      "ec2:CreateSnapshot"
    ],
    "Resource": "*"
  }]
}
```

Lock the `Resource` down to specific instance ARNs or tag conditions in production. Don't grant blanket `ec2:StartInstances` and call it a day.

---

## The Server, End to End

We'll build an MCP server that exposes:

- A **resource** for each EC2 instance (read details by URI)
- A **resource** for each VPC
- Four **tools**: get status, start, stop, create snapshot

This is the entire file. Save as `ec2_mcp_server.py`.

```python
# ec2_mcp_server.py
"""MCP server exposing read-only and safe-write EC2 operations."""
from __future__ import annotations
import logging
from typing import Annotated

import boto3
from botocore.exceptions import ClientError
from mcp.server.fastmcp import FastMCP
from pydantic import Field

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("ec2-mcp")

mcp = FastMCP("aws-ec2")
ec2 = boto3.client("ec2")


# ---- helpers ----------------------------------------------------------------

def _name_from_tags(tags: list[dict] | None) -> str:
    for t in tags or []:
        if t["Key"] == "Name":
            return t["Value"]
    return "(unnamed)"


def _serialize_instance(inst: dict) -> dict:
    return {
        "instance_id": inst["InstanceId"],
        "name": _name_from_tags(inst.get("Tags")),
        "type": inst["InstanceType"],
        "state": inst["State"]["Name"],
        "private_ip": inst.get("PrivateIpAddress"),
        "public_ip": inst.get("PublicIpAddress"),
        "vpc_id": inst.get("VpcId"),
        "subnet_id": inst.get("SubnetId"),
        "launch_time": inst["LaunchTime"].isoformat(),
        "tags": {t["Key"]: t["Value"] for t in inst.get("Tags", [])},
    }


# ---- resources --------------------------------------------------------------

@mcp.resource("ec2://instance/{instance_id}")
def get_instance(instance_id: str) -> dict:
    """Return detailed information about one EC2 instance."""
    resp = ec2.describe_instances(InstanceIds=[instance_id])
    for r in resp["Reservations"]:
        for inst in r["Instances"]:
            return _serialize_instance(inst)
    raise ValueError(f"instance {instance_id} not found")


@mcp.resource("ec2://vpc/{vpc_id}")
def get_vpc(vpc_id: str) -> dict:
    """Return detailed information about one VPC."""
    resp = ec2.describe_vpcs(VpcIds=[vpc_id])
    if not resp["Vpcs"]:
        raise ValueError(f"vpc {vpc_id} not found")
    v = resp["Vpcs"][0]
    return {
        "vpc_id": v["VpcId"],
        "state": v["State"],
        "cidr_block": v["CidrBlock"],
        "is_default": v["IsDefault"],
        "tags": {t["Key"]: t["Value"] for t in v.get("Tags", [])},
    }


# ---- tools ------------------------------------------------------------------

@mcp.tool()
def list_instances(
    state: Annotated[str | None,
        Field(description="Filter by state: running, stopped, pending, etc.")] = None,
) -> list[dict]:
    """List EC2 instances in the account, optionally filtered by state."""
    filters = [{"Name": "instance-state-name", "Values": [state]}] if state else []
    resp = ec2.describe_instances(Filters=filters)
    out = []
    for r in resp["Reservations"]:
        for inst in r["Instances"]:
            out.append(_serialize_instance(inst))
    return out


@mcp.tool()
def get_instance_status(
    instance_id: Annotated[str, Field(description="EC2 instance ID, e.g. i-0abc1234")],
) -> dict:
    """Return state plus system and instance status checks."""
    try:
        details = ec2.describe_instances(InstanceIds=[instance_id])
        inst = details["Reservations"][0]["Instances"][0]
        info = _serialize_instance(inst)
        status = ec2.describe_instance_status(
            InstanceIds=[instance_id], IncludeAllInstances=True
        )
        if status["InstanceStatuses"]:
            s = status["InstanceStatuses"][0]
            info["system_status"] = s["SystemStatus"]["Status"]
            info["instance_status"] = s["InstanceStatus"]["Status"]
        return info
    except ClientError as e:
        log.error("get_instance_status failed: %s", e)
        raise


@mcp.tool()
def start_instance(
    instance_id: Annotated[str, Field(description="EC2 instance ID to start")],
) -> dict:
    """Start a stopped EC2 instance. No-op if already running."""
    current = ec2.describe_instances(InstanceIds=[instance_id])
    state = current["Reservations"][0]["Instances"][0]["State"]["Name"]
    if state == "running":
        return {"instance_id": instance_id, "previous_state": state, "action": "noop"}
    ec2.start_instances(InstanceIds=[instance_id])
    return {"instance_id": instance_id, "previous_state": state, "action": "started"}


@mcp.tool()
def stop_instance(
    instance_id: Annotated[str, Field(description="EC2 instance ID to stop")],
) -> dict:
    """Stop a running EC2 instance. No-op if already stopped/stopping."""
    current = ec2.describe_instances(InstanceIds=[instance_id])
    state = current["Reservations"][0]["Instances"][0]["State"]["Name"]
    if state in ("stopped", "stopping"):
        return {"instance_id": instance_id, "previous_state": state, "action": "noop"}
    ec2.stop_instances(InstanceIds=[instance_id])
    return {"instance_id": instance_id, "previous_state": state, "action": "stopping"}


@mcp.tool()
def create_snapshot(
    instance_id: Annotated[str, Field(description="EC2 instance ID to snapshot")],
    description: Annotated[str, Field(description="Snapshot description")] = "Created via MCP",
) -> list[dict]:
    """Snapshot every EBS volume attached to the instance."""
    inst = ec2.describe_instances(InstanceIds=[instance_id])["Reservations"][0]["Instances"][0]
    snaps = []
    for bdm in inst.get("BlockDeviceMappings", []):
        vol_id = bdm["Ebs"]["VolumeId"]
        device = bdm["DeviceName"]
        resp = ec2.create_snapshot(
            VolumeId=vol_id,
            Description=f"{description} - {instance_id} - {device}",
            TagSpecifications=[{
                "ResourceType": "snapshot",
                "Tags": [
                    {"Key": "CreatedBy", "Value": "mcp-server"},
                    {"Key": "SourceInstance", "Value": instance_id},
                ],
            }],
        )
        snaps.append({"snapshot_id": resp["SnapshotId"], "volume_id": vol_id, "device": device})
    return snaps


# ---- prompts ----------------------------------------------------------------

@mcp.prompt()
def triage_instance(instance_id: str) -> str:
    """Reusable prompt to triage a misbehaving instance."""
    return (
        f"Investigate EC2 instance {instance_id}. Steps:\n"
        f"1. Call get_instance_status({instance_id}).\n"
        f"2. If system_status or instance_status is impaired, summarize why.\n"
        f"3. Suggest one concrete remediation. Do NOT call stop_instance unless "
        f"the user explicitly confirms.\n"
    )


if __name__ == "__main__":
    mcp.run()  # stdio transport by default
```

A few things to note about this code:

- **`FastMCP` does the heavy lifting.** Decorators generate the JSON Schema that the client sends to the LLM. Type hints + `Field(description=...)` become tool documentation the model actually sees.
- **No `asyncio.run` or `stdio_server` boilerplate.** `mcp.run()` handles it. The older `Server(...)` API with `stdio_server()` still works but is more verbose.
- **`Annotated[..., Field(...)]`** is the modern Pydantic way to attach descriptions to parameters. Old `description=` arguments on functions don't propagate.
- **Snapshots are tagged** with `CreatedBy=mcp-server`. That way you can find and clean them up later.

> **Warning:** Notice there's no `terminate_instance` tool. Don't expose destructive operations to an MCP server reachable by an LLM. The model will eventually call something you didn't expect.

---

## Running and Testing

The fastest way to see if it works is the MCP CLI inspector, which ships with `mcp[cli]`:

```bash
mcp dev ec2_mcp_server.py
```

This launches an interactive UI where you can list tools, call them with arguments, and see exactly what the protocol traffic looks like. It's invaluable during development.

For an automated smoke test, use the MCP client SDK:

```python
# test_client.py
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    params = StdioServerParameters(command="python", args=["ec2_mcp_server.py"])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("tools:", [t.name for t in tools.tools])

            result = await session.call_tool(
                "list_instances", arguments={"state": "running"}
            )
            print("running instances:")
            for item in result.content:
                print(" -", item.text[:120])


if __name__ == "__main__":
    asyncio.run(main())
```

Run it:

```bash
python test_client.py
```

If `list_instances` returns something sensible, the server works.

---

## Wiring It Into Claude Desktop

Claude Desktop reads `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS (`%APPDATA%\Claude\claude_desktop_config.json` on Windows):

```json
{
  "mcpServers": {
    "aws-ec2": {
      "command": "python",
      "args": ["/absolute/path/to/ec2_mcp_server.py"],
      "env": {
        "AWS_PROFILE": "default",
        "AWS_REGION": "us-east-1"
      }
    }
  }
}
```

Restart Claude Desktop. You should see a tools icon appear in the chat. Ask: *"List my running EC2 instances."* Claude will call `list_instances(state="running")` and summarize what comes back.

---

## Wiring It Into VS Code Copilot

VS Code's GitHub Copilot Chat supports MCP servers as of late 2025. Add to your workspace `.vscode/mcp.json` (or user-level `mcp.json`):

```json
{
  "servers": {
    "aws-ec2": {
      "command": "python",
      "args": ["${workspaceFolder}/ec2_mcp_server.py"],
      "env": {
        "AWS_PROFILE": "default",
        "AWS_REGION": "us-east-1"
      }
    }
  }
}
```

Reload the window. In Copilot Chat, use Agent mode and reference the tools by name, or just ask in plain language. Copilot will pick the right tool based on the descriptions you wrote.

---

## What Good Tool Design Looks Like

You'll write more MCP tools. A few lessons from writing too many:

**Names are part of the prompt.** The LLM picks tools by name and description. `list_instances` is good. `do_ec2_stuff` is not. Match the verb-noun convention every cloud API uses.

**Descriptions matter more than docstrings.** The model reads the description, not the function body. Two crisp sentences > a five-paragraph docstring. Say what the tool does and what it returns.

**Return structured data.** Models handle JSON better than English prose. Let the client format it.

**Make idempotency obvious.** `start_instance` on a running instance should return `"action": "noop"`, not error. Models retry on errors. You don't want them retrying state mutations.

**Surface errors as data, not exceptions, when the error is the model's fault.** Bad instance ID? Return `{"error": "instance not found", "instance_id": "i-0abc"}`. The model can recover from data. Stack traces just confuse it.

**Pre-validate destructive operations.** If you must expose a tool that mutates state, require the model to call a `describe` tool first. Or take a confirmation token: `stop_instance(instance_id, confirm=True)`.

---

## A Failure Story

We added a `delete_snapshot` tool to a development MCP server. "Just for testing." A coworker ran a chat session that started "clean up old snapshots from staging" and ended with the model deleting two production snapshots because their `CreatedBy` tag was missing.

Three things went wrong:

1. The tool was destructive.
2. The tool didn't take a confirmation argument.
3. The IAM role didn't scope by tag, so the model had power it shouldn't have had.

The fix wasn't a smarter prompt. It was: remove the tool. We replaced it with `mark_snapshot_for_deletion`, which adds a tag. A separate, non-LLM cron job actually deletes snapshots that have been tagged for 7+ days.

This pattern — LLM proposes, system disposes — is the right shape for anything destructive. The model is fast and wrong sometimes. Your deletion pipeline should not be both.

---

## Beyond stdio — When to Use HTTP

stdio is great for desktop clients. The server runs as a subprocess of the client. Simple, secure, no networking.

You'll want HTTP (specifically MCP's SSE or streamable HTTP transport) when:

- The server runs in a different process / container / host than the client
- Multiple clients should share one server
- You need to put auth in front of it (OAuth, JWT, mTLS)

`FastMCP` supports HTTP transport with a flag:

```python
if __name__ == "__main__":
    mcp.run(transport="streamable-http")  # serves on http://127.0.0.1:8000/mcp
```

But putting an MCP server on a network is a bigger conversation — authn, authz, audit logs, rate limits. That's covered in [MCP for DevOps](/02-mcp-for-devops/00-toc.md). For local development and personal tools, stay on stdio.

---

## Chapter Summary

- MCP standardizes how LLMs talk to tools. One server, many clients.
- `FastMCP` decorators turn Python functions into MCP tools and resources with minimal boilerplate.
- Resources are read-only and addressed by URI. Tools are verbs the model can call.
- Tool names and descriptions are part of the prompt — write them carefully.
- Never expose destructive operations directly. Mark-for-deletion + async cleanup.
- Start with stdio. Reach for HTTP only when you need network-facing servers.

Next: [AI Agents](05-02-ai-agent.md) — building loops that call these tools to actually get work done.

---

## Resources

- [Model Context Protocol — spec & docs](https://modelcontextprotocol.io/)
- [`modelcontextprotocol/python-sdk`](https://github.com/modelcontextprotocol/python-sdk)
- [Awesome MCP servers](https://github.com/punkpeye/awesome-mcp-servers)
- [MCP for DevOps (this repo's deep dive)](/02-mcp-for-devops/00-toc.md)

---

[![Sponsor](https://img.shields.io/badge/Sponsor-%E2%9D%A4-red?style=for-the-badge)](https://github.com/sponsors/hoalongnatsu)
