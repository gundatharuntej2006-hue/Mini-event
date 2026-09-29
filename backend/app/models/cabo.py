"""
Cabo Tournament Table Assignment and Player Scorecard Models for EVENT HQ.
Source of Truth: Authoritative Event Documentation (Reconciled in Step 6B & Step 7).

Implements 5-player table seating and individual table placements (1st=5, 2nd=3, 3rd=2, 4th=1, 5th=0)
across 3 Cabo games, with a maximum possible squad score of 75 points.
"""

import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import (
    String, Integer, Float, DateTime, ForeignKey,
    UniqueConstraint, CheckConstraint, Text
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, utc_now

if TYPE_CHECKING:
    from app.models.team import Team
    from app.models.participant import Participant


class CaboTableAssignment(Base):
    """
    Seating assignment for individual participants across Cabo tournament games.
    Constraints:
    - 5 players per table, each representing a distinct team
    - A team cannot have 2 players at the same table in the same game
    - A participant cannot appear in multiple seats in the same game
    - Exactly 3 Cabo games (game_number: 1, 2, 3)
    """
    __tablename__ = "cabo_table_assignments"
    __table_args__ = (
        CheckConstraint("game_number IN (1, 2, 3)", name="ck_cabo_assignment_game_number"),
        CheckConstraint("table_number >= 1 AND table_number <= 24", name="ck_cabo_assignment_table_number"),
        CheckConstraint("seat_position >= 1 AND seat_position <= 5", name="ck_cabo_assignment_seat_position"),
        # Unique constraint: distinct teams at a table
        UniqueConstraint("game_number", "table_number", "team_id", name="uq_cabo_game_table_team"),
        # Unique constraint: participant cannot appear twice in the same game
        UniqueConstraint("game_number", "participant_id", name="uq_cabo_game_participant"),
        # Unique constraint: seat position unique per table per game
        UniqueConstraint("game_number", "table_number", "seat_position", name="uq_cabo_game_table_seat"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: f"cba-{uuid.uuid4().hex[:8]}"
    )
    game_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    table_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    participant_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("participants.id", ondelete="RESTRICT"),
        index=True,
        nullable=False
    )
    team_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("teams.id", ondelete="RESTRICT"),
        index=True,
        nullable=False
    )
    seat_position: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False
    )

    # Relationships
    team: Mapped["Team"] = relationship("Team", back_populates="cabo_table_assignments")
    participant: Mapped["Participant"] = relationship("Participant")
    scorecard: Mapped[Optional["CaboPlayerScorecard"]] = relationship(
        "CaboPlayerScorecard",
        back_populates="table_assignment",
        uselist=False
    )


class CaboPlayerScorecard(Base):
    """
    Individual scorecard for a participant in a Cabo game.
    Official table placements are 1st through 5th:
      1st -> 5 points
      2nd -> 3 points
      3rd -> 2 points
      4th -> 1 point
      5th -> 0 points
    """
    __tablename__ = "cabo_player_scorecards"
    __table_args__ = (
        CheckConstraint("game_number IN (1, 2, 3)", name="ck_cabo_scorecard_game_number"),
        CheckConstraint("placement >= 1 AND placement <= 5", name="ck_cabo_scorecard_placement"),
        # One scorecard per participant per game
        UniqueConstraint("game_number", "participant_id", name="uq_cabo_scorecard_game_participant"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: f"cbsc-{uuid.uuid4().hex[:8]}"
    )
    game_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    participant_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("participants.id", ondelete="RESTRICT"),
        index=True,
        nullable=False
    )
    team_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("teams.id", ondelete="RESTRICT"),
        index=True,
        nullable=False
    )
    table_assignment_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("cabo_table_assignments.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    placement: Mapped[int] = mapped_column(Integer, nullable=False)
    placement_points: Mapped[float] = mapped_column(Float, nullable=False)
    final_card_hand_total: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False
    )

    # Relationships
    team: Mapped["Team"] = relationship("Team", back_populates="cabo_player_scorecards")
    participant: Mapped["Participant"] = relationship("Participant")
    table_assignment: Mapped[Optional["CaboTableAssignment"]] = relationship(
        "CaboTableAssignment",
        back_populates="scorecard"
    )


class CaboTieBreakResolution(Base):
    """
    Records how an organiser broke a Cabo tie that the metrics could not.

    ODDyssey Section 4 lists five tie-breakers, in order:

        1. Higher team placement score
        2. Lower combined final card total
        3. More first-place finishes
        4. One sudden-death Cabo game with one representative per tied team
        5. Organiser draw if still tied

    The platform implemented the first three and then stopped, flagging
    anything still level as "unresolved" with no way to resolve it. Since
    Round 2 cuts 24 squads to 12, a tie across that boundary left the round
    un-finalisable: the tie blocks finalisation, and nothing could clear the
    tie. One row here is one squad's finishing position within its tied group.
    """

    __tablename__ = "cabo_tie_break_resolutions"
    __table_args__ = (
        UniqueConstraint("team_id", name="uq_cabo_tie_break_team"),
        CheckConstraint(
            "method IN ('SUDDEN_DEATH', 'ORGANISER_DRAW')",
            name="ck_cabo_tie_break_method",
        ),
        CheckConstraint("resolution_rank >= 1", name="ck_cabo_tie_break_rank"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: f"cabotb-{uuid.uuid4().hex[:8]}"
    )
    team_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("teams.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # Tie-breaker 4 or 5. The organiser states which was used; the platform
    # never picks one on its own, and never breaks a tie at random.
    method: Mapped[str] = mapped_column(String(32), nullable=False)
    # 1 = finished first within the tied group.
    resolution_rank: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolved_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    resolved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
