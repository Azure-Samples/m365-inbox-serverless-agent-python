# Weekly Rule Suggestions Output Spec

The weekly agent proposes rule changes for a human to review. It does not edit files or mutate Outlook rules.

## Digest structure

- Summary of the analysis window and data sources.
- Existing rules that matched during the week.
- 3-5 proposed new rules.
- Risks, false-positive concerns, and manual review notes.
- A copy-paste markdown block ready for `skills/vip-rules.md`.

## Proposed rule format

Each proposed rule must use this format:

```markdown
### Rule N: <short descriptive name>

- **Trigger:** <sender, keyword, or `regex:<pattern>`>
- **Condition:** <optional extra condition, or `None`>
- **Action:** <post Teams alert, reply, mark read, skip, or summarize>
- **Priority:** <First or normal>
- **Safety:** <what the agent must not do>
- **Evidence:** <brief aggregate pattern, no sensitive body text>
```

## Evidence standards

- Use aggregate counts and examples such as subjects or domains only when safe.
- Do not expose confidential message bodies.
- Do not recommend rules from a single weak signal unless the sender is clearly important.
- Do not propose duplicate rules already covered by `vip-rules.md`.

## Good candidates

- Repeated urgent sender that always gets routed to Teams.
- Incident messages that matter only when they mention a product keyword.
- Partner or customer contact that consistently gets a fast reply.
- Automated newsletter or bulk source that is always skipped.
- Recurring meeting logistics that should be summarized but not replied to.

## Required footer

End the digest with: `Human review required: edit skills/vip-rules.md and redeploy to activate any rule.`
