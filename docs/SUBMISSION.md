# Devpost submission draft — Cashflow Voice

**Track:** Alexa+ (self-hosted MCP server, spec 2025-11-25, Streamable HTTP)
**Mini challenge:** Open Source (MIT-licensed public repo) — optional: AWS Builder if deployed with an AWS service
**Deadline:** Oct 23, 2026 12:00 PDT = Oct 24, 2026 04:00 JST

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

## Product feedback (required) — FILL IN from your actual experience
- **Alexa+ / MCP docs** — used for: ___. Worked well: ___. Needs work: ___. Onboarding (zero → hello world): ___ min. Would build again: yes/no.
- **MCP Python SDK** — used for the Streamable HTTP server. Worked well: decorator tools, schema generation. Needs work: v2 renamed FastMCP → MCPServer, so most tutorials break unless you pin `mcp<2`. Would build again: yes.
- **Devpost / submission flow** — ___

## Friction log (optional, up to +10% bonus)
| Task | Steps | Expected | Actual | Severity | Workaround | Suggestion |
|---|---|---|---|---|---|---|
| Install MCP SDK | `pip install mcp` | FastMCP import works | 2.x removed `mcp.server.fastmcp` | Medium | pin `mcp>=1.25,<2` | Version banner in Alexa+ MCP docs |
| Local client behind proxy | run client vs localhost | connects | "Session terminated" because HTTP(S)_PROXY captured localhost | Low | set `NO_PROXY=127.0.0.1` | mention in troubleshooting |

## Demo video script (< 3 min, English, public on YouTube)
1. **0:00–0:20** Hook: café owner at the counter. "Alexa, how's my cash?" → spoken answer (cash_position).
2. **0:20–0:50** "Can I buy a new oven for 400,000 yen on November 2nd?" → can_i_afford says not safely, explains the low point.
3. **0:50–1:30** "What should I do?" → shortfall_plan: ask supplier for extension / chase invoice early.
4. **1:30–2:05** "Do it." → propose_action reads a code; owner says it; confirm_action runs in sandbox. Show audit_log.
5. **2:05–2:30** New session: recall shows "payroll is always the 25th". Architecture slide (Alexa+ → MCP Streamable HTTP → engine + SQLite).
6. **2:30–2:50** Impact + what's next. End card with repo URL.
(If live Alexa+ access is unavailable, record MCP Inspector / scripts/demo_client.py with TTS voice-over.)

## Submission checklist
- [ ] Repo public with LICENSE (or private + add chris-trag, knmeiss, giolaq, anishamalde, mosesroth, emersonsklar + Devpost account)
- [ ] Deployed HTTPS endpoint `/mcp`
- [ ] Demo video < 3 min, English, YouTube/Vimeo public
- [ ] Text description (above)
- [ ] Product feedback filled in
- [ ] Track: Alexa+; mini challenge fields
- [ ] Submit on Devpost before Oct 24 04:00 JST
