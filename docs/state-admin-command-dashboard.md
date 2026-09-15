# MENTAURA — State Administrator Command Dashboard Verification & Flow

## 1. Purpose
The **Command & Coordination Dashboard** (`command-dashboard.html`) provides state-level administrators with aggregate intelligence, multi-district response tracking, and high-level case escalation oversight. It enables state officials to monitor cross-district support velocity without exposing confidential raw victim narratives or audio binaries.

## 2. Account Setup
- **Pre-Configured Account**: `stateadmin@mentaura.example` (or `state_admin@mentaura.example`).
- **Verified Role**: `state_administrator` (or `state_admin`).
- **Account Status**: `active` (verified official).
- **Default Password**: `Mentaura@2026` (stored securely using Argon2id).
- **Database Verification**: Role and status can be inspected in the `users` table via `SELECT email, verified_role, account_status FROM users WHERE requested_category = 'state_administrator';`.

## 3. Login & Navigation Flow
- Navigate to the login portal at `http://127.0.0.1:8000/index.html`.
- Enter the state admin credentials (`stateadmin@mentaura.example` / `Mentaura@2026`).
- Upon successful authentication, the backend automatically resolves the verified role and redirects the user to `command-dashboard.html`.
- In the navigation bar, **"Command Dashboard"** is marked as active with the state administrator chip (`State Director S. Mukherjee`) displayed in the header profile popover.

## 4. Expected State Admin View
- **Jurisdiction Banner**: Displays **Maharashtra State Command** with the tag `State Coordination Level`.
- **State Overview Cards**: Displays state-level aggregate counts (`Active Cases: 142`, `Active Interventions: 68`, `New Pulses: 42+`, `Pending Requests: 115+`).
- **6 Aid Category Breakdown Cards**: Visualizes support distributions across Counselling, Legal Aid, Protection, Medical, Compensation, and Rehabilitation.
- **Procedural Case Stages**: Real-time distribution across FIR Registration, Investigation, Charge Sheet, Court Trial, Support Monitoring, and Rehabilitation.
- **Priority Escalation Queue**: Displays priority cases flagged across districts with masked victim identifiers (`[V****m] (A****a S.)`) and administrative escalation controls.
- **District-Wise Summary Table**: A dedicated comparative table listing multiple districts (`Nagpur`, `Pune`, `Mumbai Suburban`, `Thane`, `Nashik`, `Chhatrapati Sambhajinagar`) with 30-day pulse volume, active cases, and health status pills (`Normal` / `High Load`).

## 5. Test Coverage
- Verified by automated test `test_state_admin_can_access_command_dashboard_and_district_summary` in `tests/test_command_dashboard.py`.
- Tests authenticate as State Admin, verify HTTP 200 on `/api/command/overview` and `/api/command/district-summary`, assert state-level case metrics and multi-district tables, and verify that non-admin roles (Victim, Counsellor) receive `403 Forbidden`.
- **Run Command**: `PYTHONPATH=. ./venv/bin/pytest tests/test_command_dashboard.py -v`
