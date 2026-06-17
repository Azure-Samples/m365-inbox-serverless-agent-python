# Troubleshooting &amp; reference

← Back to the [README](../README.md)

## Local setup

- **`Port 7071 is unavailable`**. Another `func` is still running. `lsof -nP -iTCP:7071 -sTCP:LISTEN` to find the PID, then `kill <pid>`.
- **`ModuleNotFoundError: agent_functions`**. The Functions host picked a Python worker that can't see the venv. Always start with `uv run func5 start`, not bare `func5 start`. `uv run` prepends `.venv/bin` so the 3.13 worker is selected.
- **Worker exits with SIGTERM 143 on startup**. The Python worker on your machine is older than 3.13. Re-run `func5 setup --features python` to pick up the current preview worker.
- **`No installed bundle workload satisfies Microsoft.Azure.Functions.ExtensionBundle.Preview`**. The extension bundles workload is missing from your v5 install. Run `func5 workload install azure.functions.cli.workloads.extensionbundles` (or `func5 setup --features python`, which installs it as part of the bundle). This was [Azure/azure-functions-core-tools#5309](https://github.com/Azure/azure-functions-core-tools/issues/5309) on early v5 previews and is fixed in `bundles@4.42.0-preview.2` and later.
- **Live mode: `403 Forbidden` from MCP**. The connector connection isn't authorized for the signed-in identity. Re-run `./infra/scripts/authorize-connectors.sh` and complete the browser consent for both Outlook and Teams.
- **Live mode: agent returns `could not read inbox`**. The Outlook connection has not completed OAuth consent (its status is not `Connected`). Run `./infra/scripts/authorize-connectors.sh`, finish the browser consent as the mailbox owner, wait for `Connected`, then retry. This is a one-time step per connection; env vars alone do not authorize it.
- **Windows PowerShell hydrate**. Use `pwsh -File ./infra/scripts/hydrate-local-settings.ps1` (skips ExecutionPolicy without `Set-ExecutionPolicy`).

## Still using v4

If you have an existing Azure Functions Core Tools v4 install (`brew install azure-functions-core-tools@4` on macOS, or the v4 installer on Windows / Linux) and don't want to add v5 yet, you can still run this template:

- Substitute `func` for `func5` everywhere in this repo (`uv run func start`, etc.).
- Start Azurite yourself in a separate terminal before `func start`: `azurite --silent --skipApiVersionCheck --location .azurite`. v4 does not auto-manage it.
- Make sure your Core Tools is ≥ 4.12.0 so the Python 3.13 worker ships.

The v5 path is recommended because it removes the Azurite terminal and ships the extension bundles workload that this template depends on. Once v5 reaches GA, this fallback section goes away.

## Windows local dev

**Symptom:** `uv run func5 start` or `func5 start` fails with:
```
ModuleNotFoundError: No module named 'azure_functions_agents'
```
or
```
ModuleNotFoundError: No module named 'pydantic_core._pydantic_core'
```

**Root cause:** Windows ships Microsoft Store Python by default. When you install Python 3.13 and create a venv, the `func` host scans for Python workers on `PATH` and finds the Store Python 3.11 stub first at `%LocalAppData%\Microsoft\WindowsApps\python.exe`. It then loads the 3.11 worker, which can't import 3.13 venv packages. You need to remove the Store Python and disable its App execution aliases.

**Fix — step by step:**

1. **Remove Microsoft Store Python 3.11:**

   Open PowerShell as Administrator and run:
   ```powershell
   Get-AppxPackage -Name "PythonSoftwareFoundation.Python.3.11" | Remove-AppxPackage
   ```

2. **Disable App execution aliases:**

   - Open Windows Settings → **Apps** → **Advanced app settings** → **App execution aliases**
   - Scroll down to the **App Installer** section
   - Toggle **OFF** all of:
     - `python.exe`
     - `python3.exe`
     - `python3.11.exe`

3. **Verify:**

   Open a fresh PowerShell and confirm the Store Python is gone:
   ```powershell
   where.exe python
   ```
   This should return **nothing** (no output). If it returns a path in `WindowsApps`, the alias is still on.

4. **Retry:**
   ```powershell
   uv run func5 start
   ```

**Note on `hydrate-local-settings.ps1`:** The provisioning script can also set `languageWorkers__python__defaultExecutablePath` to point at your venv Python, which helps — but this mitigation is **not sufficient alone**. The OS-level `PATH` search still happens first, so you must still remove the Store Python and disable aliases. Both steps together ensure the 3.13 worker loads correctly.

**If the issue persists:** Confirm your venv is using Python 3.13 with `uv python --version`. You must have Python 3.13+ installed locally (via `uv python install 3.13` or direct download) and a fresh venv created with `uv sync` after removing Store Python.

## Deployed / connectors

| Symptom | Try this |
| --- | --- |
| Connector authorization fails | Reopen the Connector Namespace portal URL from deployment outputs, sign in with the mailbox/channel owner, and reauthorize Outlook and Teams. |
| MCP endpoint missing | Run `azd env get-values` and confirm `OUTLOOK_MCP_ENDPOINT` and `TEAMS_MCP_ENDPOINT` are populated. If blank, rerun `azd up` and check Connector Namespace deployment logs. |
| Timer is not firing | Confirm the Functions host shows the timer trigger loaded at startup. The v5 CLI starts Azurite automatically; pass `--no-azurite` only if you intentionally point `AzureWebJobsStorage` elsewhere. |
| Local run cannot reach Azure | Leave the MCP endpoint variables blank and use `chat.py`; every agent runs DRY RUN and prints its deliverable as text. Option 4 shows what's missing to go live. |
| Manual trigger returns 404 | Confirm the Functions host is running and agent function names are `inbox-triage`, `daily-briefing`, and `weekly-rule-suggestions`. |
| Deploy fails: `azure-functions==2.1.0 ... No matching distribution found` | The Flex remote build is using Python 3.11.8 instead of 3.13. Use the pre-built deploy workaround in [deploy-python-313.md](deploy-python-313.md). Tracking: [Azure/azure-dev#8538](https://github.com/Azure/azure-dev/issues/8538). |

> **Migrating from an earlier version?** `MAILBOX_OWNER_EMAIL` was previously `TO_EMAIL`. Run `azd env set MAILBOX_OWNER_EMAIL <value>`, then delete the old `TO_EMAIL=...` line from `.azure/<env>/.env`.

## Learn more

- [Serverless agents runtime in Azure Functions](https://learn.microsoft.com/en-us/azure/azure-functions/functions-serverless-agents-runtime)
- [Tutorial: Host an MCP server on Azure Functions](https://learn.microsoft.com/en-us/azure/azure-functions/functions-mcp-tutorial)
- [Model Context Protocol specification](https://modelcontextprotocol.io/specification/latest)
- [Office 365 Outlook connector reference](https://learn.microsoft.com/en-us/connectors/office365/)
- [Microsoft Teams connector reference](https://learn.microsoft.com/en-us/connectors/teams/)
- [Azure Functions timer trigger](https://learn.microsoft.com/en-us/azure/azure-functions/functions-bindings-timer)
