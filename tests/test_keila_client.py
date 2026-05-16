import json
import pytest
from unittest.mock import Mock, patch

from src.keila_client import KeilaClient, KeilaAuthError, KeilaNotFoundError, KeilaRateLimitError, KeilaApiError, KeilaValidationError


def make_mock_response(status_code=200, json_data=None, headers=None, empty_body=False):
    mock = Mock()
    mock.status_code = status_code
    mock.json.return_value = json_data or {}
    mock.headers = headers or {}
    mock.content = b"" if empty_body else b'{"ok": true}'
    return mock


class TestKeilaClientGetCampaigns:
    def setup_method(self):
        self.client = KeilaClient(
            base_url="https://your-keila-instance.example.com",
            api_key="test-key-123"
        )

    # T004: Happy path
    def test_get_campaigns_returns_all_campaigns(self):
        mock_response_data = {
            "data": [
                {"id": "mc_1", "subject": "Welcome", "sent_at": "2026-01-01T01:00:00Z",
                 "inserted_at": "2026-01-01T00:00:00Z",
                 "scheduled_for": None, "updated_at": "2026-01-01T01:00:00Z"},
                {"id": "mc_2", "subject": "Newsletter March",
                 "inserted_at": "2026-03-15T00:00:00Z",
                 "scheduled_for": None, "updated_at": "2026-03-15T12:00:00Z"},
            ]
        }
        mock_resp = make_mock_response(200, mock_response_data)

        with patch.object(self.client.session, "get", return_value=mock_resp) as mock_get:
            result = self.client.get_campaigns()

        assert len(result) == 2
        assert result[0]["id"] == "mc_1"
        assert result[0]["subject"] == "Welcome"
        assert result[0]["status"] == "sent"
        assert result[0]["created_at"] == "2026-01-01T00:00:00Z"
        assert result[1]["id"] == "mc_2"
        assert result[1]["status"] == "draft"

        mock_get.assert_called_once_with(
            "https://your-keila-instance.example.com/api/v1/campaigns",
            params={},
            timeout=10
        )

    # T005: Status filter
    def test_get_campaigns_with_status_filter(self):
        mock_response_data = {
            "data": [
                {"id": "mc_3", "subject": "Scheduled Campaign",
                 "inserted_at": "2026-05-01T00:00:00Z",
                 "scheduled_for": "2026-05-10T09:00:00Z", "updated_at": "2026-05-01T12:00:00Z"},
            ]
        }
        mock_resp = make_mock_response(200, mock_response_data)

        with patch.object(self.client.session, "get", return_value=mock_resp) as mock_get:
            result = self.client.get_campaigns(status="scheduled")

        assert len(result) == 1
        assert result[0]["status"] == "scheduled"

        mock_get.assert_called_once_with(
            "https://your-keila-instance.example.com/api/v1/campaigns",
            params={"filter[status]": "scheduled"},
            timeout=10
        )

    # T006: Subject search
    def test_get_campaigns_with_subject_search(self):
        mock_response_data = {"data": []}
        mock_resp = make_mock_response(200, mock_response_data)

        with patch.object(self.client.session, "get", return_value=mock_resp) as mock_get:
            result = self.client.get_campaigns(q="welcome")

        assert result == []

        mock_get.assert_called_once_with(
            "https://your-keila-instance.example.com/api/v1/campaigns",
            params={"filter[subject]": "welcome"},
            timeout=10
        )

    def test_get_campaigns_with_combined_filters(self):
        mock_response_data = {"data": []}
        mock_resp = make_mock_response(200, mock_response_data)

        with patch.object(self.client.session, "get", return_value=mock_resp) as mock_get:
            result = self.client.get_campaigns(status="sent", q="newsletter")

        assert result == []

        mock_get.assert_called_once_with(
            "https://your-keila-instance.example.com/api/v1/campaigns",
            params={"filter[status]": "sent", "filter[subject]": "newsletter"},
            timeout=10
        )

    # T007: Auth failure
    def test_get_campaigns_auth_failure(self):
        mock_resp = make_mock_response(401, {"error": "Unauthorized"})

        with patch.object(self.client.session, "get", return_value=mock_resp):
            with pytest.raises(KeilaAuthError) as exc:
                self.client.get_campaigns()

        assert "401" in str(exc.value)

    # T008: Rate limit with retry
    def test_get_campaigns_rate_limit_retry_then_success(self):
        mock_resp_429 = make_mock_response(429, {"error": "Rate limit exceeded"})
        mock_resp_200 = make_mock_response(200, {"data": []})

        mock_get = Mock(
            side_effect=[mock_resp_429, mock_resp_429, mock_resp_200]
        )

        with patch.object(self.client.session, "get", mock_get):
            result = self.client.get_campaigns()

        assert result == []
        assert mock_get.call_count == 3

    def test_get_campaigns_rate_limit_exhausted(self):
        mock_resp_429 = make_mock_response(429, {"error": "Rate limit exceeded"})

        mock_get = Mock(return_value=mock_resp_429)

        with patch.object(self.client.session, "get", mock_get):
            with pytest.raises(KeilaRateLimitError) as exc:
                self.client.get_campaigns()

        assert "429" in str(exc.value)
        assert mock_get.call_count >= 3

    # T009: API failure
    def test_get_campaigns_api_failure(self):
        mock_resp = make_mock_response(500, {"error": "Internal Server Error"})

        with patch.object(self.client.session, "get", return_value=mock_resp):
            with pytest.raises(KeilaApiError) as exc:
                self.client.get_campaigns()

        assert "500" in str(exc.value)

    def test_get_campaigns_network_error(self):
        import requests

        with patch.object(self.client.session, "get", side_effect=requests.ConnectionError("Connection refused")):
            with pytest.raises(KeilaApiError) as exc:
                self.client.get_campaigns()

        assert "Connection refused" in str(exc.value)


