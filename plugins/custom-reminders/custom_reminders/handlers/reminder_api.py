"""SimpleAPI for admin and patient views."""
import json
from http import HTTPStatus

from canvas_sdk.caching.plugins import get_cache
from canvas_sdk.effects import Effect
from canvas_sdk.effects.simple_api import HTMLResponse, JSONResponse, Response
from canvas_sdk.handlers.simple_api import SimpleAPI, StaffSessionAuthMixin, api
from logger import log

from custom_reminders.services.config import CampaignConfig, load_config, save_config


class ReminderAPI(StaffSessionAuthMixin, SimpleAPI):
    """API endpoints for admin configuration and message history."""

    PREFIX = ""

    @api.get("/admin")
    def get_admin_page(self) -> list[Response | Effect]:
        """Serve admin configuration page."""
        html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Custom Reminders Admin</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .tabs {
            display: flex;
            border-bottom: 1px solid #e0e0e0;
        }
        .tab {
            padding: 16px 24px;
            cursor: pointer;
            border-bottom: 3px solid transparent;
            font-weight: 500;
        }
        .tab.active {
            border-bottom-color: #1976d2;
            color: #1976d2;
        }
        .tab-content {
            display: none;
            padding: 24px;
        }
        .tab-content.active {
            display: block;
        }
        .campaign-card {
            border: 1px solid #e0e0e0;
            border-radius: 4px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .campaign-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }
        .campaign-title {
            font-size: 18px;
            font-weight: 600;
        }
        .form-group {
            margin-bottom: 16px;
        }
        label {
            display: block;
            margin-bottom: 4px;
            font-weight: 500;
            font-size: 14px;
        }
        input[type="text"], textarea {
            width: 100%;
            padding: 8px;
            border: 1px solid #ccc;
            border-radius: 4px;
            font-family: inherit;
            box-sizing: border-box;
        }
        textarea {
            min-height: 80px;
            resize: vertical;
        }
        .checkbox-group {
            display: flex;
            gap: 16px;
            margin-top: 8px;
        }
        .checkbox-group label {
            display: flex;
            align-items: center;
            gap: 6px;
            font-weight: normal;
        }
        button {
            background: #1976d2;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
        }
        button:hover {
            background: #1565c0;
        }
        .save-btn {
            margin-top: 20px;
        }
        .toggle {
            position: relative;
            display: inline-block;
            width: 48px;
            height: 24px;
        }
        .toggle input {
            opacity: 0;
            width: 0;
            height: 0;
        }
        .slider {
            position: absolute;
            cursor: pointer;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: #ccc;
            border-radius: 24px;
            transition: .4s;
        }
        .slider:before {
            position: absolute;
            content: "";
            height: 18px;
            width: 18px;
            left: 3px;
            bottom: 3px;
            background-color: white;
            border-radius: 50%;
            transition: .4s;
        }
        input:checked + .slider {
            background-color: #1976d2;
        }
        input:checked + .slider:before {
            transform: translateX(24px);
        }
        .history-table {
            width: 100%;
            border-collapse: collapse;
        }
        .history-table th {
            background: #f5f5f5;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            border-bottom: 2px solid #e0e0e0;
        }
        .history-table td {
            padding: 12px;
            border-bottom: 1px solid #e0e0e0;
        }
        .status-badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 500;
        }
        .status-delivered {
            background: #e8f5e9;
            color: #2e7d32;
        }
        .status-failed {
            background: #ffebee;
            color: #c62828;
        }
        .status-dry-run {
            background: #fff3e0;
            color: #e65100;
        }
        .global-settings {
            background: #f5f5f5;
            padding: 16px;
            border-radius: 4px;
            margin-bottom: 24px;
        }
        .interval-list {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-top: 8px;
        }
        .interval-tag {
            background: #e3f2fd;
            padding: 6px 12px;
            border-radius: 16px;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .interval-remove {
            cursor: pointer;
            color: #1976d2;
            font-weight: bold;
        }
        .add-interval {
            margin-top: 8px;
        }
        .test-mode-banner {
            background: #fff3e0;
            border: 1px solid #ffb74d;
            color: #e65100;
            padding: 12px 20px;
            margin: 16px 24px 0;
            border-radius: 4px;
            font-weight: 500;
            display: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <div id="test_mode_banner" class="test-mode-banner">
            TEST MODE — Messaging secrets not configured. Messages are logged but not actually sent.
        </div>
        <div class="tabs">
            <div class="tab active" onclick="switchTab('campaigns')">Campaigns</div>
            <div class="tab" onclick="switchTab('history')">Message History</div>
        </div>

        <div id="campaigns" class="tab-content active">
            <div class="global-settings">
                <h3 style="margin-top: 0;">Global Settings</h3>
                <div class="form-group">
                    <label>Clinic Name</label>
                    <input type="text" id="clinic_name" placeholder="Our Clinic">
                </div>
                <div class="form-group">
                    <label>Clinic Phone</label>
                    <input type="text" id="clinic_phone" placeholder="(555) 123-4567">
                </div>
            </div>

            <div class="campaign-card">
                <div class="campaign-header">
                    <div class="campaign-title">Appointment Confirmation</div>
                    <label class="toggle">
                        <input type="checkbox" id="confirmation_enabled">
                        <span class="slider"></span>
                    </label>
                </div>
                <div class="form-group">
                    <label>Channels</label>
                    <div class="checkbox-group">
                        <label><input type="checkbox" class="confirmation_channels" value="sms"> SMS</label>
                        <label><input type="checkbox" class="confirmation_channels" value="email"> Email</label>
                    </div>
                </div>
                <div class="form-group">
                    <label>SMS Template</label>
                    <textarea id="confirmation_sms_template"></textarea>
                </div>
                <div class="form-group">
                    <label>Email Template (HTML)</label>
                    <textarea id="confirmation_email_template"></textarea>
                </div>
            </div>

            <div class="campaign-card">
                <div class="campaign-header">
                    <div class="campaign-title">Appointment Reminders</div>
                    <label class="toggle">
                        <input type="checkbox" id="reminders_enabled">
                        <span class="slider"></span>
                    </label>
                </div>
                <div class="form-group">
                    <label>Reminder Intervals</label>
                    <div class="interval-list" id="interval_list"></div>
                    <div class="add-interval">
                        <input type="number" id="new_interval" placeholder="Minutes before appointment" style="width: 200px;">
                        <button onclick="addInterval()">Add Interval</button>
                    </div>
                </div>
                <div class="form-group">
                    <label>Channels</label>
                    <div class="checkbox-group">
                        <label><input type="checkbox" class="reminder_channels" value="sms"> SMS</label>
                        <label><input type="checkbox" class="reminder_channels" value="email"> Email</label>
                    </div>
                </div>
                <div class="form-group">
                    <label>SMS Template</label>
                    <textarea id="reminder_sms_template"></textarea>
                </div>
                <div class="form-group">
                    <label>Email Template (HTML)</label>
                    <textarea id="reminder_email_template"></textarea>
                </div>
            </div>

            <div class="campaign-card">
                <div class="campaign-header">
                    <div class="campaign-title">No-Show Alert</div>
                    <label class="toggle">
                        <input type="checkbox" id="noshow_enabled">
                        <span class="slider"></span>
                    </label>
                </div>
                <div class="form-group">
                    <label>Channels</label>
                    <div class="checkbox-group">
                        <label><input type="checkbox" class="noshow_channels" value="sms"> SMS</label>
                        <label><input type="checkbox" class="noshow_channels" value="email"> Email</label>
                    </div>
                </div>
                <div class="form-group">
                    <label>SMS Template</label>
                    <textarea id="noshow_sms_template"></textarea>
                </div>
                <div class="form-group">
                    <label>Email Template (HTML)</label>
                    <textarea id="noshow_email_template"></textarea>
                </div>
            </div>

            <div class="campaign-card">
                <div class="campaign-header">
                    <div class="campaign-title">Cancellation Alert</div>
                    <label class="toggle">
                        <input type="checkbox" id="cancellation_enabled">
                        <span class="slider"></span>
                    </label>
                </div>
                <div class="form-group">
                    <label>Channels</label>
                    <div class="checkbox-group">
                        <label><input type="checkbox" class="cancellation_channels" value="sms"> SMS</label>
                        <label><input type="checkbox" class="cancellation_channels" value="email"> Email</label>
                    </div>
                </div>
                <div class="form-group">
                    <label>SMS Template</label>
                    <textarea id="cancellation_sms_template"></textarea>
                </div>
                <div class="form-group">
                    <label>Email Template (HTML)</label>
                    <textarea id="cancellation_email_template"></textarea>
                </div>
            </div>

            <button class="save-btn" onclick="saveConfig()">Save Configuration</button>
        </div>

        <div id="history" class="tab-content">
            <h2>Message History</h2>
            <table class="history-table">
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Patient ID</th>
                        <th>Campaign</th>
                        <th>Channel</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody id="history_body">
                </tbody>
            </table>
        </div>
    </div>

    <script>
        let currentIntervals = [];

        function switchTab(tabName) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById(tabName).classList.add('active');

            if (tabName === 'history') {
                loadHistory();
            }
        }

        async function loadConfig() {
            const response = await fetch('/plugin-io/api/custom_reminders/admin/config');
            const config = await response.json();

            document.getElementById('clinic_name').value = config.clinic_name;
            document.getElementById('clinic_phone').value = config.clinic_phone;

            document.getElementById('confirmation_enabled').checked = config.confirmation_enabled;
            document.getElementById('confirmation_sms_template').value = config.confirmation_sms_template;
            document.getElementById('confirmation_email_template').value = config.confirmation_email_template;
            setChannels('confirmation_channels', config.confirmation_channels);

            document.getElementById('reminders_enabled').checked = config.reminders_enabled;
            currentIntervals = config.reminder_intervals;
            renderIntervals();
            document.getElementById('reminder_sms_template').value = config.reminder_sms_template;
            document.getElementById('reminder_email_template').value = config.reminder_email_template;
            setChannels('reminder_channels', config.reminder_channels);

            document.getElementById('noshow_enabled').checked = config.noshow_enabled;
            document.getElementById('noshow_sms_template').value = config.noshow_sms_template;
            document.getElementById('noshow_email_template').value = config.noshow_email_template;
            setChannels('noshow_channels', config.noshow_channels);

            document.getElementById('cancellation_enabled').checked = config.cancellation_enabled;
            document.getElementById('cancellation_sms_template').value = config.cancellation_sms_template;
            document.getElementById('cancellation_email_template').value = config.cancellation_email_template;
            setChannels('cancellation_channels', config.cancellation_channels);
        }

        function setChannels(className, channels) {
            document.querySelectorAll('.' + className).forEach(cb => {
                cb.checked = channels.includes(cb.value);
            });
        }

        function getChannels(className) {
            return Array.from(document.querySelectorAll('.' + className + ':checked')).map(cb => cb.value);
        }

        function renderIntervals() {
            const container = document.getElementById('interval_list');
            container.innerHTML = '';
            currentIntervals.forEach((interval, index) => {
                const tag = document.createElement('div');
                tag.className = 'interval-tag';
                const label = formatInterval(interval);
                tag.innerHTML = `<span>${label}</span><span class="interval-remove" onclick="removeInterval(${index})">×</span>`;
                container.appendChild(tag);
            });
        }

        function formatInterval(minutes) {
            if (minutes >= 1440) {
                const days = Math.floor(minutes / 1440);
                return `${days}d`;
            } else if (minutes >= 60) {
                const hours = Math.floor(minutes / 60);
                return `${hours}h`;
            } else {
                return `${minutes}m`;
            }
        }

        function addInterval() {
            const input = document.getElementById('new_interval');
            const minutes = parseInt(input.value);
            if (minutes > 0) {
                currentIntervals.push(minutes);
                currentIntervals.sort((a, b) => b - a);
                renderIntervals();
                input.value = '';
            }
        }

        function removeInterval(index) {
            currentIntervals.splice(index, 1);
            renderIntervals();
        }

        async function saveConfig() {
            const config = {
                clinic_name: document.getElementById('clinic_name').value,
                clinic_phone: document.getElementById('clinic_phone').value,
                confirmation_enabled: document.getElementById('confirmation_enabled').checked,
                confirmation_sms_template: document.getElementById('confirmation_sms_template').value,
                confirmation_email_template: document.getElementById('confirmation_email_template').value,
                confirmation_channels: getChannels('confirmation_channels'),
                reminders_enabled: document.getElementById('reminders_enabled').checked,
                reminder_intervals: currentIntervals,
                reminder_sms_template: document.getElementById('reminder_sms_template').value,
                reminder_email_template: document.getElementById('reminder_email_template').value,
                reminder_channels: getChannels('reminder_channels'),
                noshow_enabled: document.getElementById('noshow_enabled').checked,
                noshow_sms_template: document.getElementById('noshow_sms_template').value,
                noshow_email_template: document.getElementById('noshow_email_template').value,
                noshow_channels: getChannels('noshow_channels'),
                cancellation_enabled: document.getElementById('cancellation_enabled').checked,
                cancellation_sms_template: document.getElementById('cancellation_sms_template').value,
                cancellation_email_template: document.getElementById('cancellation_email_template').value,
                cancellation_channels: getChannels('cancellation_channels'),
            };

            const response = await fetch('/plugin-io/api/custom_reminders/admin/config', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(config)
            });

            if (response.ok) {
                alert('Configuration saved successfully!');
            } else {
                alert('Failed to save configuration');
            }
        }

        async function loadHistory() {
            const response = await fetch('/plugin-io/api/custom_reminders/admin/history');
            const history = await response.json();

            const tbody = document.getElementById('history_body');
            tbody.innerHTML = '';

            history.forEach(entry => {
                const row = tbody.insertRow();
                row.insertCell(0).textContent = new Date(entry.timestamp).toLocaleString();
                row.insertCell(1).textContent = entry.patient_id;
                row.insertCell(2).textContent = entry.campaign_type;
                row.insertCell(3).textContent = entry.channel.toUpperCase();
                const statusCell = row.insertCell(4);
                const badge = document.createElement('span');
                const statusClass = entry.dry_run ? 'dry-run' : entry.status;
                badge.className = 'status-badge status-' + statusClass;
                badge.textContent = entry.dry_run ? 'test' : entry.status;
                statusCell.appendChild(badge);
            });
        }

        async function checkTestMode() {
            const response = await fetch('/plugin-io/api/custom_reminders/admin/status');
            const data = await response.json();
            if (data.dry_run) {
                document.getElementById('test_mode_banner').style.display = 'block';
            }
        }

        checkTestMode();
        loadConfig();
    </script>
