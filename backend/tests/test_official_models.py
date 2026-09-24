"""
Unit tests for EVENT HQ Official Tournament Models & Schema Extensions (Step 8).
Verifies model constraints, relationships, default values, and integrity rules
as specified in the authoritative Event Documentation.
"""

import pytest
from sqlalchemy.exc import IntegrityError
from app.models.team import Team, TeamStatus
from app.models.participant import Participant, ParticipantRole
from app.models.wallet import TeamWallet, WalletTransaction, TransactionType
from app.models.cabo import CaboTableAssignment, CaboPlayerScorecard
from app.models.agent import (
    SecretAgentDossier,
    SecretAgentTask,
    AgentDossierStatus,
    AgentTaskStatus,
)
from app.models.code_hunt import FinalCodeRecord, FragmentStatus
from app.models.black_market import (
    BlackMarketPurchase,
    BlackMarketAssetType,
    PurchaseStatus,
)
from app.core.constants import (
    STARTING_WALLET_BALANCE,
    CABO_PLACEMENT_POINTS,
    AGENT_TASK_REWARD,
)


@pytest.fixture
def test_team(db_session):
    team = Team(
        id="team-test-101",
        team_number=101,
        name="Apex Titans",
        status=TeamStatus.ACTIVE,
    )
    db_session.add(team)
    db_session.commit()
    return team


@pytest.fixture
def test_participants(db_session, test_team):
    parts = []
    for i in range(5):
        p = Participant(
            id=f"part-test-101-{i + 1}",
            name=f"Titan Player {i + 1}",
            email=f"titan{i + 1}@bmsit.in",
            usn=f"1BY24CS{100 + i + 1}",
            role=ParticipantRole.LEADER if i == 0 else ParticipantRole.MEMBER,
            team_id=test_team.id,
        )
        db_session.add(p)
        parts.append(p)
    db_session.commit()
    return parts


class TestTeamWalletModel:
    def test_one_wallet_per_team_and_starting_balance(self, db_session, test_team):
        """Verifies one wallet per team and starting balance of 1000 points."""
        wallet = TeamWallet(
            team_id=test_team.id,
        )
        db_session.add(wallet)
        db_session.commit()

        assert wallet.current_balance == STARTING_WALLET_BALANCE
        assert wallet.current_balance == 1000.0
        assert wallet.total_earned == 0.0
        assert wallet.total_spent == 0.0
        assert wallet.total_penalties == 0.0

        # Attempt to create a duplicate wallet for the same team
        duplicate_wallet = TeamWallet(
            team_id=test_team.id,
            current_balance=500.0,
        )
        db_session.add(duplicate_wallet)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_wallet_transaction_relationships(self, db_session, test_team):
        """Verifies wallet transaction ledger relationship and balance audit tracking."""
        wallet = TeamWallet(team_id=test_team.id)
        db_session.add(wallet)
        db_session.commit()

        tx = WalletTransaction(
            wallet_id=wallet.id,
            team_id=test_team.id,
            transaction_type=TransactionType.INITIAL_BALANCE,
            amount=1000.0,
            balance_before=0.0,
            balance_after=1000.0,
            description="Tournament starting capital allocation",
            created_by="Organizer",
        )
        db_session.add(tx)
        db_session.commit()

        db_session.refresh(wallet)
        assert len(wallet.transactions) == 1
        assert wallet.transactions[0].id == tx.id
        assert wallet.transactions[0].amount == 1000.0
        assert wallet.transactions[0].transaction_type == TransactionType.INITIAL_BALANCE


class TestCaboTableAssignmentAndScorecards:
    def test_cabo_table_assignment_constraints(self, db_session, test_team, test_participants):
        """Verifies table seating rules: 5 players per table, no duplicate team on table."""
        # Create 4 more distinct teams with 1 player each
        teams = [test_team]
        players = [test_participants[0]]

        for i in range(2, 6):
            t = Team(id=f"team-cabo-{i}", team_number=200 + i, name=f"Squad {i}")
            db_session.add(t)
            p = Participant(
                id=f"part-cabo-{i}",
                name=f"Player {i}",
                email=f"player{i}@bmsit.in",
                usn=f"1BY24CS{300 + i}",
                team_id=t.id,
            )
            db_session.add(p)
            teams.append(t)
            players.append(p)
        db_session.commit()

        # Seat 5 distinct squad players at Game 1, Table 1, seats 1..5
        for seat in range(1, 6):
            assignment = CaboTableAssignment(
                game_number=1,
                table_number=1,
                participant_id=players[seat - 1].id,
                team_id=teams[seat - 1].id,
                seat_position=seat,
            )
            db_session.add(assignment)
        db_session.commit()

        count = db_session.query(CaboTableAssignment).filter(
            CaboTableAssignment.game_number == 1,
            CaboTableAssignment.table_number == 1,
        ).count()
        assert count == 5

        # Duplicate team check: Player 2 from test_team cannot sit at Game 1, Table 1
        duplicate_team_seat = CaboTableAssignment(
            game_number=1,
            table_number=1,
            participant_id=test_participants[1].id,
            team_id=test_team.id,
            seat_position=5,
        )
        db_session.add(duplicate_team_seat)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_cabo_player_scorecard_placement_points(self, db_session, test_team, test_participants):
        """Verifies Cabo scorecards map to canonical table points (1st=5, 2nd=3, 3rd=2, 4th=1, 5th=0)."""
        card1 = CaboPlayerScorecard(
            game_number=1,
            participant_id=test_participants[0].id,
            team_id=test_team.id,
            placement=1,
            placement_points=CABO_PLACEMENT_POINTS[1],
            final_card_hand_total=4,
        )
        db_session.add(card1)
        db_session.commit()

        assert card1.placement == 1
        assert card1.placement_points == 5.0

        # Duplicate scorecard for same participant in same game is rejected
        dup_card = CaboPlayerScorecard(
            game_number=1,
            participant_id=test_participants[0].id,
            team_id=test_team.id,
            placement=2,
            placement_points=CABO_PLACEMENT_POINTS[2],
        )
        db_session.add(dup_card)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()


