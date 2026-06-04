# Inbox Polling Pattern

If RUN MODE is DRY RUN, call no connectors; use the injected inbox snapshot only.

The inbox triage agent is event-driven: a connector trigger calls it whenever new mail arrives, so it does not poll. The timer agents (daily briefing, weekly suggestions) read on a schedule with a lookback window using the query pattern below.

## Lookback approach (timer agents)

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

## DRY RUN

When Outlook MCP is not configured, the client runs the agent in DRY RUN and injects `sample-data/inbox/*.json` as the inbox snapshot. This supports demos and tests but is not a production inbox source.
