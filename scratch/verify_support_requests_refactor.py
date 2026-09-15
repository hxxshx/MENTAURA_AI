"""
Verification script for Support Request Restructuring in Counsellor Login.
"""
from backend.app.database import SessionLocal
from backend.app.models.user import User
from backend.app.models.support_request import SupportRequest
from backend.app.routers.counsellor import (
    get_counsellor_support_requests,
    record_counsellor_review_action,
    ReviewActionPayload
)

def run_tests():
    db = SessionLocal()
    try:
        counsellor = db.query(User).filter(User.verified_role == 'counsellor').first()
        assert counsellor is not None, "Counsellor user not found"
        print(f"[1] Verified Counsellor Found: {counsellor.full_name} ({counsellor.email})")

        # Test 1: Fetch all active support requests
        all_res = get_counsellor_support_requests(official=counsellor, db=db)
        print(f"[2] All Support Requests: Total Active={all_res['total_count']}, Clinical={all_res['clinical_count']}, Statutory={all_res['statutory_count']}, Inactive={all_res['inactive_count']}")
        assert all_res['total_count'] == all_res['clinical_count'] + all_res['statutory_count'], "Total active count mismatch"
        assert all_res['clinical_count'] > 0, "No clinical requests found"
        assert all_res['statutory_count'] > 0, "No statutory requests found"

        # Test 2: Filter by domain = 'clinical'
        clinical_res = get_counsellor_support_requests(domain='clinical', official=counsellor, db=db)
        print(f"[3] Filtered Clinical Requests Count: {clinical_res['filtered_count']}")
        assert clinical_res['filtered_count'] == all_res['clinical_count'], "Clinical filter count mismatch"
        for item in clinical_res['support_requests'][:5]:
            assert item['domain'] == 'clinical', f"Expected clinical domain, got {item['domain']}"
            assert item['action_mode'] == 'clinical_care'
            print(f"    - [Clinical] {item['masked_requester']}: {item['category_label']} | Target: {item['target_agency']}")

        # Test 3: Filter by domain = 'statutory'
        statutory_res = get_counsellor_support_requests(domain='statutory', official=counsellor, db=db)
        print(f"[4] Filtered Statutory Requests Count: {statutory_res['filtered_count']}")
        assert statutory_res['filtered_count'] == all_res['statutory_count'], "Statutory filter count mismatch"
        for item in statutory_res['support_requests'][:5]:
            assert item['domain'] == 'statutory', f"Expected statutory domain, got {item['domain']}"
            assert item['action_mode'] == 'statutory_referral'
            print(f"    - [Statutory] {item['masked_requester']}: {item['category_label']} | Target: {item['target_agency']}")

        # Test 4: Action - Schedule Clinical Session
        clinical_item = clinical_res['support_requests'][0]
        schedule_payload = ReviewActionPayload(
            target_type="support_request",
            target_id=clinical_item['id'],
            action_type="schedule_session",
            status="scheduled",
            appointment_date="2026-09-16T10:30:00Z",
            notes="Format: TELEPHONIC | Clinical Assessment: Initial trauma stabilization and safety planning."
        )
        act_res1 = record_counsellor_review_action(payload=schedule_payload, official=counsellor, db=db)
        assert act_res1['success'] is True, "Clinical scheduling action failed"
        
        # Verify in DB
        updated_req1 = db.query(SupportRequest).filter(SupportRequest.id == clinical_item['id']).first()
        assert updated_req1.status == "scheduled", f"Status not updated to scheduled, got {updated_req1.status}"
        assert "scheduled with" in updated_req1.next_step
        print(f"[5] Successfully Scheduled Clinical Session for {clinical_item['id']}: Next Step='{updated_req1.next_step}'")

        # Test 5: Action - Forward Cross-Agency Statutory Referral
        statutory_item = statutory_res['support_requests'][0]
        referral_payload = ReviewActionPayload(
            target_type="support_request",
            target_id=statutory_item['id'],
            action_type="refer_to_agency",
            status="referred",
            target_agency="DLSA Legal Aid Cell",
            notes="Urgency: HIGH DISTRESS | Clinical Reason: Victim reports extreme trial anxiety and unrepresented witness summons."
        )
        act_res2 = record_counsellor_review_action(payload=referral_payload, official=counsellor, db=db)
        assert act_res2['success'] is True, "Statutory referral action failed"

        # Verify in DB
        updated_req2 = db.query(SupportRequest).filter(SupportRequest.id == statutory_item['id']).first()
        assert updated_req2.status == "referred", f"Status not updated to referred, got {updated_req2.status}"
        assert updated_req2.assigned_role == "DLSA Legal Aid Cell"
        assert "DLSA Legal Aid Cell" in updated_req2.next_step
        print(f"[6] Successfully Forwarded Statutory Referral for {statutory_item['id']}: Assigned Role='{updated_req2.assigned_role}', Next Step='{updated_req2.next_step}'")

        print("\nALL BACKEND VERIFICATION TESTS PASSED SUCCESSFULLY!")
    finally:
        db.close()

if __name__ == '__main__':
    run_tests()
