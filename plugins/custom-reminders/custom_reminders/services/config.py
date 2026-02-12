"""Campaign configuration management using Cache API."""
import json
from dataclasses import dataclass, field
from typing import Any

from canvas_sdk.caching.plugins import get_cache


@dataclass
class CampaignConfig:
    """Campaign configuration for reminders."""

    # Global settings
    clinic_name: str = "Our Clinic"
    clinic_phone: str = ""

    # Confirmation campaign
    confirmation_enabled: bool = True
    confirmation_sms_template: str = (
        "Hi {{patient_first_name}}, your appointment with {{provider_name}} at "
        "{{clinic_name}} is confirmed for {{appointment_date}} at {{appointment_time}}. "
        "Call {{clinic_phone}} to reschedule."
    )
    confirmation_email_template: str = (
        "<html><body>"
        "<h2>Appointment Confirmation</h2>"
        "<p>Hi {{patient_first_name}},</p>"
        "<p>Your appointment with {{provider_name}} at {{clinic_name}} is confirmed for "
        "{{appointment_date}} at {{appointment_time}}.</p>"
        "<p>Call {{clinic_phone}} to reschedule.</p>"
        "</body></html>"
    )
    confirmation_channels: list[str] = field(default_factory=lambda: ["sms", "email"])

    # Reminder campaign
    reminders_enabled: bool = True
    reminder_intervals: list[int] = field(default_factory=lambda: [10080, 1440, 120])  # 7d, 24h, 2h in minutes
    reminder_sms_template: str = (
        "Reminder: You have an appointment with {{provider_name}} on {{appointment_date}} "
        "at {{appointment_time}} at {{clinic_name}}. Reply STOP to opt out."
    )
    reminder_email_template: str = (
        "<html><body>"
        "<h2>Appointment Reminder</h2>"
        "<p>You have an appointment with {{provider_name}} on {{appointment_date}} "
        "at {{appointment_time}} at {{clinic_name}}.</p>"
        "</body></html>"
    )
    reminder_channels: list[str] = field(default_factory=lambda: ["sms", "email"])

    # No-show campaign
    noshow_enabled: bool = True
    noshow_sms_template: str = (
        "We missed you today at {{clinic_name}}. Please call {{clinic_phone}} to "
        "reschedule your appointment with {{provider_name}}."
    )
    noshow_email_template: str = (
        "<html><body>"
        "<h2>We Missed You</h2>"
        "<p>We missed you today at {{clinic_name}}.</p>"
        "<p>Please call {{clinic_phone}} to reschedule your appointment with {{provider_name}}.</p>"
        "</body></html>"
    )
    noshow_channels: list[str] = field(default_factory=lambda: ["sms", "email"])

    # Cancellation campaign
    cancellation_enabled: bool = True
    cancellation_sms_template: str = (
        "Your appointment with {{provider_name}} on {{appointment_date}} at "
        "{{appointment_time}} has been cancelled. Call {{clinic_phone}} to rebook."
    )
    cancellation_email_template: str = (
        "<html><body>"
        "<h2>Appointment Cancelled</h2>"
        "<p>Your appointment with {{provider_name}} on {{appointment_date}} at "
        "{{appointment_time}} has been cancelled.</p>"
        "<p>Call {{clinic_phone}} to rebook.</p>"
        "</body></html>"
    )
    cancellation_channels: list[str] = field(default_factory=lambda: ["sms", "email"])

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "clinic_name": self.clinic_name,
            "clinic_phone": self.clinic_phone,
            "confirmation_enabled": self.confirmation_enabled,
            "confirmation_sms_template": self.confirmation_sms_template,
            "confirmation_email_template": self.confirmation_email_template,
            "confirmation_channels": self.confirmation_channels,
            "reminders_enabled": self.reminders_enabled,
            "reminder_intervals": self.reminder_intervals,
            "reminder_sms_template": self.reminder_sms_template,
            "reminder_email_template": self.reminder_email_template,
            "reminder_channels": self.reminder_channels,
            "noshow_enabled": self.noshow_enabled,
            "noshow_sms_template": self.noshow_sms_template,
            "noshow_email_template": self.noshow_email_template,
            "noshow_channels": self.noshow_channels,
            "cancellation_enabled": self.cancellation_enabled,
            "cancellation_sms_template": self.cancellation_sms_template,
            "cancellation_email_template": self.cancellation_email_template,
            "cancellation_channels": self.cancellation_channels,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CampaignConfig":
        """Create from dictionary."""
        return cls(**data)


CACHE_KEY_CONFIG = "cr:config"
CACHE_TTL = 1209600  # 14 days in seconds


def load_config() -> CampaignConfig:
    """Load campaign configuration from cache."""
    cache = get_cache()
    data = cache.get(CACHE_KEY_CONFIG)
    if data is None:
        # Return default config
        return CampaignConfig()
    return CampaignConfig.from_dict(json.loads(data))


def save_config(config: CampaignConfig) -> None:
    """Save campaign configuration to cache."""
    cache = get_cache()
    cache.set(CACHE_KEY_CONFIG, json.dumps(config.to_dict()), timeout=CACHE_TTL)
