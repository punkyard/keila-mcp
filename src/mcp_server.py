import logging
import os
import sys
import time
import uuid

from src.keila_client import (
    KeilaAuthError,
    KeilaApiError,
    KeilaClient,
    KeilaRateLimitError,
)

logger = logging.getLogger("keyla-mcp")

VALID_STATUSES = {"draft", "scheduled", "sent", "archived", "paused"}
_client: KeilaClient | None = None


def get_client() -> KeilaClient:
    global _client
    if _client is None:
        base_url = os.environ.get("KEILA_URL", "https://your-keila-instance.example.com")
        api_key = os.environ.get("KEILA_API_KEY", "")
        _client = KeilaClient(base_url=base_url, api_key=api_key)
    return _client


def list_campaigns(status: str | None = None, q: str | None = None) -> list | dict:
    correlation_id = str(uuid.uuid4())[:8]

    if status is not None and status not in VALID_STATUSES:
        valid = ", ".join(sorted(VALID_STATUSES))
        msg = f"Invalid status '{status}'. Must be one of: {valid}"
        logger.error("campaigns.list.errors", extra={
            "correlation_id": correlation_id,
            "status": status,
            "error_type": "validation",
        })
        return {"error": f"400: {msg}"}

    start = time.time()
    try:
        campaigns = get_client().get_campaigns(status=status, q=q)
        campaigns.sort(key=lambda c: c.get("created_at", ""), reverse=True)
        elapsed = time.time() - start

        logger.info("campaigns.list.latency", extra={
            "correlation_id": correlation_id,
            "duration_ms": round(elapsed * 1000, 1),
            "count": len(campaigns),
            "status_filter": status,
            "q_filter": q,
        })
        logger.info("campaigns.list.result", extra={
            "correlation_id": correlation_id,
            "count": len(campaigns),
            "campaign_ids": [c.get("id") for c in campaigns],
        })
        return campaigns
    except KeilaAuthError as e:
        elapsed = time.time() - start
        logger.error("campaigns.list.errors", extra={
            "correlation_id": correlation_id,
            "duration_ms": round(elapsed * 1000, 1),
            "error_type": "auth",
        })
        return {"error": str(e)}
    except KeilaRateLimitError as e:
        elapsed = time.time() - start
        logger.error("campaigns.list.errors", extra={
            "correlation_id": correlation_id,
            "duration_ms": round(elapsed * 1000, 1),
            "error_type": "rate_limit",
        })
        return {"error": str(e)}
    except KeilaApiError as e:
        elapsed = time.time() - start
        logger.error("campaigns.list.errors", extra={
            "correlation_id": correlation_id,
            "duration_ms": round(elapsed * 1000, 1),
            "error_type": "api",
        })
        return {"error": str(e)}


def main():
    from mcp.server.fastmcp import FastMCP

    app = FastMCP("keyla-mcp", description="MCP server for Keila API")

    @app.tool()
    def list_campaigns_tool(
        status: str | None = None, q: str | None = None
    ) -> list | dict:
        return list_campaigns(status=status, q=q)

    transport = "stdio"
    if "--http" in sys.argv:
        transport = "http"

    logger.info("starting_server", extra={"transport": transport})
    app.run(transport=transport)


if __name__ == "__main__":
    main()
