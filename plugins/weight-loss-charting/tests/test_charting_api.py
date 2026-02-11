import json
from datetime import date
from http import HTTPStatus
from unittest.mock import MagicMock, patch, PropertyMock

import pytest
from canvas_sdk.effects import EffectType
from canvas_sdk.effects.simple_api import HTMLResponse, JSONResponse

from weight_loss_charting.handlers.charting_api import WeightLossChartingAPI


@pytest.fixture
def api():
    """Create a WeightLossChartingAPI instance with mocked internals."""
    event = MagicMock()
    event.context = {"method": "GET", "path": "/chart"}
    handler = WeightLossChartingAPI.__new__(WeightLossChartingAPI)
    handler.event = event
    handler.secrets = {}
    handler.environment = {}
    handler._handler = None
    handler._path_pattern = None
    return handler


@pytest.fixture
def mock_request(api):
    """Provide a mock request attached to the api handler."""
    request = MagicMock()
    type(api).request = PropertyMock(return_value=request)
    return request


class TestGetNoteUuid:
    def test_resolves_dbid_to_uuid(self, api):
        with patch("weight_loss_charting.handlers.charting_api.Note") as MockNote:
            mock_note = MagicMock()
            mock_note.id = "uuid-abc-123"
            MockNote.objects.get.return_value = mock_note

            result = api._get_note_uuid("42")

            MockNote.objects.get.assert_called_once_with(dbid=42)
            assert result == "uuid-abc-123"


