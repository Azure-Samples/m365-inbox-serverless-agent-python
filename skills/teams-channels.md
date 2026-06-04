# Teams Channel Routing

Teams alerts can post to more than one channel. There is one **default channel**
plus any number of optional **named routes**. A rule opts into a named route; if
it does not, or the route is not configured, the alert goes to the default.

## Default channel (always present, distinct)

The default channel is the pair of environment variables:

- `TEAMS_TEAM_ID`
- `TEAMS_CHANNEL_ID`

Every Teams alert uses the default unless a matched rule names a configured
route. The default is never replaced by a named route — it is the fallback.

## Named routes (optional, additive)

A named route is just two extra environment variables, suffixed with the
upper-cased route name:

- `TEAMS_TEAM_ID__<ROUTE>`
- `TEAMS_CHANNEL_ID__<ROUTE>`

Route names are short lowercase identifiers (`[a-z0-9]`, internal hyphens
allowed), and the env suffix is the route upper-cased with `-` replaced by `_`.

| Route name | Team id env | Channel id env |
| --- | --- | --- |
| *(default)* | `TEAMS_TEAM_ID` | `TEAMS_CHANNEL_ID` |
| `incidents` | `TEAMS_TEAM_ID__INCIDENTS` | `TEAMS_CHANNEL_ID__INCIDENTS` |
| `team-updates` | `TEAMS_TEAM_ID__TEAM_UPDATES` | `TEAMS_CHANNEL_ID__TEAM_UPDATES` |

Get a team/channel id pair from the Teams channel link
(`groupId=<TEAM_ID>` and the `19:…@thread.tacv2` channel id). Never commit real
ids — keep them in environment/`local.settings.json` (gitignored).

- **Local runs:** set the env vars in `local.settings.json` (or `azd env set …`
  then re-run `infra/scripts/hydrate-local-settings.sh`).
- **Deployed:** the **default** channel (`TEAMS_TEAM_ID` / `TEAMS_CHANNEL_ID`) is
  wired through Bicep, so `azd env set TEAMS_TEAM_ID <id>` + `azd provision`
  pushes it to the Function App. **Named routes** are dynamic, so Bicep cannot
  enumerate them — set each one directly on the deployed app, e.g.
  `az functionapp config appsettings set -g <rg> -n <app> --settings TEAMS_TEAM_ID__INCIDENTS=<id> TEAMS_CHANNEL_ID__INCIDENTS=<id>`.

## How to add a route

1. Pick a route name, e.g. `incidents`.
2. Set `TEAMS_TEAM_ID__INCIDENTS` and `TEAMS_CHANNEL_ID__INCIDENTS`.
3. Add a `Channel:` line to the rule that should use it, in
   `skills/vip-rules.md`:

   ```markdown
   ### Rule N: …
   - **Trigger:** …
   - **Action:** Post a Teams alert first.
   - **Channel:** incidents
   ```

No code or infrastructure change is needed — the Teams connector already accepts
the target channel per call, and `match_rule` resolves the route to a recipient.

## How routing resolves (match_rule)

When an email matches a rule, the `match_rule` tool resolves its `Channel:`:

- **No `Channel:` line** — no routing fields are returned; the agent posts to the
  default channel.
- **`Channel:` names a fully-wired route** — `match_rule` returns
  `route_resolved: true` and a `teams_recipient` object
  `{ "groupId": …, "channelId": … }`. The agent copies it straight into the
  Teams post's `body.recipient`.
- **`Channel:` names an unset/invalid route** — `match_rule` returns
  `route_resolved: false` and no `teams_recipient`; the agent falls back to the
  default channel (so a misconfigured route never blocks the alert).

`route_resolved` and `channel` are diagnostic only — never post them to the
channel.
