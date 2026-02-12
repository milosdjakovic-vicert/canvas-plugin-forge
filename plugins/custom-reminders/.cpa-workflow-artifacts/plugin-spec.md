# Plugin Specification: Custom Reminders

## Problem Statement

Clinics need automated, customizable patient messaging around appointments — confirmations, reminders, no-show alerts, and cancellation alerts — delivered via SMS and email. Admins need to configure campaign content and timing, and all staff need visibility into what messages were sent at both patient and global levels.

## Target Users

| Role | Access |
|------|--------|
| Practice admins | Configure campaign templates, timing, channels; view global message history |
| All staff | View patient-level message history in chart context |

## Campaign Types

### 1. Appointment Confirmation
- **Trigger:** `APPOINTMENT_CREATED` event (instant)
- **Channels:** SMS + Email (based on patient preference)
- **Default template (SMS):** `Hi {{patient_first_name}}, your appointment with {{provider_name}} at {{clinic_name}} is confirmed for {{appointment_date}} at {{appointment_time}}. Call {{clinic_phone}} to reschedule.`
- **Default template (Email):** HTML-formatted version with clinic branding header

### 2. Appointment Reminders
- **Trigger:** `CronTask` (runs every 15 minutes, checks for appointments needing reminders)
- **Default schedule:** 7 days before, 24 hours before, 2 hours before (configurable chain)
- **Channels:** SMS + Email
- **Default template (SMS):** `Reminder: You have an appointment with {{provider_name}} on {{appointment_date}} at {{appointment_time}} at {{clinic_name}}. Reply STOP to opt out.`

### 3. No-Show Alert
- **Trigger:** `APPOINTMENT_NO_SHOWED` event (instant)
- **Channels:** SMS + Email
- **Default template (SMS):** `We missed you today at {{clinic_name}}. Please call {{clinic_phone}} to reschedule your appointment with {{provider_name}}.`

### 4. Cancellation Alert
- **Trigger:** `APPOINTMENT_CANCELED` event (instant)
- **Channels:** SMS + Email
- **Default template (SMS):** `Your appointment with {{provider_name}} on {{appointment_date}} at {{appointment_time}} has been cancelled. Call {{clinic_phone}} to rebook.`

## Template Variables

| Variable | Source |
|----------|--------|
| `{{patient_first_name}}` | `Patient.first_name` |
| `{{patient_last_name}}` | `Patient.last_name` |
| `{{provider_name}}` | `Appointment.provider` (Staff first + last name) |
| `{{clinic_name}}` | `PracticeLocation.full_name` or configurable default |
| `{{clinic_phone}}` | Configurable in campaign settings |
| `{{appointment_date}}` | `Appointment.start_time` formatted as date |
| `{{appointment_time}}` | `Appointment.start_time` formatted as time |
| `{{location_name}}` | `Appointment.location.full_name` |

## Architecture

### SDK Handlers

| Handler | Type | Purpose |
|---------|------|---------|
| `ReminderAdminApp` | `Application` (global) | Admin UI — campaign config + global message log |
| `ReminderPatientApp` | `Application` (patient_specific) | Patient chart — per-patient message history |
| `AppointmentEventHandler` | `BaseHandler` | Responds to CREATED, CANCELED, NO_SHOWED → sends instant messages |
| `ReminderScheduler` | `CronTask` | Runs every 15 min, checks for upcoming appointments needing reminders |
| `ReminderAPI` | `SimpleAPI` (multiple routes) | Serves HTML pages + JSON endpoints for config and history |

### Data Storage

| Data | Storage | Rationale |
|------|---------|-----------|
| Campaign config (templates, timing, channels) | Cache API | Admin-set, refreshable; 14-day TTL with CRON keepalive |
| Per-appointment message tracking | Appointment Metadata | Permanent, queryable; keys like `reminder_7d_sent`, `confirmation_sent` |
| Message log entries | Cache API | Rolling window for display; appointment metadata is source of truth |

### Appointment Metadata Keys

Each appointment gets metadata entries tracking what was sent:

