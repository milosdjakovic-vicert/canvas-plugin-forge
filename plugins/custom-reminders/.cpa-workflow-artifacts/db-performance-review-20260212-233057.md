# Database Performance Review: custom-reminders

**Generated:** 2026-02-12 23:30:57
**Reviewer:** Claude Code (CPA)

## Summary

| Category | Status | Issues |
|----------|--------|--------|
| N+1 Query Patterns | ⚠️ 1 issue | `Patient.objects.get()` inside appointment loop |
| select_related Usage | ⚠️ 2 issues | Missing on scheduler filter + event handler get |
| prefetch_related Usage | ✅ Pass | `telecom.all()` called once per patient, not in bulk loop |
| Query Bounds | ✅ Pass | 7-day window is a natural bound |

## Detailed Findings

### N+1 Query Patterns

**Finding: `Patient.objects.get()` inside loop** (MEDIUM)
- Location: `reminder_scheduler.py:62`
- The scheduler iterates over all appointments in a 7-day window (line 40). For each appointment needing a reminder, it calls `Patient.objects.get(id=appointment.patient.id)` (line 62).
- This triggers 2 extra queries per reminder: one for `appointment.patient` (FK), one for `Patient.objects.get()`.
- The `Patient.objects.get()` is redundant — `appointment.patient` already returns the Patient if the FK is prefetched.
- Worst case: 3 intervals x N appointments = 3N extra queries per cron run.

### select_related Opportunities

**Finding 1: Scheduler appointment query** (MEDIUM)
- Location: `reminder_scheduler.py:36`
- `Appointment.objects.filter(start_time__gte=now, start_time__lte=end_window)` — no `select_related`
- Downstream access: `appointment.patient.id` (line 62), then `appointment.provider.first_name/last_name` and `appointment.location.full_name` via `templates.py:45,50`
- Each appointment triggers 3 extra queries (patient, provider, location)
- Fix: `.select_related('patient', 'provider', 'location')`

**Finding 2: Event handler appointment get** (LOW)
- Location: `event_handler.py:52`
- `Appointment.objects.get(id=appointment_id)` — no `select_related`
- Downstream: `templates.py:45,50` accesses `appointment.provider` and `appointment.location`
- Only 1 appointment per event, so impact is 2 extra queries per event (not a loop)
- Fix: `.select_related('provider', 'location')`

### prefetch_related Opportunities

**No issues found.**
- `patient.telecom.all()` in `messaging.py:129` is called once per patient per send operation, not inside a bulk patient loop. Prefetching would require restructuring the call chain and the gain is marginal.

### Unbounded Queries

**No issues found.**
- `Appointment.objects.filter(start_time__gte=now, start_time__lte=end_window)` has a 7-day natural bound — unlikely to return thousands of results for a single clinic.

## Recommendations

| Priority | Issue | Location | Recommendation |
|----------|-------|----------|----------------|
| MEDIUM | N+1 + missing select_related | `reminder_scheduler.py:36,62` | Add `.select_related('patient', 'provider', 'location')` to filter query, replace `Patient.objects.get(id=appointment.patient.id)` with `appointment.patient` |
| LOW | Missing select_related | `event_handler.py:52` | Add `.select_related('provider', 'location')` to appointment get |

## Verdict

**⚠️ ISSUES FOUND** — 2 issues require attention (1 MEDIUM, 1 LOW)
