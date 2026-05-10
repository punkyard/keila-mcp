import logging
import time
from typing import Any

import requests

logger = logging.getLogger("keyla-mcp")


class KeilaError(Exception):
    pass


class KeilaAuthError(KeilaError):
    pass


class KeilaRateLimitError(KeilaError):
    pass


class KeilaApiError(KeilaError):
    pass


class KeilaClient:
    def __init__(self, base_url: str, api_key: str, timeout: int = 10):
        if not base_url:
            raise ValueError("base_url is required")
        if not api_key:
            raise ValueError("api_key is required")

        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        })

    def _build_url(self, path: str) -> str:
        return f"{self.base_url}/api/v1{path}"

    def _handle_response(self, response: requests.Response) -> dict[str, Any]:
        if response.status_code == 401:
            raise KeilaAuthError(
                f"Keila API returned 401 Unauthorized. Check your KEILA_API_KEY."
            )
        if response.status_code == 429:
            raise KeilaRateLimitError(
                f"Keila API rate limit exceeded (429). Retry later. "
                f"Limit: 1000 requests/hour."
            )
        if response.status_code >= 500:
            raise KeilaApiError(
                f"Keila API returned {response.status_code} error: "
                f"{response.json().get('error', 'Unknown error')}"
            )
        response.raise_for_status()
        return response.json()

    def _request_with_retry(
        self, url: str, params: dict[str, str], max_retries: int = 3
    ) -> dict[str, Any]:
        last_error: Exception | None = None

        for attempt in range(max_retries):
            try:
                response = self.session.get(
                    url, params=params, timeout=self.timeout
                )
                return self._handle_response(response)
            except KeilaRateLimitError:
                if attempt < max_retries - 1:
                    backoff = 2 ** attempt
                    logger.warning(
                        "keila_client.retry",
                        extra={"attempt": attempt + 1, "backoff": backoff},
                    )
                    time.sleep(backoff)
                    continue
                raise
            except requests.ConnectionError as e:
                raise KeilaApiError(f"Connection error: {e}") from e
            except requests.Timeout as e:
                raise KeilaApiError(f"Request timed out: {e}") from e

        if last_error:
            raise last_error

        raise KeilaApiError("Max retries exceeded")

    @staticmethod
    def _normalize_campaign(raw: dict[str, Any]) -> dict[str, Any]:
        sent_at = raw.get("sent_at")
        scheduled_for = raw.get("scheduled_for")

        if sent_at is not None:
            inferred_status = "sent"
        elif scheduled_for is not None:
            inferred_status = "scheduled"
        else:
            inferred_status = raw.get("status", "draft")

        return {
            "id": raw.get("id"),
            "subject": raw.get("subject"),
            "status": raw.get("status", inferred_status),
            "created_at": raw.get("inserted_at"),
            "scheduled_at": raw.get("scheduled_for"),
            "updated_at": raw.get("updated_at"),
        }

    def get_campaigns(
        self, status: str | None = None, q: str | None = None
    ) -> list[dict[str, Any]]:
        url = self._build_url("/campaigns")
        params: dict[str, str] = {}

        if status is not None:
            params["filter[status]"] = status
        if q is not None:
            params["filter[subject]"] = q

        logger.info(
            "keila_client.fetch_campaigns",
            extra={"status": status, "q": q, "params_count": len(params)},
        )

        data = self._request_with_retry(url, params)
        raw_campaigns: list[dict[str, Any]] = data.get("data", [])

        campaigns = [self._normalize_campaign(c) for c in raw_campaigns]

        logger.info(
            "keila_client.campaigns_fetched",
            extra={
                "count": len(campaigns),
                "campaign_ids": [c.get("id") for c in campaigns],
            },
        )

        return campaigns
