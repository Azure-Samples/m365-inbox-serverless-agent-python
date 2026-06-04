# M365 Inbox Agent for Azure Functions (Python) [![Python](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/downloads/) [![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://github.com/codespaces/new?repo=Azure-Samples%2Fm365-inbox-agent-functions-python) [![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template/uri/<TODO-integrator-fill>)

**Think of it as [🦞 OpenClaw](https://github.com/openclaw/openclaw) for the business: a skills-driven agent that actually does things, but secured by Azure managed identity, Entra-authorized M365 connectors, and your own auditable Python functions.**

An inbox-triage sample for the Azure Functions Serverless Agents Runtime (preview). Three agents read a Microsoft 365 inbox, decide what matters, send replies, post urgent alerts to Teams, and suggest rule changes for a human to approve.

You can run all three agents fully locally. Use `uv run func start` against your real Outlook + Teams via the MCP connectors, or run offline against `sample-data/inbox/*.json` after a one-time `azd provision` (creates the Foundry model deployment the agents need). The one capability that only works deployed is the OnNewEmailV3 event trigger that fires `inbox-triage` automatically on new mail; locally you fire it manually from `chat.py`.

> 📝 Prefer pure markdown with no custom Python? See the [markdown-only sibling](https://github.com/Azure-Samples/m365-inbox-agent-functions-markdown). Full comparison at [the bottom](#-python-variant-vs-markdown-variant).

## <img src="https://raw.githubusercontent.com/microsoft/fluentui-system-icons/main/assets/Wrench/SVG/ic_fluent_wrench_24_regular.svg" width="22" align="center"> Prerequisites

- Python 3.13+. Easiest install: [uv](https://docs.astral.sh/uv/). Then `uv python install 3.13`.
- [Azure Functions Core Tools v4](https://learn.microsoft.com/en-us/azure/azure-functions/functions-run-local) ≥ 4.12.0 (v5 preview is not yet compatible)
- [Azure Developer CLI (`azd`)](https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/)
- For live M365 or deploy: an Azure subscription, a Microsoft Foundry project/model deployment, and permission to authorize Microsoft 365 connectors
- The `connector-namespace` Azure CLI extension (needed for live M365 or `azd up`):

  ```bash
  curl -fsSL https://aka.ms/connector-namespace-cli-install | sh
  ```

  PowerShell + offline install: [Connectors quickstart](https://sandboxes.azure.com/docs/sandboxes/connectors).

## <img src="https://raw.githubusercontent.com/microsoft/fluentui-system-icons/main/assets/Shield/SVG/ic_fluent_shield_24_regular.svg" width="22" align="center"> Make it yours (private copy)

Once you start editing rules, sample inbox data, or running against your real M365 tenant, you'll want a private copy. Public forks cannot be made private on GitHub. Use this repo as a template instead: click <kbd>Use this template</kbd> at the top of GitHub and choose Private, or with [GitHub CLI](https://cli.github.com/):

```bash
OWNER=$(gh api user --jq .login)   # or override with your org
REPO=my-inbox-agent                # or override with any name

gh repo create "$OWNER/$REPO" \
  --template Azure-Samples/m365-inbox-agent-functions-python \
  --private --clone
```

This creates an independent repo with no fork relationship, so accidental PRs back to `Azure-Samples` are not possible.

Files most likely to contain personal/tenant information:

- `skills/vip-rules.md`, `skills/triage-rules.md`: your VIPs and triage logic
- `sample-data/inbox/*.json`: any real mail you paste in for testing
- `local.settings.json`, `.env`: secrets and endpoints (already gitignored)
- `infra/main.parameters.json`: subscription/tenant-specific values if you customize

Even in a private repo, never commit real secrets. This sample uses managed identity for Foundry and Entra-authorized connectors for Microsoft 365, so there are no app-managed credentials to leak. For any custom integrations you add, keep that pattern (managed identity, then role assignment) rather than pasting keys.

**Getting upstream updates.** Sync your private copy from this repo with a single GitHub CLI command, then pull locally:

```bash
gh repo sync "$OWNER/$REPO" --source Azure-Samples/m365-inbox-agent-functions-python
git pull
```

The Functions Serverless Agents Runtime is in preview, so expect occasional fixes worth pulling in. Your edits to `skills/`, `sample-data/`, and `infra/main.parameters.json` will typically merge cleanly.

## <img src="https://raw.githubusercontent.com/microsoft/fluentui-system-icons/main/assets/Rocket/SVG/ic_fluent_rocket_24_regular.svg" width="22" align="center"> Quickstart

### One-time setup

```bash
brew tap azure/functions
brew install azure-functions-core-tools@4
npm install -g azurite
curl -LsSf https://astral.sh/uv/install.sh | sh
```

> Linux / Windows / WSL: use the [Core Tools v4 install guide](https://learn.microsoft.com/en-us/azure/azure-functions/functions-run-local#install-the-azure-functions-core-tools), [Azurite install guide](https://learn.microsoft.com/en-us/azure/storage/common/storage-use-azurite), and [uv install guide](https://docs.astral.sh/uv/getting-started/installation/).

### Run it offline (sample-data)

```bash
# Terminal A
azurite --silent --location .azurite

# Terminal B
azd provision
./infra/scripts/hydrate-local-settings.sh
uv run func start

# Terminal C
uv run python chat.py     # pick 1, 2, or 3
```

`chat.py` shows a 🟡 Offline banner. The agent reads `sample-data/inbox/*.json` and logs what it would have done to `out/read-log.txt`. No real email or Teams post is sent.

```text
[2026-06-03T00:00:00+00:00] inbox-triage list_inbox returned 5 messages from sample-data/inbox
[2026-06-03T00:00:01+00:00] inbox-triage match_rule matched "URGENT: Customer renewal blocker needs decision today" as post_teams (VIP contact)
[2026-06-03T00:00:02+00:00] inbox-triage post_teams (offline) channel=<TEAMS_CHANNEL_ID> summary="🚨 VIP Alert..."
```

### Go live with real M365 (still local)

```bash
azd env set MAILBOX_OWNER_EMAIL you@your-tenant.com
./infra/scripts/hydrate-local-settings.sh
./infra/scripts/authorize-connectors.sh
# Ctrl-C the func host, then `uv run func start` again
```

`chat.py` now shows 🟢 Live. Pick 1, 2, or 3, and the agents read your real inbox and send real mail / Teams posts. `MAILBOX_OWNER_EMAIL` is a safety guardrail: outbound digests go only to that address. Start with your own.

<details>
<summary>Troubleshooting</summary>

- **`Port 7071 is unavailable`**. Another `func` is still running. `lsof -nP -iTCP:7071 -sTCP:LISTEN` to find the PID, then `kill <pid>`.
- **`ModuleNotFoundError: agent_functions`**. Core Tools picked a Python worker that can't see the venv. Always start with `uv run func start`, not bare `func start`. `uv run` prepends `.venv/bin` so the 3.13 worker is selected.
- **`Connection refused 127.0.0.1:10000`**. Azurite isn't running. Start it in another terminal.
- **`No installed bundle workload satisfies Microsoft.Azure.Functions.ExtensionBundle.Preview`**. You're on Core Tools v5 preview. v5 can't load the Preview bundle yet ([tracking issue #5309](https://github.com/Azure/azure-functions-core-tools/issues/5309)). Stay on v4.
- **Worker exits with SIGTERM 143 on startup**. Core Tools < 4.12.0 ships only a Python 3.12 worker. `brew upgrade azure-functions-core-tools@4` to ≥ 4.12.0.
- **Live mode: `403 Forbidden` from MCP**. The connector connection isn't authorized for the signed-in identity. Re-run `./infra/scripts/authorize-connectors.sh` and complete the browser consent for both Outlook and Teams.
- **Windows PowerShell hydrate**. Use `pwsh -File ./infra/scripts/hydrate-local-settings.ps1` (skips ExecutionPolicy without `Set-ExecutionPolicy`).

</details>

## <img src="https://raw.githubusercontent.com/microsoft/fluentui-system-icons/main/assets/Code/SVG/ic_fluent_code_24_regular.svg" width="22" align="center"> Source Code

```text
README.md                         This guide.
chat.py                           Friendly local client for manually triggering timer agents.
.env.example                      Environment variable reference for local and deployed runs.
sample-data/inbox.json            Offline Graph-shaped inbox fixture used by local fallback tools.
sample-data/inbox/*.json          Individual mock inbox messages for scenarios and tests.
function_app.py                   Minimal Functions entry point that loads the agents runtime.
inbox-triage.agent.md             Timer agent that classifies inbox items and takes action.
daily-briefing.agent.md           Timer agent that summarizes inbox and calendar priorities.
weekly-rule-suggestions.agent.md  Timer agent that proposes rule updates for human review.
agents.config.yaml                Default model and runtime configuration.
mcp.json                          Outlook and Teams MCP server configuration.
tools/                            Local Python tools and fallback action logging.
skills/vip-rules.md               Editable triage policy used by the agents.
infra/                            Azure resources created by azd.
```

## <img src="https://raw.githubusercontent.com/microsoft/fluentui-system-icons/main/assets/Cloud/SVG/ic_fluent_cloud_24_regular.svg" width="22" align="center"> Deploy to Azure

```bash
azd up
```

**What you get:** `inbox-triage` now fires automatically on every new mail. No `chat.py`, no timer wait. The agent reads, classifies, replies, and posts to Teams on its own.

**Try it:** send yourself an email, then watch the Teams channel (for VIP/incident mail) or your inbox (for action-required replies). Tail the live decision trace:

```bash
azd monitor --logs
```

> **Migrating from an earlier version?** `MAILBOX_OWNER_EMAIL` was previously `TO_EMAIL`. Run `azd env set MAILBOX_OWNER_EMAIL <value>`, then delete the old `TO_EMAIL=...` line from `.azure/<env>/.env`.

## <img src="https://raw.githubusercontent.com/microsoft/fluentui-system-icons/main/assets/Cloud/SVG/ic_fluent_cloud_24_regular.svg" width="22" align="center"> What Gets Deployed

- Azure Functions app on a serverless hosting plan
- Azure Storage for host state, timer leases, and runtime state
- Application Insights for traces and action logs
- Microsoft Foundry account/project connection and model deployment configuration
- Connector Namespace resources for Outlook and Teams MCP managed servers
- Managed identity and RBAC assignments needed by the Function App
- App settings for `MAILBOX_OWNER_EMAIL`, MCP endpoints, Teams target IDs, and Foundry model settings

## <img src="https://raw.githubusercontent.com/microsoft/fluentui-system-icons/main/assets/Building/SVG/ic_fluent_building_24_regular.svg" width="22" align="center"> Architecture

```mermaid
flowchart TD
    User["Developer or operator"] --> Func["Azure Function App\nServerless Agents Runtime"]

    subgraph FunctionApp["Function App"]
        InboxAgent["Agent: inbox-triage\nOnNewEmailV3 connector trigger"]
        BriefingAgent["Agent: daily-briefing\nDaily digest (timer)"]
        RulesAgent["Agent: weekly-rule-suggestions\nHuman-in-the-loop tuning (timer)"]
    end

    Func --> FunctionApp
    FunctionApp --> MCP["MCP layer\nConnector Namespace managed servers"]

    subgraph M365["Microsoft 365 services"]
        Outlook["Outlook\nInbox, mail send"]
        Calendar["Calendar\nAvailability context"]
        Teams["Teams Channel\nUrgent alerts"]
    end

    MCP --> Outlook
    MCP --> Calendar
    MCP --> Teams

    Storage["Azure Storage\nTimer leases and state"] --> Func
    Func --> AppInsights["Application Insights\nLogs and traces"]
    Func --> Storage

    InboxAgent --> MCP
    BriefingAgent --> MCP
    RulesAgent --> MCP
    InboxAgent --> AppInsights
    BriefingAgent --> AppInsights
    RulesAgent --> AppInsights
```

## <img src="https://raw.githubusercontent.com/microsoft/fluentui-system-icons/main/assets/Flowchart/SVG/ic_fluent_flowchart_24_regular.svg" width="22" align="center"> How the building blocks work

| Building block | Tool that implements it | Skill that explains it | Agent that uses it |
| --- | --- | --- | --- |
| Trigger on inbox | Timer trigger declared on `inbox-triage.agent.md`; local manual runs use `POST /admin/functions/inbox-triage` | `skills/vip-rules.md` explains what counts as important inbox work | `inbox-triage` |
| Read inbox | `tools/list_inbox.py` reads Microsoft Graph through Outlook MCP when configured, or `sample-data/inbox.json` offline | `skills/vip-rules.md` describes VIP, incident, FYI, and action-required handling | `inbox-triage`, `daily-briefing`, `weekly-rule-suggestions` |
| Send email | Outlook MCP `sendMail` through the Connector Namespace; local fallback logs the draft action | `skills/vip-rules.md` explains when to draft or send a reply | `inbox-triage` |
| Post to Teams | Teams MCP channel-post tool through the Connector Namespace; local fallback logs the Teams alert | `skills/vip-rules.md` explains escalation criteria | `inbox-triage`, `daily-briefing` |

## <img src="https://raw.githubusercontent.com/microsoft/fluentui-system-icons/main/assets/Beaker/SVG/ic_fluent_beaker_24_regular.svg" width="22" align="center"> Scenarios

### <img src="https://raw.githubusercontent.com/microsoft/fluentui-system-icons/main/assets/Star/SVG/ic_fluent_star_24_regular.svg" width="22" align="center"> 1. VIP urgent mail posts to Teams

**Goal:** verify the agent recognizes VIP urgency and routes to Teams. In Python offline mode, verify the local log; with connectors authorized, verify the real Teams post.

**Setup:** the message is already in `sample-data/inbox/01-vip-urgent.json` (no action needed).

<details><summary>What's in the message</summary>

```json
{
  "subject": "URGENT: Customer renewal blocker needs decision today",
  "from": { "emailAddress": { "name": "Morgan Lee", "address": "vip-name@example.com" } },
  "body": { "content": "...blocked on the discount approval. We need a decision today..." }
}
```

</details>

**Run:**

```bash
uv run python chat.py   # then pick 1
```

**What you should see (offline / Python):**
- In the `func start` terminal: lines like `inbox-triage: classified URGENT... as vip` and `dispatching Teams alert via tool fallback`.
- In `out/read-log.txt`: `[<ts>] inbox-triage post_teams (offline) channel=<TEAMS_CHANNEL_ID> summary="🚨 VIP Alert..."`.
- Verify with: `tail -n 20 out/read-log.txt`.

**What you should see (deployed / connectors authorized):**
- A real message appears in the configured Teams channel within about one minute.
- Application Insights `traces` shows the VIP decision and Teams post.

### <img src="https://raw.githubusercontent.com/microsoft/fluentui-system-icons/main/assets/Warning/SVG/ic_fluent_warning_24_regular.svg" width="22" align="center"> 2. Incident alert becomes a briefing item

**Goal:** verify the agent treats a P1 incident as urgent and includes it in the next briefing.

**Setup:** the message is already in `sample-data/inbox/03-incident-alert.json` (no action needed).

<details><summary>What's in the message</summary>

```json
{
  "subject": "P1 IcM: Checkout API elevated failures",
  "from": { "emailAddress": { "name": "Incident Bot", "address": "incident.bot@contoso.example" } },
  "body": { "content": "Severity: P1... Product: Checkout API... Impact: 18%..." }
}
```

</details>

**Run:**

```bash
uv run python chat.py   # pick 1 for triage, then pick 2 for daily-briefing
```

**What you should see (offline / Python):**
- In the `func start` terminal: incident classification plus a briefing summary that names Checkout API.
- In `out/read-log.txt`: `post_teams (offline)` for the incident and `send_reply (offline)` for the daily briefing.
- Verify with: `tail -n 20 out/read-log.txt` and open the newest `out/*.eml`.

**What you should see (deployed / connectors authorized):**
- A Teams alert appears for the P1 incident.
- The configured `MAILBOX_OWNER_EMAIL` mailbox receives a daily briefing that includes severity, product, impact, and owner ask.

### <img src="https://raw.githubusercontent.com/microsoft/fluentui-system-icons/main/assets/Checkmark/SVG/ic_fluent_checkmark_24_regular.svg" width="22" align="center"> 3. Action-required mail gets a reply

**Goal:** verify the agent recognizes a response deadline and prepares a grounded reply.

**Setup:** the message is already in `sample-data/inbox/05-action-required.json` (no action needed).

<details><summary>What's in the message</summary>

```json
{
  "subject": "Action required: Review launch FAQ by Friday",
  "from": { "emailAddress": { "name": "Priya Patel", "address": "priya.patel@contoso.example" } },
  "body": { "content": "Could you review the launch FAQ by Friday..." }
}
```

</details>

**Run:**

```bash
uv run python chat.py   # then pick 1
```

**What you should see (offline / Python):**
- In the `func start` terminal: `action-required` classification and reply planning.
- In `out/read-log.txt`: `[<ts>] inbox-triage send_reply (offline) to=priya.patel@contoso.example subject="..."`.
- Verify with: `tail -n 20 out/read-log.txt` and open the newest matching `out/*.eml`.

**What you should see (deployed / connectors authorized):**
- Outlook sends or drafts a concise reply that acknowledges Friday and lists next steps.
- Application Insights `traces` shows the reply decision.

## <img src="https://raw.githubusercontent.com/microsoft/fluentui-system-icons/main/assets/Edit/SVG/ic_fluent_edit_24_regular.svg" width="22" align="center"> Customizing Rules

Edit `skills/vip-rules.md` to change who counts as a VIP, what should be skipped, and which topics require Teams escalation. Redeploy after changing production rules:

```bash
azd deploy
```

The `weekly-rule-suggestions` agent reviews recent decisions and suggests small policy changes. Treat those suggestions as human-in-the-loop recommendations: copy only the changes you approve into `skills/vip-rules.md`, review them, then redeploy.

## <img src="https://raw.githubusercontent.com/microsoft/fluentui-system-icons/main/assets/Cloud/SVG/ic_fluent_cloud_24_regular.svg" width="22" align="center"> Choosing a model provider

The agents runtime auto-selects a provider from environment variables. This sample defaults to Microsoft Foundry with managed identity. `azd provision` creates the AI Services account + model deployment, and `infra/scripts/hydrate-local-settings.sh` copies the outputs into `local.settings.json`. No API keys.

**Local + production (default), Foundry + Entra ID:**

```bash
AZURE_FUNCTIONS_AGENTS_PROVIDER=foundry
FOUNDRY_PROJECT_ENDPOINT=https://<your-ai-services>.services.ai.azure.com/api/projects/<project>
FOUNDRY_MODEL=gpt-5.4-mini
```

Local auth flows through `DefaultAzureCredential` (your `az login`); deployed auth uses the function app's user-assigned managed identity (`AZURE_CLIENT_ID`).

**Azure OpenAI direct (alternative):** set `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_DEPLOYMENT`. Auth defaults to managed identity; set `AZURE_OPENAI_API_KEY` if you must use keys.

> **Note on GitHub Models for free local dev:** the runtime calls the OpenAI Responses API (`/responses`), which GitHub Models does not implement (`/chat/completions` only). Tracking with the runtime team.

Keep M365 connector endpoint values blank for offline sample-data runs; set them for deployed Microsoft 365 actions.

## <img src="https://raw.githubusercontent.com/microsoft/fluentui-system-icons/main/assets/Broom/SVG/ic_fluent_broom_24_regular.svg" width="22" align="center"> Cleanup

Delete Azure resources when you are finished:

```bash
azd down --purge
```

## <img src="https://raw.githubusercontent.com/microsoft/fluentui-system-icons/main/assets/Bug/SVG/ic_fluent_bug_24_regular.svg" width="22" align="center"> Troubleshooting

| Symptom | Try this |
| --- | --- |
| Connector authorization fails | Reopen the Connector Namespace portal URL from deployment outputs, sign in with the mailbox/channel owner, and reauthorize Outlook and Teams. |
| MCP endpoint missing | Run `azd env get-values` and confirm `OUTLOOK_MCP_ENDPOINT` and `TEAMS_MCP_ENDPOINT` are populated. If blank, rerun `azd up` and check Connector Namespace deployment logs. |
| Timer is not firing | Confirm the Functions host shows the timer trigger loaded at startup. The v5 CLI starts Azurite automatically; pass `--no-azurite` only if you intentionally point `AzureWebJobsStorage` elsewhere. |
| Local run cannot reach Azure | Leave MCP endpoint variables blank and use option 1 in `chat.py`; the tools should read `sample-data/inbox.json` and log actions to `out/read-log.txt`. |
| Manual trigger returns 404 | Confirm the Functions host is running and agent function names are `inbox-triage`, `daily-briefing`, and `weekly-rule-suggestions`. |

## <img src="https://raw.githubusercontent.com/microsoft/fluentui-system-icons/main/assets/Book/SVG/ic_fluent_book_24_regular.svg" width="22" align="center"> Learn More

- [Serverless agents runtime in Azure Functions](https://learn.microsoft.com/en-us/azure/azure-functions/functions-serverless-agents-runtime)
- [Tutorial: Host an MCP server on Azure Functions](https://learn.microsoft.com/en-us/azure/azure-functions/functions-mcp-tutorial)
- [Model Context Protocol specification](https://modelcontextprotocol.io/specification/latest)
- [Office 365 Outlook connector reference](https://learn.microsoft.com/en-us/connectors/office365/)
- [Microsoft Teams connector reference](https://learn.microsoft.com/en-us/connectors/teams/)
- [Azure Functions timer trigger](https://learn.microsoft.com/en-us/azure/azure-functions/functions-bindings-timer)

## <img src="https://raw.githubusercontent.com/microsoft/fluentui-system-icons/main/assets/Mail/SVG/ic_fluent_mail_24_regular.svg" width="22" align="center"> Python variant vs Markdown variant

Both repos define the same three agents, same skills, same Bicep, same governance. The difference is where the logic lives.

| | **This repo (Python)** | [Markdown sibling](https://github.com/Azure-Samples/m365-inbox-agent-functions-markdown) |
|---|---|---|
| Agent logic | LLM reasons from `.agent.md` + skills text, plus custom `tools/*.py` functions | Same, but without `tools/` |
| `tools/` directory | ✅ ~5 Python tools (rule matching, triage actions, etc.) | ❌ none (by design) |
| I/O path | MCP or local file fallback when MCP env vars unset | MCP only (Outlook & Teams managed connectors) |
| Offline dev | `uv run python chat.py` reads `sample-data/inbox/*.json`, writes `.eml`/`.md` to `out/` | Requires provisioned MCP |
| `function_app.py` | One line: `app = create_function_app()` (tools auto-discovered) | Identical one line |
| Hand-written Python | ~1 line + ~300 across `tools/` | ~1 line |

**Pick this repo if** you want a code escape hatch for offline hacking, deterministic rule matching, or learning the SDK.
**Pick the markdown sibling if** you want to see the runtime's declarative promise: a production-shaped M365 agent with effectively zero hand-written code.
