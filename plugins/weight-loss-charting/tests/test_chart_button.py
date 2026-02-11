import json
from unittest.mock import MagicMock

from canvas_sdk.effects import EffectType
from canvas_sdk.events import EventType

from weight_loss_charting.handlers.chart_button import WeightLossChartButton


class TestWeightLossChartButton:
    def _make_handler(self, event_type, context=None, patient_id="patient-123"):
        event = MagicMock()
        event.type = event_type
        event.name = EventType.Name(event_type)
        event.context = context or {"note_id": "note-uuid-456"}
        event.target.id = patient_id
        return WeightLossChartButton(event=event)

    def test_button_attributes(self):
        assert WeightLossChartButton.BUTTON_TITLE == "Weight Loss Chart"
        assert WeightLossChartButton.BUTTON_KEY == "WEIGHT_LOSS_CHART"
        assert (
            WeightLossChartButton.BUTTON_LOCATION
            == WeightLossChartButton.ButtonLocation.NOTE_HEADER
        )

    def test_handle_returns_launch_modal_effect(self):
        handler = self._make_handler(EventType.ACTION_BUTTON_CLICKED)
        effects = handler.handle()
        assert len(effects) == 1
        assert effects[0].type == EffectType.LAUNCH_MODAL

    def test_handle_url_contains_note_and_patient(self):
        handler = self._make_handler(
            EventType.ACTION_BUTTON_CLICKED,
            context={"note_id": "abc-123"},
            patient_id="pat-789",
        )
        effects = handler.handle()
        payload = json.loads(effects[0].payload)
        url = payload["data"]["url"]
        assert "/plugin-io/api/weight_loss_charting/chart" in url
        assert "note_id=abc-123" in url
        assert "patient_id=pat-789" in url

    def test_handle_uses_right_chart_pane_large(self):
        handler = self._make_handler(EventType.ACTION_BUTTON_CLICKED)
        effects = handler.handle()
        payload = json.loads(effects[0].payload)
        assert payload["data"]["target"] == "right_chart_pane_large"

    def test_compute_shows_button_on_note_header_event(self):
        handler = self._make_handler(EventType.SHOW_NOTE_HEADER_BUTTON)
        effects = handler.compute()
        assert len(effects) == 1

    def test_compute_handles_click(self):
        handler = self._make_handler(
            EventType.ACTION_BUTTON_CLICKED,
            context={"key": "WEIGHT_LOSS_CHART"},
        )
        effects = handler.compute()
        assert len(effects) == 1
        assert effects[0].type == EffectType.LAUNCH_MODAL

    def test_handle_empty_note_id(self):
        handler = self._make_handler(
            EventType.ACTION_BUTTON_CLICKED,
            context={},
        )
        effects = handler.handle()
        payload = json.loads(effects[0].payload)
        url = payload["data"]["url"]
        assert "note_id=&" in url or "note_id=" in url

    def test_compute_wrong_key_returns_empty(self):
        handler = self._make_handler(
            EventType.ACTION_BUTTON_CLICKED,
            context={"key": "WRONG_KEY"},
        )
        effects = handler.compute()
        assert effects == []
