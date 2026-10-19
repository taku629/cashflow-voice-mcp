"""Deterministic cash-flow engine used by the MCP tools.

No LLM is involved here: every number Alexa+ speaks comes from these
functions, so answers are reproducible and auditable.
"""
from __future__ import annotations

import csv
import io
import json
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from statistics import mean

RECURRING = {"rent", "payroll", "utilities", "lease", "cogs"}


@dataclass
class Txn:
    day: date
    description: str
    amount: int
    category: str
    counterparty: str


def parse_transactions(csv_text: str) -> list[Txn]:
    """Parse a bank-style CSV (date,description,amount[,category,counterparty])."""
    rows = []
    reader = csv.DictReader(io.StringIO(csv_text.strip()))
    required = {"date", "description", "amount"}
    if not reader.fieldnames or not required.issubset({f.strip().lower() for f in reader.fieldnames}):
        raise ValueError("CSV needs at least date, description, amount columns")
    for i, raw in enumerate(reader, start=2):
        r = {k.strip().lower(): (v or "").strip() for k, v in raw.items() if k}
        try:
            amt = int(round(float(r["amount"].replace(",", ""))))
            d = date.fromisoformat(r["date"])
        except ValueError as exc:
            raise ValueError(f"Row {i}: {exc}") from exc
        desc = r["description"][:120]
        rows.append(Txn(d, desc, amt, (r.get("category") or "other").lower(), r.get("counterparty", "")[:80]))
    rows.sort(key=lambda t: t.day)
    return rows


class Store:
    """Per-business persistent memory (SQLite) so context survives across Alexa sessions."""

    def __init__(self, path: str | Path = ":memory:"):
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.db.executescript(
            """
            create table if not exists txns(business text, day text, description text, amount int, category text, counterparty text);
            create table if not exists invoices(business text, id text, counterparty text, amount int, due text, direction text);
            create table if not exists notes(business text, ts text, note text);
            create table if not exists actions(id text primary key, business text, kind text, payload text, status text, code text, created text);
            create table if not exists audit(ts text, business text, event text, detail text);
            """
        )

    # --- audit ---------------------------------------------------------
    def log(self, business: str, event: str, detail: dict) -> None:
        self.db.execute("insert into audit values(?,?,?,?)", (_now(), business, event, json.dumps(detail, ensure_ascii=False)))
        self.db.commit()

    def audit_trail(self, business: str, limit: int = 20) -> list[dict]:
        cur = self.db.execute("select ts,event,detail from audit where business=? order by rowid desc limit ?", (business, limit))
        return [{"ts": ts, "event": ev, "detail": json.loads(d)} for ts, ev, d in cur]

    # --- data ----------------------------------------------------------
    def load_transactions(self, business: str, txns: list[Txn], replace: bool = True) -> int:
        if replace:
            self.db.execute("delete from txns where business=?", (business,))
        self.db.executemany(
            "insert into txns values(?,?,?,?,?,?)",
            [(business, t.day.isoformat(), t.description, t.amount, t.category, t.counterparty) for t in txns],
        )
        self.db.commit()
        self.log(business, "import_transactions", {"rows": len(txns)})
        return len(txns)

    def load_invoices(self, business: str, csv_text: str) -> int:
        reader = csv.DictReader(io.StringIO(csv_text.strip()))
        self.db.execute("delete from invoices where business=?", (business,))
        n = 0
        for r in reader:
            self.db.execute(
                "insert into invoices values(?,?,?,?,?,?)",
                (business, r["id"], r["counterparty"], int(r["amount"]), r["due_date"], r["direction"]),
            )
            n += 1
        self.db.commit()
        self.log(business, "import_invoices", {"rows": n})
        return n

    def txns(self, business: str) -> list[Txn]:
        cur = self.db.execute("select day,description,amount,category,counterparty from txns where business=? order by day", (business,))
        return [Txn(date.fromisoformat(d), de, a, c, cp) for d, de, a, c, cp in cur]

    def invoices(self, business: str) -> list[dict]:
        cur = self.db.execute("select id,counterparty,amount,due,direction from invoices where business=? order by due", (business,))
        return [dict(id=i, counterparty=c, amount=a, due=d, direction=dr) for i, c, a, d, dr in cur]

    def add_note(self, business: str, note: str) -> None:
        self.db.execute("insert into notes values(?,?,?)", (business, _now(), note[:500]))
        self.db.commit()

    def notes(self, business: str) -> list[dict]:
        cur = self.db.execute("select ts,note from notes where business=? order by rowid desc limit 10", (business,))
        return [{"ts": ts, "note": n} for ts, n in cur]

    # --- human-in-the-loop actions --------------------------------------
    def propose(self, business: str, kind: str, payload: dict) -> dict:
        aid = "ACT-" + secrets.token_hex(3).upper()
        code = f"{secrets.randbelow(10000):04d}"
        self.db.execute("insert into actions values(?,?,?,?,?,?,?)", (aid, business, kind, json.dumps(payload, ensure_ascii=False), "pending", code, _now()))
        self.db.commit()
        self.log(business, "propose_action", {"id": aid, "kind": kind, **payload})
        return {"action_id": aid, "status": "pending", "confirmation_code": code}

    def confirm(self, business: str, action_id: str, code: str) -> dict:
        row = self.db.execute("select kind,payload,status,code from actions where id=? and business=?", (action_id, business)).fetchone()
        if not row:
            return {"ok": False, "reason": "unknown action"}
        kind, payload, status, real = row
        if status != "pending":
            return {"ok": False, "reason": f"action already {status}"}
        if not secrets.compare_digest(code.strip(), real):
            self.log(business, "confirm_failed", {"id": action_id})
            return {"ok": False, "reason": "confirmation code mismatch"}
        self.db.execute("update actions set status='executed_sandbox' where id=?", (action_id,))
        self.db.commit()
        self.log(business, "execute_sandbox", {"id": action_id, "kind": kind})
        return {"ok": True, "action_id": action_id, "kind": kind, "payload": json.loads(payload), "mode": "sandbox (no real money moves)"}

    def cancel(self, business: str, action_id: str) -> dict:
        cur = self.db.execute("update actions set status='cancelled' where id=? and business=? and status='pending'", (action_id, business))
        self.db.commit()
        self.log(business, "cancel_action", {"id": action_id, "changed": cur.rowcount})
        return {"ok": bool(cur.rowcount), "action_id": action_id}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --- analytics -------------------------------------------------------------

