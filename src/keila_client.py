import logging
import time
from typing import Any

import requests

logger = logging.getLogger("keyla-mcp")


class KeilaError(Exception):
    pass


class KeilaAuthError(KeilaError):
    pass


class KeilaNotFoundError(KeilaError):
    pass


class KeilaValidationError(KeilaError):
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
        if response.status_code == 404:
            raise KeilaNotFoundError(
                f"Keila API returned 404 Not Found: {response.request.url}"
            )
        if response.status_code == 422:
            body = response.json()
            detail = body.get("error", body.get("details", "Validation error"))
            raise KeilaValidationError(
                f"Keila API returned 422: {detail}"
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
        if not response.content:
            return {}
        return response.json()

    _METHODS = {
        "GET": lambda s, u, **kw: s.session.get(u, **kw),
        "POST": lambda s, u, **kw: s.session.post(u, **kw),
        "PUT": lambda s, u, **kw: s.session.put(u, **kw),
        "PATCH": lambda s, u, **kw: s.session.patch(u, **kw),
        "DELETE": lambda s, u, **kw: s.session.delete(u, **kw),
    }

    def _request_with_retry(
        self,
        url: str,
        params: dict[str, str] | None = None,
        method: str = "GET",
        json_body: dict[str, Any] | None = None,
        max_retries: int = 3,
    ) -> dict[str, Any]:
        last_error: Exception | None = None
        http_fn = self._METHODS[method]
        http_kwargs: dict[str, Any] = {"timeout": self.timeout}
        if params is not None:
            http_kwargs["params"] = params
        if json_body is not None:
            http_kwargs["json"] = json_body

        for attempt in range(max_retries):
            try:
                response = http_fn(self, url, **http_kwargs)
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

    def _get(
        self, path: str, params: dict[str, str] | None = None
    ) -> dict[str, Any]:
        url = self._build_url(path)
        return self._request_with_retry(url, params=params, method="GET")

    def _post(
        self, path: str, json_body: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        url = self._build_url(path)
        return self._request_with_retry(url, method="POST", json_body=json_body)

    def _put(
        self, path: str, json_body: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        url = self._build_url(path)
        return self._request_with_retry(url, method="PUT", json_body=json_body, params=params)

    def _patch(
        self, path: str, json_body: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        url = self._build_url(path)
        return self._request_with_retry(url, method="PATCH", json_body=json_body, params=params)

    def _delete(
        self, path: str, params: dict[str, str] | None = None
    ) -> dict[str, Any]:
        url = self._build_url(path)
        return self._request_with_retry(url, params=params, method="DELETE")

    @staticmethod
    def _unwrap_response(data: dict[str, Any]) -> dict[str, Any]:
        raw = data.get("data", data)
        if isinstance(raw, dict):
            return raw
        return data

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
            "template_id": raw.get("template_id"),
            "sender_id": raw.get("sender_id"),
            "segment_id": raw.get("segment_id"),
            "preview_text": raw.get("preview_text"),
            "settings": raw.get("settings"),
            "data": raw.get("data"),
        }

    def get_campaigns(
        self, status: str | None = None, q: str | None = None
    ) -> list[dict[str, Any]]:
        params: dict[str, str] = {}

        if status is not None:
            params["filter[status]"] = status
        if q is not None:
            params["filter[subject]"] = q

        logger.info(
            "keila_client.fetch_campaigns",
            extra={"status": status, "q": q, "params_count": len(params)},
        )

        data = self._get("/campaigns", params=params)
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

    def create_campaign(
        self,
        subject: str,
        body_type: str,
        text_body: str | None = None,
        json_body: dict | None = None,
        mjml_body: str | None = None,
        preview_text: str | None = None,
        sender_id: str | None = None,
        segment_id: str | None = None,
        data: dict | None = None,
        do_not_track: bool | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "subject": subject,
            "settings": {"type": body_type},
        }
        if text_body is not None:
            body["text_body"] = text_body
        if json_body is not None:
            body["json_body"] = json_body
        if mjml_body is not None:
            body["mjml_body"] = mjml_body
        if preview_text is not None:
            body["preview_text"] = preview_text
        if sender_id is not None:
            body["sender_id"] = sender_id
        if segment_id is not None:
            body["segment_id"] = segment_id
        if data is not None:
            body["data"] = data
        if do_not_track is not None:
            body["do_not_track"] = do_not_track

        logger.info("keila_client.create_campaign", extra={"subject": subject})
        data = self._post("/campaigns", json_body={"data": body})
        return self._unwrap_response(data)

    def get_campaign(self, id: str) -> dict[str, Any]:
        logger.info("keila_client.get_campaign", extra={"id": id})
        data = self._get(f"/campaigns/{id}")
        return self._unwrap_response(data)

    def update_campaign(
        self,
        id: str,
        subject: str | None = None,
        text_body: str | None = None,
        json_body: dict | None = None,
        mjml_body: str | None = None,
        preview_text: str | None = None,
        sender_id: str | None = None,
        segment_id: str | None = None,
        data: dict | None = None,
        do_not_track: bool | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {}
        if subject is not None:
            body["subject"] = subject
        if text_body is not None:
            body["text_body"] = text_body
        if json_body is not None:
            body["json_body"] = json_body
        if mjml_body is not None:
            body["mjml_body"] = mjml_body
        if preview_text is not None:
            body["preview_text"] = preview_text
        if sender_id is not None:
            body["sender_id"] = sender_id
        if segment_id is not None:
            body["segment_id"] = segment_id
        if data is not None:
            body["data"] = data
        if do_not_track is not None:
            body["do_not_track"] = do_not_track

        logger.info("keila_client.update_campaign", extra={"id": id})
        data = self._put(f"/campaigns/{id}", json_body={"data": body})
        return self._unwrap_response(data)

    def delete_campaign(self, id: str) -> dict[str, Any]:
        logger.info("keila_client.delete_campaign", extra={"id": id})
        return self._delete(f"/campaigns/{id}")

    def send_campaign(self, id: str, sender_id: str | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {}
        if sender_id is not None:
            body["sender_id"] = sender_id
        logger.info("keila_client.send_campaign", extra={"id": id})
        return self._post(f"/campaigns/{id}/actions/send", json_body=body or None)

    def schedule_campaign(self, id: str, scheduled_for: str) -> dict[str, Any]:
        logger.info("keila_client.schedule_campaign", extra={"id": id, "scheduled_for": scheduled_for})
        data = self._post(f"/campaigns/{id}/actions/schedule", json_body={"data": {"scheduled_for": scheduled_for}})
        return self._unwrap_response(data)

    # Keys that the Keila API rejects on POST /forms but accepts on PATCH /forms/:id
    _FORM_CREATE_BLOCKED_SETTINGS = frozenset(
        {"welcome_enabled", "welcome_subject", "welcome_markdown_body"}
    )

    def create_form(
        self,
        name: str,
        sender_id: str | None = None,
        fields: list[dict] | None = None,
        settings: dict | None = None,
    ) -> dict[str, Any]:
        logger.info("keila_client.create_form", extra={"name": name})
        raw_settings: dict = settings if settings is not None else {}
        # Split settings into create-safe and welcome-only parts
        deferred_settings = {
            k: v
            for k, v in raw_settings.items()
            if k in self._FORM_CREATE_BLOCKED_SETTINGS
        }
        create_settings = {
            k: v
            for k, v in raw_settings.items()
            if k not in self._FORM_CREATE_BLOCKED_SETTINGS
        }
        body: dict[str, Any] = {"name": name}
        if sender_id is not None:
            body["sender_id"] = sender_id
        if fields is not None:
            # cast must be True for fields to render on the public form page;
            # omitting or sending null causes a 500. Default to True if not set.
            body["fields"] = [
                {k: v for k, v in {**{"cast": True}, **f}.items() if v is not None}
                for f in fields
            ]
        body["settings"] = create_settings
        data = self._post("/forms", json_body={"data": body})
        form = self._unwrap_response(data)
        # Apply deferred welcome settings via PATCH if needed
        if deferred_settings:
            form = self.update_form(form["id"], settings=deferred_settings)
        return form

    def update_form(
        self,
        id: str,
        name: str | None = None,
        sender_id: str | None = None,
        fields: list[dict] | None = None,
        settings: dict | None = None,
    ) -> dict[str, Any]:
        logger.info("keila_client.update_form", extra={"id": id})
        body: dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if sender_id is not None:
            body["sender_id"] = sender_id
        if fields is not None:
            body["fields"] = [
                {k: v for k, v in {**{"cast": True}, **f}.items() if v is not None}
                for f in fields
            ]
        if settings is not None:
            body["settings"] = settings
        data = self._patch(f"/forms/{id}", json_body={"data": body})
        return self._unwrap_response(data)

    def delete_form(self, id: str) -> dict[str, Any]:
        logger.info("keila_client.delete_form", extra={"id": id})
        data = self._delete(f"/forms/{id}")
        return self._unwrap_response(data)


    def create_contact(
        self,
        email: str,
        first_name: str | None = None,
        last_name: str | None = None,
        external_id: str | None = None,
        status: str | None = None,
        data: dict | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"email": email}
        if first_name is not None:
            body["first_name"] = first_name
        if last_name is not None:
            body["last_name"] = last_name
        if external_id is not None:
            body["external_id"] = external_id
        if status is not None:
            body["status"] = status
        if data is not None:
            body["data"] = data

        logger.info("keila_client.create_contact", extra={"email": email})
        resp = self._post("/contacts", json_body={"data": body})
        return self._unwrap_response(resp)

    def get_contact(self, id: str, id_type: str | None = None) -> dict[str, Any]:
        params: dict[str, str] = {}
        if id_type is not None:
            params["id_type"] = id_type

        logger.info("keila_client.get_contact", extra={"id": id, "id_type": id_type})
        resp = self._get(f"/contacts/{id}", params=params or None)
        return self._unwrap_response(resp)

    def update_contact(
        self,
        id: str,
        email: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        external_id: str | None = None,
        data: dict | None = None,
        id_type: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {}
        params: dict[str, str] = {}
        if email is not None:
            body["email"] = email
        if first_name is not None:
            body["first_name"] = first_name
        if last_name is not None:
            body["last_name"] = last_name
        if external_id is not None:
            body["external_id"] = external_id
        if data is not None:
            body["data"] = data
        if id_type is not None:
            params["id_type"] = id_type

        logger.info("keila_client.update_contact", extra={"id": id})
        resp = self._put(f"/contacts/{id}", json_body={"data": body}, params=params or None)
        return self._unwrap_response(resp)

    def delete_contact(self, id: str, id_type: str | None = None) -> dict[str, Any]:
        params: dict[str, str] = {}
        if id_type is not None:
            params["id_type"] = id_type

        logger.info("keila_client.delete_contact", extra={"id": id, "id_type": id_type})
        return self._delete(f"/contacts/{id}", params=params or None)

    def list_contacts(
        self, page: int = 0, page_size: int = 50, q: str | None = None
    ) -> dict[str, Any]:
        # Keila API /contacts rejects any extra query params with 400 "Unexpected field".
        # Fetch all contacts, then apply filter and pagination client-side.
        logger.info("keila_client.list_contacts", extra={"page": page, "page_size": page_size, "q": q})
        raw = self._get("/contacts")
        contacts: list[dict] = raw.get("data", [])

        # Client-side substring filter on email, first_name, last_name
        if q:
            q_lower = q.lower()
            contacts = [
                c for c in contacts
                if q_lower in (c.get("email") or "").lower()
                or q_lower in (c.get("first_name") or "").lower()
                or q_lower in (c.get("last_name") or "").lower()
            ]

        total_count = len(contacts)

        # Client-side pagination (page is 0-based)
        start = page * page_size
        end = start + page_size
        page_data = contacts[start:end]

        import math
        page_count = math.ceil(total_count / page_size) if page_size > 0 else 0

        return {
            "data": page_data,
            "meta": {
                "total_count": total_count,
                "page": page,
                "page_size": page_size,
                "page_count": page_count,
                "server_pagination": False,
            },
        }

    def list_senders(self) -> list[dict[str, Any]]:
        logger.info("keila_client.list_senders")
        data = self._get("/senders")
        return data.get("data", [])

    def create_segment(self, name: str, filter: dict) -> dict[str, Any]:
        body = {"name": name, "filter": filter}
        logger.info("keila_client.create_segment", extra={"name": name})
        resp = self._post("/segments", json_body={"data": body})
        return self._unwrap_response(resp)

    def list_segments(self) -> list[dict[str, Any]]:
        logger.info("keila_client.list_segments")
        data = self._get("/segments")
        return data.get("data", [])

    def get_segment(self, id: str) -> dict[str, Any]:
        logger.info("keila_client.get_segment", extra={"id": id})
        resp = self._get(f"/segments/{id}")
        return self._unwrap_response(resp)

    def delete_segment(self, id: str) -> dict[str, Any]:
        logger.info("keila_client.delete_segment", extra={"id": id})
        return self._delete(f"/segments/{id}")

    def list_forms(self) -> list[dict[str, Any]]:
        logger.info("keila_client.list_forms")
        data = self._get("/forms")
        return data.get("data", [])

    def get_form(self, id: str) -> dict[str, Any]:
        logger.info("keila_client.get_form", extra={"id": id})
        resp = self._get(f"/forms/{id}")
        return self._unwrap_response(resp)
