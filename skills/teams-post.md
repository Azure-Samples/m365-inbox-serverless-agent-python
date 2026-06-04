# Teams Channel Posting Pattern

Channel alerts go through the Teams MCP `teams_PostMessageToConversation` action. In DRY RUN (the client injects a `RUN MODE: DRY RUN` block) do not call any connector; draft the alert as text in the run output instead.

## When to post

- VIP stakeholder email that requires immediate awareness.
- Product-impacting incident that matches `vip-rules.md`.
- Daily briefing contains urgent items.
- A rule explicitly says Teams is the first action.

## Post format

- Start with a short severity marker: `🚨`, `⚠️`, or `📌`.
- Include sender, subject, received time, and a 1-2 sentence summary.
- Include the recommended next action.
- Link to the message or thread when MCP provides a safe web link.
- Avoid dumping full email bodies unless the rule explicitly asks for it.

## Mentions

- Use Teams-compatible `<at>User Name</at>` mention syntax only when you have a confirmed mention target from Teams MCP.
- Do not invent user IDs or mention entities.
- If no mention target is available, write a plain-text owner hint instead.

## Environment values

- Team id comes from `$TEAMS_TEAM_ID`.
- Channel id comes from `$TEAMS_CHANNEL_ID`.
- When either id is a placeholder, the client runs the agent in DRY RUN, so no post is attempted.

## Safety

- Teams alerts are for awareness; do not claim an incident was acknowledged or resolved.
- Do not post confidential content to broad channels.
- In DRY RUN, include the alert in the run output only. In LIVE, only fall back to email if the agent prompt explicitly defines an email briefing; otherwise omit the post.
