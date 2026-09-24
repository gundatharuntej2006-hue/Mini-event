"""
Unit and Integration Tests for EVENT HQ Code Hunt, Final Code Gate & Secret Agent Systems (Step 11).
Source of Truth: Authoritative Event Documentation (Reconciled in Step 6B & Step 7).

Verifies all 30 mandatory requirements:
1. Fragment 1 can be recorded.
2. Fragment 2 can be recorded.
3. Duplicate fragment recording rejected/idempotent.
4. Final code cannot assemble with only Fragment 1.
5. Final code cannot assemble with only Fragment 2.
6. Final code assembles only with both fragments.
7. Correct final code verifies successfully.
8. Wrong final code fails.
9. Wrong verification does not expose expected code.
10. Verified code cannot be downgraded accidentally.
11. Missing fragment purchase works.
12. Already-owned fragment cannot be purchased.
13. Insufficient wallet balance rejects purchase.
14. Purchase creates wallet ledger entry.
15. Purchased fragment changes status correctly.
16. Round 4 eligibility false without verified code.
17. Round 4 eligibility true after verified code.
18. Valid participant can be assigned.
19. Participant from another team rejected.
20. Duplicate active agent per team rejected.
21. Agent task creation works.
22. Task submission requires evidence.
23. Verification changes status to VERIFIED.
24. Rejection changes status to REJECTED.
25. +50 awarded only after verification.
26. Duplicate verification does not award another +50.
27. Agent identity hidden from normal team endpoint.
28. Agent identity visible only to authorized organizer/marshal.
29. Evidence is linked to correct task.
30. Audit records created.
Plus API endpoints and RBAC security tests.
"""

import pytest
from fastapi.testclient import TestClient

from app.models.team import Team, TeamStatus
from app.models.participant import Participant, ParticipantRole
from app.models.user import User, UserRole
from app.models.code_hunt import FinalCodeRecord, FragmentStatus
from app.models.agent import SecretAgentDossier, SecretAgentTask, AgentDossierStatus, AgentTaskStatus
from app.models.wallet import TeamWallet, WalletTransaction, TransactionType
from app.models.progression import AuditLog
from app.services.code_hunt_service import (
    record_fragment_1,
    record_fragment_2,
    assemble_final_code,
    verify_final_code,
    recover_missing_fragment,
    can_enter_round4,
    verify_round4_gate,
    get_code_hunt_status,
    FragmentAlreadyRecordedError,
    FinalCodeVerificationError,
    MissingFragmentPurchaseError,
    Round4GateError,
)
from app.services.secret_agent_service import (
    assign_secret_agent,
    create_agent_task,
    submit_agent_task,
    verify_agent_task,
    reject_agent_task,
    get_secret_agent_dossier,
    get_team_agent_tasks,
    AgentAssignmentError,
    AgentTaskError,
    AgentEvidenceError,
)
from app.services.wallet import get_or_create_wallet, InsufficientFundsError


# ==============================================================================
# TEST FIXTURES
# ==============================================================================
@pytest.fixture
def sample_squads(db_session):
    """Creates two test squads with 5 participants each and initialized wallets."""
    squads = []
    for t_idx in range(1, 3):
        team = Team(
            id=f"team-test-{t_idx}",
            team_number=t_idx,
            name=f"Cyber Squad {t_idx}",
            status=TeamStatus.ACTIVE,
            current_round=3,
        )
        db_session.add(team)
        db_session.flush()

        for p_idx in range(1, 6):
            part = Participant(
                id=f"part-t{t_idx}-{p_idx}",
                team_id=team.id,
                name=f"Agent {t_idx}-{p_idx}",
                email=f"agent_{t_idx}_{p_idx}@bmsit.in",
                usn=f"1BY21CS{t_idx:02d}{p_idx:02d}",
                phone=f"98765432{t_idx}{p_idx}",
                role=ParticipantRole.LEADER if p_idx == 1 else ParticipantRole.MEMBER,
                checked_in=True,
            )
            db_session.add(part)

        get_or_create_wallet(db_session, team.id, created_by="test_admin")
        squads.append(team)

    db_session.commit()
    for s in squads:
        db_session.refresh(s)
    return squads