class TestKeilaClientCreateCampaign:
    def setup_method(self):
        self.client = KeilaClient(base_url="https://your-keila-instance.example.com", api_key="test-key-123")

    def test_create_campaign_required_fields(self):
        mock_resp = make_mock_response(200, {"data": {"id": "mc_42", "subject": "Test", "status": "draft"}})
        with patch.object(self.client.session, "post", return_value=mock_resp) as mock_post:
            result = self.client.create_campaign(subject="Test", body_type="markdown", text_body="Hello")

        assert result["id"] == "mc_42"
        mock_post.assert_called_once_with(
            "https://your-keila-instance.example.com/api/v1/campaigns",
            json={"data": {"subject": "Test", "settings": {"type": "markdown"}, "text_body": "Hello"}},
            timeout=10,
        )

    def test_create_campaign_all_optional_fields(self):
        mock_resp = make_mock_response(200, {"data": {"id": "mc_43", "status": "draft"}})
        with patch.object(self.client.session, "post", return_value=mock_resp) as mock_post:
            result = self.client.create_campaign(
                subject="Full", body_type="mjml", mjml_body="<mjml></mjml>",
                preview_text="Preview", sender_id="s_1", segment_id="sg_1",
                data={"key": "val"}, do_not_track=True,
            )

        assert result["id"] == "mc_43"
        body = mock_post.call_args[1]["json"]["data"]
        assert body["subject"] == "Full"
        assert body["settings"]["type"] == "mjml"
        assert body["mjml_body"] == "<mjml></mjml>"
        assert body["sender_id"] == "s_1"

    def test_create_campaign_422_error(self):
        mock_resp = make_mock_response(422, {"error": "subject can't be blank"})
        with patch.object(self.client.session, "post", return_value=mock_resp):
            with pytest.raises(KeilaValidationError) as exc:
                self.client.create_campaign(subject="", body_type="markdown", text_body="")

        assert "subject" in str(exc.value)


class TestKeilaClientGetCampaign:
    def setup_method(self):
        self.client = KeilaClient(base_url="https://your-keila-instance.example.com", api_key="test-key-123")

    def test_get_campaign_by_id(self):
        mock_resp = make_mock_response(200, {"data": {"id": "mc_1", "subject": "Welcome"}})
        with patch.object(self.client.session, "get", return_value=mock_resp) as mock_get:
            result = self.client.get_campaign("mc_1")

        assert result["id"] == "mc_1"
        mock_get.assert_called_once_with("https://your-keila-instance.example.com/api/v1/campaigns/mc_1", timeout=10)

    def test_get_campaign_404(self):
        mock_resp = make_mock_response(404, {"error": "Not found"})
        with patch.object(self.client.session, "get", return_value=mock_resp):
            with pytest.raises(KeilaNotFoundError):
                self.client.get_campaign("mc_nonexistent")


