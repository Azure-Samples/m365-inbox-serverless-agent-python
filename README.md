# M365 Inbox Agent for Azure Functions (Python) [![Python](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/downloads/) [![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://github.com/codespaces/new?repo=Azure-Samples%2Fm365-inbox-agent-functions-python)

An AI agent that triages your Microsoft 365 inbox: it escalates urgent mail to Teams, drafts replies, and emails you a daily briefing — all following rules you write in plain markdown.

**Powered by Azure Functions and Microsoft 365 connectors. You bring the markdown logic and a little Python for your rules.**

Run it locally in minutes against sample data, point it at your real inbox, then deploy it so it runs on its own.

> 📝 Prefer pure markdown with no custom Python? See the [markdown-only sibling](https://github.com/Azure-Samples/m365-inbox-agent-functions-markdown) ([how they differ](docs/how-it-works.md#python-vs-markdown)).

## What it does for you

- 🚨 **Escalate** — VIP / urgent mail is posted to your Teams channel, with an @mention.
- ✉️ **Reply** — action-required mail gets a grounded draft reply.
- 📋 **Brief** — a daily summary of what matters lands in your inbox.
- 💬 **Chat** — ask read-only questions about your recent mail.

→ Full walkthroughs in [docs/use-cases.md](docs/use-cases.md).

## <img src="https://raw.githubusercontent.com/microsoft/fluentui-system-icons/main/assets/Wrench/SVG/ic_fluent_wrench_24_regular.svg" width="20" align="center"> Prerequisites

- Python 3.13+. Easiest install: [uv](https://docs.astral.sh/uv/), then `uv python install 3.13`.
- [Azure Functions Core Tools v4](https://learn.microsoft.com/en-us/azure/azure-functions/functions-run-local) ≥ 4.12.0 (the v5 preview is not yet compatible).
- [Azure Developer CLI (`azd`)](https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/).
- An Azure subscription. `azd provision` (Quickstart step 2) creates the Microsoft Foundry model deployment the agents need — required even for the offline path.
- For real M365 (or `azd up`): permission to authorize Microsoft 365 connectors, plus the `connector-namespace` CLI extension:

**macOS / Linux:**
```bash
curl -fsSL https://aka.ms/connector-namespace-cli-install | sh
```

**Windows:**
```powershell
powershell -Command "Invoke-WebRequest -Uri 'https://aka.ms/connector-namespace-cli-install' -OutFile 'install.sh'; wsl bash install.sh"
```

## <img src="https://raw.githubusercontent.com/microsoft/fluentui-system-icons/main/assets/Rocket/SVG/ic_fluent_rocket_24_regular.svg" width="20" align="center"> Quickstart

Five steps: install, get resources, run locally, try it, deploy.

### 1. Install the tools

**macOS:**
```bash
brew tap azure/functions
brew install azure-functions-core-tools@4
brew install azure-dev
npm install -g azurite
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Linux / Windows / WSL:**
Use the [Core Tools v4 install guide](https://learn.microsoft.com/en-us/azure/azure-functions/functions-run-local#install-the-azure-functions-core-tools), [azd install guide](https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/install-azd), [Azurite install guide](https://learn.microsoft.com/en-us/azure/storage/common/storage-use-azurite), and [uv install guide](https://docs.astral.sh/uv/getting-started/installation/).

### 2. Get the resources you need

`azd provision` creates the Foundry model deployment the agents require (needed even offline); `hydrate` copies the settings into `local.settings.json`. No API keys — managed identity throughout.

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

> Yes — even the offline, sample-data run needs this one-time `azd provision`, because the agents call a Foundry model. It provisions the model deployment only; it never touches your inbox.

### 3. Run the local client

```bash
azurite --silent --skipApiVersionCheck --location .azurite   # terminal A
uv run func start                      # terminal B
uv run python chat.py                  # terminal C
```

(These commands work identically on macOS, Linux, and Windows.)

> 🪟 **Windows local dev:** If `uv run func start` fails with `ModuleNotFoundError: No module named 'azure_functions_agents'`, the Microsoft Store python.exe alias on your `PATH` is shadowing the venv Python. See [Troubleshooting: Windows local dev](docs/troubleshooting.md#windows-local-dev) for the fix — you'll need to remove the Store Python and disable App execution aliases in Windows Settings.

### 4. Try it (offline, safe)

Pick **1**, **2**, or **3**. The client shows a 🟡 Offline banner and runs every agent in **DRY RUN** against `sample-data/inbox/*.json`: it produces the full deliverable as text and calls no connector, so nothing is ever sent. Pick **5** to chat with the sample inbox.

Want it to act on your real inbox while still local? See [Go live with real M365](docs/configuration.md#go-live-with-real-m365).

### 5. Deploy to Azure, then try it again

```bash
azd up
```

> **Known issue (point-in-time):** `azd up` may currently fail at the deploy step on Python 3.13 — the Flex remote build uses Python 3.11.8 ([Azure/azure-dev#8538](https://github.com/Azure/azure-dev/issues/8538)). Simple workaround: [docs/deploy-python-313.md](docs/deploy-python-313.md). This note can be removed once the bug is fixed.

Now `inbox-triage` fires automatically on every new email — no client, no waiting. Send yourself a message, then watch your Teams channel (VIP / incident) or your inbox (replies). Tail the live trace with `azd monitor --logs`.

### Clean up

```bash
azd down --purge
```

> Hitting an error? See [docs/troubleshooting.md](docs/troubleshooting.md).

## <img src="https://raw.githubusercontent.com/microsoft/fluentui-system-icons/main/assets/Shield/SVG/ic_fluent_shield_24_regular.svg" width="20" align="center"> Make it yours

- ✍️ Edit `skills/vip-rules.md` to set your VIPs, what to skip, and what escalates to Teams.
- 🔁 The `weekly-rule-suggestions` agent proposes tuning that you approve by hand.
- 🔒 Use this repo as a **private template** before adding real rules or tenant data.

→ Full guide: [docs/customize.md](docs/customize.md).

## How it works (the short version)

This is an Azure Functions app on the serverless agents runtime. Each agent is a markdown file (`*.agent.md`) that reasons over your rules in `skills/*.md`; a small `tools/match_rule.py` adds deterministic classification. Microsoft 365 actions go through Entra-authorized MCP connectors — no app secrets, managed identity end to end.

→ Deeper dives: [How it works](docs/how-it-works.md) · [Configuration & deployment](docs/configuration.md) · [Customize](docs/customize.md) · [Troubleshooting & reference](docs/troubleshooting.md)

## Learn more

- [Serverless agents runtime in Azure Functions](https://learn.microsoft.com/en-us/azure/azure-functions/functions-serverless-agents-runtime)
- [Office 365 Outlook connector](https://learn.microsoft.com/en-us/connectors/office365/) · [Microsoft Teams connector](https://learn.microsoft.com/en-us/connectors/teams/)
- [Python vs Markdown variants](docs/how-it-works.md#python-vs-markdown)
