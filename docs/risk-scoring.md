# Light Explainable Risk Scoring Framework
**MENTAURA — Secure, Case-Aware Support Intelligence Platform (SIH26094)**

---

## 1. Purpose
The Light Risk Scoring system provides an automated, transparent, and explainable prioritization aid for psychological counsellors and district/state administrators. It translates victim-reported well-being states, situational factors, and requested support needs into an auditable risk indicator (`low`, `medium`, `high`) without relying on black-box neural networks or proprietary AI models.

---

## 2. Scoring Rules & Formula

The scoring system calculates an integer score starting at `0` based on deterministic rules:

### A. Well-Being State
- **Very Unsafe / Critical**: `+3`
- **Unsafe / Distressed**: `+2`
- **Neutral / Uneasy / Struggling**: `+1`
- **Safe / Very Safe / Steady**: `+0`

### B. Affecting Factors
- **Self-Harm / Suicidal Thoughts / Severe Crisis**: `+3`
- **Threats / Violence / Stalking / Intimidation / Abuse**: `+2`
- **Housing Insecurity / Financial Distress / Family Conflict**: `+1`

### C. Support Needs
- **Emergency Protection / Police Protection / Emergency Medical / Shelter**: `+2`
- **Legal Aid / Psychological Counselling / Interim Compensation / Rehabilitation**: `+1`

### D. Private Text Note Keywords (Capped at `+3`)
- `+1` per distinct matched keyword from safety keyword list (`threat`, `hurt myself`, `kill`, `suicide`, `police`, `court`, `shelter`, `emergency`, `danger`, `weapon`, `stalk`, `violence`, `attack`, `fear`, `scared`, `unsafe`).

### E. Risk Level Categorization Thresholds
| Risk Score | Risk Level | Visual Badge | Recommended Official Action |
|---|---|---|---|
| **0 – 2** | `Low` | Emerald Green (`.badge-risk-low`) | Standard scheduled check-in and ongoing support monitoring |
| **3 – 5** | `Medium` | Amber Yellow (`.badge-risk-medium`) | Prioritized review by assigned counsellor within 24 hours |
| **6+** | `High` | Crimson Red (`.badge-risk-high` with pulse) | Urgent escalation to protection officers, DLSA, and district authority |

---

## 3. Storage & Computation Architecture

- **Persistent Model**: Stored directly on the `support_pulses` table via `risk_level` (`VARCHAR(20)`) and `risk_score` (`INTEGER`) columns.
- **On Pulse Submission**: When a victim submits a Support Pulse via `/api/victim/pulse`, `calculate_risk_score(...)` evaluates the payload and persists the results atomically.
- **On Read / Backward Compatibility**: If historical pulses exist without populated risk scores, the serializer computes the score on-the-fly dynamically.
- **Privacy Assurance**: Raw narrative texts and audio notes are **never** logged or serialized into administrative case overviews.

---

## 4. UI Representation

1. **Counsellor Review Workspace (`counsellor-workspace.html`)**:
   - Integrated as a dedicated **Risk Level** column in the Support Pulse Triage Queue.
   - Rendered using accessibility-compliant badges with explicit text and icons (`<i class="fa-solid fa-triangle-exclamation"></i> High`).
2. **Command & Coordination Dashboard (`command-dashboard.html`)**:
   - Integrated into the **Priority Cases & Escalation Queue** table.
   - High-risk cases feature glowing pulse animation to attract immediate administrative attention for inter-agency relief.

---

## 5. Ethical Disclaimers & Governance Limitations

> [!IMPORTANT]
> **Advisory Triage Aid Only**: The risk scoring engine is strictly an operational triage and scheduling aid for official workflow prioritization. It does **not** constitute a clinical psychological diagnosis, psychiatric evaluation, or legal determination of guilt or imminent danger.

1. **Human-in-the-Loop Oversight**: All decisions regarding protective escort allocation, case escalation, and DLSA legal representation require human official confirmation.
2. **No Automated Denial of Aid**: A `low` risk score never denies or delays access to statutory support mechanisms.
3. **Transparent Audit Trail**: The breakdown scores (`wellbeing_score`, `factors_score`, `needs_score`, `text_score`) are explainable and verifiable upon administrative review.

---

## 6. How to Run Automated Tests

Execute the automated test suite using `pytest`:

```bash
# Run Risk Scoring test suite
PYTHONPATH=. ./venv/bin/pytest tests/test_risk_scoring.py -v

# Run entire platform regression suite (74+ tests)
PYTHONPATH=. ./venv/bin/pytest tests/ -v
```
