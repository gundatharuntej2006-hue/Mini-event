import { Team } from '../types/team';
import {
  BlackMarketTransaction,
  TeamCodeRecord,
} from '../types/round3';
import { DEFAULT_ROUND3_CONFIG } from '../utils/round3Economy';

/**
 * Generates initial demo transactions for the 12 Round 3 teams.
 * Includes earned income, expenditures, manual adjustments, and an audited reversal.
 */
export function generateInitialRound3Transactions(
  teams: Team[]
): BlackMarketTransaction[] {
  const transactions: BlackMarketTransaction[] = [];
  const baseTime = new Date('2026-09-19T14:30:00Z').getTime();

  // Distinct demo trading profiles for 12 squads
  // Gives a realistic balance spread from ~240 down to ~70
  const profiles = [
    { earns: [50, 45, 30], spends: [20], adj: 10 },    // Team 1: ~215 net + 100 = 315
    { earns: [40, 50, 35], spends: [30], adj: 0 },     // Team 2: ~195 net + 100 = 295
    { earns: [45, 30, 40], spends: [25], adj: 5 },     // Team 3: ~190 net + 100 = 290
    { earns: [35, 40, 30], spends: [20], adj: 0 },     // Team 4: ~185 net + 100 = 285
    { earns: [40, 30, 25], spends: [20], adj: 0 },     // Team 5: ~175 net + 100 = 275
    { earns: [30, 35, 25], spends: [25], adj: -5 },    // Team 6: ~160 net + 100 = 260
    { earns: [30, 30, 20], spends: [30], adj: 0 },     // Team 7: ~150 net + 100 = 250
    { earns: [25, 30, 20], spends: [35], adj: 5 },     // Team 8: ~140 net + 100 = 240 (Cutoff Rank #8)
    { earns: [20, 25, 20], spends: [40], adj: 0 },     // Team 9: ~125 net + 100 = 225 (Cutoff Rank #9)
    { earns: [20, 20, 15], spends: [45], adj: -10 },   // Team 10: ~100 net + 100 = 200
    { earns: [15, 20, 10], spends: [50], adj: 0 },     // Team 11: ~95 net + 100 = 195
    { earns: [15, 15, 10], spends: [60], adj: 0 },     // Team 12: ~80 net + 100 = 180
  ];

  const earnReasons = [
    'Resource Contract: Cipher Decryption Payout',
    'Asset Trading: Station Alpha Intel Drop',
    'Field Bounty: Protocol Verification Completed',
    'Commodity Arbitrage: Data Ledger Verification',
  ];

  const spendReasons = [
    'Procurement: Station Bypass Permission Pass',
    'Market Purchase: Signal Amplifier Contraband',
    'Asset Acquisition: Safehouse Network Access',
    'Tactical Intel: Competitor Movement Packet',
  ];

  teams.slice(0, 12).forEach((team, idx) => {
    const p = profiles[idx] || profiles[0];
    let offset = idx * 60000;

    // Earn transactions
    p.earns.forEach((amt, eIdx) => {
      transactions.push({
        id: `tx-earn-${team.id}-${eIdx + 1}`,
        teamId: team.id,
        amount: amt,
        type: 'earn',
        reason: earnReasons[eIdx % earnReasons.length],
        organizerRef: 'Marshal-03',
        timestamp: new Date(baseTime + offset + eIdx * 180000).toISOString(),
        isReversed: false,
      });
    });

    // Spend transactions
    p.spends.forEach((amt, sIdx) => {
      transactions.push({
        id: `tx-spend-${team.id}-${sIdx + 1}`,
        teamId: team.id,
        amount: amt,
        type: 'spend',
        reason: spendReasons[sIdx % spendReasons.length],
        organizerRef: 'Market-Ops',
        timestamp: new Date(baseTime + offset + 300000 + sIdx * 120000).toISOString(),
        isReversed: false,
      });
    });

    // Adjustment transaction if any
    if (p.adj !== 0) {
      transactions.push({
        id: `tx-adj-${team.id}-1`,
        teamId: team.id,
        amount: p.adj,
        type: 'adjustment',
        reason: p.adj > 0 ? 'Marshal Review: Bonus for verified speed puzzle solve' : 'Audit Penalty: Procedural market trading violation',
        organizerRef: 'Chief-Judge',
        timestamp: new Date(baseTime + offset + 600000).toISOString(),
        isReversed: false,
      });
    }
  });

  // Add 1 sample Audited Reversal for Team 2 to demonstrate full audit trail functionality
  if (teams.length > 1) {
    const sampleTeam = teams[1];
    const origId = `tx-earn-${sampleTeam.id}-audit-sample`;
    const revId = `tx-rev-${sampleTeam.id}-audit-sample`;

    // The original transaction that was reversed (marked isReversed: true)
    transactions.push({
      id: origId,
      teamId: sampleTeam.id,
      amount: 35,
      type: 'earn',
      reason: 'Duplicate Claim: Secondary Intel Bounty (Flagged for Reversal)',
      organizerRef: 'Marshal-02',
      timestamp: new Date(baseTime + 120000).toISOString(),
      isReversed: true,
      reversalTransactionId: revId,
    });

    // The compensating reversal transaction linking back to origId
    transactions.push({
      id: revId,
      teamId: sampleTeam.id,
      amount: 35,
      type: 'reversal',
      reason: 'Reversal of tx-earn: Duplicate claim voided upon organizer review',
      organizerRef: 'Chief-Auditor',
      timestamp: new Date(baseTime + 240000).toISOString(),
      isReversed: false,
      reversedTransactionId: origId,
    });
  }

  return transactions;
}

/**
 * Generates initial code fragment progress for the 12 Round 3 teams.
 * NOTE: Secret code contents are NEVER included here or exposed in public views.
 */
export function generateInitialRound3CodeRecords(
  teams: Team[]
): Record<string, TeamCodeRecord> {
  const codeRecords: Record<string, TeamCodeRecord> = {};
  const baseTime = new Date('2026-09-19T14:45:00Z').getTime();

  teams.slice(0, 12).forEach((team, idx) => {
    const fragmentsCount = idx < 6 ? 3 : idx < 9 ? 2 : 1; // Top teams have recovered more fragments
    const fragments = [];

    for (let f = 1; f <= fragmentsCount; f++) {
      fragments.push({
        fragmentIndex: f,
        recoveredAt: new Date(baseTime + idx * 300000 + f * 600000).toISOString(),
        recoveredBy: `Checkpoint-Marshal-${f}`,
        notes: `Physical verification card scanned at Station 0${f}`,
      });
    }

    codeRecords[team.id] = {
      teamId: team.id,
      fragments,
      isComplete: false, // Remains false until requirements are officially confirmed and evaluated
      verifiedAt: fragmentsCount >= 3 ? new Date(baseTime + 3600000).toISOString() : null,
      verifiedBy: fragmentsCount >= 3 ? 'Chief-Marshal' : null,
    };
  });

  return codeRecords;
}

export { DEFAULT_ROUND3_CONFIG };