class TestKeilaClientUpdateCampaign:
    def setup_method(self):
        self.client = KeilaClient(base_url="https://your-keila-instance.example.com", api_key="test-key-123")

    def test_update_campaign_partial_fields(self):
        mock_resp = make_mock_response(200, {"data": {"id": "mc_1", "subject": "Updated"}})
        with patch.object(self.client.session, "put", return_value=mock_resp) as mock_put:
            result = self.client.update_campaign("mc_1", subject="Updated")

        assert result["subject"] == "Updated"
        mock_put.assert_called_once_with(
            "https://your-keila-instance.example.com/api/v1/campaigns/mc_1",
            json={"data": {"subject": "Updated"}},
            timeout=10,
        )

    def test_update_campaign_404(self):
        mock_resp = make_mock_response(404, {"error": "Not found"})
        with patch.object(self.client.session, "put", return_value=mock_resp):
            with pytest.raises(KeilaNotFoundError):
                self.client.update_campaign("mc_gone", subject="Nope")


class TestKeilaClientDeleteCampaign:
    def setup_method(self):
        self.client = KeilaClient(base_url="https://your-keila-instance.example.com", api_key="test-key-123")

    def test_delete_campaign_success(self):
        mock_resp = make_mock_response(200, {"success": True})
        with patch.object(self.client.session, "delete", return_value=mock_resp) as mock_del:
            result = self.client.delete_campaign("mc_1")

        assert result.get("success") is True
        mock_del.assert_called_once_with("https://your-keila-instance.example.com/api/v1/campaigns/mc_1", timeout=10)

    def test_delete_campaign_204_no_content(self):
        """Keila returns 204 No Content on successful delete — must not crash."""
        mock_resp = make_mock_response(204, empty_body=True)
        with patch.object(self.client.session, "delete", return_value=mock_resp):
            result = self.client.delete_campaign("mc_1")
        assert result == {}


class TestKeilaClientSendCampaign:
    def setup_method(self):
        self.client = KeilaClient(base_url="https://your-keila-instance.example.com", api_key="test-key-123")

    def test_send_campaign_success(self):
        mock_resp = make_mock_response(200, {"delivery_queued": True, "campaign_id": "mc_1"})
        with patch.object(self.client.session, "post", return_value=mock_resp) as mock_post:
            result = self.client.send_campaign("mc_1")

        assert result["delivery_queued"] is True
        mock_post.assert_called_once_with(
            "https://your-keila-instance.example.com/api/v1/campaigns/mc_1/actions/send",
            timeout=10,
        )

    def test_send_campaign_with_sender(self):
        mock_resp = make_mock_response(200, {"delivery_queued": True, "campaign_id": "mc_1"})
        with patch.object(self.client.session, "post", return_value=mock_resp) as mock_post:
            result = self.client.send_campaign("mc_1", sender_id="s_1")

        assert result["delivery_queued"] is True
        body = mock_post.call_args[1].get("json", {})
        assert body.get("sender_id") == "s_1"


class TestKeilaClientScheduleCampaign:
    def setup_method(self):
        self.client = KeilaClient(base_url="https://your-keila-instance.example.com", api_key="test-key-123")

    def test_schedule_campaign_success(self):
        mock_resp = make_mock_response(200, {"data": {"id": "mc_1", "status": "scheduled"}})
        with patch.object(self.client.session, "post", return_value=mock_resp) as mock_post:
            result = self.client.schedule_campaign("mc_1", "2026-06-01T09:00:00Z")

        assert result["status"] == "scheduled"
        mock_post.assert_called_once_with(
            "https://your-keila-instance.example.com/api/v1/campaigns/mc_1/actions/schedule",
            json={"data": {"scheduled_for": "2026-06-01T09:00:00Z"}},
            timeout=10,
        )


