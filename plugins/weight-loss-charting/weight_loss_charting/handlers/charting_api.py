import json
from datetime import date
from http import HTTPStatus

from canvas_sdk.commands.commands.assess import AssessCommand
from canvas_sdk.commands.commands.goal import GoalCommand
from canvas_sdk.commands.commands.plan import PlanCommand
from canvas_sdk.commands.commands.vitals import VitalsCommand
from canvas_sdk.effects import Effect
from canvas_sdk.effects.simple_api import HTMLResponse, JSONResponse, Response
from canvas_sdk.handlers.simple_api import StaffSessionAuthMixin
from canvas_sdk.handlers.simple_api.api import SimpleAPI, get, post
from canvas_sdk.templates import render_to_string
from canvas_sdk.v1.data.condition import Condition
from canvas_sdk.v1.data.goal import Goal
from canvas_sdk.v1.data.observation import Observation
from canvas_sdk.v1.data.note import Note
from canvas_sdk.v1.data.patient import Patient
from logger import log


class WeightLossChartingAPI(StaffSessionAuthMixin, SimpleAPI):
    """API serving the weight loss charting interface and handling command creation."""

    def _get_note_uuid(self, note_id: str) -> str:
        """Resolve a note's integer dbid to its UUID."""
        note = Note.objects.get(dbid=int(note_id))
        return str(note.id)

    @get("/chart")
    def get_chart(self) -> list[Response | Effect]:
        """Render the weight loss charting form with patient data."""
        note_id = self.request.query_params.get("note_id", "")
        patient_id = self.request.query_params.get("patient_id", "")

        patient_name = "Unknown Patient"
        try:
            patient = Patient.objects.get(id=patient_id)
            patient_name = f"{patient.first_name} {patient.last_name}".strip()
        except Exception:
            log.warning(f"Could not find patient {patient_id}")

        # Fetch weight history for trend chart
        weight_history = []
        try:
            observations = (
                Observation.objects.for_patient(patient_id)
                .filter(category="vital-signs", name="weight", deleted=False)
                .order_by("effective_datetime")
            )
            for obs in observations:
                try:
                    oz_value = float(obs.value)
                    lbs_value = round(oz_value / 16, 1)
                    weight_history.append({
                        "date": obs.effective_datetime.strftime("%Y-%m-%d"),
                        "lbs": lbs_value,
                    })
                except (ValueError, TypeError):
                    continue
        except Exception:
            log.warning(f"Could not fetch weight history for patient {patient_id}")

        # Fetch existing goals
        goals_data = []
        try:
            goals = Goal.objects.filter(patient_id=patient_id).order_by("-start_date")
            for goal in goals:
                goals_data.append({
                    "id": str(goal.id),
                    "statement": goal.goal_statement,
                    "start_date": str(goal.start_date) if goal.start_date else "",
                    "due_date": str(goal.due_date) if goal.due_date else "",
                    "achievement_status": goal.achievement_status or "",
                    "priority": goal.priority or "",
                    "lifecycle_status": goal.lifecycle_status or "",
                })
        except Exception:
            log.warning(f"Could not fetch goals for patient {patient_id}")

        # Fetch active weight-related conditions (E66.*)
        conditions_data = []
        try:
            conditions = (
                Condition.objects.for_patient(patient_id)
                .active()
                .prefetch_related("codings")
            )
            for condition in conditions:
                codings = condition.codings.all()
                is_weight_related = any(
                    c.code.startswith("E66") for c in codings if c.code
                )
                if is_weight_related:
                    display = ", ".join(
                        f"{c.code} — {c.display}" for c in codings if c.code
                    )
                    conditions_data.append({
                        "id": str(condition.id),
                        "display": display or "Weight-related condition",
                        "onset_date": str(condition.onset_date) if condition.onset_date else "",
                    })
        except Exception:
            log.warning(f"Could not fetch conditions for patient {patient_id}")

        context = {
            "note_id": note_id,
            "patient_id": patient_id,
            "patient_name": patient_name,
            "weight_history_json": json.dumps(weight_history),
            "goals_json": json.dumps(goals_data),
            "conditions_json": json.dumps(conditions_data),
        }

        html = render_to_string("templates/weight_loss_form.html", context)
        return [HTMLResponse(html)]

    @post("/vitals")
    def post_vitals(self) -> list[Response | Effect]:
        """Create a VitalsCommand from submitted vitals data."""
        try:
            data = self.request.json()
        except Exception:
            return [JSONResponse({"error": "Invalid JSON"}, status_code=HTTPStatus.BAD_REQUEST)]

        note_id = data.get("note_id", "")
        if not note_id:
            return [JSONResponse({"error": "note_id is required"}, status_code=HTTPStatus.BAD_REQUEST)]

        note_uuid = self._get_note_uuid(note_id)
        kwargs = {"note_uuid": note_uuid}

        if data.get("weight_lbs"):
            kwargs["weight_lbs"] = int(data["weight_lbs"])
        if data.get("height"):
            kwargs["height"] = int(data["height"])
        if data.get("blood_pressure_systole"):
            kwargs["blood_pressure_systole"] = int(data["blood_pressure_systole"])
        if data.get("blood_pressure_diastole"):
            kwargs["blood_pressure_diastole"] = int(data["blood_pressure_diastole"])
        if data.get("waist_circumference"):
            kwargs["waist_circumference"] = int(data["waist_circumference"])

        command = VitalsCommand(**kwargs)
        return [JSONResponse({"status": "ok"}), command.originate()]

    @post("/goal")
    def post_goal(self) -> list[Response | Effect]:
        """Create a GoalCommand from submitted goal data."""
        try:
            data = self.request.json()
        except Exception:
            return [JSONResponse({"error": "Invalid JSON"}, status_code=HTTPStatus.BAD_REQUEST)]

        note_id = data.get("note_id", "")
        if not note_id:
            return [JSONResponse({"error": "note_id is required"}, status_code=HTTPStatus.BAD_REQUEST)]

        note_uuid = self._get_note_uuid(note_id)
        kwargs = {
            "note_uuid": note_uuid,
            "goal_statement": data.get("goal_statement", ""),
        }

        if data.get("start_date"):
            kwargs["start_date"] = date.fromisoformat(data["start_date"])
        if data.get("due_date"):
            kwargs["due_date"] = date.fromisoformat(data["due_date"])
        if data.get("priority"):
            kwargs["priority"] = GoalCommand.Priority(data["priority"])
        if data.get("achievement_status"):
            kwargs["achievement_status"] = GoalCommand.AchievementStatus(data["achievement_status"])

        command = GoalCommand(**kwargs)
        return [JSONResponse({"status": "ok"}), command.originate()]

    @post("/assess")
    def post_assess(self) -> list[Response | Effect]:
        """Create an AssessCommand for a condition."""
        try:
            data = self.request.json()
        except Exception:
            return [JSONResponse({"error": "Invalid JSON"}, status_code=HTTPStatus.BAD_REQUEST)]

        note_id = data.get("note_id", "")
        if not note_id:
            return [JSONResponse({"error": "note_id is required"}, status_code=HTTPStatus.BAD_REQUEST)]

        note_uuid = self._get_note_uuid(note_id)
        kwargs = {"note_uuid": note_uuid}

        if data.get("condition_id"):
            kwargs["condition_id"] = data["condition_id"]
        if data.get("status"):
            kwargs["status"] = data["status"]
        if data.get("narrative"):
            kwargs["narrative"] = data["narrative"]
        if data.get("background"):
            kwargs["background"] = data["background"]

        command = AssessCommand(**kwargs)
        return [JSONResponse({"status": "ok"}), command.originate()]

    @post("/plan")
    def post_plan(self) -> list[Response | Effect]:
        """Create a PlanCommand with narrative."""
        try:
            data = self.request.json()
        except Exception:
            return [JSONResponse({"error": "Invalid JSON"}, status_code=HTTPStatus.BAD_REQUEST)]

        note_id = data.get("note_id", "")
        if not note_id:
            return [JSONResponse({"error": "note_id is required"}, status_code=HTTPStatus.BAD_REQUEST)]

        note_uuid = self._get_note_uuid(note_id)
        command = PlanCommand(
            note_uuid=note_uuid,
            narrative=data.get("narrative", ""),
        )
        return [JSONResponse({"status": "ok"}), command.originate()]
