# Safe Email Reply Pattern

Use Outlook MCP to send or reply in production. The `send_reply` tool is an offline fallback that writes `.eml` files.

## Before replying

- Confirm the message expects a response.
- Check `conversationId` and sent mail so you do not reply twice.
- Apply `vip-rules.md` first; rule actions must lead the plan.
- Include only facts present in the message, thread, or trusted context.
- If confidence is low, send a briefing to the user instead of replying to the sender.

## Reply content

- Keep the subject threaded as `Re: <original subject>` unless sending a digest.
- Be concise, specific, and helpful.
- Avoid commitments about dates, pricing, roadmap, legal terms, security posture, or incident status unless source content explicitly supports them.
- Include a next step when useful.
- Do not expose internal reasoning or rule names to external recipients.

## Execution order

1. Send the reply with Outlook MCP when available.
2. If MCP is unavailable, call `send_reply` with `to`, `subject`, `body_html`, and optional `in_reply_to_id`.
3. After a successful send, mark the original message read with Outlook MCP or `mark_read`.
4. Log the action in the run summary.

## Never do this

- Never reply twice in the same conversation.
- Never reply to spam-like or phishing-like messages.
- Never send full inbox summaries to the original sender.
- Never mark read before the reply succeeds.
