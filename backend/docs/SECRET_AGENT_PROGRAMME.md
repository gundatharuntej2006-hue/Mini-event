# The Secret Agent programme: run it on paper

**Decision, 23 September 2026.** This is the one item on the build list that is
answered by *not* building something. It is written down here because "we'll
figure it out" is how it would otherwise reach the day undecided.

## What the documentation asks for

Section 3.2 describes a programme that runs underneath every round:

- Each team secretly nominates one member as its Secret Agent, submitted "in a
  sealed envelope or private form to the organisers only" (Section 2).
- Tasks are issued privately — "sealed slips or direct message" — at set points
  in the event.
- Completed tasks are verified, and Section 3.3 pays **+50 points per verified
  task** into the team's Black Market balance. Failed or exposed tasks earn 0.
- In the finale, each of the 8 teams guesses the agents of the other 7, scoring
  **+30** for a correct guess and **−20** for a wrong one (Section 8.2).

## Why it is not in the database

The agent identities are the event. Everything else — times, card placements,
balances — is public within minutes of being recorded. The agent list is the
one piece of information that has to stay secret until the finale, and it is
the one piece that decides the finale.

If it lives in the platform, then everyone with database access can read it:
every organiser account, every marshal running a Black Market stall, anyone
with the Render dashboard, anyone who can reach a backup. A single glance at a
screen over somebody's shoulder ends the round. There is no access-control
design that makes 160 players believe the list stayed secret, and belief is the
point — a guessing round nobody trusts is not worth running.

Sealed envelopes have a property no permission model has: a broken seal is
visible.

## What actually happens on the day

**Agent Control** is one named person who is not an organiser working a round.
They hold:

1. The sealed nomination envelopes, opened only by them.
2. A paper master list — one copy, on their person.
3. The task slips, issued by hand at the set points.
4. A verification log: task, team, verified yes/no, time, their initials.

## What the platform does

Only the consequences, never the identities:

- **Verified task points.** Agent Control reads their log to an organiser, who
  enters `+50` per verified task as an ordinary Round 3 `earn` transaction with
  the reason `Secret agent task (verified)`. This is why
  `award_carryover_points` deliberately awards Round 1 and Round 2 only —
  see the docstring in `app/services/round_service.py`.
- **Finale guesses.** Judges enter each team's guesses and whether each was
  correct; the platform applies +30 / −20 / 0 from `event_rules`. Agent Control
  reveals the master list at the moment of resolution, not before.
- **The intel card.** A team that buys `agent_intel_card` (250 points,
  Section 6.2) gets a physical clue card from Agent Control. The platform
  records that the purchase happened and takes the money; it never stores what
  the clue said.

## What this costs

The platform cannot check that a +50 award corresponds to a real verified task.
That is a genuine trade-off, accepted deliberately: the verification log is
paper, signed, and one person owns it. For a 160-player campus event, an
auditable paper trail held by a named person is a stronger control than a
database row that a dozen accounts could have written.

## What would change the decision

If a future edition wants agents in the platform, the minimum bar is per-role
field encryption with a key Agent Control alone holds, plus an access log on
every read. That is real work and it buys less than an envelope does. It is not
worth doing for this event.

## Consequences for the build

- No agent model, no agent table, no agent endpoints. Not an oversight.
- Agent Control must be named and briefed **before** Round 1 — they cannot be
  recruited on the day, because the nominations are collected at registration.
- The finale cannot be scored until Agent Control is in the room with the list.
  Put them on the run sheet.
- Print the verification log sheets in advance. They are the only record that
  the +50 awards were earned.
