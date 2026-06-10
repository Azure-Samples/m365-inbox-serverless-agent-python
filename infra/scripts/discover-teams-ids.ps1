$ErrorActionPreference = "Stop"

Write-Output "Microsoft 365 Inbox Agent — Teams configuration discovery"
Write-Output "========================================================"
Write-Output ""

Write-Output "Looking up signed-in Microsoft Graph user..."
$user = az rest --method GET --url "https://graph.microsoft.com/v1.0/me" --query "{id:id, displayName:displayName, userPrincipalName:userPrincipalName}" -o json | ConvertFrom-Json
Write-Output "Signed in as: $($user.displayName) ($($user.userPrincipalName))"
Write-Output ""

Write-Output "Teams you have joined:"
$teams = az rest --method GET --url "https://graph.microsoft.com/v1.0/me/joinedTeams" --query "value[].{id:id,name:displayName}" -o json | ConvertFrom-Json
if (-not $teams -or $teams.Count -eq 0) {
    throw "No joined teams were returned by Microsoft Graph."
}
for ($i = 0; $i -lt $teams.Count; $i++) {
    Write-Output ("  {0}. {1}" -f ($i + 1), $teams[$i].name)
}
Write-Output ""
$teamNumber = [int](Read-Host "Pick a team number")
if ($teamNumber -lt 1 -or $teamNumber -gt $teams.Count) {
    throw "Invalid team number."
}
$team = $teams[$teamNumber - 1]
Write-Output "Selected team: $($team.name)"
Write-Output ""

Write-Output "Channels in selected team:"
$channels = az rest --method GET --url "https://graph.microsoft.com/v1.0/teams/$($team.id)/channels" --query "value[].{id:id,name:displayName}" -o json | ConvertFrom-Json
if (-not $channels -or $channels.Count -eq 0) {
    throw "No channels were returned by Microsoft Graph for the selected team."
}
for ($i = 0; $i -lt $channels.Count; $i++) {
    Write-Output ("  {0}. {1}" -f ($i + 1), $channels[$i].name)
}
Write-Output ""
$channelNumber = [int](Read-Host "Pick a channel number")
if ($channelNumber -lt 1 -or $channelNumber -gt $channels.Count) {
    throw "Invalid channel number."
}
$channel = $channels[$channelNumber - 1]
Write-Output "Selected channel: $($channel.name)"
Write-Output ""

Write-Output "Run these commands to configure the sample:"
Write-Output "azd env set TEAMS_TEAM_ID `"$($team.id)`""
Write-Output "azd env set TEAMS_CHANNEL_ID `"$($channel.id)`""
Write-Output "azd env set TEAMS_MENTION_USER_ID `"$($user.id)`""
Write-Output "azd env set TEAMS_MENTION_NAME `"$($user.displayName)`""