class TestKeilaClientCreateContact:
    def setup_method(self):
        self.client = KeilaClient(base_url="https://your-keila-instance.example.com", api_key="test-key-123")

    def test_create_contact_required_only(self):
        mock_resp = make_mock_response(200, {"data": {"id": "c_1", "email": "a@b.com", "status": "active"}})
        with patch.object(self.client.session, "post", return_value=mock_resp) as mock_post:
            result = self.client.create_contact(email="a@b.com")
        assert result["id"] == "c_1"
        mock_post.assert_called_once_with(
            "https://your-keila-instance.example.com/api/v1/contacts",
            json={"data": {"email": "a@b.com"}},
            timeout=10,
        )

    def test_create_contact_all_fields(self):
        mock_resp = make_mock_response(200, {"data": {"id": "c_2"}})
        with patch.object(self.client.session, "post", return_value=mock_resp) as mock_post:
            self.client.create_contact(email="b@c.com", first_name="John", last_name="Doe",
                                       external_id="ext_1", status="active", data={"city": "NYC"})
        body = mock_post.call_args[1]["json"]["data"]
        assert body["email"] == "b@c.com"
        assert body["first_name"] == "John"
        assert body["status"] == "active"

    def test_create_contact_validation_error(self):
        mock_resp = make_mock_response(422, {"error": "email has invalid format"})
        with patch.object(self.client.session, "post", return_value=mock_resp):
            with pytest.raises(KeilaValidationError):
                self.client.create_contact(email="bad")


class TestKeilaClientGetContact:
    def setup_method(self):
        self.client = KeilaClient(base_url="https://your-keila-instance.example.com", api_key="test-key-123")

    def test_get_contact_by_id(self):
        mock_resp = make_mock_response(200, {"data": {"id": "c_1", "email": "a@b.com"}})
        with patch.object(self.client.session, "get", return_value=mock_resp) as mock_get:
            result = self.client.get_contact("c_1")
        assert result["id"] == "c_1"
        mock_get.assert_called_once_with("https://your-keila-instance.example.com/api/v1/contacts/c_1", timeout=10)

    def test_get_contact_by_email(self):
        mock_resp = make_mock_response(200, {"data": {"id": "c_1"}})
        with patch.object(self.client.session, "get", return_value=mock_resp) as mock_get:
            self.client.get_contact("a@b.com", id_type="email")
        mock_get.assert_called_once_with(
            "https://your-keila-instance.example.com/api/v1/contacts/a@b.com",
            params={"id_type": "email"},
            timeout=10,
        )

    def test_get_contact_404(self):
        mock_resp = make_mock_response(404, {"error": "Not found"})
        with patch.object(self.client.session, "get", return_value=mock_resp):
            with pytest.raises(KeilaNotFoundError):
                self.client.get_contact("c_nonexistent")


class TestKeilaClientUpdateContact:
    def setup_method(self):
        self.client = KeilaClient(base_url="https://your-keila-instance.example.com", api_key="test-key-123")

    def test_update_contact_fields(self):
        mock_resp = make_mock_response(200, {"data": {"id": "c_1", "first_name": "Jane"}})
        with patch.object(self.client.session, "put", return_value=mock_resp) as mock_put:
            result = self.client.update_contact("c_1", first_name="Jane")
        assert result["first_name"] == "Jane"
        mock_put.assert_called_once_with(
            "https://your-keila-instance.example.com/api/v1/contacts/c_1",
            json={"data": {"first_name": "Jane"}},
            timeout=10,
        )

    def test_update_contact_by_email(self):
        mock_resp = make_mock_response(200, {"data": {"id": "c_1"}})
        with patch.object(self.client.session, "put", return_value=mock_resp) as mock_put:
            self.client.update_contact("a@b.com", first_name="J", id_type="email")
        mock_put.assert_called_once_with(
            "https://your-keila-instance.example.com/api/v1/contacts/a@b.com",
            params={"id_type": "email"},
            json={"data": {"first_name": "J"}},
            timeout=10,
        )


class TestKeilaClientDeleteContact:
    def setup_method(self):
        self.client = KeilaClient(base_url="https://your-keila-instance.example.com", api_key="test-key-123")

    def test_delete_contact_by_id(self):
        mock_resp = make_mock_response(200, {"success": True})
        with patch.object(self.client.session, "delete", return_value=mock_resp) as mock_del:
            result = self.client.delete_contact("c_1")
        assert result.get("success") is True
        mock_del.assert_called_once_with("https://your-keila-instance.example.com/api/v1/contacts/c_1", timeout=10)

    def test_delete_contact_204_no_content(self):
        """Keila returns 204 No Content on successful delete — must not crash."""
        mock_resp = make_mock_response(204, empty_body=True)
        with patch.object(self.client.session, "delete", return_value=mock_resp):
            result = self.client.delete_contact("c_1")
        assert result == {}

    def test_delete_contact_by_email(self):
        mock_resp = make_mock_response(200, {"success": True})
        with patch.object(self.client.session, "delete", return_value=mock_resp) as mock_del:
            self.client.delete_contact("a@b.com", id_type="email")
        mock_del.assert_called_once_with(
            "https://your-keila-instance.example.com/api/v1/contacts/a@b.com",
            params={"id_type": "email"},
            timeout=10,
        )


