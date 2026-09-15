# MENTAURA — State Administrator Command & Coordination Demo Flow

## 1. Purpose
This document provides an end-to-end, repeatable demonstration script for the **State Administrator Command & Coordination Tier** on Mentaura. It showcases cross-district oversight, aggregate support volume monitoring, procedural case distribution, and inter-district priority case escalation without exposing private victim narratives or audio recordings.

## 2. Prerequisites
- **Server Running**: Backend server active on `http://127.0.0.1:8000`.
- **State Admin Account**: `stateadmin@mentaura.example` (Password: `Mentaura@2026`).
- **Verified Role**: `state_administrator` (State-level coordination tier).
- **Supported Browser**: Chrome, Firefox, Edge, or Safari with JavaScript enabled.

## 3. Step-by-Step Demo Script
1. **Open Portal**: Navigate to `http://127.0.0.1:8000/index.html` in your web browser.
2. **Authenticate**: Click **Login** and authenticate using `stateadmin@mentaura.example` / `Mentaura@2026`.
3. **Verify Landing Page**: Observe automatic redirection to `command-dashboard.html` with the active navbar tab highlighted.
4. **Inspect State Jurisdiction**: Point out the header banner: **Maharashtra State Command** with the badge `State Coordination Level`.
5. **Review Overview Cards**: Highlight state-wide totals:
   - **Active Cases**: `~142` active cases across the state.
   - **Active Interventions**: `~68` ongoing protection, legal, and relief actions.
   - **New Support Pulses (7d)**: Live aggregated check-in volume.
   - **Pending Support Requests**: Multi-category requests awaiting coordination.
6. **Demonstrate 6 Support Categories**: Click on individual cards (e.g. *Counselling*, *Legal Aid*, *Protection*) to filter the dashboard by aid category.
7. **Inspect Multi-District Summary**: Scroll to the **District-Wise Summary** table to compare volume across 6 key districts (*Nagpur, Pune, Mumbai Suburban, Thane, Nashik, Chhatrapati Sambhajinagar*), highlighting health indicators (`Normal` vs `High Load`).
8. **Inspect Priority Case Dossier**: In the **Priority Cases Requiring Escalation** table, click **Details** (<i class="fa-solid fa-eye"></i>) on a case (e.g., `MH-NGP-***-08942`). Review the structured milestones and recent aid timeline in the modal.
9. **Execute Case Escalation**: Click **Escalate Priority** inside the modal, choose `Inter-District Coordination Requisition`, type a justification (e.g. *"Coordinating safe inter-district witness transit"*), and click **Submit Escalation Requisition**.
10. **Verify Confirmation**: Confirm the success toast notification and the immutable entry recorded in the backend review log.

## 4. Expected Behaviour
- **State Scoping**: Automatically scales metrics to state level (142 cases vs. district 28 cases).
- **Multi-District Visibility**: Displays all 6 districts with comparative metrics in the summary table.
- **Privacy Enforcement**: All victim personal names (`[V****m] (A****a S.)`) and case numbers (`MH-NGP-***-08942`) remain masked.
- **Escalation Logging**: Submitting an escalation persists a `ReviewAction` record in the database with status `escalated_inter_district`.

## 5. Automated Test Coverage
- Verified by automated tests `test_state_admin_can_access_command_dashboard_and_district_summary` and `test_state_admin_demo_flow_sanity` in `tests/test_command_dashboard.py`.
- Tests cover state login, metric scoping, district summary retrieval, priority case loading, and escalation audit logging.
- **Run Command**: `PYTHONPATH=. ./venv/bin/pytest tests/test_command_dashboard.py -v`

## 6. Known Considerations
- **Mock Aggregation Baselines**: District table and baseline overview metrics include pre-seeded reference distributions for Maharashtra to ensure high-fidelity presentation during evaluation.
- **Role Isolation**: Non-admin roles (Victims and Counsellors) attempting to access `/api/command/*` receive a strict HTTP 403 Forbidden response.