class TestGetChart:
    def test_returns_html_response(self, api, mock_request):
        mock_request.query_params = {"note_id": "1", "patient_id": "pat-1"}

        with (
            patch("weight_loss_charting.handlers.charting_api.Patient") as MockPatient,
            patch("weight_loss_charting.handlers.charting_api.Observation") as MockObs,
            patch("weight_loss_charting.handlers.charting_api.Goal") as MockGoal,
            patch("weight_loss_charting.handlers.charting_api.Condition") as MockCond,
            patch("weight_loss_charting.handlers.charting_api.render_to_string") as mock_render,
        ):
            mock_patient = MagicMock()
            mock_patient.first_name = "John"
            mock_patient.last_name = "Doe"
            MockPatient.objects.get.return_value = mock_patient

            MockObs.objects.for_patient.return_value.filter.return_value.order_by.return_value = []
            MockGoal.objects.filter.return_value.order_by.return_value = []
            MockCond.objects.for_patient.return_value.active.return_value.prefetch_related.return_value = []

            mock_render.return_value = "<html>chart</html>"

            result = api.get_chart()

            assert len(result) == 1
            mock_render.assert_called_once()
            ctx = mock_render.call_args[0][1]
            assert ctx["patient_name"] == "John Doe"
            assert ctx["note_id"] == "1"
            assert ctx["patient_id"] == "pat-1"

    def test_patient_not_found_uses_unknown(self, api, mock_request):
        mock_request.query_params = {"note_id": "1", "patient_id": "bad-id"}

        with (
            patch("weight_loss_charting.handlers.charting_api.Patient") as MockPatient,
            patch("weight_loss_charting.handlers.charting_api.Observation") as MockObs,
            patch("weight_loss_charting.handlers.charting_api.Goal") as MockGoal,
            patch("weight_loss_charting.handlers.charting_api.Condition") as MockCond,
            patch("weight_loss_charting.handlers.charting_api.render_to_string") as mock_render,
        ):
            MockPatient.objects.get.side_effect = Exception("Not found")
            MockObs.objects.for_patient.return_value.filter.return_value.order_by.return_value = []
            MockGoal.objects.filter.return_value.order_by.return_value = []
            MockCond.objects.for_patient.return_value.active.return_value.prefetch_related.return_value = []
            mock_render.return_value = "<html/>"

            api.get_chart()

            ctx = mock_render.call_args[0][1]
            assert ctx["patient_name"] == "Unknown Patient"

    def test_weight_history_parsed_correctly(self, api, mock_request):
        mock_request.query_params = {"note_id": "1", "patient_id": "pat-1"}

        with (
            patch("weight_loss_charting.handlers.charting_api.Patient") as MockPatient,
            patch("weight_loss_charting.handlers.charting_api.Observation") as MockObs,
            patch("weight_loss_charting.handlers.charting_api.Goal") as MockGoal,
            patch("weight_loss_charting.handlers.charting_api.Condition") as MockCond,
            patch("weight_loss_charting.handlers.charting_api.render_to_string") as mock_render,
        ):
            MockPatient.objects.get.return_value = MagicMock(first_name="A", last_name="B")

            obs = MagicMock()
            obs.value = "3200"  # 3200 oz = 200 lbs
            obs.effective_datetime.strftime.return_value = "2025-01-15"
            MockObs.objects.for_patient.return_value.filter.return_value.order_by.return_value = [obs]

            MockGoal.objects.filter.return_value.order_by.return_value = []
            MockCond.objects.for_patient.return_value.active.return_value.prefetch_related.return_value = []
            mock_render.return_value = "<html/>"

            api.get_chart()

            ctx = mock_render.call_args[0][1]
            weight_history = json.loads(ctx["weight_history_json"])
            assert len(weight_history) == 1
            assert weight_history[0]["lbs"] == 200.0
            assert weight_history[0]["date"] == "2025-01-15"

    def test_invalid_weight_value_skipped(self, api, mock_request):
        mock_request.query_params = {"note_id": "1", "patient_id": "pat-1"}

        with (
            patch("weight_loss_charting.handlers.charting_api.Patient") as MockPatient,
            patch("weight_loss_charting.handlers.charting_api.Observation") as MockObs,
            patch("weight_loss_charting.handlers.charting_api.Goal") as MockGoal,
            patch("weight_loss_charting.handlers.charting_api.Condition") as MockCond,
            patch("weight_loss_charting.handlers.charting_api.render_to_string") as mock_render,
        ):
            MockPatient.objects.get.return_value = MagicMock(first_name="A", last_name="B")

            obs = MagicMock()
            obs.value = "not-a-number"
            MockObs.objects.for_patient.return_value.filter.return_value.order_by.return_value = [obs]

            MockGoal.objects.filter.return_value.order_by.return_value = []
            MockCond.objects.for_patient.return_value.active.return_value.prefetch_related.return_value = []
            mock_render.return_value = "<html/>"

            api.get_chart()

            ctx = mock_render.call_args[0][1]
            assert json.loads(ctx["weight_history_json"]) == []

    def test_goals_fetched(self, api, mock_request):
        mock_request.query_params = {"note_id": "1", "patient_id": "pat-1"}

        with (
            patch("weight_loss_charting.handlers.charting_api.Patient") as MockPatient,
            patch("weight_loss_charting.handlers.charting_api.Observation") as MockObs,
            patch("weight_loss_charting.handlers.charting_api.Goal") as MockGoal,
            patch("weight_loss_charting.handlers.charting_api.Condition") as MockCond,
            patch("weight_loss_charting.handlers.charting_api.render_to_string") as mock_render,
        ):
            MockPatient.objects.get.return_value = MagicMock(first_name="A", last_name="B")
            MockObs.objects.for_patient.return_value.filter.return_value.order_by.return_value = []

            goal = MagicMock()
            goal.id = "goal-1"
            goal.goal_statement = "Lose 20 lbs"
            goal.start_date = date(2025, 1, 1)
            goal.due_date = date(2025, 6, 1)
            goal.achievement_status = "in-progress"
            goal.priority = "high-priority"
            goal.lifecycle_status = "active"
            MockGoal.objects.filter.return_value.order_by.return_value = [goal]

            MockCond.objects.for_patient.return_value.active.return_value.prefetch_related.return_value = []
            mock_render.return_value = "<html/>"

            api.get_chart()

            ctx = mock_render.call_args[0][1]
            goals = json.loads(ctx["goals_json"])
            assert len(goals) == 1
            assert goals[0]["statement"] == "Lose 20 lbs"

    def test_conditions_filters_e66(self, api, mock_request):
        mock_request.query_params = {"note_id": "1", "patient_id": "pat-1"}

        with (
            patch("weight_loss_charting.handlers.charting_api.Patient") as MockPatient,
            patch("weight_loss_charting.handlers.charting_api.Observation") as MockObs,
            patch("weight_loss_charting.handlers.charting_api.Goal") as MockGoal,
            patch("weight_loss_charting.handlers.charting_api.Condition") as MockCond,
            patch("weight_loss_charting.handlers.charting_api.render_to_string") as mock_render,
        ):
            MockPatient.objects.get.return_value = MagicMock(first_name="A", last_name="B")
            MockObs.objects.for_patient.return_value.filter.return_value.order_by.return_value = []
            MockGoal.objects.filter.return_value.order_by.return_value = []

            coding = MagicMock()
            coding.code = "E66.01"
            coding.display = "Morbid obesity"
            condition = MagicMock()
            condition.id = "cond-1"
            condition.codings.all.return_value = [coding]
            condition.onset_date = date(2024, 3, 1)
            MockCond.objects.for_patient.return_value.active.return_value.prefetch_related.return_value = [condition]

            mock_render.return_value = "<html/>"

            api.get_chart()

            ctx = mock_render.call_args[0][1]
            conditions = json.loads(ctx["conditions_json"])
            assert len(conditions) == 1
            assert "E66.01" in conditions[0]["display"]

    def test_non_e66_condition_excluded(self, api, mock_request):
        mock_request.query_params = {"note_id": "1", "patient_id": "pat-1"}

        with (
            patch("weight_loss_charting.handlers.charting_api.Patient") as MockPatient,
            patch("weight_loss_charting.handlers.charting_api.Observation") as MockObs,
            patch("weight_loss_charting.handlers.charting_api.Goal") as MockGoal,
            patch("weight_loss_charting.handlers.charting_api.Condition") as MockCond,
            patch("weight_loss_charting.handlers.charting_api.render_to_string") as mock_render,
        ):
            MockPatient.objects.get.return_value = MagicMock(first_name="A", last_name="B")
            MockObs.objects.for_patient.return_value.filter.return_value.order_by.return_value = []
            MockGoal.objects.filter.return_value.order_by.return_value = []

            coding = MagicMock()
            coding.code = "J45.0"
            coding.display = "Asthma"
            condition = MagicMock()
            condition.codings.all.return_value = [coding]
            MockCond.objects.for_patient.return_value.active.return_value.prefetch_related.return_value = [condition]

            mock_render.return_value = "<html/>"

            api.get_chart()

            ctx = mock_render.call_args[0][1]
            assert json.loads(ctx["conditions_json"]) == []

    def test_observation_fetch_exception(self, api, mock_request):
        mock_request.query_params = {"note_id": "1", "patient_id": "pat-1"}

        with (
            patch("weight_loss_charting.handlers.charting_api.Patient") as MockPatient,
            patch("weight_loss_charting.handlers.charting_api.Observation") as MockObs,
            patch("weight_loss_charting.handlers.charting_api.Goal") as MockGoal,
            patch("weight_loss_charting.handlers.charting_api.Condition") as MockCond,
            patch("weight_loss_charting.handlers.charting_api.render_to_string") as mock_render,
        ):
            MockPatient.objects.get.return_value = MagicMock(first_name="A", last_name="B")
            MockObs.objects.for_patient.side_effect = Exception("DB error")
            MockGoal.objects.filter.return_value.order_by.return_value = []
            MockCond.objects.for_patient.return_value.active.return_value.prefetch_related.return_value = []
            mock_render.return_value = "<html/>"

            result = api.get_chart()

            assert len(result) == 1
            ctx = mock_render.call_args[0][1]
            assert json.loads(ctx["weight_history_json"]) == []

    def test_goals_fetch_exception(self, api, mock_request):
        mock_request.query_params = {"note_id": "1", "patient_id": "pat-1"}

        with (
            patch("weight_loss_charting.handlers.charting_api.Patient") as MockPatient,
            patch("weight_loss_charting.handlers.charting_api.Observation") as MockObs,
            patch("weight_loss_charting.handlers.charting_api.Goal") as MockGoal,
            patch("weight_loss_charting.handlers.charting_api.Condition") as MockCond,
            patch("weight_loss_charting.handlers.charting_api.render_to_string") as mock_render,
        ):
            MockPatient.objects.get.return_value = MagicMock(first_name="A", last_name="B")
            MockObs.objects.for_patient.return_value.filter.return_value.order_by.return_value = []
            MockGoal.objects.filter.side_effect = Exception("DB error")
            MockCond.objects.for_patient.return_value.active.return_value.prefetch_related.return_value = []
            mock_render.return_value = "<html/>"

            result = api.get_chart()

            ctx = mock_render.call_args[0][1]
            assert json.loads(ctx["goals_json"]) == []

    def test_conditions_fetch_exception(self, api, mock_request):
        mock_request.query_params = {"note_id": "1", "patient_id": "pat-1"}

        with (
            patch("weight_loss_charting.handlers.charting_api.Patient") as MockPatient,
            patch("weight_loss_charting.handlers.charting_api.Observation") as MockObs,
            patch("weight_loss_charting.handlers.charting_api.Goal") as MockGoal,
            patch("weight_loss_charting.handlers.charting_api.Condition") as MockCond,
            patch("weight_loss_charting.handlers.charting_api.render_to_string") as mock_render,
        ):
            MockPatient.objects.get.return_value = MagicMock(first_name="A", last_name="B")
            MockObs.objects.for_patient.return_value.filter.return_value.order_by.return_value = []
            MockGoal.objects.filter.return_value.order_by.return_value = []
            MockCond.objects.for_patient.side_effect = Exception("DB error")
            mock_render.return_value = "<html/>"

            result = api.get_chart()

            ctx = mock_render.call_args[0][1]
            assert json.loads(ctx["conditions_json"]) == []

    def test_missing_query_params_default_empty(self, api, mock_request):
        mock_request.query_params = {}

        with (
            patch("weight_loss_charting.handlers.charting_api.Patient") as MockPatient,
            patch("weight_loss_charting.handlers.charting_api.Observation") as MockObs,
            patch("weight_loss_charting.handlers.charting_api.Goal") as MockGoal,
            patch("weight_loss_charting.handlers.charting_api.Condition") as MockCond,
            patch("weight_loss_charting.handlers.charting_api.render_to_string") as mock_render,
        ):
            MockPatient.objects.get.side_effect = Exception("Not found")
            MockObs.objects.for_patient.return_value.filter.return_value.order_by.return_value = []
            MockGoal.objects.filter.return_value.order_by.return_value = []
            MockCond.objects.for_patient.return_value.active.return_value.prefetch_related.return_value = []
            mock_render.return_value = "<html/>"

            api.get_chart()

            ctx = mock_render.call_args[0][1]
            assert ctx["note_id"] == ""
            assert ctx["patient_id"] == ""


