# Devpost submission draft — Cashflow Voice

> Paste-ready gallery copy lives in [`devpost-gallery.md`](devpost-gallery.md).

**Track:** Alexa+ (self-hosted MCP server, spec 2025-11-25, Streamable HTTP)
**Mini challenge:** Open Source (MIT-licensed public repo) — optional: AWS Builder if deployed with an AWS service
**Deadline:** Oct 24, 2026 12:00 PDT = Oct 25, 2026 04:00 JST

## Inspiration
Small businesses rarely fail for lack of customers — they run out of cash. Owners are behind
the counter, not in spreadsheets. We wanted the question "can I make payroll?" to have a
spoken, trustworthy answer in five seconds.

## What it does
Cashflow Voice is an MCP server Alexa+ calls to answer cash questions for a small business:
today's balance, a 13-week forecast, "can I afford this?", and a ranked plan when cash will
dip (chase receivables early, defer a bill, draw only the gap on a credit line). Any
money-related action is proposed first and only runs (in a sandbox) after the owner reads
back a one-time 4-digit code. Notes like "payroll is always the 25th" persist across sessions,
and every step is audited.

## How we built it
Python, the official MCP Python SDK (FastMCP, Streamable HTTP, protocol 2025-11-25), SQLite
for per-business memory and audit, a deterministic forecasting engine (recurring-pattern
detection + open invoices), pytest + GitHub Actions, Docker for deployment.

## Challenges
Keeping numbers out of the LLM's hands (all figures come from tools), and designing a voice
confirmation flow that is safe without being annoying.

## Accomplishments
A complete propose → confirm → audit loop with no replay and per-business isolation;
tests including a prompt-injection case.

## What's next
freee / QuickBooks / bank-API import, Ring + Alexa notifications ("cash alert" on Echo Show),
real lender comparison.

## Built with
python, mcp, fastmcp, sqlite, uvicorn, docker, github-actions