# ==============================================================================
# 1. CODE HUNT UNIT TESTS
# ==============================================================================
def test_fragment_1_recording(db_session, sample_squads):
    """Requirement 1: Fragment 1 can be recorded."""
    team = sample_squads[0]
    rec = record_fragment_1(db_session, team.id, "ALPHA-1234", actor="organizer@bmsit.in")
    assert rec.fragment_1_status == FragmentStatus.RECOVERED
    assert rec.fragment_1_value == "ALPHA-1234"
    assert rec.fragment_1_discovered_at is not None
    assert rec.final_code_verified is False


def test_fragment_2_recording(db_session, sample_squads):
    """Requirement 2: Fragment 2 can be recorded."""
    team = sample_squads[0]
    rec = record_fragment_2(db_session, team.id, "BRAVO-5678", actor="organizer@bmsit.in")
    assert rec.fragment_2_status == FragmentStatus.RECOVERED
    assert rec.fragment_2_value == "BRAVO-5678"
    assert rec.fragment_2_discovered_at is not None


def test_duplicate_fragment_recording(db_session, sample_squads):
    """Requirement 3: Duplicate fragment recording is idempotent or rejected if different without overwrite."""
    team = sample_squads[0]
    rec1 = record_fragment_1(db_session, team.id, "ALPHA-1234", actor="organizer@bmsit.in")
    # Idempotent re-submission
    rec2 = record_fragment_1(db_session, team.id, "ALPHA-1234", actor="organizer@bmsit.in")
    assert rec1.id == rec2.id

    # Modification without overwrite flag raises FragmentAlreadyRecordedError
    with pytest.raises(FragmentAlreadyRecordedError):
        record_fragment_1(db_session, team.id, "NEW-ALPHA-9999", actor="organizer@bmsit.in", overwrite=False)

    # Explicit overwrite allowed
    rec3 = record_fragment_1(db_session, team.id, "NEW-ALPHA-9999", actor="organizer@bmsit.in", overwrite=True)
    assert rec3.fragment_1_value == "NEW-ALPHA-9999"


def test_final_code_cannot_assemble_with_only_fragment_1(db_session, sample_squads):
    """Requirement 4: Final code cannot assemble with only Fragment 1."""
    team = sample_squads[0]
    record_fragment_1(db_session, team.id, "ALPHA-1234", actor="organizer@bmsit.in")
    assembled = assemble_final_code(db_session, team.id)
    assert assembled is None


def test_final_code_cannot_assemble_with_only_fragment_2(db_session, sample_squads):
    """Requirement 5: Final code cannot assemble with only Fragment 2."""
    team = sample_squads[0]
    record_fragment_2(db_session, team.id, "BRAVO-5678", actor="organizer@bmsit.in")
    assembled = assemble_final_code(db_session, team.id)
    assert assembled is None


def test_final_code_assembles_with_both_fragments(db_session, sample_squads):
    """Requirement 6: Final code assembles only when both Fragment 1 and Fragment 2 exist."""
    team = sample_squads[0]
    record_fragment_1(db_session, team.id, "ALPHA-1234", actor="organizer@bmsit.in")
    record_fragment_2(db_session, team.id, "BRAVO-5678", actor="organizer@bmsit.in")
    assembled = assemble_final_code(db_session, team.id)
    assert assembled == "ALPHA-1234BRAVO-5678"


def test_correct_final_code_verifies_successfully(db_session, sample_squads):
    """Requirement 7: Correct final code verifies successfully and updates state."""
    team = sample_squads[0]
    record_fragment_1(db_session, team.id, "ALPHA-1234", actor="organizer@bmsit.in")
    record_fragment_2(db_session, team.id, "BRAVO-5678", actor="organizer@bmsit.in")

    result = verify_final_code(db_session, team.id, "ALPHA-1234BRAVO-5678", actor="lead_organizer@bmsit.in")
    assert result is True

    record = db_session.query(FinalCodeRecord).filter(FinalCodeRecord.team_id == team.id).first()
    assert record.final_code_verified is True
    assert record.verified_by == "lead_organizer@bmsit.in"
    assert record.verified_at is not None