class TestPostVitals:
    def test_creates_vitals_command(self, api, mock_request):
        mock_request.json.return_value = {"note_id": "42", "weight_lbs": "180"}

        with (
            patch("weight_loss_charting.handlers.charting_api.Note") as MockNote,
            patch("weight_loss_charting.handlers.charting_api.VitalsCommand") as MockCmd,
        ):
            MockNote.objects.get.return_value = MagicMock(id="uuid-1")
            mock_effect = MagicMock()
            MockCmd.return_value.originate.return_value = mock_effect

            result = api.post_vitals()

            assert len(result) == 2
            MockCmd.assert_called_once_with(note_uuid="uuid-1", weight_lbs=180)

    def test_all_vitals_fields(self, api, mock_request):
        mock_request.json.return_value = {
            "note_id": "42",
            "weight_lbs": "180",
            "height": "70",
            "blood_pressure_systole": "120",
            "blood_pressure_diastole": "80",
            "waist_circumference": "34",
        }

        with (
            patch("weight_loss_charting.handlers.charting_api.Note") as MockNote,
            patch("weight_loss_charting.handlers.charting_api.VitalsCommand") as MockCmd,
        ):
            MockNote.objects.get.return_value = MagicMock(id="uuid-1")
            MockCmd.return_value.originate.return_value = MagicMock()

            api.post_vitals()

            MockCmd.assert_called_once_with(
                note_uuid="uuid-1",
                weight_lbs=180,
                height=70,
                blood_pressure_systole=120,
                blood_pressure_diastole=80,
                waist_circumference=34,
            )

    def test_invalid_json(self, api, mock_request):
        mock_request.json.side_effect = Exception("Bad JSON")

        result = api.post_vitals()

        assert len(result) == 1
        assert result[0].status_code == HTTPStatus.BAD_REQUEST

    def test_missing_note_id(self, api, mock_request):
        mock_request.json.return_value = {"weight_lbs": "180"}

        result = api.post_vitals()

        assert len(result) == 1
        assert result[0].status_code == HTTPStatus.BAD_REQUEST


