"""Admin application for campaign configuration."""
from canvas_sdk.effects import Effect
from canvas_sdk.effects.launch_modal import LaunchModalEffect
from canvas_sdk.handlers.application import Application


class ReminderAdminApp(Application):
    """Global admin application for reminder campaign configuration."""

    def on_open(self) -> Effect | list[Effect]:
        """Launch admin configuration page."""
        url = "/plugin-io/api/custom_reminders/admin"
        return LaunchModalEffect(
            url=url,
            target=LaunchModalEffect.TargetType.RIGHT_CHART_PANE_LARGE,
            title="Custom Reminders Admin",
        ).apply()
