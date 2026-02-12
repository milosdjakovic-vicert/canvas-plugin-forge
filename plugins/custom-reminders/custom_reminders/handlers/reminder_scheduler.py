"""Cron task for scheduled appointment reminders."""
from datetime import datetime, timedelta, timezone

from canvas_sdk.caching.plugins import get_cache
from canvas_sdk.effects import Effect
from canvas_sdk.handlers.cron_task import CronTask
from canvas_sdk.v1.data.appointment import Appointment
from logger import log

from custom_reminders.services.config import load_config, save_config
from custom_reminders.services.messaging import log_message_to_cache, send_campaign_messages


class ReminderScheduler(CronTask):
    """Check for appointments needing reminders every 15 minutes."""

    SCHEDULE = "*/15 * * * *"  # Every 15 minutes

    def execute(self) -> list[Effect]:
        """Check appointments and send reminders."""
        config = load_config()

        # Refresh config TTL every time we run (every 15 min)
        save_config(config)

        if not config.reminders_enabled:
            log.info("Reminders disabled, skipping")
            return []

        cache = get_cache()
        now = datetime.now(timezone.utc)

        # Get appointments in the next 7 days (max reminder window)
        end_window = now + timedelta(days=7)
        appointments = Appointment.objects.filter(
            start_time__gte=now, start_time__lte=end_window
        ).select_related("patient", "provider", "location")

        reminders_sent = 0

        for appointment in appointments:
            # Calculate time until appointment
            time_until = appointment.start_time - now
            minutes_until = int(time_until.total_seconds() / 60)

            # Check each reminder interval
            for interval_minutes in config.reminder_intervals:
                # Check if we're within a 15-minute window of the interval
                # (since we run every 15 minutes)
                if abs(minutes_until - interval_minutes) <= 15:
                    # Check if we've already sent this reminder
                    cache_key = f"cr:reminder_sent:{appointment.id}:{interval_minutes}"
                    already_sent = cache.get(cache_key)

                    if already_sent:
                        continue

                    # Send reminder
                    log.info(
                        f"Sending {interval_minutes}-minute reminder for appointment {appointment.id}"
                    )

                    results = send_campaign_messages(
                        appointment.patient, appointment, config, "reminder", self.secrets
                    )

                    # Log to cache
                    log_message_to_cache(appointment.id, appointment.patient.id, "reminder", results)

                    # Mark as sent (TTL = 7 days, longer than any reminder window)
                    cache.set(cache_key, "1", timeout_seconds=604800)

                    reminders_sent += 1

        log.info(f"Sent {reminders_sent} reminders")
        return []
