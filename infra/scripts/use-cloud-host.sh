#!/usr/bin/env bash
# Source (do not execute) this file:
#   source ./infra/scripts/use-cloud-host.sh
# It exports AGENT_URL + FUNCTION_KEY so `uv run python chat.py` calls the
# deployed Function App in Azure instead of the local Functions host
# (skips needing `azurite` + `uv run func start` in two extra terminals).

_die() { echo "use-cloud-host: $*" >&2; return 1 2>/dev/null || exit 1; }

command -v azd >/dev/null || _die "azd not on PATH" || return 1
command -v az  >/dev/null || _die "az not on PATH"  || return 1

_uri=$(azd env get-value SERVICE_API_URI 2>/dev/null) || _die "no azd env — run 'azd up' first" || return 1
_rg=$(azd env get-value RESOURCE_GROUP 2>/dev/null)        || _die "RESOURCE_GROUP not in azd env"        || return 1
_app=$(azd env get-value AZURE_FUNCTION_APP_NAME 2>/dev/null) || _die "AZURE_FUNCTION_APP_NAME not in azd env" || return 1

_key=$(az functionapp keys list -g "$_rg" -n "$_app" --query functionKeys.default -o tsv 2>/dev/null) \
  || _die "could not fetch function key — try 'az login'" || return 1
[ -n "$_key" ] || _die "function key empty — host may still be starting" || return 1

export AGENT_URL="$_uri"
export FUNCTION_KEY="$_key"
echo "AGENT_URL=$AGENT_URL"
echo "FUNCTION_KEY=***${_key: -4}"
echo "chat.py will now call the deployed Function App ($_app)."
unset _uri _rg _app _key