class TestPostGoal:
    def test_creates_goal_command(self, api, mock_request):
        mock_request.json.return_value = {
            "note_id": "42",
            "goal_statement": "Lose 20 lbs",
        }

        with (
            patch("weight_loss_charting.handlers.charting_api.Note") as MockNote,
            patch("weight_loss_charting.handlers.charting_api.GoalCommand") as MockCmd,
        ):
            MockNote.objects.get.return_value = MagicMock(id="uuid-1")
            MockCmd.return_value.originate.return_value = MagicMock()

            result = api.post_goal()

            assert len(result) == 2
            MockCmd.assert_called_once_with(
                note_uuid="uuid-1",
                goal_statement="Lose 20 lbs",
            )

    def test_all_goal_fields(self, api, mock_request):
        mock_request.json.return_value = {
            "note_id": "42",
            "goal_statement": "Lose 20 lbs",
            "start_date": "2025-01-01",
            "due_date": "2025-06-01",
            "priority": "high-priority",
            "achievement_status": "in-progress",
        }

        with (
            patch("weight_loss_charting.handlers.charting_api.Note") as MockNote,
            patch("weight_loss_charting.handlers.charting_api.GoalCommand") as MockCmd,
        ):
            MockNote.objects.get.return_value = MagicMock(id="uuid-1")
            MockCmd.Priority.return_value = "high-priority"
            MockCmd.AchievementStatus.return_value = "in-progress"
            MockCmd.return_value.originate.return_value = MagicMock()

            api.post_goal()

            MockCmd.assert_called_once_with(
                note_uuid="uuid-1",
                goal_statement="Lose 20 lbs",
                start_date=date(2025, 1, 1),
                due_date=date(2025, 6, 1),
                priority="high-priority",
                achievement_status="in-progress",
            )

    def test_invalid_json(self, api, mock_request):
        mock_request.json.side_effect = Exception("Bad JSON")

        result = api.post_goal()

        assert len(result) == 1
        assert result[0].status_code == HTTPStatus.BAD_REQUEST

    def test_missing_note_id(self, api, mock_request):
        mock_request.json.return_value = {"goal_statement": "Lose 20 lbs"}

        result = api.post_goal()

        assert len(result) == 1
        assert result[0].status_code == HTTPStatus.BAD_REQUEST


