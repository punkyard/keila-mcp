import logging
import os
import sys
import time
import uuid
from typing import Literal

from keila_mcp.keila_client import (
    KeilaApiError,
    KeilaAuthError,
    KeilaClient,
    KeilaNotFoundError,
    KeilaRateLimitError,
    KeilaValidationError,
)

logger = logging.getLogger("keila-mcp")

VALID_STATUSES = {"draft", "scheduled", "sent", "archived", "paused"}
_client: KeilaClient | None = None


def _safe_tool(fn):
    """Decorator: catch any unhandled exception in a tool and return {"error": ...}."""
    import functools

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            logger.error(
                "tool.unexpected_error", extra={"tool": fn.__name__, "error": str(e)}
            )
            return {"error": f"Unexpected error: {e}"}

    return wrapper


def _validate_env() -> None:
    """Exit with a clear error if required env vars are missing."""
    missing = [v for v in ("KEILA_URL", "KEILA_API_KEY") if not os.environ.get(v)]
    if missing:
        for var in missing:
            print(
                f"ERROR: required environment variable {var} is not set.",
                file=sys.stderr,
            )
        sys.exit(1)


def get_client() -> KeilaClient:
    global _client
    if _client is None:
        base_url = os.environ.get(
            "KEILA_URL", "https://your-keila-instance.example.com"
        )
        api_key = os.environ.get("KEILA_API_KEY", "")
        _client = KeilaClient(base_url=base_url, api_key=api_key)
    return _client


@_safe_tool
def list_campaigns(status: str | None = None, q: str | None = None) -> list | dict:
    correlation_id = str(uuid.uuid4())[:8]

    if status is not None and status not in VALID_STATUSES:
        valid = ", ".join(sorted(VALID_STATUSES))
        msg = f"Invalid status '{status}'. Must be one of: {valid}"
        logger.error(
            "campaigns.list.errors",
            extra={
                "correlation_id": correlation_id,
                "status": status,
                "error_type": "validation",
            },
        )
        return {"error": f"400: {msg}"}

    start = time.time()
    try:
        campaigns = get_client().get_campaigns(status=status, q=q)
        campaigns.sort(key=lambda c: c.get("created_at", ""), reverse=True)
        elapsed = time.time() - start

        logger.info(
            "campaigns.list.latency",
            extra={
                "correlation_id": correlation_id,
                "duration_ms": round(elapsed * 1000, 1),
                "count": len(campaigns),
                "status_filter": status,
                "q_filter": q,
            },
        )
        logger.info(
            "campaigns.list.result",
            extra={
                "correlation_id": correlation_id,
                "count": len(campaigns),
                "campaign_ids": [c.get("id") for c in campaigns],
            },
        )
        return campaigns
    except KeilaAuthError as e:
        elapsed = time.time() - start
        logger.error(
            "campaigns.list.errors",
            extra={
                "correlation_id": correlation_id,
                "duration_ms": round(elapsed * 1000, 1),
                "error_type": "auth",
            },
        )
        return {"error": str(e)}
    except KeilaRateLimitError as e:
        elapsed = time.time() - start
        logger.error(
            "campaigns.list.errors",
            extra={
                "correlation_id": correlation_id,
                "duration_ms": round(elapsed * 1000, 1),
                "error_type": "rate_limit",
            },
        )
        return {"error": str(e)}
    except KeilaApiError as e:
        elapsed = time.time() - start
        logger.error(
            "campaigns.list.errors",
            extra={
                "correlation_id": correlation_id,
                "duration_ms": round(elapsed * 1000, 1),
                "error_type": "api",
            },
        )
        return {"error": str(e)}


