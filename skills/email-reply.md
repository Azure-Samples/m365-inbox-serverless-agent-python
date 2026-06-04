# Safe Email Reply Pattern

Replies go through the Outlook MCP `office365_SendEmailV2` action. In DRY RUN (the client injects a `RUN MODE: DRY RUN` block) do not call any connector; draft the reply as text in the run output instead.

## Before replying

- Confirm the message expects a response.
- Check `conversationId` and sent mail so you do not reply twice.
- Apply `vip-rules.md` first; rule actions must lead the plan.
- Include only facts present in the message, thread, or trusted context.
- If confidence is low, send a briefing to the user instead of replying to the sender.

## Reply content

- Keep the subject threaded with the per-agent prompt's prefix (for example `[DEMO] Re: <original subject>`) unless sending a digest.
- Be concise, specific, and helpful.
- Avoid commitments about dates, pricing, roadmap, legal terms, security posture, or incident status unless source content explicitly supports them.
- Include a next step when useful.
- Do not expose internal reasoning or rule names to external recipients.

## Execution order

1. In DRY RUN, draft the reply as text and stop; call no connector.
2. In LIVE, call `office365_SendEmailV2` with `To`, the prompt's `Subject` prefix, and an HTML body.
3. After a successful send, mark the original message read with `office365_MarkAsRead_V3`.
4. Record the action in the run summary.

## Never do this

- Never reply twice in the same conversation.
- Never reply to spam-like or phishing-like messages.
- Never send full inbox summaries to the original sender.
- Never mark read before the reply succeeds.
