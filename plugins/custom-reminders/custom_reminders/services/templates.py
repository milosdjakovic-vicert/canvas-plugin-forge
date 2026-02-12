"""Template rendering for reminder messages."""
from typing import Any

from canvas_sdk.v1.data.appointment import Appointment
from canvas_sdk.v1.data.patient import Patient


def render_template(template: str, variables: dict[str, Any]) -> str:
    """
    Render a template string by replacing {{variable}} placeholders.

    Args:
        template: Template string with {{variable}} placeholders
        variables: Dictionary of variable names to values

    Returns:
        Rendered template string
    """
    result = template
    for key, value in variables.items():
        placeholder = f"{{{{{key}}}}}"
        result = result.replace(placeholder, str(value))
    return result


def get_template_variables(patient: Patient, appointment: Appointment) -> dict[str, str]:
    """
    Extract template variables from patient and appointment.

    Args:
        patient: Patient object
        appointment: Appointment object

    Returns:
        Dictionary of template variable names to values
    """
    # Format appointment date and time
    appointment_date = appointment.start_time.strftime("%B %d, %Y")
    appointment_time = appointment.start_time.strftime("%I:%M %p")

    # Get provider name
    provider_name = "your provider"
    if appointment.provider:
        provider_name = f"{appointment.provider.first_name} {appointment.provider.last_name}"

    # Get location name
    location_name = "our clinic"
    if appointment.location:
        location_name = appointment.location.full_name

    return {
        "patient_first_name": patient.first_name,
        "patient_last_name": patient.last_name,
        "provider_name": provider_name,
        "appointment_date": appointment_date,
        "appointment_time": appointment_time,
        "location_name": location_name,
    }
