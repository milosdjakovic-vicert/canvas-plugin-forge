"""Patient application for viewing message history."""
from canvas_sdk.effects import Effect
from canvas_sdk.effects.launch_modal import LaunchModalEffect
from canvas_sdk.handlers.application import Application


class ReminderPatientApp(Application):
    """Patient-specific application for viewing message history."""

    def on_open(self) -> Effect | list[Effect]:
        """Launch patient message history page."""
        # Get patient ID from event context
        patient_id = self.event.context.get("patient", {}).get("id", "")

        url = f"/plugin-io/api/custom_reminders/patient-view?patient_id={patient_id}"
        return LaunchModalEffect(
            url=url,
            target=LaunchModalEffect.TargetType.RIGHT_CHART_PANE,
            title="Message History",
        ).apply()
