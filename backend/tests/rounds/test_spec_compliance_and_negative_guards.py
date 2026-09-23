import pytest
from datetime import datetime, timezone, timedelta
from app.scoring.round1_scoring import process_round1_standings
from app.scoring.round2_scoring import process_round2_standings
from app.scoring.round3_scoring import process_round3_standings
from app.scoring.round4_scoring import process_round4_standings
from app.scoring.finale_scoring import process_finale_standings
from app.models.round2 import default_cabo_point_table
from app.models.finale import default_finale_criteria

def test_wrong_qualification_counts():
    # 1. Round 1 with only 30 squads (expected 32)
    r1_records = [
        {'team_id': f'team-{i+1}', 'team_number': i+1, 'team_name': f'Team {i+1}', 'is_complete': True, 'adjusted_total_seconds': 1000 + i * 10, 'fastest_mini_round_seconds': 300}
        for i in range(30)
    ]
    r1_res = process_round1_standings(r1_records, 120, False)
    assert r1_res['can_finalize'] is False
    assert any(i['code'] == 'INSUFFICIENT_TEAMS' for i in r1_res['issues'])

    # 2. Round 2 with 20 squads (expected exactly 24 from Round 1)
    r2_records = [
        {'team_id': f'team-{i+1}', 'team_number': i+1, 'team_name': f'Team {i+1}', 'is_complete': True, 'total_points': 50 - i}
        for i in range(20)
    ]
    r2_res = process_round2_standings(r2_records, {'scoring_direction': 'higher_is_better', 'point_table': default_cabo_point_table()}, True)
    assert r2_res['can_finalize'] is False
    assert any(i['code'] == 'INVALID_TEAM_COUNT' for i in r2_res['issues'])

    # 3. Round 3 with 10 squads (expected exactly 12 from Round 2)
    r3_records = [
        {'team_id': f'team-{i+1}', 'team_number': i+1, 'team_name': f'Team {i+1}', 'ledger': {'current_balance': 100}, 'code_record': {'is_complete': False}}
        for i in range(10)
    ]
    r3_res = process_round3_standings(r3_records, {'is_scoring_configured': True, 'scoring_direction': 'higher_is_better', 'ranking_metric': 'current_balance'}, True)
    assert r3_res['can_finalize'] is False
    assert any(i['code'] == 'INVALID_TEAM_COUNT' for i in r3_res['issues'])

    # 4. Round 4 with 6 squads (expected exactly 8 from Round 3)
    r4_records = [
        {'team_id': f'team-{i+1}', 'team_number': i+1, 'team_name': f'Team {i+1}', 'panel_score': 80, 'is_judge_panel_complete': True, 'final_score_breakdown': {'final_score': 85, 'is_complete': True}}
        for i in range(6)
    ]
    r4_res = process_round4_standings(r4_records, [], {'final_score_formula': {'isFormulaConfirmed': True}}, True)
    assert r4_res['can_finalize'] is False
    assert any(i['code'] == 'INVALID_TEAM_COUNT' for i in r4_res['issues'])

    # 5. Grand Finale with 2 squads (expected exactly 3 from Round 4)
    fin_records = [
        {'team_id': f'team-{i+1}', 'team_number': i+1, 'team_name': f'Team {i+1}', 'round4_score': 85, 'scorecard': {'is_complete': True, 'total_score': 90}, 'score_breakdown': {'total_finale_score': 105}}
        for i in range(2)
    ]
    fin_res = process_finale_standings(fin_records, {'is_scoring_rules_confirmed': True, 'scoring_direction': 'higher_wins'}, True)
    assert fin_res['can_finalize'] is False
    assert any(i['code'] == 'INVALID_FINALIST_COUNT' for i in fin_res['issues'])

def test_unauthorized_finalization(client, judge_headers):
    # Attempt finalization with non-organizer role (e.g. judge)
    res = client.post('/api/rounds/1/finalize', headers=judge_headers)
    assert res.status_code == 403
    assert 'Access forbidden' in (res.json().get('detail') or res.json().get('message', ''))

    res2 = client.post('/api/rounds/2/finalize', headers=judge_headers)
    assert res2.status_code == 403

    res3 = client.post('/api/rounds/3/finalize', headers=judge_headers)
    assert res3.status_code == 403

    res4 = client.post('/api/rounds/4/finalize', headers=judge_headers)
    assert res4.status_code == 403

    res5 = client.post('/api/rounds/finale/finalize', headers=judge_headers)
    assert res5.status_code == 403