def test_wrong_final_code_fails(db_session, sample_squads):
    """Requirement 8: Wrong final code fails verification."""
    team = sample_squads[0]
    record_fragment_1(db_session, team.id, "ALPHA-1234", actor="organizer@bmsit.in")
    record_fragment_2(db_session, team.id, "BRAVO-5678", actor="organizer@bmsit.in")

    with pytest.raises(FinalCodeVerificationError):
        verify_final_code(db_session, team.id, "WRONG-CODE-9999", actor="lead_organizer@bmsit.in")

    record = db_session.query(FinalCodeRecord).filter(FinalCodeRecord.team_id == team.id).first()
    assert record.final_code_verified is False


def test_wrong_verification_does_not_expose_expected_code(db_session, sample_squads):
    """Requirement 9: Verification failure message does not leak expected secret code."""
    team = sample_squads[0]
    record_fragment_1(db_session, team.id, "SECRET_PART_A", actor="organizer@bmsit.in")
    record_fragment_2(db_session, team.id, "SECRET_PART_B", actor="organizer@bmsit.in")

    with pytest.raises(FinalCodeVerificationError) as exc_info:
        verify_final_code(db_session, team.id, "INVALID_GUESS", actor="lead_organizer@bmsit.in")

    msg = str(exc_info.value)
    assert "SECRET_PART_A" not in msg
    assert "SECRET_PART_B" not in msg
    assert msg == "Final Code verification failed."


def test_verified_code_cannot_be_downgraded(db_session, sample_squads):
    """Requirement 10: Already-verified code returns True idempotently and cannot be downgraded."""
    team = sample_squads[0]
    record_fragment_1(db_session, team.id, "ALPHA", actor="organizer@bmsit.in")
    record_fragment_2(db_session, team.id, "BETA", actor="organizer@bmsit.in")
    verify_final_code(db_session, team.id, "ALPHABETA", actor="organizer@bmsit.in")

    # Second call returns True
    res = verify_final_code(db_session, team.id, "ANYTHING", actor="organizer@bmsit.in")
    assert res is True
    record = db_session.query(FinalCodeRecord).filter(FinalCodeRecord.team_id == team.id).first()
    assert record.final_code_verified is True


def test_missing_fragment_purchase_works(db_session, sample_squads):
    """Requirement 11: Missing fragment can be purchased with Black Market points."""
    team = sample_squads[0]
    # Team starts with 1000.0 points
    rec = recover_missing_fragment(
        db_session,
        team_id=team.id,
        fragment_number=1,
        price=400.0,
        actor="organizer@bmsit.in",
        recovered_value="PURCHASED-ALPHA",
    )
    assert rec.fragment_1_status == FragmentStatus.PURCHASED
    assert rec.fragment_1_value == "PURCHASED-ALPHA"

    wallet = db_session.query(TeamWallet).filter(TeamWallet.team_id == team.id).first()
    assert wallet.current_balance == 600.0  # 1000 - 400


def test_already_owned_fragment_cannot_be_purchased(db_session, sample_squads):
    """Requirement 12: Cannot purchase a fragment that is already recovered."""
    team = sample_squads[0]
    record_fragment_1(db_session, team.id, "ALREADY-HAVE-THIS", actor="organizer@bmsit.in")

    with pytest.raises(MissingFragmentPurchaseError):
        recover_missing_fragment(db_session, team_id=team.id, fragment_number=1, price=400.0)


def test_insufficient_wallet_balance_rejects_purchase(db_session, sample_squads):
    """Requirement 13: Insufficient wallet balance rejects fragment purchase."""
    team = sample_squads[0]
    # Set wallet balance to 100
    wallet = db_session.query(TeamWallet).filter(TeamWallet.team_id == team.id).first()
    wallet.current_balance = 100.0
    db_session.commit()

    with pytest.raises(InsufficientFundsError):
        recover_missing_fragment(db_session, team_id=team.id, fragment_number=1, price=400.0)


