# Inbox Intelligence

Analyze inbox and sent-mail patterns to identify what deserves attention and why.

## Inputs

- `inbox[]`: received messages with sender, subject, preview/body, received time, importance, read state, categories, conversation id, and attachment flag.
- `sent[]`: sent messages with recipients, subject, body preview, sent time, and conversation id.
- `period`: analysis window such as `24h` or `7d`.
- `rules`: current VIP rules from `skills/vip-rules.md`.

## Analysis sections

### Response patterns

- Top senders the user replies to most.
- Topics or threads with repeated back-and-forth.
- Average response time by importance.
- Domains or partners that receive fast responses.

### Blind spots

- Unanswered VIP or partner messages.
- Frequent senders with no recent reply.
- High-importance unread messages.
- Aging threads where the last message is inbound.

### Nominated emails

Nominate up to 15 emails using category badges:

- `vip`: matched VIP rule or trusted stakeholder.
- `urgent`: deadline, escalation, outage, blocking issue, or high importance.
- `easy-win`: quick acknowledgement or simple answer.
- `relationship`: frequent collaborator or partner relationship.
- `strategic`: product, customer, leadership, or cross-team impact.
- `overdue`: oldest still-actionable unreplied message.

## Each nomination includes

- Rank and category badge.
- Sender, subject, and received date.
- Why it matters.
- Suggested next action.
- Draft reply only when grounded in sent mail or clearly marked as best-practice fallback.
- Confidence: high, medium, or low.

## Grounding rules

- Sent mail is the grounding source for tone and recurring response patterns.
- Cite real sent subjects and dates when used.
- If no similar sent mail exists, say `No prior pattern; suggested based on best practices`.
- Do not fabricate quotes, recipients, or history.
