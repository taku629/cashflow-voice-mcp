"""Scripted 'Alexa+ conversation' against the running MCP server over Streamable HTTP."""
import asyncio, json, sys
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000/mcp"

async def main():
    async with streamablehttp_client(URL) as (r, w, _):
        async with ClientSession(r, w) as s:
            init = await s.initialize()
            print("protocol:", init.protocolVersion)
            print("tools:", [t.name for t in (await s.list_tools()).tools])
            async def call(name, **kw):
                res = await s.call_tool(name, kw)
                data = json.loads(res.content[0].text)
                print(f"\n> {name}({kw})\n  {data.get('speech', json.dumps(data, ensure_ascii=False)[:300])}")
                return data
            await call("cash_position")
            await call("can_i_afford", amount_yen=400000, on_date="2026-11-02")  # "Can I buy a new oven?"
            plan = await call("shortfall_plan")
            first = plan["options"][0] if plan["options"] else {"type": "draft_credit_application"}
            kind = first["type"] if first["type"] != "short_term_credit_line" else "draft_credit_application"
            p = await call("propose_action", kind=kind, invoice_id=first.get("invoice", ""), note=first.get("note", ""))
            await call("confirm_action", action_id=p["action_id"], confirmation_code=p["confirmation_code"])
            await call("remember", note="Payroll is always on the 25th")
            await call("audit_log", limit=5)

asyncio.run(main())