</body>
</html>
        """
        return [HTMLResponse(html)]

    @api.get("/admin/status")
    def get_status(self) -> list[Response | Effect]:
        """Check if plugin is running in dry-run (test) mode."""
        sms_ok = all(self.secrets.get(k) for k in ("twilio-account-sid", "twilio-auth-token", "twilio-phone-number"))
        email_ok = all(self.secrets.get(k) for k in ("sendgrid-api-key", "sendgrid-from-email"))
        return [JSONResponse({"dry_run": not sms_ok or not email_ok}, status_code=HTTPStatus.OK)]

    @api.get("/admin/config")
    def get_config(self) -> list[Response | Effect]:
        """Get current campaign configuration."""
        config = load_config()
        return [JSONResponse(config.to_dict(), status_code=HTTPStatus.OK)]

    @api.post("/admin/config")
    def save_config_endpoint(self) -> list[Response | Effect]:
        """Save campaign configuration."""
        data = self.request.json()
        try:
            config = CampaignConfig.from_dict(data)
        except TypeError as e:
            return [JSONResponse({"error": f"Invalid configuration: {e}"}, status_code=HTTPStatus.BAD_REQUEST)]
        save_config(config)
        return [JSONResponse({"status": "ok"}, status_code=HTTPStatus.OK)]

    @api.get("/admin/history")
    def get_global_history(self) -> list[Response | Effect]:
        """Get global message history."""
        cache = get_cache()
        history_json = cache.get("cr:global_log", default="[]")
        history = json.loads(history_json)

        # Reverse to show newest first
        history.reverse()

        return [JSONResponse(history, status_code=HTTPStatus.OK)]

    @api.get("/patient/<patient_id>/history")
    def get_patient_history(self) -> list[Response | Effect]:
        """Get patient-specific message history."""
        patient_id = self.request.path_params["patient_id"]
        cache = get_cache()
        history_json = cache.get(f"cr:log:{patient_id}", default="[]")
        history = json.loads(history_json)

        # Reverse to show newest first
        history.reverse()

        return [JSONResponse(history, status_code=HTTPStatus.OK)]

    @api.get("/patient-view")
    def get_patient_view_page(self) -> list[Response | Effect]:
        """Serve patient message history page."""
        html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Patient Message History</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            padding: 24px;
        }
        h2 {
            margin-top: 0;
        }
        .history-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        .history-table th {
            background: #f5f5f5;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            border-bottom: 2px solid #e0e0e0;
        }
        .history-table td {
            padding: 12px;
            border-bottom: 1px solid #e0e0e0;
        }
        .status-badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 500;
        }
        .status-delivered {
            background: #e8f5e9;
            color: #2e7d32;
        }
        .status-failed {
            background: #ffebee;
            color: #c62828;
        }
        .status-dry-run {
            background: #fff3e0;
            color: #e65100;
        }
        .empty-state {
            text-align: center;
            padding: 40px;
            color: #757575;
        }
    </style>
</head>
<body>
    <div class="container">
        <h2>Patient Message History</h2>
        <div id="content">
            <div class="empty-state">Loading...</div>
        </div>
    </div>

    <script>
        async function loadHistory() {
            try {
                // Get patient ID from URL parameter
                const urlParams = new URLSearchParams(window.location.search);
                const patientId = urlParams.get('patient_id');

                if (!patientId) {
                    document.getElementById('content').innerHTML = '<div class="empty-state">No patient ID provided</div>';
                    return;
                }

                const response = await fetch('/plugin-io/api/custom_reminders/patient/' + patientId + '/history', {cache: 'no-store'});

                if (!response.ok) {
                    document.getElementById('content').innerHTML = '<div class="empty-state">Error: ' + response.status + ' ' + response.statusText + '</div>';
                    return;
                }

                const history = await response.json();

                if (history.length === 0) {
                    document.getElementById('content').innerHTML = '<div class="empty-state">No messages sent to this patient yet</div>';
                    return;
                }

                const table = document.createElement('table');
                table.className = 'history-table';
                const thead = table.createTHead();
                const headerRow = thead.insertRow();
                ['Date', 'Campaign', 'Channel', 'Status'].forEach(text => {
                    const th = document.createElement('th');
                    th.textContent = text;
                    headerRow.appendChild(th);
                });

                const tbody = table.createTBody();
                history.forEach(entry => {
                    const row = tbody.insertRow();
                    row.insertCell(0).textContent = new Date(entry.timestamp).toLocaleString();
                    row.insertCell(1).textContent = entry.campaign_type;
                    row.insertCell(2).textContent = entry.channel.toUpperCase();
                    const statusCell = row.insertCell(3);
                    const badge = document.createElement('span');
                    const statusClass = entry.dry_run ? 'dry-run' : entry.status;
                    badge.className = 'status-badge status-' + statusClass;
                    badge.textContent = entry.dry_run ? 'test' : entry.status;
                    statusCell.appendChild(badge);
                });

                const content = document.getElementById('content');
                content.innerHTML = '';
                content.appendChild(table);
            } catch (err) {
                document.getElementById('content').innerHTML = '<div class="empty-state">Error: ' + err.message + '</div>';
            }
        }

        loadHistory();
    </script>
</body>
</html>
        """
        return [HTMLResponse(html)]
