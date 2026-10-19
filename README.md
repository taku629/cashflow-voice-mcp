# Cashflow Voice — an Alexa+ MCP server for small-business cash flow

> "Alexa, can I make payroll next month?"
> "You have 1,868,000 yen today. Cash dips below zero the week of December 21. Want a plan?"

Cashflow Voice is a **self-hosted MCP server (spec 2025-11-25, Streamable HTTP)** for the
**Alexa+ track** (priority category: *business systems*). It turns a café or shop owner's
bank CSV and open invoices into spoken answers, a 13-week forecast, and a ranked plan to
avoid a cash crunch — and it never moves money without a spoken confirmation code.

## Why

Most small businesses that fail run out of cash, not customers. Owners are busy on the
floor, not in spreadsheets. Voice is where they already are (kitchen, counter, car).

## What it does (MCP tools)

| Tool | Purpose |
|---|---|
| `import_transactions` | Load a bank CSV (date, description, amount[, category, counterparty]) |
| `cash_position` | Balance today + one-sentence 13-week outlook |
| `forecast_cashflow` | Week-by-week forecast with the drivers behind each week |
| `can_i_afford` | "Can I buy a ¥400k oven on Nov 2?" against a safety buffer |
| `shortfall_plan` | Ranked fixes: chase receivables early, defer bills, draw only the gap |
| `propose_action` | Prepare an action; returns an id + 4-digit code. Nothing executes |
| `confirm_action` | Executes in **sandbox** only after the owner reads back the code |
| `cancel_action` | Cancel a pending action |
| `remember` / `recall` | Context that survives across Alexa sessions |
| `audit_log` | Every import, question, proposal and confirmation, timestamped |

## Design principles

- **Deterministic numbers.** The LLM speaks; the engine calculates. Same input, same answer.
- **Human-in-the-loop money.** Two-step propose → confirm with a one-time code, no replay,
  per-business isolation, sandbox execution.
- **Prompt-injection hygiene.** Transaction text is treated as data (see tests).
- **Memory across sessions.** SQLite per business (`CASHFLOW_DB`).

## Run locally

```bash
pip install -e ".[dev]"
pytest -q                                   # 10 tests
CASHFLOW_TODAY=2026-10-19 cashflow-voice    # serves http://0.0.0.0:8000/mcp
python scripts/demo_client.py http://127.0.0.1:8000/mcp
```

Deploy: `Dockerfile` / `render.yaml` included (any HTTPS host works). Point Alexa+ (or any
MCP client such as MCP Inspector) at `https://<host>/mcp`.

## Demo data

`data/sample_transactions.csv` and `data/invoices.csv` model a small Tokyo café.

## License

MIT
