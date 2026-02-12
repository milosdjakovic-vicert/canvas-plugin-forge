"""Tests for admin application handler."""
import json

from custom_reminders.handlers.admin_app import ReminderAdminApp


def test_on_open_returns_launch_modal_effect():
    """Test on_open returns a LaunchModalEffect targeting the admin page."""
    handler = ReminderAdminApp.__new__(ReminderAdminApp)

    result = handler.on_open()

    assert result.type == 3000  # LAUNCH_MODAL
    payload = json.loads(result.payload)
    assert payload["data"]["url"] == "/plugin-io/api/custom_reminders/admin"
    assert payload["data"]["target"] == "right_chart_pane_large"
    assert payload["data"]["title"] == "Custom Reminders Admin"
