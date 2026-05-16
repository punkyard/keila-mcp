from unittest.mock import Mock, patch

from src.keila_client import KeilaAuthError, KeilaApiError, KeilaNotFoundError, KeilaRateLimitError, KeilaValidationError


class TestListCampaigns:
    # T012: Happy path
    def test_list_campaigns_returns_all_campaigns(self):
        mock_campaigns = [
            {"id": "mc_1", "subject": "Welcome", "status": "sent",
             "created_at": "2026-01-01T00:00:00Z",
             "scheduled_at": None, "updated_at": "2026-01-01T01:00:00Z"},
            {"id": "mc_2", "subject": "Newsletter March", "status": "draft",
             "created_at": "2026-03-15T00:00:00Z",
             "scheduled_at": None, "updated_at": "2026-03-15T12:00:00Z"},
        ]

        with patch("src.mcp_server.get_client") as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client
            mock_client.get_campaigns.return_value = mock_campaigns
            from src.mcp_server import list_campaigns
            result = list_campaigns()

        assert len(result) == 2
        assert result[0]["id"] == "mc_2"
        assert result[0]["subject"] == "Newsletter March"
        assert result[1]["id"] == "mc_1"

    # T013: Empty state
    def test_list_campaigns_empty_state(self):
        with patch("src.mcp_server.get_client") as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client
            mock_client.get_campaigns.return_value = []
            from src.mcp_server import list_campaigns
            result = list_campaigns()

        assert result == []

    # T014: Sort order (created_at desc)
    def test_list_campaigns_sort_order(self):
        mock_campaigns = [
            {"id": "mc_1", "subject": "Old", "status": "sent",
             "created_at": "2026-01-01T00:00:00Z",
             "scheduled_at": None, "updated_at": None},
            {"id": "mc_2", "subject": "New", "status": "draft",
             "created_at": "2026-03-15T00:00:00Z",
             "scheduled_at": None, "updated_at": None},
        ]

        with patch("src.mcp_server.get_client") as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client
            mock_client.get_campaigns.return_value = mock_campaigns
            from src.mcp_server import list_campaigns
            result = list_campaigns()

        assert len(result) == 2
        assert result[0]["id"] == "mc_2"
        assert result[0]["created_at"] > result[1]["created_at"]

    # T017: Status filter
    def test_list_campaigns_with_status_filter(self):
        with patch("src.mcp_server.get_client") as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client
            mock_client.get_campaigns.return_value = []
            from src.mcp_server import list_campaigns
            list_campaigns(status="scheduled")

        mock_client.get_campaigns.assert_called_once_with(
            status="scheduled", q=None
        )

    # T018: Subject search
    def test_list_campaigns_with_subject_search(self):
        with patch("src.mcp_server.get_client") as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client
            mock_client.get_campaigns.return_value = []
            from src.mcp_server import list_campaigns
            list_campaigns(q="welcome")

        mock_client.get_campaigns.assert_called_once_with(
            status=None, q="welcome"
        )

    # T019: Combined filter + search
    def test_list_campaigns_passes_filters_to_client(self):
        with patch("src.mcp_server.get_client") as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client
            mock_client.get_campaigns.return_value = []
            from src.mcp_server import list_campaigns
            list_campaigns(status="sent", q="welcome")

        mock_client.get_campaigns.assert_called_once_with(
            status="sent", q="welcome"
        )

    def test_list_campaigns_no_filters(self):
        with patch("src.mcp_server.get_client") as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client
            mock_client.get_campaigns.return_value = []
            from src.mcp_server import list_campaigns
            list_campaigns()

        mock_client.get_campaigns.assert_called_once_with(
            status=None, q=None
        )


    def test_list_campaigns_invalid_status(self):
        from src.mcp_server import list_campaigns
        result = list_campaigns(status="invalid_status")

        assert "error" in result
        assert "400" in result["error"]
        assert "draft" in result["error"]