def test_purchase_creates_wallet_ledger_entry(db_session, sample_squads):
    """Requirement 14: Purchase creates immutable wallet ledger transaction."""
    team = sample_squads[0]
    recover_missing_fragment(db_session, team_id=team.id, fragment_number=2, price=400.0, actor="organizer@bmsit.in")

    tx = (
        db_session.query(WalletTransaction)
        .filter(
            WalletTransaction.team_id == team.id,
            WalletTransaction.transaction_type == TransactionType.BLACK_MARKET_PURCHASE,
        )
        .first()
    )
    assert tx is not None
    assert tx.amount == -400.0
    assert tx.balance_after == 600.0


def test_purchased_fragment_status_update(db_session, sample_squads):
    """Requirement 15: Purchased fragment updates status correctly and allows final code verification."""
    team = sample_squads[0]
    record_fragment_1(db_session, team.id, "FRAG1", actor="organizer@bmsit.in")
    recover_missing_fragment(
        db_session,
        team_id=team.id,
        fragment_number=2,
        price=400.0,
        actor="organizer@bmsit.in",
        recovered_value="FRAG2",
    )

    assembled = assemble_final_code(db_session, team.id)
    assert assembled == "FRAG1FRAG2"

    verified = verify_final_code(db_session, team.id, "FRAG1FRAG2", actor="organizer@bmsit.in")
    assert verified is True


def test_round4_eligibility_false_without_verified_code(db_session, sample_squads):
    """Requirement 16: Round 4 eligibility returns False without verified Final Code."""
    team = sample_squads[0]
    record_fragment_1(db_session, team.id, "FRAG1", actor="organizer@bmsit.in")
    record_fragment_2(db_session, team.id, "FRAG2", actor="organizer@bmsit.in")

    assert can_enter_round4(db_session, team.id) is False
    with pytest.raises(Round4GateError):
        verify_round4_gate(db_session, team.id)


def test_round4_eligibility_true_after_verified_code(db_session, sample_squads):
    """Requirement 17: Round 4 eligibility returns True after Final Code verification."""
    team = sample_squads[0]
    record_fragment_1(db_session, team.id, "A", actor="organizer@bmsit.in")
    record_fragment_2(db_session, team.id, "B", actor="organizer@bmsit.in")
    verify_final_code(db_session, team.id, "AB", actor="organizer@bmsit.in")

    assert can_enter_round4(db_session, team.id) is True
    # Does not raise
    verify_round4_gate(db_session, team.id)


# ==============================================================================
# 2. SECRET AGENT UNIT TESTS
# ==============================================================================
def test_valid_participant_can_be_assigned_as_agent(db_session, sample_squads):
    """Requirement 18: Valid participant can be assigned as undercover secret agent."""
    team = sample_squads[0]
    participant = team.members[0]

    dossier = assign_secret_agent(
        db_session,
        team_id=team.id,
        participant_id=participant.id,
        codename="Shadow Viper",
        actor="organizer@bmsit.in",
    )
    assert dossier.status == AgentDossierStatus.ACTIVE
    assert dossier.codename == "Shadow Viper"
    assert dossier.participant_id == participant.id
    assert dossier.team_id == team.id


def test_participant_from_another_team_rejected(db_session, sample_squads):
    """Requirement 19: Participant from a different team is rejected."""
    team_1 = sample_squads[0]
    team_2 = sample_squads[1]
    part_from_team_2 = team_2.members[0]

    with pytest.raises(AgentAssignmentError):
        assign_secret_agent(
            db_session,
            team_id=team_1.id,
            participant_id=part_from_team_2.id,
            codename="Infiltrator",
            actor="organizer@bmsit.in",
        )


def test_duplicate_active_agent_per_team_rejected(db_session, sample_squads):
    """Requirement 20: Duplicate active agent per team is rejected."""
    team = sample_squads[0]
    part_1 = team.members[0]
    part_2 = team.members[1]

    assign_secret_agent(db_session, team_id=team.id, participant_id=part_1.id, codename="Agent 1")

    with pytest.raises(AgentAssignmentError):
        assign_secret_agent(db_session, team_id=team.id, participant_id=part_2.id, codename="Agent 2")