def balance(txns: list[Txn]) -> int:
    return sum(t.amount for t in txns)


def monthly_pattern(txns: list[Txn]) -> list[dict]:
    """Infer recurring flows: same category & day-of-month, averaged amount."""
    groups: dict[tuple[str, str], list[Txn]] = {}
    for t in txns:
        if t.category == "opening":
            continue
        key = (t.category, t.counterparty or t.description)
        groups.setdefault(key, []).append(t)
    pattern = []
    for (cat, who), items in groups.items():
        if cat in RECURRING or cat == "revenue":
            pattern.append({
                "category": cat,
                "counterparty": who,
                "day": round(mean(t.day.day for t in items)),
                "amount": int(mean(t.amount for t in items)),
                "evidence": len(items),
            })
    return sorted(pattern, key=lambda p: p["day"])


def forecast(txns: list[Txn], invoices: list[dict], start: date, weeks: int = 13) -> dict:
    weeks = max(1, min(weeks, 26))
    bal = balance(txns)
    pat = monthly_pattern(txns)
    # recurring items already covered by a matching invoice in the same week are skipped
    rows, lowest = [], (bal, start)
    for w in range(weeks):
        ws, we = start + timedelta(days=7 * w), start + timedelta(days=7 * w + 6)
        inflow = outflow = 0
        drivers = []
        d = ws
        while d <= we:
            for p in pat:
                if d.day == min(p["day"], 28):
                    dup = any(i["counterparty"] == p["counterparty"] and ws <= date.fromisoformat(i["due"]) <= we for i in invoices)
                    if dup:
                        continue
                    if p["amount"] > 0:
                        inflow += p["amount"]
                    else:
                        outflow += p["amount"]
                    drivers.append(f"{p['category']}:{p['counterparty']} {p['amount']:+,}")
            d += timedelta(days=1)
        for i in invoices:
            due = date.fromisoformat(i["due"])
            if ws <= due <= we:
                amt = i["amount"] if i["direction"] == "receivable" else -i["amount"]
                if amt > 0:
                    inflow += amt
                else:
                    outflow += amt
                drivers.append(f"{i['id']} {amt:+,}")
        bal += inflow + outflow
        rows.append({"week_start": ws.isoformat(), "inflow": inflow, "outflow": outflow, "closing_balance": bal, "drivers": drivers})
        if bal < lowest[0]:
            lowest = (bal, ws)
    return {
        "opening_balance": balance(txns),
        "weeks": rows,
        "lowest_balance": lowest[0],
        "lowest_week": lowest[1].isoformat(),
        "shortfall": lowest[0] < 0,
        "method": "recurring-pattern + open invoices, deterministic",
    }


