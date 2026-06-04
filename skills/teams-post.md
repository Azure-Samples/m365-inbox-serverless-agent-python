# Teams Channel Posting Pattern

Channel alerts go through the Teams MCP `teams_PostMessageToConversation` action. In DRY RUN (the client injects a `RUN MODE: DRY RUN` block) do not call any connector; draft the alert as text in the run output instead.

## When to post

- VIP stakeholder email that requires immediate awareness.
- Product-impacting incident that matches `vip-rules.md`.
- Daily briefing contains urgent items.
- A rule explicitly says Teams is the first action.

## Call shape

`teams_PostMessageToConversation` takes three flat arguments:

- `poster` — `"Flow bot"`.
- `location` — `"Channel"`.
- `body` — an object:
  `{ "recipient": { "groupId": "$TEAMS_TEAM_ID", "channelId": "$TEAMS_CHANNEL_ID" }, "messageBody": "<html…>" }`.

`messageBody` is **HTML by default** — compose with `<b>`, `<i>`, `<br>`, and
`<a href>` rather than plain text or Markdown.

`recipient` above is the **default channel**. A rule can route its alert to a
different channel: when `match_rule` returns a `teams_recipient` object, copy it
verbatim into `body.recipient` instead. See `teams-channels.md` for the
default-vs-named routing model and how to add a named channel.

## Post format

- Start with a short severity marker: `🚨`, `⚠️`, or `📌`.
- Include sender, subject, received time, and a 1-2 sentence summary.
- Include the recommended next action.
- Link to the message or thread when MCP provides a safe web link.
- Avoid dumping full email bodies unless the rule explicitly asks for it.

## Mentions

- To @mention a person, embed the literal token `<at>UPN-or-email</at>` directly
  in the HTML `messageBody` — e.g. `<at>$MAILBOX_OWNER_EMAIL</at>` to mention the
  owner / "me". The connector resolves it into a real ping; **no** separate tool
  call is required.
- Only mention real, known addresses (the owner, or a sender from the trigger
  data). Do not invent addresses or names.

## One Teams call at a time

`teams_PostMessageToConversation` must be called **one at a time**. If several
alerts need posting, post them in separate steps and wait for each call to
return before the next. Never issue two Teams MCP tool calls in the same step —
concurrent calls on the shared connector session can deadlock.

## Environment values

- Team id comes from `$TEAMS_TEAM_ID`.
- Channel id comes from `$TEAMS_CHANNEL_ID`.
- When either id is a placeholder, the client runs the agent in DRY RUN, so no post is attempted.

## Safety

- Teams alerts are for awareness; do not claim an incident was acknowledged or resolved.
- Do not post confidential content to broad channels.
- In DRY RUN, include the alert in the run output only. In LIVE, only fall back to email if the agent prompt explicitly defines an email briefing; otherwise omit the post.