def test_agent_task_creation_works(db_session, sample_squads):
    """Requirement 21: Agent task creation works."""
    team = sample_squads[0]
    part = team.members[0]
    assign_secret_agent(db_session, team_id=team.id, participant_id=part.id, codename="Ghost")

    task = create_agent_task(
        db_session,
        team_id=team.id,
        task_description="Place decoy memo in briefing room",
        reward_points=50.0,
        actor="organizer@bmsit.in",
    )
    assert task.status == AgentTaskStatus.ASSIGNED
    assert task.task_description == "Place decoy memo in briefing room"
    assert task.reward_points == 50.0


def test_task_submission_requires_evidence(db_session, sample_squads):
    """Requirement 22: Task submission requires non-empty evidence."""
    team = sample_squads[0]
    part = team.members[0]
    assign_secret_agent(db_session, team_id=team.id, participant_id=part.id, codename="Ghost")
    task = create_agent_task(db_session, team_id=team.id, task_description="Decoy Mission")

    with pytest.raises(AgentEvidenceError):
        submit_agent_task(db_session, task_id=task.id, evidence_reference="")

    submitted_task = submit_agent_task(
        db_session,
        task_id=task.id,
        evidence_reference="https://evidence.bmsit.in/photo-123.jpg",
        actor="agent@bmsit.in",
    )
    assert submitted_task.status == AgentTaskStatus.SUBMITTED
    assert submitted_task.evidence_reference == "https://evidence.bmsit.in/photo-123.jpg"


def test_task_verification_changes_status(db_session, sample_squads):
    """Requirement 23: Verification changes task status to VERIFIED."""
    team = sample_squads[0]
    part = team.members[0]
    assign_secret_agent(db_session, team_id=team.id, participant_id=part.id)
    task = create_agent_task(db_session, team_id=team.id, task_description="Sabotage Mission")
    submit_agent_task(db_session, task_id=task.id, evidence_reference="Verified photo")

    verified_task = verify_agent_task(db_session, task_id=task.id, actor="lead_organizer@bmsit.in")
    assert verified_task.status == AgentTaskStatus.VERIFIED
    assert verified_task.organizer_id == "lead_organizer@bmsit.in"
    assert verified_task.verified_at is not None


def test_task_rejection_changes_status(db_session, sample_squads):
    """Requirement 24: Rejection changes task status to REJECTED with reason."""
    team = sample_squads[0]
    part = team.members[0]
    assign_secret_agent(db_session, team_id=team.id, participant_id=part.id)
    task = create_agent_task(db_session, team_id=team.id, task_description="Covert Mission")
    submit_agent_task(db_session, task_id=task.id, evidence_reference="Blurry photo")

    rejected_task = reject_agent_task(
        db_session,
        task_id=task.id,
        rejection_reason="Evidence is blurred and unverifiable",
        actor="organizer@bmsit.in",
    )
    assert rejected_task.status == AgentTaskStatus.REJECTED
    assert rejected_task.rejection_reason == "Evidence is blurred and unverifiable"


def test_50_points_awarded_only_after_verification(db_session, sample_squads):
    """Requirement 25: +50 points awarded only after verification, not on assigned or submitted."""
    team = sample_squads[0]
    part = team.members[0]
    assign_secret_agent(db_session, team_id=team.id, participant_id=part.id)

    # 1. Created -> balance 1000
    task = create_agent_task(db_session, team_id=team.id, task_description="Intel Collection")
    wallet = db_session.query(TeamWallet).filter(TeamWallet.team_id == team.id).first()
    assert wallet.current_balance == 1000.0

    # 2. Submitted -> balance still 1000
    submit_agent_task(db_session, task_id=task.id, evidence_reference="Report document")
    db_session.refresh(wallet)
    assert wallet.current_balance == 1000.0

    # 3. Verified -> balance becomes 1050
    verify_agent_task(db_session, task_id=task.id, actor="organizer@bmsit.in")
    db_session.refresh(wallet)
    assert wallet.current_balance == 1050.0