| Key | Value (JSON) |
|-----|------|
| `cr_confirmation_sent` | `{"ts": "ISO8601", "channels": ["sms", "email"], "status": "delivered"}` |
| `cr_reminder_7d_sent` | `{"ts": "ISO8601", "channels": ["sms"], "status": "delivered"}` |
| `cr_reminder_24h_sent` | `{"ts": "ISO8601", "channels": ["sms", "email"], "status": "delivered"}` |
| `cr_reminder_2h_sent` | `{"ts": "ISO8601", "channels": ["sms"], "status": "delivered"}` |
| `cr_noshow_sent` | `{"ts": "ISO8601", "channels": ["sms", "email"], "status": "delivered"}` |
| `cr_cancel_sent` | `{"ts": "ISO8601", "channels": ["sms", "email"], "status": "delivered"}` |

Prefix `cr_` (custom reminders) avoids collision with other plugins.

### API Routes (SimpleAPI)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/admin` | Serves admin configuration HTML page |
| GET | `/admin/config` | Returns current campaign configuration JSON |
| POST | `/admin/config` | Saves campaign configuration |
| GET | `/admin/history` | Returns global message history (paginated) |
| GET | `/patient/{patient_id}/history` | Returns patient-specific message history |
| GET | `/patient-view` | Serves patient message history HTML page |

### Message Delivery

- **SMS:** Twilio REST API via `httpx` (async HTTP client)
- **Email:** SendGrid v3 API via `httpx`
- API keys stored as **plugin secrets** (hidden from customers)
- Patient channel preference determined by:
  1. `PatientContactPoint.opted_out == False`
  2. `PatientContactPoint.has_consent == True`
  3. `PatientContactPoint.state == "active"`
  4. System: `phone` for SMS, `email` for email

### Patient Opt-Out

- SMS: Include `Reply STOP to opt out` in every message
- Twilio handles STOP/START automatically at carrier level
- Email: Include unsubscribe link (SendGrid handles)
- Plugin respects `PatientContactPoint.opted_out` flag

## Plugin Secrets

| Secret Name | Description |
|-------------|-------------|
| `twilio-account-sid` | Twilio Account SID |
| `twilio-auth-token` | Twilio Auth Token |
| `twilio-phone-number` | Twilio sender phone number |
| `sendgrid-api-key` | SendGrid API key |
| `sendgrid-from-email` | SendGrid sender email address |
| `api-key` | API key for authenticating SimpleAPI requests |

## Data Access (Manifest)

### Read
- `v1.Patient`
- `v1.Appointment`
- `v1.Staff`
- `v1.PracticeLocation`

### Write
- Appointment metadata (via effects)

## UI Design

### Admin Application (Global)
- **Tabs:** Campaigns | Message History
- **Campaigns tab:** Card per campaign type (Confirmation, Reminders, No-Show, Cancellation)
  - Toggle enable/disable per campaign
  - Edit SMS template (plain text textarea)
  - Edit Email template (HTML textarea with preview)
  - Channel selection (SMS, Email, Both)
  - Timing config (reminders only): add/remove intervals from chain
  - Clinic phone number + clinic name defaults
- **Message History tab:** Table with columns: Date, Patient, Campaign Type, Channel, Status
  - Filterable by campaign type, date range, status
  - Paginated (50 per page)

### Patient Application (Chart)
- Single-page view showing message history for current patient
- Table: Date, Campaign Type, Channel, Status, Appointment Date
- Color-coded status (green=delivered, red=failed, yellow=pending)

## HIPAA Considerations
- Messages contain **no clinical/diagnostic information**
- Only: patient first name, provider name, appointment date/time, clinic name/phone
- No PHI beyond what's necessary for appointment logistics

## Constraints & Limitations
- Campaign configuration stored in cache (14-day TTL) — CRON task refreshes TTL every 12 hours
- Message history in cache has rolling 14-day window; appointment metadata is permanent source of truth
- CronTask minimum resolution is 1 minute; using 15-minute intervals for reminder checks
- Plugin runs in sandboxed environment — no direct database writes, only via Effects
