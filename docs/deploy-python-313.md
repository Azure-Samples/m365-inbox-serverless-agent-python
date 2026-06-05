# Deploying on Python 3.13 (Flex Consumption)

← Back to the [README](../README.md)

This app targets **Python 3.13** and depends on packages that are published 3.13‑only
(e.g. `azure-functions==2.1.0`, which declares `Requires-Python >=3.13`). On
**Flex Consumption**, the Azure remote build can pick the wrong Python version and
fail the deploy. This page explains the symptom and the one‑command workaround.

## Symptom

`azd up` / `azd deploy` provisions fine, then the **deploy** step fails during the
remote build:

```
/opt/Kudu/Scripts/starter.sh oryx build /tmp/zipdeploy/extracted -o /home/site/wwwroot \
  --platform python --platform-version 3.11.8 -p packagedir=.python_packages/lib/site-packages
ERROR: Could not find a version that satisfies the requirement azure-functions==2.1.0
       (from versions: ... 1.26.0b3)
ERROR: No matching distribution found for azure-functions==2.1.0
```

The giveaway is `--platform-version 3.11.8`: the remote Oryx build is running on
**Python 3.11**, so pip filters out the 3.13‑only wheel by `Requires-Python`. The
`(from versions: ... 1.26.0b3)` list stops short of `2.x` for the same reason.

## Root cause

The Function App's runtime is correctly set to 3.13
(`functionAppConfig.runtime = { name: python, version: 3.13 }`, verified with
`az functionapp show`), but the **Flex Consumption remote build** ignores it and
defaults the build interpreter to 3.11.8. This is an Azure platform / `azd` defect,
tracked here:

- **azd issue:** https://github.com/Azure/azure-dev/issues/8538

Things that do **not** fix it: changing `infra/main.bicep` `runtimeVersion` to `'3.13'`
and re‑provisioning, restarting the app, or adding a repo‑root `runtime.txt` — the
remote build still uses 3.11.8.

## Workaround — deploy a pre‑built package (no remote build)

Build the dependencies for the target interpreter yourself, then publish the package
as‑is so no remote build runs. The 3.13 runtime container then imports the prebuilt
Linux `cp313` wheels.

```bash
# 1. (re)generate requirements.txt the same way the azd prepackage hook does
uv export --format requirements-txt --no-hashes --no-dev --no-emit-project > requirements.txt

# 2. cross-build Linux cp313 wheels into .python_packages
#    uv evaluates environment markers for the TARGET platform/version
uv pip install \
  --target .python_packages/lib/site-packages \
  --python-platform x86_64-unknown-linux-gnu \
  --python-version 3.13 \
  --only-binary :all: \
  -r requirements.txt

# 3. deploy as-is — skips both local and remote build
func azure functionapp publish <FUNCTION_APP_NAME> --no-build
```

Get `<FUNCTION_APP_NAME>` from `azd env get-values | grep AZURE_FUNCTION_APP_NAME`.

Notes:

- `--only-binary :all:` makes the cross-build **fail fast** if any dependency lacks a
  `cp313` manylinux wheel, instead of silently compiling something unusable.
- `.funcignore` keeps the deployment package clean (excludes `.venv`, caches, etc.);
  `.python_packages` is **not** ignored, so the prebuilt wheels ship.
- A working build includes real Linux native wheels — sanity check with
  `ls .python_packages/lib/site-packages | grep -E 'cpython-313-x86_64-linux-gnu'`.

## After deploying with `func`

Because you bypassed `azd deploy`, run the post‑deploy wiring (connector trigger +
OAuth consent) yourself:

```bash
azd hooks run postdeploy        # creates the OnNewEmail trigger, then opens consent
# or, if you only need to (re)authorize connections:
./infra/scripts/authorize-connectors.sh
```

Verify the result:

```bash
# connections should be Connected, trigger Enabled
az connector-namespace connection show -g <RG> --namespace <CONNECTOR_GATEWAY_NAME> \
  -n office365-outlook --query "properties.overallStatus" -o tsv
az connector-namespace trigger show -g <RG> --namespace <CONNECTOR_GATEWAY_NAME> \
  -n office365-outlook-onnewemail --query "properties.state" -o tsv
```

When the upstream azd issue is fixed, plain `azd up` will work and this workaround
can be removed.