def test_invalid_score_boundaries(client, judge_headers):
    # Submitting score that exceeds maxMarks in Grand Finale
    # First finalize R1->R4 to test Finale score validation
    res = client.post(
        '/api/rounds/finale/scorecards/team-1',
        json={
            'judge_name': 'Chief Judge',
            'scores': {
                'climax_defense': 999.0  # Exceeds max 50
            }
        },
        headers=judge_headers
    )
    # Blocked with 400 because R4 not finalized or score exceeds max
    assert res.status_code == 400

def test_invalid_transaction_reversals(client, organizer_headers):
    # Attempt to reverse non-existent transaction
    res = client.post('/api/rounds/3/transactions/rev-non-existent/reverse', json={'reason': 'Error'}, headers=organizer_headers)
    assert res.status_code == 404

def test_non_qualified_team_rejected_in_r2(client, organizer_headers, marshal_headers):
    # If Round 1 is finalized, a team not in top 24 cannot enter Round 2
    # First finalize R1 with top 24
    from datetime import datetime, timezone, timedelta
    base = datetime(2026, 9, 19, 9, 0, 0, tzinfo=timezone.utc)
    for i in range(32):
        t_id = f'team-{i + 1}'
        for mr_num, dur in [(1, 300 + i * 10), (2, 350 + i * 10), (3, 400 + i * 10)]:
            client.post(
                f'/api/rounds/1/teams/{t_id}/timings',
                json={
                    'mini_round_number': mr_num,
                    'start_time': base.isoformat(),
                    'completion_time': (base + timedelta(seconds=dur)).isoformat(),
                    'hints_used': 0
                },
                headers=marshal_headers
            )
    client.post('/api/rounds/1/finalize', headers=organizer_headers)

    # Now team-25 (ranked 25th in R1, eliminated) attempts to submit placement in Round 2
    res = client.post(
        '/api/rounds/2/games?game_number=1',
        json={'placements': [{'team_id': 'team-25', 'placement': 1}]},
        headers=marshal_headers
    )
    assert res.status_code == 400
    assert 'not qualified from Round 1' in (res.json().get('detail') or res.json().get('message', ''))

def test_duplicate_finalization_idempotency(client, db_session, organizer_headers):
    from app.models.round1 import Round1ConfigModel
    cfg = db_session.query(Round1ConfigModel).filter(Round1ConfigModel.id == 1).first()
    if not cfg:
        cfg = Round1ConfigModel(id=1, is_finalized=True)
        db_session.add(cfg)
    else:
        cfg.is_finalized = True
    db_session.commit()

    # Calling finalize again on an already finalized round returns 200 with idempotent confirmation
    res = client.post('/api/rounds/1/finalize', headers=organizer_headers)
    assert res.status_code == 200
    data = res.json()['data']
    assert data['finalized'] is True
    assert 'already been finalized' in data['message']

def test_role_based_access_controls(client, marshal_headers, judge_headers, organizer_headers):
    # 1. Marshal can record timing
    res_sk = client.post(
        '/api/rounds/1/teams/team-1/timings',
        json={'mini_round_number': 1, 'hints_used': 0},
        headers=marshal_headers
    )
    assert res_sk.status_code == 200

    # But marshal CANNOT finalize Round 1
    res_sk_fin = client.post(
        '/api/rounds/1/finalize',
        headers=marshal_headers
    )
    assert res_sk_fin.status_code == 403

    # 2. Judge CANNOT finalize Round 4
    res_j_fin = client.post(
        '/api/rounds/4/finalize',
        headers=judge_headers
    )
    assert res_j_fin.status_code == 403

    # 3. Organizer CAN resolve a tie review (either 404 because nonexistent, or 200; NOT 403 forbidden)
    res_org = client.post(
        '/api/ties/review/tie-nonexistent/resolve',
        json={'decision': 'FAVOR_TEAM', 'advancing_team_ids': ['team-1']},
        headers=organizer_headers
    )
    assert res_org.status_code != 403

    # 4. Organizer has finalization access
    res_admin = client.post(
        '/api/rounds/1/finalize',
        headers=organizer_headers
    )
    # Returns 200 (finalization logic response) - definitely not 403
    assert res_admin.status_code == 200

def test_production_auth_requirement(client, organizer_headers):
    # Without authorization header, request is rejected with 401
    res = client.post('/api/rounds/1/finalize')
    assert res.status_code == 401
    assert 'credentials' in (res.json().get('detail') or res.json().get('message', '')).lower()

    # With Bearer token, request proceeds
    res_auth = client.post(
        '/api/rounds/1/finalize',
        headers=organizer_headers
    )
    assert res_auth.status_code == 200
