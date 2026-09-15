"""
Escalation Detector — Module 2
Analyzes a sequence of past distress scores → detects whether the victim's
psychological distress is escalating, improving, or stable.

Uses rule-based trend analysis (v1). Optional ML upgrade for phase-2.
"""

from typing import Optional

from config import get_settings
from schemas.distress import DistressResult, RiskLevel
from schemas.escalation import EscalationResult, TrendDirection


# Risk level ordering for jump detection
RISK_ORDER = {
    "low": 0,
    "medium": 1,
    "high": 2,
    "critical": 3,
}


class EscalationDetector:
    """
    Stateless trend analyzer. Feed it a sequence of DistressResults.
    """

    def __init__(self):
        self.settings = get_settings()

    # ----------------------------------------------------------
    # Detect escalation from a sequence of distress results
    # ----------------------------------------------------------
    def detect(
        self,
        victim_id: str,
        recent_results: list[DistressResult],
    ) -> Optional[EscalationResult]:
        """
        Analyze trend over recent pulses.

        Args:
            victim_id: victim identifier
            recent_results: list of DistressResult, oldest → newest

        Returns:
            EscalationResult if enough history (>= 2 pulses), else None.
        """
        window = self.settings.ESCALATION_WINDOW
        threshold = self.settings.ESCALATION_DELTA

        # Need at least 2 pulses to measure change
        if not recent_results or len(recent_results) < 2:
            return None

        # Use last N pulses (most recent)
        window_results = recent_results[-window:]
        scores = [r.distress_score for r in window_results]
        levels = [r.risk_level for r in window_results]

        # Compute deltas between consecutive scores
        deltas = [scores[i + 1] - scores[i] for i in range(len(scores) - 1)]

        avg_delta = sum(deltas) / len(deltas) if deltas else 0.0

        # ---------------- Trend direction ----------------
        if avg_delta > threshold:
            trend = TrendDirection.WORSENING
        elif avg_delta < -threshold:
            trend = TrendDirection.IMPROVING
        else:
            trend = TrendDirection.STABLE

        # ---------------- Escalation reasons ----------------
        reasons: list[str] = []
        escalation = False

        # Rule 1: Monotonic increase (all deltas > threshold)
        if len(deltas) >= 2 and all(d > threshold for d in deltas):
            escalation = True
            reasons.append("monotonic_increase")

        # Rule 2: Big jump in risk level between any two consecutive pulses
        for i in range(len(levels) - 1):
            curr = RISK_ORDER.get(_level_str(levels[i]), 0)
            nxt = RISK_ORDER.get(_level_str(levels[i + 1]), 0)
            if nxt - curr >= 2:
                escalation = True
                reasons.append(f"risk_jump_{_level_str(levels[i])}_to_{_level_str(levels[i+1])}")
                break

        # Rule 3: Latest reading is HIGH or CRITICAL and was LOW/MEDIUM before
        latest_level = _level_str(levels[-1])
        if latest_level in ("high", "critical"):
            earlier = [_level_str(l) for l in levels[:-1]]
            if any(l in ("low", "medium") for l in earlier):
                escalation = True
                reasons.append(f"crossed_into_{latest_level}")

        # Rule 4: Latest single-step delta is large (>= threshold * 2)
        if deltas and deltas[-1] >= threshold * 2:
            escalation = True
            reasons.append(f"large_recent_jump:+{deltas[-1]:.1f}")

        # ---------------- Explanation ----------------
        explanation = _build_explanation(
            trend, escalation, scores, avg_delta, reasons
        )

        return EscalationResult(
            victim_id=victim_id,
            escalation_flag=escalation,
            trend_direction=trend,
            window_size=len(window_results),
            recent_scores=[round(s, 1) for s in scores],
            avg_delta=round(avg_delta, 2),
            escalation_reasons=reasons,
            explanation=explanation,
        )


# ============================================================
# Helpers
# ============================================================

def _level_str(level) -> str:
    """Normalize RiskLevel enum or str → lowercase string."""
    if isinstance(level, RiskLevel):
        return level.value
    s = str(level).lower()
    if "." in s:
        s = s.split(".")[-1]
    return s


def _build_explanation(
    trend: TrendDirection,
    escalation: bool,
    scores: list[float],
    avg_delta: float,
    reasons: list[str],
) -> str:
    """Build human-readable explanation."""
    scores_str = " → ".join(f"{s:.0f}" for s in scores)

    if trend == TrendDirection.WORSENING:
        base = f"Distress is worsening ({scores_str}). Average increase of {avg_delta:+.1f} points per check-in."
    elif trend == TrendDirection.IMPROVING:
        base = f"Distress is improving ({scores_str}). Average change of {avg_delta:+.1f} points per check-in."
    else:
        base = f"Distress is stable ({scores_str})."

    if escalation:
        base += f" Escalation flagged: {', '.join(reasons)}."

    return base


# Singleton accessor
_detector_instance: Optional[EscalationDetector] = None


def get_escalation_detector() -> EscalationDetector:
    """Return the global EscalationDetector instance."""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = EscalationDetector()
    return _detector_instance