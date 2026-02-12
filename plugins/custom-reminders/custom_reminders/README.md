# Custom Reminders Plugin

Automated patient appointment reminders via SMS and email with customizable campaigns for confirmations, reminders, no-shows, and cancellations.

## Features

- **Appointment Confirmation**: Instant SMS/email when appointments are created
- **Appointment Reminders**: Scheduled reminders (default: 7 days, 24 hours, 2 hours before)
- **No-Show Alerts**: Instant SMS/email when appointments are marked as no-showed
- **Cancellation Alerts**: Instant SMS/email when appointments are canceled
- **Admin Configuration**: Web UI for managing campaign templates and settings
- **Message History**: Global and per-patient message tracking

## Campaign Types

### 1. Appointment Confirmation
- **Trigger**: `APPOINTMENT_CREATED` event
- **Default schedule**: Instant
- **Channels**: SMS + Email

### 2. Appointment Reminders
- **Trigger**: CronTask (every 15 minutes)
- **Default schedule**: 7 days, 24 hours, 2 hours before appointment
- **Channels**: SMS + Email

### 3. No-Show Alert
- **Trigger**: `APPOINTMENT_NO_SHOWED` event
- **Default schedule**: Instant
- **Channels**: SMS + Email

### 4. Cancellation Alert
- **Trigger**: `APPOINTMENT_CANCELED` event
- **Default schedule**: Instant
- **Channels**: SMS + Email

## Configuration

### Required Secrets

Configure these secrets in the Canvas plugin settings:

- `twilio-account-sid`: Twilio Account SID
- `twilio-auth-token`: Twilio Auth Token
- `twilio-phone-number`: Twilio sender phone number (E.164 format)
- `sendgrid-api-key`: SendGrid API key
- `sendgrid-from-email`: SendGrid sender email address

### Admin UI

Access the admin UI via the "Reminders Admin" global application to:

- Enable/disable campaigns
- Edit SMS and email templates
- Configure reminder intervals
- Set clinic name and phone number
- View global message history

### Template Variables

Available variables for message templates:

- `{{patient_first_name}}`: Patient's first name
- `{{patient_last_name}}`: Patient's last name
- `{{provider_name}}`: Provider's full name
- `{{clinic_name}}`: Clinic name (configurable)
- `{{clinic_phone}}`: Clinic phone (configurable)
- `{{appointment_date}}`: Appointment date (formatted)
- `{{appointment_time}}`: Appointment time (formatted)
- `{{location_name}}`: Practice location name

## Patient Contact Points

The plugin respects patient contact preferences:

- Only sends to contacts with `state == "active"`
- Checks `has_consent == True`
- Respects `opted_out == False`
- SMS opt-out handled by Twilio (STOP/START keywords)
- Email opt-out handled by SendGrid unsubscribe links

## Data Storage

- **Campaign config**: Cache API (14-day TTL, refreshed by cron)
- **Message logs**: Cache API (per-patient and global)
- **Message tracking**: Cache API (prevents duplicate reminders)

## Architecture

### Handlers

- `AppointmentEventHandler`: Responds to APPOINTMENT_CREATED, APPOINTMENT_CANCELED, APPOINTMENT_NO_SHOWED
- `ReminderScheduler`: CronTask runs every 15 minutes to check for pending reminders
- `ReminderAPI`: SimpleAPI with routes for admin/patient views and configuration

### Applications

- `ReminderAdminApp`: Global scope - admin configuration and message history
- `ReminderPatientApp`: Patient-specific scope - per-patient message history

### Services

- `config.py`: Campaign configuration management
- `templates.py`: Template variable rendering
- `messaging.py`: Twilio SMS and SendGrid email integration

## HIPAA Compliance

Messages contain **no clinical or diagnostic information**. Only appointment logistics:

- Patient first name
- Provider name
- Appointment date and time
- Clinic name and phone number

No PHI beyond what's necessary for appointment management.

## Development

### Running Tests

```bash
pytest tests/
```

### Type Checking

```bash
mypy custom_reminders/
```

### Local Development

1. Install dependencies: `uv sync`
2. Set up secrets in `.env` file
3. Run tests: `pytest`
4. Deploy to test instance: `uv run canvas install`

## Support

For issues or questions, contact the plugin development team.