@_safe_tool
def create_campaign_tool(
    subject: str,
    body_type: str,
    text_body: str | None = None,
    preview_text: str | None = None,
    sender_id: str | None = None,
    segment_id: str | None = None,
    data: dict | None = None,
    do_not_track: bool | None = None,
) -> dict:
    correlation_id = str(uuid.uuid4())[:8]
    valid_types = {"markdown", "text", "block", "mjml"}
    if body_type not in valid_types:
        valid = ", ".join(sorted(valid_types))
        msg = f"Invalid body_type '{body_type}'. Must be one of: {valid}"
        logger.error(
            "campaigns.create.error",
            extra={"correlation_id": correlation_id, "error_type": "validation"},
        )
        return {"error": f"400: {msg}"}

    start = time.time()
    try:
        result = get_client().create_campaign(
            subject=subject,
            body_type=body_type,
            text_body=text_body,
            preview_text=preview_text,
            sender_id=sender_id,
            segment_id=segment_id,
            data=data,
            do_not_track=do_not_track,
        )
        elapsed = time.time() - start
        logger.info(
            "campaigns.create.result",
            extra={
                "correlation_id": correlation_id,
                "duration_ms": round(elapsed * 1000, 1),
                "campaign_id": result.get("id"),
            },
        )
        return result
    except KeilaAuthError as e:
        return {"error": str(e)}
    except KeilaValidationError as e:
        return {"error": str(e)}
    except KeilaRateLimitError as e:
        return {"error": str(e)}
    except KeilaApiError as e:
        return {"error": str(e)}


@_safe_tool
def get_campaign_tool(id: str) -> dict:
    correlation_id = str(uuid.uuid4())[:8]
    start = time.time()
    try:
        result = get_client().get_campaign(id)
        elapsed = time.time() - start
        logger.info(
            "campaigns.get.result",
            extra={
                "correlation_id": correlation_id,
                "duration_ms": round(elapsed * 1000, 1),
                "campaign_id": id,
            },
        )
        return result
    except KeilaNotFoundError as e:
        return {"error": str(e)}
    except KeilaAuthError as e:
        return {"error": str(e)}
    except KeilaRateLimitError as e:
        return {"error": str(e)}
    except KeilaApiError as e:
        return {"error": str(e)}


@_safe_tool
def update_campaign_tool(
    id: str,
    subject: str | None = None,
    preview_text: str | None = None,
) -> dict:
    correlation_id = str(uuid.uuid4())[:8]
    start = time.time()
    try:
        campaign = get_client().get_campaign(id)
        if campaign.get("status") == "sent":
            logger.warning(
                "campaigns.update.sent_warning",
                extra={
                    "correlation_id": correlation_id,
                    "campaign_id": id,
                },
            )
        result = get_client().update_campaign(
            id=id,
            subject=subject,
            preview_text=preview_text,
        )
        elapsed = time.time() - start
        logger.info(
            "campaigns.update.result",
            extra={
                "correlation_id": correlation_id,
                "duration_ms": round(elapsed * 1000, 1),
                "campaign_id": id,
            },
        )
        if campaign.get("status") == "sent":
            result["warning"] = (
                "Campaign has already been sent. Updates may not affect delivered emails."
            )
        return result
    except KeilaNotFoundError as e:
        return {"error": str(e)}
    except KeilaAuthError as e:
        return {"error": str(e)}
    except KeilaRateLimitError as e:
        return {"error": str(e)}
    except KeilaApiError as e:
        return {"error": str(e)}


@_safe_tool
def delete_campaign_tool(id: str) -> dict:
    correlation_id = str(uuid.uuid4())[:8]
    start = time.time()
    try:
        campaign = get_client().get_campaign(id)
        if campaign.get("status") == "sent":
            logger.warning(
                "campaigns.delete.sent_warning",
                extra={
                    "correlation_id": correlation_id,
                    "campaign_id": id,
                },
            )
        result = get_client().delete_campaign(id)
        elapsed = time.time() - start
        logger.info(
            "campaigns.delete.result",
            extra={
                "correlation_id": correlation_id,
                "duration_ms": round(elapsed * 1000, 1),
                "campaign_id": id,
            },
        )
        if campaign.get("status") == "sent":
            result["warning"] = (
                "Campaign had already been sent. Recipients may have already received it."
            )
        return result
    except KeilaNotFoundError as e:
        return {"error": str(e)}
    except KeilaAuthError as e:
        return {"error": str(e)}
    except KeilaRateLimitError as e:
        return {"error": str(e)}
    except KeilaApiError as e:
        return {"error": str(e)}


