# Configuration &amp; deployment details

← Back to the [README](../README.md)

Going live with your real tenant, what `azd up` provisions, and where everything lives in the repo.

## Go live with real M365

Run the agents against your real Outlook + Teams while still developing locally:

```bash
azd env set MAILBOX_OWNER_EMAIL you@your-tenant.com
./infra/scripts/hydrate-local-settings.sh
./infra/scripts/authorize-connectors.sh
# Ctrl-C the func host, then `uv run func5 start` again
```

`authorize-connectors.sh` is **required** the first time you go live: it runs a one-time OAuth consent so the connector namespace can read your mailbox and send on your behalf. It opens a browser tab per connection and waits until the connection reports `Connected`. Setting the env vars alone is not enough. Until consent completes, LIVE runs fail with `could not read inbox` (the agent stops and sends nothing). Re-running the script is safe; already-authorized connections are skipped.

`chat.py` now shows 🟢 Live. Pick 1, 2, or 3, and the agents read your real inbox and send real mail / Teams posts. `MAILBOX_OWNER_EMAIL` is a safety guardrail: outbound digests go only to that address. Start with your own.

> Routing alerts to more than one Teams channel? See [`skills/teams-channels.md`](../skills/teams-channels.md).

## Deploy to Azure

```bash
azd up
```

**What you get:** `inbox-triage` now fires automatically on every new mail. No `chat.py`, no timer wait. The agent reads, classifies, replies, and posts to Teams on its own.

**Try it:** send yourself an email, then watch the Teams channel (for VIP/incident mail) or your inbox (for action-required replies). Tail the live decision trace:

```bash
azd monitor --logs
```

Redeploy code or rule changes without re-provisioning infrastructure:

```bash
azd deploy
```

## What gets deployed

- Azure Functions app on a serverless hosting plan
- Azure Storage for host state, timer leases, and runtime state
- Application Insights for traces and action logs
- Microsoft Foundry account/project connection and model deployment configuration
- Connector Namespace resources for Outlook and Teams MCP managed servers
- Managed identity and RBAC assignments needed by the Function App
- App settings for `MAILBOX_OWNER_EMAIL`, MCP endpoints, Teams target IDs, and Foundry model settings

## Source code

```text
README.md                         This guide.
chat.py                           Friendly local client for manually triggering timer agents.
.env.example                      Environment variable reference for local and deployed runs.
sample-data/inbox/*.json          Mock inbox messages used as the DRY RUN snapshot and in scenarios/tests.
function_app.py                   Minimal Functions entry point that loads the agents runtime.
inbox-triage.agent.md             Event-driven agent (connector trigger) that classifies new mail and acts.
daily-briefing.agent.md           Timer agent that summarizes inbox and calendar priorities.
weekly-rule-suggestions.agent.md  Timer agent that proposes rule updates for human review.
inbox-chat.agent.md               Read-only conversational agent (no tools) for chatting with your inbox.
agents.config.yaml                Default model and runtime configuration.
mcp.json                          Outlook and Teams MCP server configuration.
tools/                            Local `match_rule` classification tool used by the agents.
skills/vip-rules.md               Editable triage policy used by the agents.
infra/                            Azure resources created by azd.
```

## Cleanup

Delete Azure resources when you are finished:

```bash
azd down --purge
```
