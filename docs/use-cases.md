# Use cases

← Back to the [README](../README.md)

Three end-to-end scenarios, each backed by a message already in `sample-data/inbox/`. Run them offline (DRY RUN, nothing sent) or live (real Outlook + Teams).

## 1. VIP urgent mail posts to Teams

**Goal:** verify the agent recognizes VIP urgency and routes to Teams. In Python offline mode, verify the local log; with connectors authorized, verify the real Teams post.

**Setup:** the message is already in `sample-data/inbox/01-vip-urgent.json` (no action needed).

<details><summary>What's in the message</summary>

```json
{
  "subject": "URGENT: Customer renewal blocker needs decision today",
  "from": { "emailAddress": { "name": "Morgan Lee", "address": "vip-name@example.com" } },
  "body": { "content": "...blocked on the discount approval. We need a decision today..." }
}
```

</details>

**Run:**

```bash
uv run python chat.py   # then pick 1
```

**What you should see (DRY RUN — offline or partial):**
- `chat.py` prints a **Triage report** with one block per message. The VIP renewal email is labeled 🚨 `escalate` with the Teams alert drafted as text; its `Status` is `drafted`, not `posted`.
- Tool calls show `match_rule ×N` and zero `office365_*` / `teams_*` calls. The run ends `Triaged 5: 2 escalate, 2 reply, 1 summarize`.

**What you should see (LIVE — connectors authorized):**
- A real message appears in the configured Teams channel within about one minute.
- Application Insights `traces` shows the VIP decision and Teams post.

## 2. Incident alert becomes a briefing item

**Goal:** verify the agent treats a P1 incident as urgent and includes it in the next briefing.

**Setup:** the message is already in `sample-data/inbox/03-incident-alert.json` (no action needed).

<details><summary>What's in the message</summary>

```json
{
  "subject": "P1 IcM: Checkout API elevated failures",
  "from": { "emailAddress": { "name": "Incident Bot", "address": "incident.bot@contoso.example" } },
  "body": { "content": "Severity: P1... Product: Checkout API... Impact: 18%..." }
}
```

</details>

**Run:**

```bash
uv run python chat.py   # pick 1 for triage, then pick 2 for daily-briefing
```

**What you should see (DRY RUN — offline or partial):**
- Option 1 (triage) labels the P1 incident 🚨 `escalate` with a drafted Teams alert naming Checkout API.
- Option 2 (daily-briefing) prints a **Daily briefing (draft)** whose top items and Urgent items section name the Checkout API incident. Tool calls: none; it ends `Briefing drafted (items=N, urgent=U) — not sent`.

**What you should see (LIVE — connectors authorized):**
- A Teams alert appears for the P1 incident.
- The configured `MAILBOX_OWNER_EMAIL` mailbox receives a daily briefing that includes severity, product, impact, and owner ask.

## 3. Action-required mail gets a reply

**Goal:** verify the agent recognizes a response deadline and prepares a grounded reply.

**Setup:** the message is already in `sample-data/inbox/05-action-required.json` (no action needed).

<details><summary>What's in the message</summary>

```json
{
  "subject": "Action required: Review launch FAQ by Friday",
  "from": { "emailAddress": { "name": "Priya Patel", "address": "priya.patel@contoso.example" } },
  "body": { "content": "Could you review the launch FAQ by Friday..." }
}
```

</details>

**Run:**

```bash
uv run python chat.py   # then pick 1
```

**What you should see (DRY RUN — offline or partial):**
- The triage report labels the launch-FAQ mail ✉️ `reply` and shows the drafted reply text under `Action`, with `Status: drafted` (nothing is sent).
- The reply acknowledges the Friday deadline and lists next steps, all inside the report.

**What you should see (LIVE — connectors authorized):**
- Outlook sends a concise reply that acknowledges Friday and lists next steps.
- Application Insights `traces` shows the reply decision.