@_safe_tool
def send_campaign_tool(id: str, sender_id: str | None = None) -> dict:
    correlation_id = str(uuid.uuid4())[:8]
    start = time.time()
    try:
        if sender_id is None:
            campaign = get_client().get_campaign(id)
            if not campaign.get("sender_id"):
                return {
                    "error": "Campaign has no sender configured. Set a sender_id on the campaign or pass sender_id to send_campaign."
                }
        result = get_client().send_campaign(id=id, sender_id=sender_id)
        elapsed = time.time() - start
        logger.info(
            "campaigns.send.result",
            extra={
                "correlation_id": correlation_id,
                "duration_ms": round(elapsed * 1000, 1),
                "campaign_id": id,
            },
        )
        return result
    except KeilaNotFoundError as e:
        return {"error": str(e)}
    except KeilaAuthError as e:
        return {"error": str(e)}
    except KeilaRateLimitError as e:
        return {"error": str(e)}
    except KeilaApiError as e:
        return {"error": str(e)}


@_safe_tool
def schedule_campaign_tool(
    id: str, scheduled_for: str, sender_id: str | None = None
) -> dict:
    correlation_id = str(uuid.uuid4())[:8]
    start = time.time()
    try:
        if sender_id is None:
            campaign = get_client().get_campaign(id)
            if not campaign.get("sender_id"):
                return {
                    "error": "Campaign has no sender configured. Set a sender_id on the campaign or pass sender_id to schedule_campaign."
                }
        result = get_client().schedule_campaign(
            id=id,
            scheduled_for=scheduled_for,
            sender_id=sender_id,
        )
        elapsed = time.time() - start
        logger.info(
            "campaigns.schedule.result",
            extra={
                "correlation_id": correlation_id,
                "duration_ms": round(elapsed * 1000, 1),
                "campaign_id": id,
                "scheduled_for": scheduled_for,
            },
        )
        return result
    except KeilaNotFoundError as e:
        return {"error": str(e)}
    except KeilaAuthError as e:
        return {"error": str(e)}
    except KeilaRateLimitError as e:
        return {"error": str(e)}
    except KeilaApiError as e:
        return {"error": str(e)}


@_safe_tool
def create_contact_tool(
    email: str,
    first_name: str | None = None,
    last_name: str | None = None,
    external_id: str | None = None,
    status: str | None = None,
    data: dict | None = None,
) -> dict:
    correlation_id = str(uuid.uuid4())[:8]
    start = time.time()
    try:
        result = get_client().create_contact(
            email=email,
            first_name=first_name,
            last_name=last_name,
            external_id=external_id,
            status=status,
            data=data,
        )
        logger.info(
            "contacts.create.result",
            extra={
                "correlation_id": correlation_id,
                "duration_ms": round((time.time() - start) * 1000, 1),
                "contact_id": result.get("id"),
            },
        )
        return result
    except KeilaValidationError as e:
        return {"error": str(e)}
    except KeilaAuthError as e:
        return {"error": str(e)}
    except KeilaRateLimitError as e:
        return {"error": str(e)}
    except KeilaApiError as e:
        return {"error": str(e)}