class TestListCampaignsErrors:
    def test_auth_error_raises(self):
        with patch("src.mcp_server.get_client") as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client
            mock_client.get_campaigns.side_effect = KeilaAuthError(
                "Keila API returned 401 Unauthorized. Check your KEILA_API_KEY."
            )
            from src.mcp_server import list_campaigns
            result = list_campaigns()

        assert "error" in result
        assert "401" in result["error"]

    def test_rate_limit_error_raises(self):
        with patch("src.mcp_server.get_client") as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client
            mock_client.get_campaigns.side_effect = KeilaRateLimitError(
                "Rate limited (429)"
            )
            from src.mcp_server import list_campaigns
            result = list_campaigns()

        assert "error" in result
        assert "429" in result["error"]

    def test_api_error_raises(self):
        with patch("src.mcp_server.get_client") as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client
            mock_client.get_campaigns.side_effect = KeilaApiError(
                "Keila API returned 500 error"
            )
            from src.mcp_server import list_campaigns
            result = list_campaigns()

        assert "error" in result
        assert "500" in result["error"]


class TestCampaignTools:
    def setup_method(self):
        self.client_patch = patch("src.mcp_server.get_client")
        self.mock_get_client = self.client_patch.start()
        self.mock_client = Mock()
        self.mock_get_client.return_value = self.mock_client

    def teardown_method(self):
        self.client_patch.stop()

    def test_create_campaign_tool(self):
        from src.mcp_server import create_campaign_tool
        self.mock_client.create_campaign.return_value = {"id": "mc_1", "status": "draft"}
        result = create_campaign_tool(subject="Test", body_type="markdown", text_body="Hello")
        assert result["id"] == "mc_1"
        self.mock_client.create_campaign.assert_called_once_with(
            subject="Test", body_type="markdown", text_body="Hello",
            preview_text=None, sender_id=None, segment_id=None,
            data=None, do_not_track=None,
        )

    def test_create_campaign_tool_validation_error(self):
        from src.mcp_server import create_campaign_tool
        result = create_campaign_tool(subject="", body_type="invalid_type", text_body="")
        assert "error" in result
        assert "400" in result["error"]

    def test_create_campaign_tool_propagates_error(self):
        from src.mcp_server import create_campaign_tool
        self.mock_client.create_campaign.side_effect = KeilaValidationError("422: bad subject")
        result = create_campaign_tool(subject="", body_type="markdown", text_body="")
        assert "error" in result
        assert "422" in result["error"]

    def test_get_campaign_tool(self):
        from src.mcp_server import get_campaign_tool
        self.mock_client.get_campaign.return_value = {"id": "mc_1", "subject": "Welcome"}
        result = get_campaign_tool(id="mc_1")
        assert result["id"] == "mc_1"
        self.mock_client.get_campaign.assert_called_once_with("mc_1")

    def test_get_campaign_tool_404(self):
        from src.mcp_server import get_campaign_tool
        self.mock_client.get_campaign.side_effect = KeilaNotFoundError("404: not found")
        result = get_campaign_tool(id="mc_gone")
        assert "error" in result
        assert "404" in result["error"]

    def test_update_campaign_tool(self):
        from src.mcp_server import update_campaign_tool
        self.mock_client.get_campaign.return_value = {"id": "mc_1", "status": "draft"}
        self.mock_client.update_campaign.return_value = {"id": "mc_1", "subject": "Updated"}
        result = update_campaign_tool(id="mc_1", subject="Updated")
        assert result["subject"] == "Updated"
        self.mock_client.update_campaign.assert_called_once_with(id="mc_1", subject="Updated", preview_text=None)

    def test_update_campaign_tool_sent_warning(self):
        from src.mcp_server import update_campaign_tool
        self.mock_client.get_campaign.return_value = {"id": "mc_1", "status": "sent"}
        self.mock_client.update_campaign.return_value = {"id": "mc_1", "subject": "Updated"}
        result = update_campaign_tool(id="mc_1", subject="Updated")
        assert "warning" in result
        assert "sent" in result["warning"].lower()

    def test_delete_campaign_tool(self):
        from src.mcp_server import delete_campaign_tool
        self.mock_client.get_campaign.return_value = {"id": "mc_1", "status": "draft"}
        self.mock_client.delete_campaign.return_value = {"success": True}
        result = delete_campaign_tool(id="mc_1")
        assert result["success"] is True
        self.mock_client.delete_campaign.assert_called_once_with("mc_1")

    def test_delete_campaign_tool_sent_warning(self):
        from src.mcp_server import delete_campaign_tool
        self.mock_client.get_campaign.return_value = {"id": "mc_1", "status": "sent"}
        self.mock_client.delete_campaign.return_value = {"success": True}
        result = delete_campaign_tool(id="mc_1")
        assert "warning" in result
        assert "sent" in result["warning"].lower()

    def test_send_campaign_tool(self):
        from src.mcp_server import send_campaign_tool
        self.mock_client.get_campaign.return_value = {"id": "mc_1", "sender_id": "s_1"}
        self.mock_client.send_campaign.return_value = {"delivery_queued": True, "campaign_id": "mc_1"}
        result = send_campaign_tool(id="mc_1")
        assert result["delivery_queued"] is True
        self.mock_client.send_campaign.assert_called_once_with(id="mc_1", sender_id=None)

    def test_send_campaign_tool_no_sender(self):
        from src.mcp_server import send_campaign_tool
        self.mock_client.get_campaign.return_value = {"id": "mc_1", "sender_id": None}
        result = send_campaign_tool(id="mc_1")
        assert "error" in result
        assert "no sender" in result["error"].lower()

    def test_schedule_campaign_tool(self):
        from src.mcp_server import schedule_campaign_tool
        self.mock_client.schedule_campaign.return_value = {"id": "mc_1", "status": "scheduled"}
        result = schedule_campaign_tool(id="mc_1", scheduled_for="2026-06-01T09:00:00Z")
        assert result["status"] == "scheduled"
        self.mock_client.schedule_campaign.assert_called_once_with(id="mc_1", scheduled_for="2026-06-01T09:00:00Z")

    def test_schedule_campaign_tool_no_sender(self):
        from src.mcp_server import schedule_campaign_tool
        self.mock_client.get_campaign.return_value = {"id": "mc_1", "sender_id": None}
        result = schedule_campaign_tool(id="mc_1", scheduled_for="2026-06-01T09:00:00Z")
        assert "error" in result
        assert "no sender" in result["error"].lower()


