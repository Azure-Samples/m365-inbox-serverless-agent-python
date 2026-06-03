# VIP and Special Routing Rules

These rules are checked before ordinary classification. A match does not remove the need for normal triage unless the rule says to stop.

## Required behavior

- Check sender, subject, and body for every rule before replying, posting to Teams, or marking read.
- Put rule-mandated actions first in the action plan.
- Do not delete, archive, move, or unsubscribe in this sample.
- Use placeholders and environment variables; never hard-code real team IDs, channel IDs, or recipients.

## Active rules

### Rule 1: VIP stakeholder -> Teams alert

- **Trigger:** The string `<vip-name>@example.com` appears in sender, subject, or body.
- **Action:** Post a Teams alert first.
- **Format:** Start with `🚨 VIP Alert`, include subject, sender, concise summary, and requested next action.
- **Priority:** First action, then continue normal processing.
- **Safety:** Reply only if the message clearly requests a response.

### Rule 2: Product incidents -> Conditional escalation

- **Trigger:** Sender is `incidents@example.com`.
- **Condition A:** Subject or body mentions `your-product`, `customer impact`, `sev`, `outage`, or `regression`.
- **Action A:** Classify as `incident` and post a Teams alert first.
- **Condition B:** No product-impact wording is present.
- **Action B:** Skip autonomous action and summarize as filtered incident noise.
- **Safety:** Do not close, acknowledge, or mutate incident state from email alone.

### Rule 3: Partner contact -> One-business-day reply

- **Trigger:** Sender is `<partner-contact>@example.com`.
- **Action:** Prepare or send a courteous response within one business day when the message asks for input.
- **Priority:** Normal priority unless urgent words are present.
- **Safety:** Do not commit dates, pricing, legal terms, or roadmap details without explicit source content.

## Adding new rules

Use this copy-paste format:

```markdown
### Rule N: Short name

- **Trigger:** Sender/keyword/`regex:<pattern>` condition.
- **Condition:** Optional extra filter.
- **Action:** Teams alert, reply, mark-read, or skip.
- **Priority:** First or normal.
- **Safety:** What the agent must not do.
```

## Matching notes

- Prefer exact sender matches for VIPs.
- Use keywords for topics that vary by sender.
- Use `regex:<pattern>` only for stable identifiers such as incident IDs.
- If multiple rules match, apply the first rule in this file.
