# Inbox Polling Pattern

Microsoft 365 mail does not appear as a native inbox-arrival trigger in this sample. The inbox triage agent therefore uses a timer trigger and a lookback window.

## Timer approach

- Run every five minutes for near-real-time triage.
- Track the last successful run in runtime state when available.
- Use a conservative overlap window to avoid missing delayed messages.
- De-duplicate by message id or internet message id.
- Process unread messages first; include recently read messages only for context.

## Query pattern

- Filter on `receivedDateTime` greater than the last checkpoint.
- Sort by newest or oldest consistently.
- Limit each poll with a `top` value to control cost and latency.
- If a page is full, continue with paging until the window is complete or the run budget is reached.

## Reliability

- Treat MCP or Graph failures as transient; log and retry on the next timer tick.
- Do not mark messages read until downstream actions succeed.
- Keep run summaries concise for Application Insights logs.
- Avoid relying on local clock guesses when the service returns timestamps.

## Alternative: Graph webhook to HTTP trigger

For lower latency, use Microsoft Graph change notifications to call an HTTP-triggered Function. That design still needs validation, de-duplication, and a follow-up Graph read because webhook payloads are notifications, not full trusted message bodies.

## Local fallback

When Outlook MCP is not configured, `list_inbox` reads `sample-data/inbox/*.json`. This supports demos and tests but is not a production inbox source.