class TestContactTools:
    def setup_method(self):
        self.client_patch = patch("src.mcp_server.get_client")
        self.mock_get_client = self.client_patch.start()
        self.mock_client = Mock()
        self.mock_get_client.return_value = self.mock_client

    def teardown_method(self):
        self.client_patch.stop()

    def test_create_contact_tool(self):
        from src.mcp_server import create_contact_tool
        self.mock_client.create_contact.return_value = {"id": "c_1", "email": "a@b.com"}
        result = create_contact_tool(email="a@b.com")
        assert result["id"] == "c_1"
        self.mock_client.create_contact.assert_called_once_with(
            email="a@b.com", first_name=None, last_name=None,
            external_id=None, status=None, data=None,
        )

    def test_get_contact_tool_by_id(self):
        from src.mcp_server import get_contact_tool
        self.mock_client.get_contact.return_value = {"id": "c_1"}
        result = get_contact_tool(id="c_1")
        assert result["id"] == "c_1"
        self.mock_client.get_contact.assert_called_once_with("c_1", None)

    def test_get_contact_tool_by_email(self):
        from src.mcp_server import get_contact_tool
        self.mock_client.get_contact.return_value = {"id": "c_1"}
        get_contact_tool(id="a@b.com", id_type="email")
        self.mock_client.get_contact.assert_called_once_with("a@b.com", "email")

    def test_update_contact_tool(self):
        from src.mcp_server import update_contact_tool
        self.mock_client.update_contact.return_value = {"id": "c_1", "first_name": "Jane"}
        result = update_contact_tool(id="c_1", first_name="Jane")
        assert result["first_name"] == "Jane"
        self.mock_client.update_contact.assert_called_once_with(
            id="c_1", first_name="Jane", last_name=None, email=None,
            external_id=None, data=None, id_type=None,
        )

    def test_delete_contact_tool(self):
        from src.mcp_server import delete_contact_tool
        self.mock_client.delete_contact.return_value = {"success": True}
        result = delete_contact_tool(id="c_1")
        assert result["success"] is True
        self.mock_client.delete_contact.assert_called_once_with("c_1", None)

    def test_list_contacts_tool(self):
        from src.mcp_server import list_contacts_tool
        self.mock_client.list_contacts.return_value = {
            "data": [{"id": "c_1", "email": "alice@example.com"}],
            "meta": {
                "total_count": 1,
                "page": 0,
                "page_size": 50,
                "page_count": 1,
                "server_pagination": False,
            },
        }
        result = list_contacts_tool(page=0, page_size=50, q=None)
        assert result["meta"]["total_count"] == 1
        assert result["meta"]["server_pagination"] is False
        assert result["meta"]["page_count"] == 1
        assert len(result["data"]) == 1
        self.mock_client.list_contacts.assert_called_once_with(page=0, page_size=50, q=None)