@_safe_tool
def get_contact_tool(id: str, id_type: str | None = None) -> dict:
    correlation_id = str(uuid.uuid4())[:8]
    start = time.time()
    try:
        result = get_client().get_contact(id, id_type)
        logger.info(
            "contacts.get.result",
            extra={
                "correlation_id": correlation_id,
                "duration_ms": round((time.time() - start) * 1000, 1),
                "contact_id": id,
            },
        )
        return result
    except KeilaNotFoundError as e:
        return {"error": str(e)}
    except KeilaAuthError as e:
        return {"error": str(e)}
    except KeilaRateLimitError as e:
        return {"error": str(e)}
    except KeilaApiError as e:
        return {"error": str(e)}


@_safe_tool
def update_contact_tool(
    id: str,
    email: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    external_id: str | None = None,
    data: dict | None = None,
    id_type: str | None = None,
) -> dict:
    correlation_id = str(uuid.uuid4())[:8]
    start = time.time()
    try:
        result = get_client().update_contact(
            id=id,
            email=email,
            first_name=first_name,
            last_name=last_name,
            external_id=external_id,
            data=data,
            id_type=id_type,
        )
        logger.info(
            "contacts.update.result",
            extra={
                "correlation_id": correlation_id,
                "duration_ms": round((time.time() - start) * 1000, 1),
                "contact_id": id,
            },
        )
        return result
    except KeilaNotFoundError as e:
        return {"error": str(e)}
    except KeilaAuthError as e:
        return {"error": str(e)}
    except KeilaRateLimitError as e:
        return {"error": str(e)}
    except KeilaApiError as e:
        return {"error": str(e)}


@_safe_tool
def delete_contact_tool(id: str, id_type: str | None = None) -> dict:
    correlation_id = str(uuid.uuid4())[:8]
    start = time.time()
    try:
        result = get_client().delete_contact(id, id_type)
        logger.info(
            "contacts.delete.result",
            extra={
                "correlation_id": correlation_id,
                "duration_ms": round((time.time() - start) * 1000, 1),
                "contact_id": id,
            },
        )
        return result
    except KeilaNotFoundError as e:
        return {"error": str(e)}
    except KeilaAuthError as e:
        return {"error": str(e)}
    except KeilaRateLimitError as e:
        return {"error": str(e)}
    except KeilaApiError as e:
        return {"error": str(e)}


@_safe_tool
def list_contacts_tool(
    page: int = 0, page_size: int = 50, q: str | None = None
) -> dict:
    correlation_id = str(uuid.uuid4())[:8]
    start = time.time()
    try:
        result = get_client().list_contacts(page=page, page_size=page_size, q=q)
        logger.info(
            "contacts.list.result",
            extra={
                "correlation_id": correlation_id,
                "duration_ms": round((time.time() - start) * 1000, 1),
                "page": page,
                "page_size": page_size,
                "q": q,
            },
        )
        return result
    except KeilaAuthError as e:
        return {"error": str(e)}
    except KeilaRateLimitError as e:
        return {"error": str(e)}
    except KeilaApiError as e:
        return {"error": str(e)}


@_safe_tool
def list_senders_tool() -> list | dict:
    correlation_id = str(uuid.uuid4())[:8]
    start = time.time()
    try:
        result = get_client().list_senders()
        logger.info(
            "senders.list.result",
            extra={
                "correlation_id": correlation_id,
                "duration_ms": round((time.time() - start) * 1000, 1),
                "count": len(result),
            },
        )
        return result
    except KeilaAuthError as e:
        return {"error": str(e)}
    except KeilaRateLimitError as e:
        return {"error": str(e)}
    except KeilaApiError as e:
        return {"error": str(e)}


@_safe_tool
def create_segment_tool(name: str, filter: dict) -> dict:
    correlation_id = str(uuid.uuid4())[:8]
    start = time.time()
    try:
        result = get_client().create_segment(name=name, filter=filter)
        logger.info(
            "segments.create.result",
            extra={
                "correlation_id": correlation_id,
                "duration_ms": round((time.time() - start) * 1000, 1),
                "segment_id": result.get("id"),
            },
        )
        return result
    except KeilaAuthError as e:
        return {"error": str(e)}
    except KeilaRateLimitError as e:
        return {"error": str(e)}
    except KeilaApiError as e:
        return {"error": str(e)}