def runway_summary(fc: dict, buffer: int = 300_000) -> str:
    if fc["shortfall"]:
        return (f"Warning: cash is projected to dip to {fc['lowest_balance']:,} yen in the week of {fc['lowest_week']}. "
                "Ask me for a shortfall plan.")
    if fc["lowest_balance"] < buffer:
        return (f"Cash stays positive but gets thin: the low point is {fc['lowest_balance']:,} yen in the week of {fc['lowest_week']}.")
    return f"You're covered for the next {len(fc['weeks'])} weeks. The low point is {fc['lowest_balance']:,} yen in the week of {fc['lowest_week']}."


def can_afford(fc: dict, amount: int, on: date, buffer: int = 300_000) -> dict:
    after = []
    for w in fc["weeks"]:
        ws = date.fromisoformat(w["week_start"])
        bal = w["closing_balance"] - (amount if ws + timedelta(days=6) >= on else 0)
        after.append(bal)
    low = min(after)
    ok = low >= buffer
    return {
        "affordable": ok,
        "lowest_balance_after": low,
        "buffer": buffer,
        "speech": (f"Yes. Even after paying {amount:,} yen, your lowest balance would be {low:,} yen."
                   if ok else f"Not safely. Paying {amount:,} yen would take your low point to {low:,} yen, under your {buffer:,} yen buffer."),
    }


def shortfall_plan(fc: dict, invoices: list[dict], buffer: int = 300_000) -> dict:
    gap = buffer - fc["lowest_balance"]
    if gap <= 0:
        return {"needed": 0, "options": [], "speech": "No action needed: you stay above your buffer."}
    low_week = date.fromisoformat(fc["lowest_week"])
    opts = []
    for i in invoices:
        due = date.fromisoformat(i["due"])
        if i["direction"] == "receivable" and due > low_week - timedelta(days=7):
            opts.append({"type": "request_early_payment", "invoice": i["id"], "counterparty": i["counterparty"], "impact": i["amount"],
                         "note": "Offer a 1% early-payment discount"})
        if i["direction"] == "payable" and due <= low_week + timedelta(days=6):
            opts.append({"type": "defer_bill", "invoice": i["id"], "counterparty": i["counterparty"], "impact": i["amount"],
                         "note": "Ask supplier for 14-day extension"})
    opts.append({"type": "short_term_credit_line", "impact": gap, "note": "Draw only the gap; compare offers before applying"})
    opts.sort(key=lambda o: (o["type"] == "short_term_credit_line", -o["impact"]))
    chosen, covered = [], 0
    for o in opts:
        if covered >= gap:
            break
        chosen.append(o)
        covered += o["impact"]
    first = chosen[0]
    return {
        "needed": gap,
        "options": chosen,
        "speech": f"You need about {gap:,} yen to stay above your buffer. The best first step is: {first['note'].lower()} ({first.get('invoice', 'credit line')}). Want me to draft it?",
    }
