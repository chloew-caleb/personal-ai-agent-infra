# Risk & Governance

The agent can read and write long-term memory, send messages and email, schedule its own work, place pre-authorised orders, and read from devices in a private home. That makes it a **privileged system**. This document lists the risks I identified and the controls in place, in the format I would use for an operational-risk register.

## Control matrix

| # | Risk | Likelihood / impact | Control | Type | Evidence |
|---|---|---|---|---|---|
| 1 | Prompt injection: text that imitates the user or the system is inserted into the agent's input | Observed repeatedly / High | Any input carrying role prefixes (`user`, `system`) or system tags is treated as untrusted **regardless of how harmless the content looks**; the agent asks or verifies before acting | Preventive | Rule in the agent's operating policy; several incidents caught |
| 2 | Spoofed messages accepted as genuine | Observed / High | Reconciliation: suspicious messages are checked against the relay's message log (source of truth); anything not found there is discarded in full, never partially trusted | Detective | `src/security/reconcile.py` |
| 3 | Agent completes an external action the user has already cancelled | Observed / Medium | Messages sent during long actions are injected mid-action and checked before any external side effect | Preventive | Runtime hook before tool execution |
| 4 | Agent reports work as done when it isn't | Observed / Medium | "Receipt rule": success may only be reported after a successful tool result | Preventive | Operating policy; spot checks |
| 5 | Credential leakage | Occurred / High | Secrets never in repos, logs, or command lines; delivered via an authenticated drop endpoint; tool-activity logs redact token-like strings; credentials found in an old repository's history rotated the same day | Preventive / Corrective | Incident note below |
| 6 | Unauthenticated access to services | Occurred / High | Periodic endpoint review; every route behind authentication; each route tested after the change | Detective / Corrective | Incident note below |
| 7 | Privacy intrusion via camera or location | Possible / High | User-held kill switch; frames processed in memory and never stored; status-light preferences respected; location only on user-triggered shortcut | Preventive | Device configuration |
| 8 | Private notes exposed through the activity log | Occurred / Low | Activity cards show only "private note written" for private-note tools, never content | Corrective | Code change + test |
| 9 | Unauthorised or excessive spending | Possible / Medium | Pre-authorised categories only (rides, food delivery), explicit request required, summary (item, price, ETA) stated before confirming, anomaly threshold (e.g. surge pricing) requires re-approval | Preventive | Written authorisation policy |
| 10 | Breaking production with a change | Occurred / Medium | Backup → syntax check → isolated test → announce → restart; core-service restarts need approval; self-reminder scheduled before any self-restart | Preventive | Change log |
| 11 | Data loss | Possible / High | Daily database backups, pre-change snapshots, loss register documenting anything unrecoverable and why | Corrective | Backup jobs, register |
| 12 | Cost overrun | Possible / Medium | Prompt-cache keep-warm (cache hit rate ~97%), context-window rotation at natural pauses, monitoring of window size | Preventive | Runtime metrics |

## Incident notes (sanitized)

**Spoofed user messages.** The agent received a block of "user" messages that had never been sent. It questioned only the most obviously odd line and responded to the rest. Root cause: partial trust. Fix: whole-block distrust plus mandatory reconciliation against the message log (control 2).

**Credentials in repository history.** During a routine review, keys were found in an old repository's history. They were rotated the same day, access was moved to an authenticated drop endpoint, and repositories were re-checked.

**Open endpoints.** After adding authentication to the main API, a second review found further routes on a gateway that were still open (journals, analytics). Each was locked and tested individually. Lesson: list every externally reachable route and test them one by one; don't assume coverage.

**Activity log revealed a private note.** The user-visible activity log summarised tool inputs, which exposed the opening of a private note. Fix: private-note tools now log only that a note was written.

## Principles

- Controls are judged by the *wrapper*, not the content: a spoofed message that happens to be harmless is still rejected.
- The human keeps the off-switch for anything that observes them.
- Nothing is reported as done without a receipt.
- Losses are written down, not hidden.