class TestPostAssess:
    def test_creates_assess_command(self, api, mock_request):
        mock_request.json.return_value = {
            "note_id": "42",
            "condition_id": "cond-1",
            "narrative": "Patient improving",
        }

        with (
            patch("weight_loss_charting.handlers.charting_api.Note") as MockNote,
            patch("weight_loss_charting.handlers.charting_api.AssessCommand") as MockCmd,
        ):
            MockNote.objects.get.return_value = MagicMock(id="uuid-1")
            MockCmd.return_value.originate.return_value = MagicMock()

            result = api.post_assess()

            assert len(result) == 2
            MockCmd.assert_called_once_with(
                note_uuid="uuid-1",
                condition_id="cond-1",
                narrative="Patient improving",
            )

    def test_all_assess_fields(self, api, mock_request):
        mock_request.json.return_value = {
            "note_id": "42",
            "condition_id": "cond-1",
            "status": "improved",
            "narrative": "Getting better",
            "background": "Weight loss program",
        }

        with (
            patch("weight_loss_charting.handlers.charting_api.Note") as MockNote,
            patch("weight_loss_charting.handlers.charting_api.AssessCommand") as MockCmd,
        ):
            MockNote.objects.get.return_value = MagicMock(id="uuid-1")
            MockCmd.return_value.originate.return_value = MagicMock()

            api.post_assess()

            MockCmd.assert_called_once_with(
                note_uuid="uuid-1",
                condition_id="cond-1",
                status="improved",
                narrative="Getting better",
                background="Weight loss program",
            )

    def test_invalid_json(self, api, mock_request):
        mock_request.json.side_effect = Exception("Bad JSON")

        result = api.post_assess()

        assert len(result) == 1
        assert result[0].status_code == HTTPStatus.BAD_REQUEST

    def test_missing_note_id(self, api, mock_request):
        mock_request.json.return_value = {"condition_id": "cond-1"}

        result = api.post_assess()

        assert len(result) == 1
        assert result[0].status_code == HTTPStatus.BAD_REQUEST


