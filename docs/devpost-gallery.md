# Cashflow Voice — Devpost gallery copy

Paste each section into the matching Devpost field.

## Tagline (≤200 chars)

Ask Alexa+ "Can I make payroll?" and get a real answer: an MCP server that turns a small shop's bank CSV into spoken forecasts, fixes, and code-confirmed sandbox actions.

## Inspiration

Small businesses usually fail because they run out of cash, not customers. The owner of a twelve-seat café is behind the counter at 7 a.m., not in a spreadsheet, and the question that keeps them up at night is short: *can I make payroll next month?* We wanted that question to get a trustworthy spoken answer in about five seconds, from the voice assistant already sitting in the kitchen.

## What it does

Cashflow Voice is a self-hosted **MCP server for Alexa+** (spec 2025-11-25, Streamable HTTP) with 12 tools:

- **Know where you stand:** `cash_position` gives today's balance plus a one-sentence 13-week outlook ("You have 1.87 million yen today. Cash dips below zero in the week of December 21").
- **Look ahead:** `forecast_cashflow` builds a week-by-week forecast and shows what drives each week (rent, payroll, invoices due).
- **Decide:** `can_i_afford` answers "Can I buy a ¥400k oven on November 2nd?" against a safety buffer.
- **Fix it:** `shortfall_plan` ranks concrete fixes: collect receivables early, defer a supplier bill, or borrow only the gap.
- **Act safely:** `propose_action` prepares an action and returns a one-time 4-digit code. `confirm_action` runs it only after the owner reads the code back, and only in a **sandbox**, so no real money moves. `cancel_action` drops a pending action.
- **Remember and account for everything:** `remember` / `recall` keep notes like "payroll is always the 25th" across Alexa sessions, and `audit_log` timestamps every import, question, proposal and confirmation.
- **Bring your own data:** `import_transactions` / `import_invoices` load a bank CSV and open invoices. Each business id is isolated from the others.

## How we built it

- **Python + the official MCP Python SDK (FastMCP)** over Streamable HTTP in stateless JSON mode, served by uvicorn with uvloop and httptools.
- **A deterministic forecasting engine:** it detects recurring patterns (rent, payroll, utilities, cost of goods) and adds open receivables and payables. The LLM only speaks. Every number comes from a tool, so the same input always gives the same answer.
- **SQLite** (WAL) for per-business memory, pending actions and the audit trail. Forecasts are memoized by business, week count, day and data version.
- **A small ASGI bearer-token shim** that returns a bare `401` with no `WWW-Authenticate` header, as Alexa+ discovery requires. An `X-Response-Time-Ms` header on every response makes the 500 ms latency budget measurable.
- **pytest + ruff in GitHub Actions**, plus Docker and a `render.yaml` blueprint. It is deployed on Render at `https://cashflow-voice-mcp.onrender.com/mcp`.

## Challenges we ran into

- **Keeping numbers out of the model's hands.** Voice assistants like to round, guess and invent. We made every figure come from a tool and wrote tool replies as short `speech` strings that can be read aloud as-is.
- **Auth that matches Alexa+ exactly.** The SDK's built-in auth middleware adds a `WWW-Authenticate` header, which Alexa+ forbids during discovery, so we wrote our own ASGI shim. Hardening it turned up an edge case: a non-ASCII `Authorization` header crashed the string comparison with a 500. It now compares raw bytes and returns a clean 401, and a regression test covers it.
- **Safe-but-not-annoying confirmation.** Money actions needed a step that holds up over voice. Our answer is a one-time, single-use, per-business 4-digit code that can't be replayed, read back by the owner.
- **SDK churn.** MCP SDK 2.x removed `mcp.server.fastmcp`, so we pinned `mcp>=1.25,<2`.

## Accomplishments that we're proud of

- A complete **propose → confirm → audit** loop with no replay, per-business isolation and sandbox-only execution.
- **About 5 ms median per tool call** measured locally, well inside Alexa+'s 500 ms budget.
- Prompt-injection hygiene: transaction descriptions are treated as data, and a test covers it.
- A lint-clean, tested codebase (18 tests in CI), MIT-licensed, that anyone can run in under a minute.

## What we learned

- For money, voice works best when the assistant is the *mouth* and deterministic code is the *brain*.
- MCP's tool schemas make a backend usable by Alexa+ with very little glue. The hard work is in reply design (short spoken sentences plus structured data) and in auth details.
- Small protocol details (an extra header on a 401, the bytes in a header) decide whether an integration works at all, so they deserve tests.

## What's next for Cashflow Voice

- Real account linking with OAuth 2.1 + PKCE (Login with Amazon) and a protected-resource metadata document.
- Direct imports from freee, QuickBooks and bank APIs instead of CSV.
- Proactive "cash alert" notifications on Echo Show when the forecast crosses the buffer.
- Real lender and invoice-factoring comparisons in `shortfall_plan`, and actions that leave the sandbox only with explicit owner opt-in.

## Built with

python, mcp, fastmcp, alexa-plus, starlette, uvicorn, sqlite, pytest, ruff, docker, render, github-actions

## Links

- Code: https://github.com/taku629/cashflow-voice-mcp
- Live MCP endpoint: https://cashflow-voice-mcp.onrender.com/mcp (bearer token; health: `/healthz`)
- Demo video: `docs/media/cashflow-voice-demo.mp4` in the repo (upload to YouTube and paste the link into Devpost's video field)
