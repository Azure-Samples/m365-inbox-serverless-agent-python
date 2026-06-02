#!/bin/bash
# Discover Microsoft Teams IDs for agent configuration.
# Prerequisite: az login with an account that can read the target team and channel.
set -euo pipefail

echo "Microsoft 365 Inbox Agent — Teams configuration discovery"
echo "========================================================"
echo

echo "Looking up signed-in Microsoft Graph user..."
USER_JSON=$(az rest --method GET --url "https://graph.microsoft.com/v1.0/me" --query "{id:id, displayName:displayName, userPrincipalName:userPrincipalName}" -o json)
USER_ID=$(echo "$USER_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin).get('id',''))")
USER_NAME=$(echo "$USER_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin).get('displayName',''))")
USER_UPN=$(echo "$USER_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin).get('userPrincipalName',''))")
echo "Signed in as: $USER_NAME ($USER_UPN)"
echo

echo "Teams you have joined:"
TEAMS_JSON=$(az rest --method GET --url "https://graph.microsoft.com/v1.0/me/joinedTeams" --query "value[].{id:id,name:displayName}" -o json)
TEAM_COUNT=$(echo "$TEAMS_JSON" | python3 -c "import json,sys; print(len(json.load(sys.stdin)))")
if [ "$TEAM_COUNT" -eq 0 ]; then
  echo "No joined teams were returned by Microsoft Graph."
  exit 1
fi

echo "$TEAMS_JSON" | python3 -c "import json,sys
teams=json.load(sys.stdin)
for index, team in enumerate(teams, 1):
    print(f'  {index}. {team[\"name\"]}')"
echo
read -r -p "Pick a team number: " TEAM_NUM

TEAM_ID=$(echo "$TEAMS_JSON" | python3 -c "import json,sys
teams=json.load(sys.stdin)
index=int(sys.argv[1])-1
if index < 0 or index >= len(teams):
    raise SystemExit('Invalid team number')
print(teams[index]['id'])" "$TEAM_NUM")
TEAM_NAME=$(echo "$TEAMS_JSON" | python3 -c "import json,sys
teams=json.load(sys.stdin)
print(teams[int(sys.argv[1])-1]['name'])" "$TEAM_NUM")
echo "Selected team: $TEAM_NAME"
echo

echo "Channels in selected team:"
CHANNELS_JSON=$(az rest --method GET --url "https://graph.microsoft.com/v1.0/teams/$TEAM_ID/channels" --query "value[].{id:id,name:displayName}" -o json)
CHANNEL_COUNT=$(echo "$CHANNELS_JSON" | python3 -c "import json,sys; print(len(json.load(sys.stdin)))")
if [ "$CHANNEL_COUNT" -eq 0 ]; then
  echo "No channels were returned by Microsoft Graph for the selected team."
  exit 1
fi

echo "$CHANNELS_JSON" | python3 -c "import json,sys
channels=json.load(sys.stdin)
for index, channel in enumerate(channels, 1):
    print(f'  {index}. {channel[\"name\"]}')"
echo
read -r -p "Pick a channel number: " CHANNEL_NUM

CHANNEL_ID=$(echo "$CHANNELS_JSON" | python3 -c "import json,sys
channels=json.load(sys.stdin)
index=int(sys.argv[1])-1
if index < 0 or index >= len(channels):
    raise SystemExit('Invalid channel number')
print(channels[index]['id'])" "$CHANNEL_NUM")
CHANNEL_NAME=$(echo "$CHANNELS_JSON" | python3 -c "import json,sys
channels=json.load(sys.stdin)
print(channels[int(sys.argv[1])-1]['name'])" "$CHANNEL_NUM")
echo "Selected channel: $CHANNEL_NAME"
echo

echo "Run these commands to configure the sample:"
echo "azd env set TEAMS_TEAM_ID \"$TEAM_ID\""
echo "azd env set TEAMS_CHANNEL_ID \"$CHANNEL_ID\""
echo "azd env set TEAMS_MENTION_USER_ID \"$USER_ID\""
echo "azd env set TEAMS_MENTION_NAME \"$USER_NAME\""
