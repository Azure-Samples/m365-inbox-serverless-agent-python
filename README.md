# M365 Inbox Agent for Azure Functions (Python) [![Python](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/downloads/) [![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://github.com/codespaces/new?repo=Azure-Samples%2Fm365-inbox-serverless-agent-python)

An AI agent that triages your Microsoft 365 inbox: it escalates urgent mail to Teams, drafts replies, and emails you a daily briefing - all following rules you write in plain markdown.

**Powered by Azure Functions and Microsoft 365 connectors. You bring the markdown logic and a little Python for your rules.**

Run it locally in minutes against sample data, point it at your real inbox, then deploy it so it runs on its own.


## What it does for you

- 📋 **Daily Briefing**: a daily summary of what matters lands in your inbox.
- 🚨 **Escalate**: VIP / urgent mail is posted to your Teams channel, with an @mention.
- ✉️ **Reply**: action-required mail gets a grounded draft reply.
- 💬 **Chat**: ask read-only questions about your recent mail.

→ Full walkthroughs in [docs/use-cases.md](docs/use-cases.md).

## <img src="https://raw.githubusercontent.com/microsoft/fluentui-system-icons/main/assets/Wrench/SVG/ic_fluent_wrench_24_regular.svg" width="20" align="center"> Prerequisites

