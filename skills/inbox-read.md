# Reading Inbox and Sent Mail

If RUN MODE is DRY RUN, call no connectors; use the injected inbox snapshot only.

Mailbox reads go through the Outlook MCP `office365_GetEmailsV3` action. This applies to the timer agents (daily briefing, weekly suggestions). The inbox triage agent is event-driven: it acts on the trigger payload and does not list the inbox.

## Preferred Outlook MCP actions

- Use `office365_GetEmailsV3` with `folderPath="Inbox"` and a `top` limit.
- Set `fetchOnlyUnread=true` for unread-only reads.
- Read sent mail with the same action against the Sent Items folder when building briefings or rule suggestions.
- Use the fields the action returns: id, from, toRecipients, subject, bodyPreview, receivedDateTime, importance, isRead, and conversationId.

## Inbox filter examples

- Last 5 minutes: `receivedDateTime ge <lastCheckpoint>` and `isRead eq false`.
- Last 24 hours: `receivedDateTime ge <now-minus-24h>`.
- Last 7 days: `receivedDateTime ge <now-minus-7d>`.

## Reading bodies

- Prefer previews for classification when enough.
- Fetch full bodies only for messages that need reply drafts, incident summaries, or VIP context.
- Preserve conversation id so the reply can stay in thread.
- Do not include full sensitive bodies in Teams unless the rule explicitly requires it.

## Sent mail for grounding

- Pull sent messages in the same period to identify reply patterns.
- Match by conversation id when possible.
- Cite only real sent-message subjects and dates; never fabricate grounding.

## DRY RUN behavior

When settings are placeholders, the client runs the agent in DRY RUN and injects a snapshot of `sample-data/inbox/*.json` as the inbox. Do not call `office365_GetEmailsV3`; read from the injected snapshot and render the result as text. State that sent mail, calendar, and server-side thread context are not available in DRY RUN.