@_safe_tool
def list_segments_tool() -> list | dict:
    correlation_id = str(uuid.uuid4())[:8]
    start = time.time()
    try:
        result = get_client().list_segments()
        logger.info(
            "segments.list.result",
            extra={
                "correlation_id": correlation_id,
                "duration_ms": round((time.time() - start) * 1000, 1),
                "count": len(result),
            },
        )
        return result
    except KeilaAuthError as e:
        return {"error": str(e)}
    except KeilaRateLimitError as e:
        return {"error": str(e)}
    except KeilaApiError as e:
        return {"error": str(e)}


@_safe_tool
def get_segment_tool(id: str) -> dict:
    correlation_id = str(uuid.uuid4())[:8]
    start = time.time()
    try:
        result = get_client().get_segment(id)
        logger.info(
            "segments.get.result",
            extra={
                "correlation_id": correlation_id,
                "duration_ms": round((time.time() - start) * 1000, 1),
                "segment_id": id,
            },
        )
        return result
    except KeilaNotFoundError as e:
        return {"error": str(e)}
    except KeilaAuthError as e:
        return {"error": str(e)}
    except KeilaRateLimitError as e:
        return {"error": str(e)}
    except KeilaApiError as e:
        return {"error": str(e)}


@_safe_tool
def delete_segment_tool(id: str) -> dict:
    correlation_id = str(uuid.uuid4())[:8]
    start = time.time()
    try:
        result = get_client().delete_segment(id)
        logger.info(
            "segments.delete.result",
            extra={
                "correlation_id": correlation_id,
                "duration_ms": round((time.time() - start) * 1000, 1),
                "segment_id": id,
            },
        )
        return result
    except KeilaNotFoundError as e:
        return {"error": str(e)}
    except KeilaAuthError as e:
        return {"error": str(e)}
    except KeilaRateLimitError as e:
        return {"error": str(e)}
    except KeilaApiError as e:
        return {"error": str(e)}


@_safe_tool
def list_forms_tool() -> list | dict:
    correlation_id = str(uuid.uuid4())[:8]
    start = time.time()
    try:
        result = get_client().list_forms()
        logger.info(
            "forms.list.result",
            extra={
                "correlation_id": correlation_id,
                "duration_ms": round((time.time() - start) * 1000, 1),
                "count": len(result),
            },
        )
        return result
    except KeilaAuthError as e:
        return {"error": str(e)}
    except KeilaRateLimitError as e:
        return {"error": str(e)}
    except KeilaApiError as e:
        return {"error": str(e)}


@_safe_tool
def get_form_tool(id: str) -> dict:
    correlation_id = str(uuid.uuid4())[:8]
    start = time.time()
    try:
        result = get_client().get_form(id)
        logger.info(
            "forms.get.result",
            extra={
                "correlation_id": correlation_id,
                "duration_ms": round((time.time() - start) * 1000, 1),
                "form_id": id,
            },
        )
        return result
    except KeilaNotFoundError as e:
        return {"error": str(e)}
    except KeilaAuthError as e:
        return {"error": str(e)}
    except KeilaRateLimitError as e:
        return {"error": str(e)}
    except KeilaApiError as e:
        return {"error": str(e)}


@_safe_tool
def create_form_tool(
    name: str,
    sender_id: str | None = None,
    fields: list | None = None,
    settings: dict | None = None,
) -> dict:
    correlation_id = str(uuid.uuid4())[:8]
    start = time.time()
    try:
        result = get_client().create_form(
            name=name,
            sender_id=sender_id,
            fields=fields,
            settings=settings,
        )
        logger.info(
            "forms.create.result",
            extra={
                "correlation_id": correlation_id,
                "duration_ms": round((time.time() - start) * 1000, 1),
                "form_id": result.get("id"),
            },
        )
        return result
    except KeilaAuthError as e:
        return {"error": str(e)}
    except KeilaRateLimitError as e:
        return {"error": str(e)}
    except KeilaApiError as e:
        return {"error": str(e)}