- [uv](https://docs.astral.sh/uv/), then `uv python install 3.13`.
- [Azurite](https://learn.microsoft.com/en-us/azure/storage/common/storage-use-azurite?tabs=npm-package) for local storage emulation (e.g. `npm install -g azurite`). `func5` launches it on demand if it's on your `PATH`.
- [Azure Developer CLI (`azd`)](https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/install-azd).
- [Azure Functions Core Tools v5 (preview)](https://github.com/Azure/azure-functions-core-tools/releases). This template calls the binary `func5` so v5 sits alongside any existing v4 `func`. Already on v4? See [Troubleshooting: still using v4](docs/troubleshooting.md#still-using-v4).
- [Azure CLI `connector-namespace` extension](https://github.com/Azure/Connectors/tree/main/public-preview/connector-namespace-cli) — needed for `azd up` and real M365 connectors.
- An Azure subscription. `azd provision` (Quickstart step 2) creates the Microsoft Foundry model deployment the agents need, required even for the offline path.

## <img src="https://raw.githubusercontent.com/microsoft/fluentui-system-icons/main/assets/Rocket/SVG/ic_fluent_rocket_24_regular.svg" width="20" align="center"> Quickstart

Five steps: install, get resources, run locally, try it, deploy.

### 1. Install the tools

Follow the prereq links above and make sure the v5 binary is on your `PATH` as `func5`. Then run this once per machine to install the Python worker, templates, and extension bundles (which ships the M365 connectors):

```bash
func5 setup --features python
```

### 2. Get the resources you need

`azd provision` creates the Foundry model deployment the agents require (needed even offline); `hydrate` copies the settings into `local.settings.json`. No API keys - managed identity throughout.

**macOS / Linux:**
```bash
azd provision
./infra/scripts/hydrate-local-settings.sh
```

**Windows:**
```powershell
azd provision
.\infra\scripts\hydrate-local-settings.ps1
```

> Yes - even the offline, sample-data run needs this one-time `azd provision`, because the agents call a Foundry model. It provisions the model deployment only; it never touches your inbox.

### 3. Run the local client

```bash
func5 run                              # terminal A (v5 auto-starts Azurite)
uv run python chat.py                  # terminal B
```

(These commands work identically on macOS, Linux, and Windows.)

> 🪟 **Windows local dev:** If `func5 run` fails with `ModuleNotFoundError: No module named 'azure_functions_agents'`, the Microsoft Store python.exe alias on your `PATH` is shadowing the venv Python. See [Troubleshooting: Windows local dev](docs/troubleshooting.md#windows-local-dev) for the fix - you'll need to remove the Store Python and disable App execution aliases in Windows Settings.

### 4. Try it (offline, safe)

Pick **1**, **2**, or **3**. The client shows a 🟡 Offline banner and runs every agent in **DRY RUN** against `sample-data/inbox/*.json`: it produces the full deliverable as text and calls no connector, so nothing is ever sent. Pick **5** to chat with the sample inbox.

Want it to act on your real inbox while still local? See [Go live with real M365](docs/configuration.md#go-live-with-real-m365).

### 5. Go live (set your recipient and Teams target)

Set who real mail and Teams posts go to, **before** you deploy. Without these, the deployed agents stay in DRY RUN (the chat client's doctor banner will tell you).

```bash
azd env set MAILBOX_OWNER_EMAIL   you@your-tenant.com       # required for LIVE mail
azd env set TEAMS_TEAM_ID         <team-id>                 # optional, enables Teams alerts
azd env set TEAMS_CHANNEL_ID      <channel-id>              # optional, enables Teams alerts
azd env set TEAMS_MENTION_USER_ID "$(az ad signed-in-user show --query id          -o tsv)"   # @mentions you on urgent alerts
azd env set TEAMS_MENTION_NAME    "$(az ad signed-in-user show --query displayName -o tsv)"   # display name for the @mention
```

Get the Teams ids by opening the target channel in Teams → ⋯ → **Get link to channel** (the URL contains both `groupId=` → `TEAMS_TEAM_ID` and `19:...@thread.tacv2` → `TEAMS_CHANNEL_ID`).

Or run `./infra/scripts/discover-teams-ids.ps1` (or `.sh`) to print all four `azd env set` lines pre-filled. More in [docs/configuration.md](docs/configuration.md).

> Already deployed with placeholders? Set them now and re-run `azd up` (or just `azd provision`) to push the new values to the Function App.

### 6. Deploy to Azure, then try it again

```bash
azd up
```

> **Known issue (point-in-time):** `azd up` may currently fail at the deploy step on Python 3.13 - the Flex remote build uses Python 3.11.8 ([Azure/azure-dev#8538](https://github.com/Azure/azure-dev/issues/8538)). Simple workaround: [docs/deploy-python-313.md](docs/deploy-python-313.md). This note can be removed once the bug is fixed.

Now `inbox-triage` fires automatically on every new email - no client, no waiting. Send yourself a message, then watch your Teams channel (VIP / incident) or your inbox (replies). Tail the live trace with `azd monitor --logs`.

### 7. <img src="https://raw.githubusercontent.com/microsoft/fluentui-system-icons/main/assets/Shield/SVG/ic_fluent_shield_24_regular.svg" width="20" align="center"> Make it yours

- ✍️ Edit `skills/vip-rules.md` to set your VIPs, what to skip, and what escalates to Teams.
- 🔁 The `weekly-rule-suggestions` agent proposes tuning that you approve by hand.
- 🔒 Use this repo as a **private template** before adding real rules or tenant data.

→ Full guide: [docs/customize.md](docs/customize.md).

### 8. Clean up

```bash
azd down --purge
```

> Hitting an error? See [docs/troubleshooting.md](docs/troubleshooting.md).

## How it works (the short version)

This is an Azure Functions app on the serverless agents runtime. Each agent is a markdown file (`*.agent.md`) that reasons over your rules in `skills/*.md`; a small `tools/match_rule.py` adds deterministic classification. Microsoft 365 actions go through Entra-authorized MCP connectors - no app secrets, managed identity end to end.

→ Deeper dives: [How it works](docs/how-it-works.md) · [Configuration & deployment](docs/configuration.md) · [Customize](docs/customize.md) · [Troubleshooting & reference](docs/troubleshooting.md)

## Learn more

- [Serverless agents runtime in Azure Functions](https://learn.microsoft.com/en-us/azure/azure-functions/functions-serverless-agents-runtime)
- [Office 365 Outlook connector](https://learn.microsoft.com/en-us/connectors/office365/) · [Microsoft Teams connector](https://learn.microsoft.com/en-us/connectors/teams/)
- [Python vs Markdown variants](docs/how-it-works.md#python-vs-markdown)