class TestKeilaClientListContacts:
    def setup_method(self):
        self.client = KeilaClient(base_url="https://your-keila-instance.example.com", api_key="test-key-123")

    # T001: Default call — no params sent to API, meta includes total_count and server_pagination
    def test_list_contacts_default(self):
        raw_contacts = [
            {"id": "c_1", "email": "alice@example.com", "first_name": "Alice", "last_name": "Smith"},
            {"id": "c_2", "email": "bob@example.com", "first_name": "Bob", "last_name": "Jones"},
        ]
        mock_resp = make_mock_response(200, {"data": raw_contacts, "meta": {"page": 0, "page_size": 50, "page_count": 1}})
        with patch.object(self.client.session, "get", return_value=mock_resp) as mock_get:
            result = self.client.list_contacts()
        # No params forwarded to API
        mock_get.assert_called_once_with(
            "https://your-keila-instance.example.com/api/v1/contacts",
            timeout=10,
        )
        # All contacts returned
        assert len(result["data"]) == 2
        # meta reflects client-side computation
        assert result["meta"]["total_count"] == 2
        assert result["meta"]["page"] == 0
        assert result["meta"]["page_size"] == 50
        assert result["meta"]["page_count"] == 1
        assert result["meta"]["server_pagination"] is False

    # T002: Client-side pagination — page=1, page_size=1 should return second contact only
    def test_list_contacts_pagination(self):
        raw_contacts = [
            {"id": "c_1", "email": "alice@example.com", "first_name": "Alice", "last_name": "Smith"},
            {"id": "c_2", "email": "bob@example.com", "first_name": "Bob", "last_name": "Jones"},
            {"id": "c_3", "email": "carol@example.com", "first_name": "Carol", "last_name": "Lee"},
        ]
        mock_resp = make_mock_response(200, {"data": raw_contacts, "meta": {"page": 0, "page_size": 50, "page_count": 1}})
        with patch.object(self.client.session, "get", return_value=mock_resp) as mock_get:
            result = self.client.list_contacts(page=1, page_size=1)
        # No params forwarded to API
        mock_get.assert_called_once_with(
            "https://your-keila-instance.example.com/api/v1/contacts",
            timeout=10,
        )
        # Only the second contact on page 1 (0-based slicing: page*page_size to (page+1)*page_size)
        assert len(result["data"]) == 1
        assert result["data"][0]["id"] == "c_2"
        assert result["meta"]["total_count"] == 3
        assert result["meta"]["page"] == 1
        assert result["meta"]["page_size"] == 1
        assert result["meta"]["page_count"] == 3
        assert result["meta"]["server_pagination"] is False

    # T003: Client-side q filter — substring match on email/first_name/last_name
    def test_list_contacts_with_q_filter(self):
        raw_contacts = [
            {"id": "c_1", "email": "john.doe@example.com", "first_name": "John", "last_name": "Doe"},
            {"id": "c_2", "email": "jane.smith@example.com", "first_name": "Jane", "last_name": "Smith"},
            {"id": "c_3", "email": "bob@example.com", "first_name": "Bob", "last_name": "Johnson"},
        ]
        mock_resp = make_mock_response(200, {"data": raw_contacts, "meta": {"page": 0, "page_size": 50, "page_count": 1}})
        with patch.object(self.client.session, "get", return_value=mock_resp) as mock_get:
            result = self.client.list_contacts(q="john")
        # No params forwarded to API
        mock_get.assert_called_once_with(
            "https://your-keila-instance.example.com/api/v1/contacts",
            timeout=10,
        )
        # Matches c_1 (email "john.doe") and c_3 (last_name "Johnson")
        assert len(result["data"]) == 2
        ids = {c["id"] for c in result["data"]}
        assert "c_1" in ids
        assert "c_3" in ids
        assert result["meta"]["total_count"] == 2
        assert result["meta"]["server_pagination"] is False

    # T004: Empty result — no contacts match filter
    def test_list_contacts_empty_result(self):
        mock_resp = make_mock_response(200, {"data": [], "meta": {"page": 0, "page_size": 50, "page_count": 0}})
        with patch.object(self.client.session, "get", return_value=mock_resp) as mock_get:
            result = self.client.list_contacts(q="zzznomatch")
        mock_get.assert_called_once_with(
            "https://your-keila-instance.example.com/api/v1/contacts",
            timeout=10,
        )
        assert result["data"] == []
        assert result["meta"]["total_count"] == 0
        assert result["meta"]["page_count"] == 0
        assert result["meta"]["server_pagination"] is False

    # T005: Page beyond range — returns empty data but valid meta
    def test_list_contacts_page_beyond_range(self):
        raw_contacts = [
            {"id": "c_1", "email": "alice@example.com", "first_name": "Alice", "last_name": "Smith"},
        ]
        mock_resp = make_mock_response(200, {"data": raw_contacts, "meta": {"page": 0, "page_size": 50, "page_count": 1}})
        with patch.object(self.client.session, "get", return_value=mock_resp) as mock_get:
            result = self.client.list_contacts(page=99, page_size=10)
        mock_get.assert_called_once_with(
            "https://your-keila-instance.example.com/api/v1/contacts",
            timeout=10,
        )
        assert result["data"] == []
        assert result["meta"]["total_count"] == 1
        assert result["meta"]["page"] == 99
        assert result["meta"]["page_count"] == 1
        assert result["meta"]["server_pagination"] is False