def test_duplicate_verification_does_not_double_reward(db_session, sample_squads):
    """Requirement 26: Duplicate verification does not award another +50."""
    team = sample_squads[0]
    part = team.members[0]
    assign_secret_agent(db_session, team_id=team.id, participant_id=part.id)
    task = create_agent_task(db_session, team_id=team.id, task_description="Mission Alpha")
    submit_agent_task(db_session, task_id=task.id, evidence_reference="Clear evidence")

    verify_agent_task(db_session, task_id=task.id, actor="organizer@bmsit.in")
    wallet = db_session.query(TeamWallet).filter(TeamWallet.team_id == team.id).first()
    assert wallet.current_balance == 1050.0

    # Re-verify
    verify_agent_task(db_session, task_id=task.id, actor="organizer@bmsit.in")
    db_session.refresh(wallet)
    assert wallet.current_balance == 1050.0  # Still 1050, no double credit


def test_agent_identity_hidden_from_public_team_endpoints(client, db_session, sample_squads):
    """Requirement 27: Agent identity is hidden from public team endpoints."""
    team = sample_squads[0]
    part = team.members[0]
    assign_secret_agent(db_session, team_id=team.id, participant_id=part.id, codename="TopSecretCodename")

    res = client.get(f"/api/v1/teams/{team.id}")
    assert res.status_code == 200
    data_str = res.text
    assert "TopSecretCodename" not in data_str
    assert "secret_agent_dossier" not in res.json().get("data", {})


def test_agent_identity_visible_only_to_authorized_roles(client, organizer_headers, judge_headers, db_session, sample_squads):
    """Requirement 28: Agent dossier is accessible strictly to authorized organizers/marshals."""
    team = sample_squads[0]
    part = team.members[0]
    assign_secret_agent(db_session, team_id=team.id, participant_id=part.id, codename="Spectre")


    # Organizer access -> 200 OK
    org_res = client.get(f"/api/v1/secret-agents/{team.id}/dossier", headers=organizer_headers)
    assert org_res.status_code == 200
    assert org_res.json()["data"]["codename"] == "Spectre"

    # Judge / unprivileged access -> 403 Forbidden
    judge_res = client.get(f"/api/v1/secret-agents/{team.id}/dossier", headers=judge_headers)
    assert judge_res.status_code == 403


def test_evidence_linked_to_correct_task(db_session, sample_squads):
    """Requirement 29: Evidence reference is linked to the correct task."""
    team = sample_squads[0]
    part = team.members[0]
    assign_secret_agent(db_session, team_id=team.id, participant_id=part.id)
    task1 = create_agent_task(db_session, team_id=team.id, task_description="Task 1")
    task2 = create_agent_task(db_session, team_id=team.id, task_description="Task 2")

    submit_agent_task(db_session, task_id=task1.id, evidence_reference="Evidence for Task 1")
    submit_agent_task(db_session, task_id=task2.id, evidence_reference="Evidence for Task 2")

    db_session.refresh(task1)
    db_session.refresh(task2)
    assert task1.evidence_reference == "Evidence for Task 1"
    assert task2.evidence_reference == "Evidence for Task 2"


def test_audit_records_created_for_code_and_agent_events(db_session, sample_squads):
    """Requirement 30: Audit records are created for code hunt and secret agent events without leaking secret strings."""
    team = sample_squads[0]
    part = team.members[0]

    record_fragment_1(db_session, team.id, "SECRET_FRAGMENT_VALUE", actor="organizer@bmsit.in")
    assign_secret_agent(db_session, team.id, part.id, codename="AuditAgent", actor="organizer@bmsit.in")

    logs = db_session.query(AuditLog).all()
    actions = [l.action for l in logs]
    assert "FRAGMENT_1_RECORDED" in actions
    assert "SECRET_AGENT_ASSIGNED" in actions

    # Verify secret fragment string is not leaked in audit log details
    for l in logs:
        if l.action == "FRAGMENT_1_RECORDED":
            details_str = str(l.details)
            assert "SECRET_FRAGMENT_VALUE" not in details_str