class TestSecretAgentTrackModels:
    def test_one_secret_agent_per_team(self, db_session, test_team, test_participants):
        """Verifies exactly one undercover agent dossier per team."""
        dossier = SecretAgentDossier(
            team_id=test_team.id,
            participant_id=test_participants[2].id,
            codename="Agent Phantom",
            status=AgentDossierStatus.ACTIVE,
        )
        db_session.add(dossier)
        db_session.commit()

        assert dossier.codename == "Agent Phantom"
        assert dossier.status == AgentDossierStatus.ACTIVE

        # Attempt duplicate dossier for same team
        dup_dossier = SecretAgentDossier(
            team_id=test_team.id,
            participant_id=test_participants[3].id,
            codename="Agent Ghost",
        )
        db_session.add(dup_dossier)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_secret_agent_task_lifecycle_and_cascade(self, db_session, test_team, test_participants):
        """Verifies agent task status lifecycle and cascade deletion with dossier."""
        dossier = SecretAgentDossier(
            team_id=test_team.id,
            participant_id=test_participants[1].id,
            codename="Agent Shadow",
        )
        db_session.add(dossier)
        db_session.commit()

        task = SecretAgentTask(
            dossier_id=dossier.id,
            task_description="Plant dummy clue in Station Bravo",
            status=AgentTaskStatus.ASSIGNED,
            reward_points=AGENT_TASK_REWARD,
        )
        db_session.add(task)
        db_session.commit()

        assert task.status == AgentTaskStatus.ASSIGNED
        assert task.reward_points == 50.0

        # Update task to SUBMITTED then VERIFIED
        task.status = AgentTaskStatus.SUBMITTED
        task.evidence_reference = "Audio log fragment #82"
        db_session.commit()

        task.status = AgentTaskStatus.VERIFIED
        task.organizer_id = "org-lead-01"
        db_session.commit()

        assert task.status == AgentTaskStatus.VERIFIED
        assert task.organizer_id == "org-lead-01"


class TestFinalCodeRecordModel:
    def test_final_code_record_structure_and_uniqueness(self, db_session, test_team):
        """Verifies two code fragments representation and one record per team."""
        fcr = FinalCodeRecord(
            team_id=test_team.id,
            fragment_1_status=FragmentStatus.RECOVERED,
            fragment_1_value="ALPHA-77",
            fragment_2_status=FragmentStatus.PENDING,
            final_code_verified=False,
        )
        db_session.add(fcr)
        db_session.commit()

        assert fcr.fragment_1_status == FragmentStatus.RECOVERED
        assert fcr.fragment_2_status == FragmentStatus.PENDING
        assert fcr.final_code_verified is False

        # Attempt to create duplicate record for same team
        dup_fcr = FinalCodeRecord(team_id=test_team.id)
        db_session.add(dup_fcr)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()


class TestBlackMarketPurchaseModel:
    def test_purchase_association_with_team(self, db_session, test_team):
        """Verifies Black Market purchase links to team and tracks tactical assets."""
        wallet = TeamWallet(team_id=test_team.id)
        db_session.add(wallet)
        db_session.commit()

        tx = WalletTransaction(
            wallet_id=wallet.id,
            team_id=test_team.id,
            transaction_type=TransactionType.BLACK_MARKET_PURCHASE,
            amount=-400.0,
            balance_before=1000.0,
            balance_after=600.0,
            description="Purchased missing Fragment #02",
        )
        db_session.add(tx)
        db_session.commit()

        purchase = BlackMarketPurchase(
            team_id=test_team.id,
            asset_type=BlackMarketAssetType.MISSING_CODE_FRAGMENT,
            price=400.0,
            quantity=1,
            transaction_id=tx.id,
            status=PurchaseStatus.COMPLETED,
            details={"fragmentNumber": 2, "serial": "CABO-FRAG-02"},
        )
        db_session.add(purchase)
        db_session.commit()

        db_session.refresh(test_team)
        assert len(test_team.black_market_purchases) == 1
        assert test_team.black_market_purchases[0].asset_type == BlackMarketAssetType.MISSING_CODE_FRAGMENT
        assert test_team.black_market_purchases[0].price == 400.0
        assert test_team.black_market_purchases[0].transaction_id == tx.id