class TestKeilaClientSenders:
    def setup_method(self):
        self.client = KeilaClient(base_url="https://your-keila-instance.example.com", api_key="test-key-123")

    def test_list_senders(self):
        mock_resp = make_mock_response(200, {"data": [{"id": "s_1", "name": "Newsletter", "from_email": "noreply@keila.io"}]})
        with patch.object(self.client.session, "get", return_value=mock_resp) as mock_get:
            result = self.client.list_senders()
        assert len(result) == 1
        assert result[0]["id"] == "s_1"
        mock_get.assert_called_once_with("https://your-keila-instance.example.com/api/v1/senders", timeout=10)


class TestKeilaClientSegments:
    def setup_method(self):
        self.client = KeilaClient(base_url="https://your-keila-instance.example.com", api_key="test-key-123")

    def test_create_segment(self):
        mock_resp = make_mock_response(200, {"data": {"id": "sg_1", "name": "Test"}})
        with patch.object(self.client.session, "post", return_value=mock_resp) as mock_post:
            result = self.client.create_segment("Test", {"email": {"$like": "%keila.io"}})
        assert result["id"] == "sg_1"
        mock_post.assert_called_once_with(
            "https://your-keila-instance.example.com/api/v1/segments",
            json={"data": {"name": "Test", "filter": {"email": {"$like": "%keila.io"}}}},
            timeout=10,
        )

    def test_list_segments(self):
        mock_resp = make_mock_response(200, {"data": []})
        with patch.object(self.client.session, "get", return_value=mock_resp) as mock_get:
            self.client.list_segments()
        mock_get.assert_called_once_with("https://your-keila-instance.example.com/api/v1/segments", timeout=10)

    def test_get_segment(self):
        mock_resp = make_mock_response(200, {"data": {"id": "sg_1", "name": "Test"}})
        with patch.object(self.client.session, "get", return_value=mock_resp) as mock_get:
            self.client.get_segment("sg_1")
        mock_get.assert_called_once_with("https://your-keila-instance.example.com/api/v1/segments/sg_1", timeout=10)

    def test_delete_segment(self):
        mock_resp = make_mock_response(200, {"success": True})
        with patch.object(self.client.session, "delete", return_value=mock_resp) as mock_del:
            self.client.delete_segment("sg_1")
        mock_del.assert_called_once_with("https://your-keila-instance.example.com/api/v1/segments/sg_1", timeout=10)

    def test_delete_segment_204_no_content(self):
        """Keila returns 204 No Content on successful delete — must not crash."""
        mock_resp = make_mock_response(204, empty_body=True)
        with patch.object(self.client.session, "delete", return_value=mock_resp):
            result = self.client.delete_segment("sg_1")
        assert result == {}


