"""Tests for template rendering service."""
from datetime import datetime, timezone

import pytest

from custom_reminders.services.templates import get_template_variables, render_template


def test_render_template_simple():
    """Test rendering a simple template."""
    template = "Hello {{name}}, welcome to {{place}}!"
    variables = {"name": "Alice", "place": "Wonderland"}

    result = render_template(template, variables)

    assert result == "Hello Alice, welcome to Wonderland!"


def test_render_template_multiple_occurrences():
    """Test rendering template with repeated variables."""
    template = "{{name}} said {{name}} loves {{name}}"
    variables = {"name": "Bob"}

    result = render_template(template, variables)

    assert result == "Bob said Bob loves Bob"


def test_render_template_unused_variable():
    """Test rendering template with unused variables."""
    template = "Hello {{name}}"
    variables = {"name": "Charlie", "age": "30", "city": "Boston"}

    result = render_template(template, variables)

    assert result == "Hello Charlie"


def test_render_template_missing_variable():
    """Test rendering template with missing variables (leaves placeholder)."""
    template = "Hello {{name}}, you are {{age}} years old"
    variables = {"name": "Dana"}

    result = render_template(template, variables)

    assert result == "Hello Dana, you are {{age}} years old"


def test_get_template_variables(mocker):
    """Test extracting template variables from patient and appointment."""
    # Mock patient
    patient = mocker.Mock()
    patient.first_name = "John"
    patient.last_name = "Doe"

    # Mock provider
    provider = mocker.Mock()
    provider.first_name = "Dr. Sarah"
    provider.last_name = "Smith"

    # Mock location
    location = mocker.Mock()
    location.full_name = "Main Clinic"

    # Mock appointment
    appointment = mocker.Mock()
    appointment.start_time = datetime(2026, 3, 15, 14, 30, tzinfo=timezone.utc)
    appointment.provider = provider
    appointment.location = location

    variables = get_template_variables(patient, appointment)

    assert variables["patient_first_name"] == "John"
    assert variables["patient_last_name"] == "Doe"
    assert variables["provider_name"] == "Dr. Sarah Smith"
    assert variables["location_name"] == "Main Clinic"
    assert "March 15, 2026" in variables["appointment_date"]
    assert "02:30 PM" in variables["appointment_time"]


def test_get_template_variables_no_provider(mocker):
    """Test template variables with no provider."""
    patient = mocker.Mock()
    patient.first_name = "Jane"
    patient.last_name = "Smith"

    appointment = mocker.Mock()
    appointment.start_time = datetime(2026, 4, 20, 10, 0, tzinfo=timezone.utc)
    appointment.provider = None
    appointment.location = None

    variables = get_template_variables(patient, appointment)

    assert variables["provider_name"] == "your provider"
    assert variables["location_name"] == "our clinic"


def test_render_full_message(mocker):
    """Test rendering a complete message template."""
    patient = mocker.Mock()
    patient.first_name = "Alice"
    patient.last_name = "Johnson"

    provider = mocker.Mock()
    provider.first_name = "Dr. Bob"
    provider.last_name = "Williams"

    location = mocker.Mock()
    location.full_name = "Downtown Clinic"

    appointment = mocker.Mock()
    appointment.start_time = datetime(2026, 5, 10, 9, 0, tzinfo=timezone.utc)
    appointment.provider = provider
    appointment.location = location

    variables = get_template_variables(patient, appointment)
    variables["clinic_name"] = "HealthCare Inc"
    variables["clinic_phone"] = "(555) 123-4567"

    template = (
        "Hi {{patient_first_name}}, your appointment with {{provider_name}} "
        "at {{clinic_name}} is confirmed for {{appointment_date}} at {{appointment_time}}. "
        "Call {{clinic_phone}} to reschedule."
    )

    result = render_template(template, variables)

    assert "Hi Alice" in result
    assert "Dr. Bob Williams" in result
    assert "HealthCare Inc" in result
    assert "May 10, 2026" in result
    assert "(555) 123-4567" in result