# ==============================================================================
# 3. API ENDPOINTS INTEGRATION TESTS
# ==============================================================================
def test_code_hunt_api_endpoints(client, organizer_headers, sample_squads):
    """Verifies all Code Hunt REST API endpoints."""
    team = sample_squads[0]

    # 1. Record Fragment 1
    r1 = client.post(
        f"/api/v1/code-hunt/{team.id}/fragment/1",
        json={"fragmentValue": "F1_VAL"},
        headers=organizer_headers,
    )
    assert r1.status_code == 200
    assert r1.json()["data"]["fragment1Status"] == "RECOVERED"

    # 2. Record Fragment 2
    r2 = client.post(
        f"/api/v1/code-hunt/{team.id}/fragment/2",
        json={"fragmentValue": "F2_VAL"},
        headers=organizer_headers,
    )
    assert r2.status_code == 200
    assert r2.json()["data"]["fragment2Status"] == "RECOVERED"

    # 3. Check Status
    r_stat = client.get(f"/api/v1/code-hunt/{team.id}/status")
    assert r_stat.status_code == 200
    assert r_stat.json()["data"]["isComplete"] is True

    # 4. Verify Final Code
    r_ver = client.post(
        f"/api/v1/code-hunt/{team.id}/verify",
        json={"suppliedCode": "F1_VALF2_VAL", "notes": "Approved by judges"},
        headers=organizer_headers,
    )
    assert r_ver.status_code == 200
    assert r_ver.json()["data"]["finalCodeVerified"] is True

    # 5. Check Round 4 Eligibility
    r_elig = client.get(f"/api/v1/rounds/4/eligibility/{team.id}")
    assert r_elig.status_code == 200
    assert r_elig.json()["data"]["isEligible"] is True


def test_secret_agent_api_endpoints(client, organizer_headers, marshal_headers, sample_squads):
    """Verifies all Secret Agent REST API endpoints."""
    team = sample_squads[1]
    part = team.members[0]

    # 1. Assign Agent
    r_assign = client.post(
        f"/api/v1/secret-agents/{team.id}/assign",
        json={"participantId": part.id, "codename": "Agent007"},
        headers=organizer_headers,
    )
    assert r_assign.status_code == 200
    assert r_assign.json()["data"]["codename"] == "Agent007"

    # 2. Create Task
    r_task = client.post(
        f"/api/v1/secret-agents/{team.id}/tasks",
        json={"taskDescription": "Secure the access badge", "rewardPoints": 50.0},
        headers=organizer_headers,
    )
    assert r_task.status_code == 200
    task_id = r_task.json()["data"]["id"]

    # 3. Submit Task
    r_sub = client.post(
        f"/api/v1/secret-agents/tasks/{task_id}/submit",
        json={"evidenceReference": "Badge photo attached"},
        headers=marshal_headers,
    )
    assert r_sub.status_code == 200
    assert r_sub.json()["data"]["status"] == "SUBMITTED"

    # 4. Verify Task
    r_verify = client.post(
        f"/api/v1/secret-agents/tasks/{task_id}/verify",
        json={"notes": "Confirmed by lead marshal"},
        headers=organizer_headers,
    )
    assert r_verify.status_code == 200
    assert r_verify.json()["data"]["status"] == "VERIFIED"

    # 5. Create another task and Reject it
    r_task2 = client.post(
        f"/api/v1/secret-agents/{team.id}/tasks",
        json={"taskDescription": "Second mission", "rewardPoints": 50.0},
        headers=organizer_headers,
    )
    task2_id = r_task2.json()["data"]["id"]
    client.post(
        f"/api/v1/secret-agents/tasks/{task2_id}/submit",
        json={"evidenceReference": "Poor evidence"},
        headers=marshal_headers,
    )
    r_reject = client.post(
        f"/api/v1/secret-agents/tasks/{task2_id}/reject",
        json={"rejectionReason": "Insufficient detail"},
        headers=organizer_headers,
    )
    assert r_reject.status_code == 200
    assert r_reject.json()["data"]["status"] == "REJECTED"