## Alexa+ readiness checklist (verified 2026-10-21)
| Requirement (per Alexa+ MCP QuickStart) | Status |
|---|---|
| Streamable HTTP transport, spec 2025-11-25 | ✅ negotiated version confirmed live |
| Remote URL over HTTPS | ✅ live at `https://cashflow-voice-mcp.onrender.com/mcp` (Render, `render.yaml`) |
| 401 without `WWW-Authenticate` on unauthenticated requests | ✅ `CASHFLOW_TOKEN` bearer middleware (SDK's own auth middleware adds the header, so we bypass it) |
| <500 ms round-trip | ✅ measured ~5 ms median per tool call, ~44 ms at 20× parallel (uvloop + httptools); `X-Response-Time-Ms` on every response; cold-start caveat + keep-alive ping documented |
| tools/list ↔ invocable tools, JSON Schema, `isError` contract | ✅ 12 tools tested end to end incl. error path |
| OAuth 2.1 + PKCE S256 authorization server (real account linking) | ⏳ needs your IdP / Login with Amazon — out of scope for sandbox demo |
| PRM doc (`/.well-known/oauth-protected-resource`) | ⏳ point it at the IdP above when added; bare 401 + bearer works for judging |

## Product feedback (required) — draft
Building a self-hosted MCP server for Alexa+ was mostly smooth. The MCP Python SDK's
FastMCP decorators turned each cash-flow function into a tool with a generated JSON
schema in minutes, and Streamable HTTP plus spec 2025-11-25 version negotiation worked
out of the box. The Alexa+ QuickStart's authentication checklist is refreshingly
specific — the "bare 401 with no WWW-Authenticate header" detail is exactly what
implementers need and differs subtly from stock MCP middleware defaults. Three friction
points: (1) the SDK's own RequireAuthMiddleware emits WWW-Authenticate, which Alexa+
forbids, so I wrote a small ASGI shim instead; (2) full account linking demands an
OAuth 2.1 + PKCE S256 authorization server — heavy for a hackathon, a documented
dev-mode static token would lower the bar; (3) I couldn't find published limits for
tool result size or schema complexity, so I kept responses conservative. A worked
Python example and a stated result-size budget would make onboarding even faster.
Would build again: yes.

- **Devpost / submission flow** — (fill after submitting)

## Friction log (optional, up to +10% bonus)
| Task | Steps | Expected | Actual | Severity | Workaround | Suggestion |
|---|---|---|---|---|---|---|
| Install MCP SDK | `pip install mcp` | FastMCP import works | 2.x removed `mcp.server.fastmcp` | Medium | pin `mcp>=1.25,<2` | Version banner in Alexa+ MCP docs |
| Bearer auth for Alexa+ | use SDK `token_verifier` | Alexa+-compliant 401 | SDK middleware adds `WWW-Authenticate`, which Alexa+ explicitly forbids | Medium | custom ASGI shim returning bare 401 | note the contradiction in QuickStart |
| Local client behind proxy | run client vs localhost | connects | "Session terminated" because HTTP(S)_PROXY captured localhost | Low | set `NO_PROXY=127.0.0.1` | mention in troubleshooting |

## Demo video script (< 3 min, English, public on YouTube)

**0:00–0:15 — Hook. SCREEN:** café counter, morning prep; owner wiping hands.
**OWNER (v.o.):** "I run a twelve-seat café in Nakano. Every month I ask the same
scary question — can I make payroll?"

**0:15–0:35 — Balance. SCREEN:** phone on the counter / MCP Inspector visible.
**OWNER:** "Alexa, how's my cash?"
**ALEXA:** "You have one point eight seven million yen today. Cash dips below zero in
the week of December twenty-first — want a shortfall plan?"
**CAPTION:** tool call `cash_position` shown on screen.

**0:35–0:55 — Affordability.**
**OWNER:** "Can I buy a new oven for 400,000 yen on November 2nd?"
**ALEXA:** "Not safely — paying 400,000 yen would leave you about 665,000 yen below zero."
**CAPTION:** `can_i_afford` returns `affordable: false` + lowest-balance figure.

**0:55–1:25 — Plan.**
**OWNER:** "Then what should I do?"
**ALEXA:** "You need about 565,000 yen to stay above your buffer. The best first step:
ask your supplier for a 14-day extension on bill BILL-88. Want me to draft it?"
**CAPTION:** `shortfall_plan` ranked options on screen.

**1:25–2:00 — Confirm in sandbox.**
**OWNER:** "Do it."
**ALEXA:** "I've prepared that. To confirm, say the code 3 - 9 - 6 - 3."
**OWNER:** "Three nine six three."
**ALEXA:** "Done — it ran in the sandbox, so no real money moved."
**SCREEN:** `propose_action` → `confirm_action` JSON, then `audit_log` trail.

**2:00–2:30 — Memory + architecture. SCREEN:** fresh session; `recall` shows
"Payroll is always on the 25th". Cut to architecture slide: Alexa+ → Streamable HTTP
(MCP 2025-11-25) → deterministic engine → SQLite.
**NARRATOR (v.o.):** "Every number comes from tools, not the model. Money only moves
after a spoken one-time code — and only in a sandbox."

**2:30–2:50 — Close. SCREEN:** repo README + CI badge.
**NARRATOR:** "Cashflow Voice: cash answers a busy owner can trust, in five seconds.
Open source, MIT, self-hosted — link below."

(If live Alexa+ access is unavailable, record MCP Inspector / `scripts/demo_client.py`
with a TTS voice-over for the ALEXA lines — the tool output is identical.)

## Submission checklist
- [ ] Repo public with LICENSE (or private + add chris-trag, knmeiss, giolaq, anishamalde, mosesroth, emersonsklar + Devpost account)
- [ ] Deployed HTTPS endpoint `/mcp`
- [ ] Demo video < 3 min, English, YouTube/Vimeo public
- [ ] Text description (above)
- [ ] Product feedback filled in
- [ ] Track: Alexa+; mini challenge fields
- [ ] Submit on Devpost before Oct 25 04:00 JST