@_safe_tool
def delete_form_tool(id: str) -> dict:
    correlation_id = str(uuid.uuid4())[:8]
    start = time.time()
    try:
        get_client().delete_form(id)
        logger.info(
            "forms.delete.result",
            extra={
                "correlation_id": correlation_id,
                "duration_ms": round((time.time() - start) * 1000, 1),
                "form_id": id,
            },
        )
        return {"message": f"Form {id} deleted successfully"}
    except KeilaNotFoundError as e:
        return {"error": str(e)}
    except KeilaAuthError as e:
        return {"error": str(e)}
    except KeilaRateLimitError as e:
        return {"error": str(e)}
    except KeilaApiError as e:
        return {"error": str(e)}


@_safe_tool
def update_segment_tool(
    id: str, name: str | None = None, filter: dict | None = None
) -> dict:
    correlation_id = str(uuid.uuid4())[:8]
    start = time.time()
    try:
        result = get_client().update_segment(id, name=name, filter=filter)
        logger.info(
            "segments.update.result",
            extra={
                "correlation_id": correlation_id,
                "duration_ms": round((time.time() - start) * 1000, 1),
                "segment_id": id,
            },
        )
        return result
    except ValueError as e:
        return {"error": str(e)}
    except KeilaNotFoundError as e:
        return {"error": str(e)}
    except KeilaAuthError as e:
        return {"error": str(e)}
    except KeilaRateLimitError as e:
        return {"error": str(e)}
    except KeilaApiError as e:
        return {"error": str(e)}


@_safe_tool
def update_form_tool(
    id: str,
    name: str | None = None,
    sender_id: str | None = None,
    fields: list | None = None,
    settings: dict | None = None,
) -> dict:
    correlation_id = str(uuid.uuid4())[:8]
    start = time.time()
    try:
        result = get_client().update_form(
            id, name=name, sender_id=sender_id, fields=fields, settings=settings
        )
        logger.info(
            "forms.update.result",
            extra={
                "correlation_id": correlation_id,
                "duration_ms": round((time.time() - start) * 1000, 1),
                "form_id": id,
            },
        )
        return result
    except KeilaNotFoundError as e:
        return {"error": str(e)}
    except KeilaAuthError as e:
        return {"error": str(e)}
    except KeilaRateLimitError as e:
        return {"error": str(e)}
    except KeilaApiError as e:
        return {"error": str(e)}


@_safe_tool
def update_contact_data_tool(id: str, data: dict, id_type: str | None = None) -> dict:
    correlation_id = str(uuid.uuid4())[:8]
    start = time.time()
    try:
        result = get_client().update_contact_data(id, data, id_type=id_type)
        logger.info(
            "contacts.update_data.result",
            extra={
                "correlation_id": correlation_id,
                "duration_ms": round((time.time() - start) * 1000, 1),
                "contact_id": id,
            },
        )
        return result
    except KeilaNotFoundError as e:
        return {"error": str(e)}
    except KeilaAuthError as e:
        return {"error": str(e)}
    except KeilaRateLimitError as e:
        return {"error": str(e)}
    except KeilaApiError as e:
        return {"error": str(e)}


@_safe_tool
def replace_contact_data_tool(id: str, data: dict, id_type: str | None = None) -> dict:
    correlation_id = str(uuid.uuid4())[:8]
    start = time.time()
    try:
        result = get_client().replace_contact_data(id, data, id_type=id_type)
        logger.info(
            "contacts.replace_data.result",
            extra={
                "correlation_id": correlation_id,
                "duration_ms": round((time.time() - start) * 1000, 1),
                "contact_id": id,
            },
        )
        return result
    except KeilaNotFoundError as e:
        return {"error": str(e)}
    except KeilaAuthError as e:
        return {"error": str(e)}
    except KeilaRateLimitError as e:
        return {"error": str(e)}
    except KeilaApiError as e:
        return {"error": str(e)}