class TestPostPlan:
    def test_creates_plan_command(self, api, mock_request):
        mock_request.json.return_value = {
            "note_id": "42",
            "narrative": "Continue current regimen",
        }

        with (
            patch("weight_loss_charting.handlers.charting_api.Note") as MockNote,
            patch("weight_loss_charting.handlers.charting_api.PlanCommand") as MockCmd,
        ):
            MockNote.objects.get.return_value = MagicMock(id="uuid-1")
            MockCmd.return_value.originate.return_value = MagicMock()

            result = api.post_plan()

            assert len(result) == 2
            MockCmd.assert_called_once_with(
                note_uuid="uuid-1",
                narrative="Continue current regimen",
            )

    def test_invalid_json(self, api, mock_request):
        mock_request.json.side_effect = Exception("Bad JSON")

        result = api.post_plan()

        assert len(result) == 1
        assert result[0].status_code == HTTPStatus.BAD_REQUEST

    def test_missing_note_id(self, api, mock_request):
        mock_request.json.return_value = {"narrative": "Some plan"}

        result = api.post_plan()

        assert len(result) == 1
        assert result[0].status_code == HTTPStatus.BAD_REQUEST

    def test_empty_narrative_defaults(self, api, mock_request):
        mock_request.json.return_value = {"note_id": "42"}

        with (
            patch("weight_loss_charting.handlers.charting_api.Note") as MockNote,
            patch("weight_loss_charting.handlers.charting_api.PlanCommand") as MockCmd,
        ):
            MockNote.objects.get.return_value = MagicMock(id="uuid-1")
            MockCmd.return_value.originate.return_value = MagicMock()

            api.post_plan()

            MockCmd.assert_called_once_with(note_uuid="uuid-1", narrative="")