class TestSupportingTools:
    def setup_method(self):
        self.client_patch = patch("src.mcp_server.get_client")
        self.mock_get_client = self.client_patch.start()
        self.mock_client = Mock()
        self.mock_get_client.return_value = self.mock_client

    def teardown_method(self):
        self.client_patch.stop()

    def test_list_senders_tool(self):
        from src.mcp_server import list_senders_tool
        self.mock_client.list_senders.return_value = [{"id": "s_1", "name": "Newsletter"}]
        result = list_senders_tool()
        assert len(result) == 1
        self.mock_client.list_senders.assert_called_once()

    def test_create_segment_tool(self):
        from src.mcp_server import create_segment_tool
        self.mock_client.create_segment.return_value = {"id": "sg_1", "name": "Test"}
        result = create_segment_tool(name="Test", filter={"email": {"$like": "%keila.io"}})
        assert result["id"] == "sg_1"
        self.mock_client.create_segment.assert_called_once_with(name="Test", filter={"email": {"$like": "%keila.io"}})

    def test_list_segments_tool(self):
        from src.mcp_server import list_segments_tool
        self.mock_client.list_segments.return_value = []
        result = list_segments_tool()
        assert result == []
        self.mock_client.list_segments.assert_called_once()

    def test_get_segment_tool(self):
        from src.mcp_server import get_segment_tool
        self.mock_client.get_segment.return_value = {"id": "sg_1"}
        result = get_segment_tool(id="sg_1")
        assert result["id"] == "sg_1"
        self.mock_client.get_segment.assert_called_once_with("sg_1")

    def test_delete_segment_tool(self):
        from src.mcp_server import delete_segment_tool
        self.mock_client.delete_segment.return_value = {"success": True}
        result = delete_segment_tool(id="sg_1")
        assert result["success"] is True
        self.mock_client.delete_segment.assert_called_once_with("sg_1")

    def test_list_forms_tool(self):
        from src.mcp_server import list_forms_tool
        self.mock_client.list_forms.return_value = []
        result = list_forms_tool()
        assert result == []
        self.mock_client.list_forms.assert_called_once()

    def test_get_form_tool(self):
        from src.mcp_server import get_form_tool
        self.mock_client.get_form.return_value = {"id": "f_1", "name": "Signup"}
        result = get_form_tool(id="f_1")
        assert result["id"] == "f_1"
        self.mock_client.get_form.assert_called_once_with("f_1")
    def test_create_form_tool(self):
        from src.mcp_server import create_form_tool
        self.mock_client.create_form.return_value = {"id": "nfrm_abc", "name": "test-form"}
        result = create_form_tool(name="test-form")
        assert result["id"] == "nfrm_abc"
        self.mock_client.create_form.assert_called_once_with(
            name="test-form",
            sender_id=None,
            fields=None,
            settings=None,
        )

    def test_delete_form_tool(self):
        from src.mcp_server import delete_form_tool
        self.mock_client.delete_form.return_value = {}
        result = delete_form_tool(id="nfrm_abc")
        assert "message" in result
        assert "nfrm_abc" in result["message"]
        self.mock_client.delete_form.assert_called_once_with("nfrm_abc")