@_safe_tool
def submit_form_tool(
    form_id: str,
    email: str,
    first_name: str | None = None,
    last_name: str | None = None,
    external_id: str | None = None,
    status: str | None = None,
    data: dict | None = None,
) -> dict:
    correlation_id = str(uuid.uuid4())[:8]
    start = time.time()
    try:
        result = get_client().submit_form(
            form_id=form_id,
            email=email,
            first_name=first_name,
            last_name=last_name,
            external_id=external_id,
            status=status,
            data=data,
        )
        logger.info(
            "forms.submit.result",
            extra={
                "correlation_id": correlation_id,
                "duration_ms": round((time.time() - start) * 1000, 1),
                "form_id": form_id,
            },
        )
        return result
    except KeilaNotFoundError as e:
        return {"error": str(e)}
    except KeilaAuthError as e:
        return {"error": str(e)}
    except KeilaRateLimitError as e:
        return {"error": str(e)}
    except KeilaApiError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}


def main():
    _validate_env()
    from mcp.server.fastmcp import FastMCP

    app = FastMCP("keila-mcp", instructions="MCP server for Keila API")

    @app.tool()
    def list_campaigns_tool(
        status: str | None = None, q: str | None = None
    ) -> list | dict:
        return list_campaigns(status=status, q=q)

    @app.tool()
    def create_campaign_tool_wrapper(
        subject: str,
        body_type: str,
        text_body: str | None = None,
        preview_text: str | None = None,
        sender_id: str | None = None,
        segment_id: str | None = None,
        data: dict | None = None,
        do_not_track: bool | None = None,
    ) -> dict:
        return create_campaign_tool(
            subject=subject,
            body_type=body_type,
            text_body=text_body,
            preview_text=preview_text,
            sender_id=sender_id,
            segment_id=segment_id,
            data=data,
            do_not_track=do_not_track,
        )

    @app.tool()
    def get_campaign_tool_wrapper(id: str) -> dict:
        return get_campaign_tool(id=id)

    @app.tool()
    def update_campaign_tool_wrapper(
        id: str,
        subject: str | None = None,
        preview_text: str | None = None,
    ) -> dict:
        return update_campaign_tool(id=id, subject=subject, preview_text=preview_text)

    @app.tool()
    def delete_campaign_tool_wrapper(id: str) -> dict:
        return delete_campaign_tool(id=id)

    @app.tool()
    def send_campaign_tool_wrapper(id: str, sender_id: str | None = None) -> dict:
        return send_campaign_tool(id=id, sender_id=sender_id)

    @app.tool()
    def schedule_campaign_tool_wrapper(
        id: str, scheduled_for: str, sender_id: str | None = None
    ) -> dict:
        return schedule_campaign_tool(
            id=id, scheduled_for=scheduled_for, sender_id=sender_id
        )

    @app.tool()
    def create_contact_tool_wrapper(
        email: str,
        first_name: str | None = None,
        last_name: str | None = None,
        external_id: str | None = None,
        status: str | None = None,
        data: dict | None = None,
    ) -> dict:
        return create_contact_tool(
            email=email,
            first_name=first_name,
            last_name=last_name,
            external_id=external_id,
            status=status,
            data=data,
        )

    @app.tool()
    def get_contact_tool_wrapper(id: str, id_type: str | None = None) -> dict:
        return get_contact_tool(id=id, id_type=id_type)

    @app.tool()
    def update_contact_tool_wrapper(
        id: str,
        email: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        external_id: str | None = None,
        data: dict | None = None,
        id_type: str | None = None,
    ) -> dict:
        return update_contact_tool(
            id=id,
            email=email,
            first_name=first_name,
            last_name=last_name,
            external_id=external_id,
            data=data,
            id_type=id_type,
        )

    @app.tool()
    def delete_contact_tool_wrapper(id: str, id_type: str | None = None) -> dict:
        return delete_contact_tool(id=id, id_type=id_type)

    @app.tool()
    def list_contacts_tool_wrapper(
        page: int = 0, page_size: int = 50, q: str | None = None
    ) -> dict:
        return list_contacts_tool(page=page, page_size=page_size, q=q)

    @app.tool()
    def list_senders_tool_wrapper() -> list | dict:
        return list_senders_tool()

    @app.tool()
    def create_segment_tool_wrapper(name: str, filter: dict) -> dict:
        return create_segment_tool(name=name, filter=filter)

    @app.tool()
    def list_segments_tool_wrapper() -> list | dict:
        return list_segments_tool()

    @app.tool()
    def get_segment_tool_wrapper(id: str) -> dict:
        return get_segment_tool(id=id)

    @app.tool()
    def delete_segment_tool_wrapper(id: str) -> dict:
        return delete_segment_tool(id=id)

    @app.tool()
    def list_forms_tool_wrapper() -> list | dict:
        return list_forms_tool()

    @app.tool()
    def get_form_tool_wrapper(id: str) -> dict:
        return get_form_tool(id=id)

    @app.tool()
    def create_form_tool_wrapper(
        name: str,
        sender_id: str | None = None,
        fields: list | None = None,
        settings: dict | None = None,
    ) -> dict:
        return create_form_tool(
            name=name, sender_id=sender_id, fields=fields, settings=settings
        )

    @app.tool()
    def delete_form_tool_wrapper(id: str) -> dict:
        return delete_form_tool(id=id)

    @app.tool()
    def update_segment_tool_wrapper(
        id: str, name: str | None = None, filter: dict | None = None
    ) -> dict:
        """Update a segment's name and/or filter. At least one of name or filter must be provided."""
        return update_segment_tool(id=id, name=name, filter=filter)

    @app.tool()
    def update_form_tool_wrapper(
        id: str,
        name: str | None = None,
        sender_id: str | None = None,
        fields: list | None = None,
        settings: dict | None = None,
    ) -> dict:
        """Update an existing signup form."""
        return update_form_tool(
            id=id, name=name, sender_id=sender_id, fields=fields, settings=settings
        )

    @app.tool()
    def update_contact_data_tool_wrapper(
        id: str, data: dict, id_type: str | None = None
    ) -> dict:
        """Merge new key/value pairs into a contact's custom data field. Existing keys not in data are preserved."""
        return update_contact_data_tool(id=id, data=data, id_type=id_type)

    @app.tool()
    def replace_contact_data_tool_wrapper(
        id: str, data: dict, id_type: str | None = None
    ) -> dict:
        """Replace a contact's entire custom data field with the provided dict."""
        return replace_contact_data_tool(id=id, data=data, id_type=id_type)

    @app.tool()
    def submit_form_tool_wrapper(
        form_id: str,
        email: str,
        first_name: str | None = None,
        last_name: str | None = None,
        external_id: str | None = None,
        status: str | None = None,
        data: dict | None = None,
    ) -> dict:
        """Submit a Keila signup form. Returns the created/updated contact on success (HTTP 200), or {"data": {"double_opt_in_required": true}} if double opt-in is enabled (HTTP 202)."""
        return submit_form_tool(
            form_id=form_id,
            email=email,
            first_name=first_name,
            last_name=last_name,
            external_id=external_id,
            status=status,
            data=data,
        )

    transport: Literal["stdio", "streamable-http"] = "stdio"
    if "--http" in sys.argv:
        transport = "streamable-http"

    if transport != "stdio":
        logger.info("starting_server", extra={"transport": transport})
    app.run(transport=transport)


if __name__ == "__main__":
    main()