class TestKeilaClientApiKeyRedaction:
    def test_api_key_not_in_auth_error_message(self):
        client = KeilaClient(base_url="https://your-keila-instance.example.com", api_key="super-secret-key-12345")
        mock_resp = make_mock_response(401, {"error": "Unauthorized"})
        with patch.object(client.session, "get", return_value=mock_resp):
            with pytest.raises(KeilaAuthError) as exc:
                client.get_campaigns()
        assert "super-secret-key-12345" not in str(exc.value)

    def test_api_key_not_in_404_error_message(self):
        client = KeilaClient(base_url="https://your-keila-instance.example.com", api_key="super-secret-key-12345")
        mock_resp = make_mock_response(404, {"error": "Not found"})
        with patch.object(client.session, "get", return_value=mock_resp):
            with pytest.raises(KeilaNotFoundError) as exc:
                client.get_campaign("mc_nonexistent")
        assert "super-secret-key-12345" not in str(exc.value)

    def test_api_key_not_in_rate_limit_error_message(self):
        client = KeilaClient(base_url="https://your-keila-instance.example.com", api_key="super-secret-key-12345")
        mock_resp = make_mock_response(429, {"error": "Rate limit"})
        with patch.object(client.session, "get", return_value=mock_resp):
            with pytest.raises(KeilaRateLimitError) as exc:
                client.get_campaigns()
        assert "super-secret-key-12345" not in str(exc.value)

    def test_api_key_not_in_server_error_message(self):
        client = KeilaClient(base_url="https://your-keila-instance.example.com", api_key="super-secret-key-12345")
        mock_resp = make_mock_response(500, {"error": "Internal error"})
        with patch.object(client.session, "get", return_value=mock_resp):
            with pytest.raises(KeilaApiError) as exc:
                client.get_campaigns()
        assert "super-secret-key-12345" not in str(exc.value)


class TestKeilaClientForms:
    def setup_method(self):
        self.client = KeilaClient(base_url="https://your-keila-instance.example.com", api_key="test-key-123")

    def test_list_forms(self):
        mock_resp = make_mock_response(200, {"data": []})
        with patch.object(self.client.session, "get", return_value=mock_resp) as mock_get:
            self.client.list_forms()
        mock_get.assert_called_once_with("https://your-keila-instance.example.com/api/v1/forms", timeout=10)

    def test_get_form(self):
        mock_resp = make_mock_response(200, {"data": {"id": "f_1", "name": "Signup"}})
        with patch.object(self.client.session, "get", return_value=mock_resp) as mock_get:
            self.client.get_form("f_1")
        mock_get.assert_called_once_with("https://your-keila-instance.example.com/api/v1/forms/f_1", timeout=10)
    def test_create_form_minimal(self):
        mock_resp = make_mock_response(200, {"data": {"id": "nfrm_abc", "name": "test-form"}})
        with patch.object(self.client.session, "post", return_value=mock_resp) as mock_post:
            result = self.client.create_form(name="test-form")
        assert result["id"] == "nfrm_abc"
        mock_post.assert_called_once_with(
            "https://your-keila-instance.example.com/api/v1/forms",
            json={"data": {"name": "test-form"}},
            timeout=10,
        )

    def test_create_form_with_sender(self):
        mock_resp = make_mock_response(200, {"data": {"id": "nfrm_abc", "name": "test-form", "sender_id": "nms_x"}})
        with patch.object(self.client.session, "post", return_value=mock_resp) as mock_post:
            result = self.client.create_form(name="test-form", sender_id="nms_x")
        assert result["sender_id"] == "nms_x"
        body = mock_post.call_args[1]["json"]
        assert body["data"]["sender_id"] == "nms_x"

    def test_create_form_with_fields_strips_nulls(self):
        mock_resp = make_mock_response(200, {"data": {"id": "nfrm_abc", "name": "test-form", "fields": [{"field": "email", "required": True}]}})
        with patch.object(self.client.session, "post", return_value=mock_resp) as mock_post:
            self.client.create_form(
                name="test-form",
                fields=[{"field": "email", "required": True, "label": None, "placeholder": None}],
            )
        body = mock_post.call_args[1]["json"]
        sent_fields = body["data"]["fields"]
        assert len(sent_fields) == 1
        assert "label" not in sent_fields[0]
        assert "placeholder" not in sent_fields[0]
        assert sent_fields[0]["field"] == "email"

    def test_delete_form_sends_delete_request(self):
        mock_resp = make_mock_response(204, None)
        with patch.object(self.client.session, "delete", return_value=mock_resp) as mock_del:
            result = self.client.delete_form("nfrm_abc")
        assert result == {}
        mock_del.assert_called_once_with(
            "https://your-keila-instance.example.com/api/v1/forms/nfrm_abc",
            timeout=10,
        )

