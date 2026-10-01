"""product_information_agent – looks up the product catalogue (Postgres `products`)."""
from __future__ import annotations

import time

from agents.state import AgentState
from agents.tools import keywords_from, search_products


def product_information_agent(state: AgentState) -> dict:
    start = time.perf_counter()
    email = state["email"]
    category = state.get("product_category")
    matches = search_products.invoke({
        "keywords": keywords_from(f"{email['subject']} {email['body']}"),
        "category": category,
        "product_name": (state.get("entities") or {}).get("product_name"),
    })

    return {
        "retrieved_data": {"products": matches},
        "data_source": "product_information",
        "agent_trace": [{
            "agent": "product_information_agent",
            "status": "completed" if matches else "no_match",
            "summary": f"{len(matches)} product(s): " + ", ".join(p["product_name"] for p in matches),
            "duration_ms": int((time.perf_counter() - start) * 1000),
            "output": {"category": category, "matched": [p["product_code"] for p in matches],
                       "tools": ["search_products"]},
        }],
    }
