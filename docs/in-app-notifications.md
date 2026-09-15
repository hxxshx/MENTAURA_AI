# In-App Notifications & Alerts System (TASK 17)

## 1. Purpose
The In-App Notifications & Alerts System provides real-time situational awareness for Psychological Counsellors, Case Officers, and District/State Administrators on Mentaura. It immediately alerts designated officials whenever a high-risk Support Pulse is submitted or when a priority case is escalated, facilitating timely human intervention without exposing victim narratives or audio binaries.

---

## 2. Trigger Conditions
Notifications are automatically dispatched under two core operational workflows:

1. **High-Risk Support Pulse Submission (`high_risk_pulse`)**:
   - **Trigger**: When a victim or witness submits a Support Pulse that scores as `risk_level == "high"` or has `priority_review == True` (e.g. feeling unsafe, physical threats, emergency requests).
   - **Recipients**: Active Counsellors, District Authorities, and State Administrators.
   - **Payload**: Masked identifier (e.g., `[V****3af0]`), pulse ID, risk level, and risk score. No raw notes or audio binaries are ever included.

2. **Case Escalation (`case_escalated`)**:
   - **Trigger**: When an administrator escalates a case via the Command Dashboard (`POST /api/command/escalate-case`).
   - **Recipients**: Assigned officials, Case Officers, District Authorities, and State Administrators.
   - **Payload**: Masked case number (e.g., `case-***-942`), escalation priority level (e.g., `critical`, `urgent`, `inter_district`), and summary reason.

---

## 3. Storage & Retrieval Architecture

### Database Model (`notifications` table):
- `id` (`VARCHAR(36)`): Primary Key (UUID).
- `user_id` (`VARCHAR(36)`): Foreign Key (`users.id`, `ON DELETE CASCADE`).
- `type` (`VARCHAR(50)`): Event type (`high_risk_pulse`, `case_escalated`, `system_alert`).
- `title` (`VARCHAR(150)`): Concise human-readable notification heading.
- `message` (`TEXT`): Privacy-safe alert summary.
- `is_read` (`BOOLEAN`): Read state (default `False`, indexed).
- `created_at` (`DATETIME`): UTC timestamp.
- `meta_data` (`TEXT`): Serialized JSON with non-sensitive identifiers and context.

### API Endpoints (`/api/notifications`):
- `GET /api/notifications`: Returns user-scoped notifications sorted by creation date descending.
- `GET /api/notifications/unread-count`: Returns `{ "unread_count": <int> }`.
- `POST /api/notifications/mark-read`: Marks specified notification IDs or all notifications as read (`{ "mark_all": true }`), returning the updated unread count.

**Role Security**: Access is strictly guarded for official roles (`counsellor`, `case_officer`, `district_authority`, `district_admin`, `state_administrator`, `state_admin`, `national_administrator`). Victims cannot access notification endpoints, and each user only sees their own scoped alerts.

---

## 4. UI Appearance & Interaction

- **Navbar Bell Icon**: Located in the authenticated header of the Counsellor Workspace, Command Dashboard, and Pending Approvals pages.
- **Unread Badge**: A pulsing crimson badge displaying the count of unread alerts (hidden when count is 0).
- **Interactive Dropdown Panel**:
  - Displays recent alerts with type-specific color indicators (red for high-risk pulses, amber for escalations, purple for system).
  - Unread items are visually highlighted with a light purple background tint and indicator dot.
  - "Mark all as read" button instantly clears unread alerts.
  - Clicking an unread notification marks it as read in the backend.
- **Background Polling**: Automatically polls `/api/notifications/unread-count` every 30 seconds for live awareness.
- **Accessibility & Responsiveness**: Keyboard navigable (Enter/Space, Escape), ARIA dialog attributes, and optimized for mobile screens.

---

## 5. Limitations & Future Scope
- **In-App Only**: Real-time delivery is currently confined to the in-app web interface and background polling.
- **Simulated External Channels**: External SMS, WhatsApp, and email alerts are simulated and logged in the backend audit trail; production SMS gateways (e.g. CDAC SMS gateway / Gov SMS) can be integrated via pluggable handlers.
- **WebSocket Upgrade**: Future iterations may incorporate WebSockets/Server-Sent Events (SSE) for sub-second push notifications beyond 30s polling.

---

## 6. How to Run Tests

Execute the automated test suite using pytest:

```bash
# Run notification-specific tests
PYTHONPATH=. ./venv/bin/pytest tests/test_notifications.py -v

# Run the complete test suite (83+ tests)
PYTHONPATH=. ./venv/bin/pytest tests/ -v
```
