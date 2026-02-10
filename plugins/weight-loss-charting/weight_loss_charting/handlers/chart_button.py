from canvas_sdk.effects import Effect
from canvas_sdk.effects.launch_modal import LaunchModalEffect
from canvas_sdk.handlers.action_button import ActionButton


class WeightLossChartButton(ActionButton):
    """Button in note headers that opens the weight loss charting interface."""

    BUTTON_TITLE = "Weight Loss Chart"
    BUTTON_KEY = "WEIGHT_LOSS_CHART"
    BUTTON_LOCATION = ActionButton.ButtonLocation.NOTE_HEADER

    def handle(self) -> list[Effect]:
        note_id = self.event.context.get("note_id", "")
        patient_id = self.event.target.id

        url = (
            f"/plugin-io/api/weight_loss_charting/chart"
            f"?note_id={note_id}&patient_id={patient_id}"
        )

        return [
            LaunchModalEffect(
                url=url,
                target=LaunchModalEffect.TargetType.RIGHT_CHART_PANE_LARGE,
                title="Weight Loss Chart",
            ).apply()
        ]
