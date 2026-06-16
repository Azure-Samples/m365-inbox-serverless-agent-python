# Customize &amp; make it yours

← Back to the [README](../README.md)

How to take a private copy, edit the rules that drive every decision, and let the agent suggest tuning.

## Make it yours (private copy)

Once you start editing rules, sample inbox data, or running against your real M365 tenant, you'll want a private copy. Public forks cannot be made private on GitHub. Use this repo as a template instead: click <kbd>Use this template</kbd> at the top of GitHub and choose Private, or with [GitHub CLI](https://cli.github.com/):

```bash
OWNER=$(gh api user --jq .login)   # or override with your org
REPO=my-inbox-agent                # or override with any name

gh repo create "$OWNER/$REPO" \
  --template Azure-Samples/m365-inbox-serverless-agent-python \
  --private --clone
```

This creates an independent repo with no fork relationship, so accidental PRs back to `Azure-Samples` are not possible.

Files most likely to contain personal/tenant information:

- `skills/vip-rules.md` (and the other `skills/*.md` files): your VIPs and triage logic
- `sample-data/inbox/*.json`: any real mail you paste in for testing
- `local.settings.json`, `.env`: secrets and endpoints (already gitignored)
- `infra/main.parameters.json`: subscription/tenant-specific values if you customize

Even in a private repo, never commit real secrets. This sample uses managed identity for Foundry and Entra-authorized connectors for Microsoft 365, so there are no app-managed credentials to leak. For any custom integrations you add, keep that pattern (managed identity, then role assignment) rather than pasting keys.

**Getting upstream updates.** Sync your private copy from this repo with a single GitHub CLI command, then pull locally:

```bash
gh repo sync "$OWNER/$REPO" --source Azure-Samples/m365-inbox-serverless-agent-python
git pull
```

The Functions Serverless Agents Runtime is in preview, so expect occasional fixes worth pulling in. Your edits to `skills/`, `sample-data/`, and `infra/main.parameters.json` will typically merge cleanly.

## Customizing rules

Edit `skills/vip-rules.md` to change who counts as a VIP, what should be skipped, and which topics require Teams escalation. Redeploy after changing production rules:

```bash
azd deploy
```

The `weekly-rule-suggestions` agent reviews recent decisions and suggests small policy changes. Treat those suggestions as human-in-the-loop recommendations: copy only the changes you approve into `skills/vip-rules.md`, review them, then redeploy.
