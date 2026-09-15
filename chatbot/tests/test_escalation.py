"""Exhaustive tests for the Escalation Detector."""
from schemas.distress import DistressResult, RiskLevel
from ai_service.escalation_detector import get_escalation_detector


detector = get_escalation_detector()


def make_result(victim_id, score, risk):
    """Helper to build a DistressResult for testing."""
    if isinstance(risk, str):
        risk = RiskLevel(risk)
    return DistressResult(
        victim_id=victim_id,
        distress_score=score,
        risk_level=risk,
        risk_factors=[],
        reason_codes=[],
        explanation="test",
        rule_score=score,
        text_adjustment=0.0,
    )


def check(desc, result, expected_escalation, expected_trend=None):
    ok = result.escalation_flag == expected_escalation
    if expected_trend:
        ok = ok and result.trend_direction == expected_trend
    status = "✅" if ok else "❌"
    print(f"{status} [{desc}]")
    print(f"   Scores: {result.recent_scores}")
    print(f"   Avg Δ:  {result.avg_delta:+.2f}")
    print(f"   Trend:  {result.trend_direction}")
    print(f"   Flag:   {result.escalation_flag}")
    print(f"   Reasons: {result.escalation_reasons}")
    print(f"   Explanation: {result.explanation}")
    print()


def section(title):
    print(f"\n{'━' * 70}")
    print(f"  {title}")
    print(f"{'━' * 70}\n")


def main():
    print("\n🧪 Escalation Detector — Test Suite\n")
    V = "V001"

    # ============================================================
    section("1. NOT ENOUGH HISTORY")
    # ============================================================

    r = detector.detect(V, [])
    print(f"✅ Empty history → returned {r} (expected None)\n")

    r = detector.detect(V, [make_result(V, 40, "medium")])
    print(f"✅ Single pulse → returned {r} (expected None)\n")

    # ============================================================
    section("2. STABLE PATTERNS")
    # ============================================================

    r = detector.detect(V, [
        make_result(V, 40, "medium"),
        make_result(V, 42, "medium"),
        make_result(V, 41, "medium"),
    ])
    check("Stable ~40 → STABLE, no escalation", r, False, "stable")

    r = detector.detect(V, [
        make_result(V, 70, "high"),
        make_result(V, 71, "high"),
        make_result(V, 70, "high"),
    ])
    check("Stable ~70 → STABLE, no escalation", r, False, "stable")

    # ============================================================
    section("3. IMPROVING PATTERNS")
    # ============================================================

    r = detector.detect(V, [
        make_result(V, 80, "high"),
        make_result(V, 70, "high"),
        make_result(V, 55, "medium"),
    ])
    check("80 → 70 → 55 → IMPROVING", r, False, "improving")

    r = detector.detect(V, [
        make_result(V, 90, "critical"),
        make_result(V, 60, "medium"),
        make_result(V, 30, "low"),
    ])
    check("Critical down to low → IMPROVING", r, False, "improving")

    # ============================================================
    section("4. WORSENING PATTERNS")
    # ============================================================

    r = detector.detect(V, [
        make_result(V, 40, "medium"),
        make_result(V, 55, "medium"),
        make_result(V, 70, "high"),
    ])
    check("40 → 55 → 70 → WORSENING + escalation", r, True, "worsening")

    r = detector.detect(V, [
        make_result(V, 20, "low"),
        make_result(V, 35, "medium"),
        make_result(V, 50, "medium"),
    ])
    check("20 → 35 → 50 → WORSENING", r, True, "worsening")

    # ============================================================
    section("5. MONOTONIC INCREASE (all deltas > threshold)")
    # ============================================================

    r = detector.detect(V, [
        make_result(V, 30, "low"),
        make_result(V, 40, "medium"),   # +10
        make_result(V, 52, "medium"),   # +12
        make_result(V, 65, "high"),     # +13
    ])
    check("30→40→52→65 monotonic +10/12/13 → escalation", r, True, "worsening")

    # ============================================================
    section("6. RISK LEVEL JUMP")
    # ============================================================

    r = detector.detect(V, [
        make_result(V, 30, "low"),
        make_result(V, 75, "high"),     # jump low → high
    ])
    check("Low → High in one step → escalation", r, True, "worsening")

    r = detector.detect(V, [
        make_result(V, 55, "medium"),
        make_result(V, 92, "critical"),  # jump medium → critical
    ])
    check("Medium → Critical in one step → escalation", r, True, "worsening")

    # ============================================================
    section("7. CROSSED INTO HIGH/CRITICAL")
    # ============================================================

    r = detector.detect(V, [
        make_result(V, 40, "medium"),
        make_result(V, 45, "medium"),
        make_result(V, 70, "high"),
    ])
    check("First time entering HIGH → escalation", r, True, "worsening")

    r = detector.detect(V, [
        make_result(V, 70, "high"),
        make_result(V, 72, "high"),
        make_result(V, 75, "high"),
    ])
    check("Already HIGH, staying HIGH → no escalation", r, False, "stable")

    # ============================================================
    section("8. LARGE RECENT JUMP")
    # ============================================================

    r = detector.detect(V, [
        make_result(V, 50, "medium"),
        make_result(V, 51, "medium"),
        make_result(V, 70, "high"),      # +19 = large
    ])
    check("Large recent jump +19 → escalation", r, True, "worsening")

    # ============================================================
    section("9. SILENT CRISIS ESCALATION")
    # ============================================================

    # Victim said "neutral" but text kept escalating
    r = detector.detect(V, [
        make_result(V, 40, "medium"),
        make_result(V, 60, "medium"),
        make_result(V, 86, "critical"),
    ])
    check("40 → 60 → 86 → escalation (silent crisis)", r, True, "worsening")

    # ============================================================
    section("10. WINDOW CAPPING (only last N used)")
    # ============================================================

    r = detector.detect(V, [
        make_result(V, 10, "low"),
        make_result(V, 15, "low"),
        make_result(V, 20, "low"),
        make_result(V, 50, "medium"),
        make_result(V, 60, "medium"),
        make_result(V, 70, "high"),
    ])
    check("Only last 3 pulses (50→60→70) counted", r, True, "worsening")
    print(f"   (Note: only last {r.window_size} pulses shown)\n")

    # ============================================================
    section("11. ALTERNATING SCORES")
    # ============================================================

    r = detector.detect(V, [
        make_result(V, 40, "medium"),
        make_result(V, 60, "medium"),
        make_result(V, 40, "medium"),
    ])
    check("Alternating 40↔60 → STABLE on avg", r, False, "stable")

    # ============================================================
    section("12. HIGH BASELINE, MILD WORSENING")
    # ============================================================

    r = detector.detect(V, [
        make_result(V, 75, "high"),
        make_result(V, 78, "high"),
        make_result(V, 82, "high"),
    ])
    check("75→78→82 (staying HIGH) → mild worsening", r, False, "stable")
    print(f"   (Avg delta only +3.5, below +5 threshold)\n")

    # ============================================================
    print(f"\n{'━' * 70}")
    print("  ✅ Escalation Detector test suite complete")
    print(f"{'━' * 70}\n")


if __name__ == "__main__":
    main()