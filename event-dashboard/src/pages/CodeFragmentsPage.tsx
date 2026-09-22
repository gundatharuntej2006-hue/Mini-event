import { useState, useMemo } from 'react';
import { QrCode, CheckCircle2, MapPin, Trophy } from 'lucide-react';
import { Card, CardHeader, CardContent } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { PageHeader } from '../components/ui/PageHeader';
import { SummaryMetric } from '../components/ui/SummaryMetric';
import { SearchFilterToolbar } from '../components/ui/SearchFilterToolbar';

interface FragmentMock {
  id: string;
  codeNumber: number;
  zone: string;
  pointValue: number;
  isFound: boolean;
  discoveredByTeam?: string;
  discoveredAt?: string;
}

const MOCK_FRAGMENTS: FragmentMock[] = Array.from({ length: 16 }).map((_, idx) => ({
  id: `frag-${idx + 1}`,
  codeNumber: idx + 1,
  zone: idx % 4 === 0 ? 'Main Library' : idx % 4 === 1 ? 'Innovation Quad' : idx % 4 === 2 ? 'Auditorium Corridor' : 'Sports Complex',
  pointValue: 10 + (idx % 3) * 5,
  isFound: idx < 6,
  discoveredByTeam: idx < 6 ? `Team T-${String(idx + 1).padStart(2, '0')}` : undefined,
  discoveredAt: idx < 6 ? '10:45 AM' : undefined,
}));

export function CodeFragmentsPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'claimed' | 'unclaimed'>('all');

  const filteredFragments = useMemo(() => {
    return MOCK_FRAGMENTS.filter((frag) => {
      const matchesSearch =
        searchQuery === '' ||
        frag.zone.toLowerCase().includes(searchQuery.toLowerCase()) ||
        `clue-#${String(frag.codeNumber).padStart(2, '0')}`.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (frag.discoveredByTeam && frag.discoveredByTeam.toLowerCase().includes(searchQuery.toLowerCase()));

      const matchesStatus =
        statusFilter === 'all' ||
        (statusFilter === 'claimed' && frag.isFound) ||
        (statusFilter === 'unclaimed' && !frag.isFound);

      return matchesSearch && matchesStatus;
    });
  }, [searchQuery, statusFilter]);

  const claimedCount = MOCK_FRAGMENTS.filter((f) => f.isFound).length;
  const totalCount = MOCK_FRAGMENTS.length;
  const claimedPoints = MOCK_FRAGMENTS.filter((f) => f.isFound).reduce((acc, f) => acc + f.pointValue, 0);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <PageHeader
        title="Campus Hidden Code Fragments Hunt"
        subtitle="Decentralized QR & cipher code discovery across BMSIT campus checkpoints"
        badge={
          <Badge variant="primary" size="sm">
            32 Physical Checkpoints
          </Badge>
        }
      />

      {/* KPI Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <SummaryMetric
          label="Total Clue Stations"
          value={totalCount}
          subtext="Configured across campus sectors"
          icon={QrCode}
          variant="blue"
        />
        <SummaryMetric
          label="Codes Discovered"
          value={claimedCount}
          subtext={`${totalCount - claimedCount} remaining hidden`}
          icon={CheckCircle2}
          variant="emerald"
        />
        <SummaryMetric
          label="Points Unlocked"
          value={`${claimedPoints} pts`}
          subtext="Awarded to discovering squads"
          icon={Trophy}
          variant="purple"
        />
        <SummaryMetric
          label="Active Campus Zones"
          value="4 Sectors"
          subtext="Library, Quad, Auditorium, Sports"
          icon={MapPin}
          variant="amber"
        />
      </div>

      {/* Search & Filter Toolbar */}
      <SearchFilterToolbar
        searchPlaceholder="Search clue #, campus sector, or discovering squad..."
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        filters={[
          {
            id: 'status',
            label: 'Discovery Status',
            value: statusFilter,
            options: [
              { label: 'All Checkpoints', value: 'all' },
              { label: 'Claimed', value: 'claimed' },
              { label: 'Unclaimed', value: 'unclaimed' },
            ],
            onChange: (val) => setStatusFilter(val as any),
          },
        ]}
        activeCount={(searchQuery ? 1 : 0) + (statusFilter !== 'all' ? 1 : 0)}
        onClearAll={() => {
          setSearchQuery('');
          setStatusFilter('all');
        }}
      />

      {/* Table Card */}
      <Card className="border-cyan-500/20 bg-[#090d1a]/80 shadow-[0_0_25px_rgba(34,211,238,0.06)] backdrop-blur-md overflow-hidden">
        <CardHeader
          title={<span className="font-display font-bold tracking-wide text-slate-100">Code Fragment Ledger</span>}
          subtitle="Real-time check-in ledger for campus discovery checkpoints"
          action={
            <Badge variant="neutral" size="sm">
              Showing {filteredFragments.length} of {totalCount} Checkpoints
            </Badge>
          }
        />
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-[#030712]/95 border-b border-cyan-500/20 text-[10px] uppercase tracking-wider font-mono font-semibold text-cyan-400/90">
                  <th className="py-3 px-4">Clue #</th>
                  <th className="py-3 px-4">Campus Sector / Zone</th>
                  <th className="py-3 px-4">Point Weight</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Discovered By</th>
                  <th className="py-3 px-4">Logged Time</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-cyan-500/10">
                {filteredFragments.map((frag) => (
                  <tr key={frag.id} className="hover:bg-cyan-500/5 transition-colors">
                    <td className="py-3 px-4 font-mono font-bold text-cyan-300">
                      CLUE-#{String(frag.codeNumber).padStart(2, '0')}
                    </td>
                    <td className="py-3 px-4 text-slate-200 font-medium">
                      {frag.zone}
                    </td>
                    <td className="py-3 px-4 font-mono text-cyan-400 font-semibold">
                      +{frag.pointValue} pts
                    </td>
                    <td className="py-3 px-4">
                      {frag.isFound ? (
                        <Badge variant="success" size="sm" dot>
                          Claimed
                        </Badge>
                      ) : (
                        <Badge variant="neutral" size="sm">
                          Unclaimed
                        </Badge>
                      )}
                    </td>
                    <td className="py-3 px-4 text-slate-300 font-medium font-mono">
                      {frag.discoveredByTeam || '—'}
                    </td>
                    <td className="py-3 px-4 text-slate-400 font-mono text-[11px]">
                      {frag.discoveredAt || '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
