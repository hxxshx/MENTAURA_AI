# MENTAURA — Support Pulse Triage Queue Sync Documentation

## 1. Issue Summary
When a victim submitted a new Support Pulse via `checkin.html`, the pulse was successfully saved to the database, but testing in dual tabs within the same browser session caused cookie overwrites between the victim and counsellor roles. Furthermore, the frontend lacked auto-polling, relying entirely on a static single page load without cache-invalidation headers, and backend queries strictly expected specific review statuses.

## 2. Fix Summary
- **Backend Queries (`backend/app/routers/counsellor.py`)**: Updated `get_counsellor_overview` and `get_triage_queue` to use SQLAlchemy `or_` conditions and an `outerjoin` on `User`, ensuring all eligible pulses (whether with `human_review_status` as `pending`, `new`, `in_review`, `escalated`, or `NULL`) are queried with fallback user relationship resolution.
- **Frontend Real-time Sync & Cache Busting (`js/counsellor.js` & `counsellor-workspace.html`)**: Added `cache: 'no-store'` and `Cache-Control: 'no-cache'` to all workspace API calls, enabled automated background polling (every 6 seconds), and added a dedicated manual **"Refresh Queue"** button with a live sync indicator.

## 3. Test Summary
- An automated self-test `test_new_pulse_appears_in_counsellor_triage_queue` was added to `tests/test_counsellor_workspace.py`.
- It authenticates as a victim, submits a live Support Pulse, authenticates as a counsellor, queries `/api/counsellor/triage-queue`, and asserts that the new pulse is immediately present with masked privacy identifiers, correct processing mode, and pending status.
- **Run command**: `PYTHONPATH=. ./venv/bin/pytest tests/test_counsellor_workspace.py -v`

## 4. Demo Guidance
- **Dual-Window Setup**: Keep the Counsellor Review Workspace (`counsellor-workspace.html`) open in your main browser window logged in as `counsellor@mentaura.example`.
- **Victim Incognito Window**: Open an Incognito / Private browser window, log in as `victim@mentaura.example`, and complete a Support Pulse check-in on `checkin.html`.
- **Live Sync Verification**: Switch back to the Counsellor window; the new pulse will appear automatically within 6 seconds at the top of the queue or immediately upon clicking **Refresh Queue**.
- **Privacy & Safety**: Notice that the victim's name is masked (e.g. `[V****m] (A****a S.)`) and sensitive long text/audio are strictly governed behind authorized human-review actions.
