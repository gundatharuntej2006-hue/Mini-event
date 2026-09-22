import { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import {
  Shield,
  Users,
  CheckCircle2,
  AlertTriangle,
  Send,
  ArrowLeft,
  Crown,
  UserCheck,
  Check,
  Building2,
  Clock,
} from 'lucide-react';
import { Card, CardHeader, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { backendApiService } from '../services/backendApiService';
import { Submission } from '../types/integration';

interface MemberFormState {
  name: string;
  usn: string;
  email: string;
  phone: string;
}

export function PublicRegistrationPage() {
  const [teamName, setTeamName] = useState('');
  
  // Leader is member index 0
  const [leader, setLeader] = useState<MemberFormState>({
    name: '',
    usn: '',
    email: '',
    phone: '',
  });

  // 4 other members (indices 1 to 4)
  const [members, setMembers] = useState<MemberFormState[]>([
    { name: '', usn: '', email: '', phone: '' },
    { name: '', usn: '', email: '', phone: '' },
    { name: '', usn: '', email: '', phone: '' },
    { name: '', usn: '', email: '', phone: '' },
  ]);

  const [consentGiven, setConsentGiven] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submissionResult, setSubmissionResult] = useState<Submission | null>(null);

  const handleMemberChange = (index: number, field: keyof MemberFormState, value: string) => {
    setMembers((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], [field]: value };
      return next;
    });
  };

  // Combine leader + 4 members for validations
  const allMembers = useMemo(() => [
    { ...leader, role: 'Leader' as const },
    ...members.map((m) => ({ ...m, role: 'Member' as const })),
  ], [leader, members]);

  // Real-time intra-form duplicate validation
  const validationErrors = useMemo(() => {
    const errors: string[] = [];

    if (!teamName.trim()) {
      errors.push('Squad Name is required.');
    }

    // Check complete fields
    allMembers.forEach((m, idx) => {
      const label = idx === 0 ? 'Team Leader' : `Member ${idx + 1}`;
      if (!m.name.trim()) errors.push(`${label}: Full Name is required.`);
      if (!m.usn.trim()) errors.push(`${label}: USN is required.`);
      if (!m.email.trim()) errors.push(`${label}: College Email is required.`);
    });

    // Check duplicate USNs
    const usns = allMembers.map((m) => m.usn.trim().toUpperCase()).filter(Boolean);
    const uniqueUsns = new Set(usns);
    if (usns.length !== uniqueUsns.size) {
      errors.push('Duplicate USN detected among the submitted squad members.');
    }

    // Check duplicate Emails
    const emails = allMembers.map((m) => m.email.trim().toLowerCase()).filter(Boolean);
    const uniqueEmails = new Set(emails);
    if (emails.length !== uniqueEmails.size) {
      errors.push('Duplicate email detected among the submitted squad members.');
    }

    if (!consentGiven) {
      errors.push('You must confirm tournament eligibility and rules consent.');
    }

    return errors;
  }, [teamName, allMembers, consentGiven]);

  const isValid = validationErrors.length === 0;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isValid) return;

    setIsSubmitting(true);
    setSubmitError(null);

    try {
      const payload = {
        team_name: teamName.trim(),
        leader: {
          name: leader.name.trim(),
          usn: leader.usn.trim().toUpperCase(),
          email: leader.email.trim().toLowerCase(),
          phone: leader.phone.trim() || undefined,
          role: 'Leader' as const,
        },
        members: members.map((m) => ({
          name: m.name.trim(),
          usn: m.usn.trim().toUpperCase(),
          email: m.email.trim().toLowerCase(),
          phone: m.phone.trim() || undefined,
          role: 'Member' as const,
        })),
        consent_given: consentGiven,
        source: 'public_web' as const,
      };

      const res = await backendApiService.submitPublicRegistration(payload);
      if (res.success && res.data) {
        setSubmissionResult(res.data);
      } else {
        setSubmitError(res.message || 'Failed to submit registration.');
      }
    } catch (err: any) {
      setSubmitError(err.message || 'An error occurred while submitting the registration.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (submissionResult) {
    const isAccepted = submissionResult.status === 'ACCEPTED';
    return (
      <div className="min-h-screen bg-[#030712] text-slate-100 flex items-center justify-center p-4">
        <div className="max-w-xl w-full">
          <Card className="border-cyan-500/30 bg-[#090d1a]/95 shadow-[0_0_50px_rgba(34,211,238,0.15)] backdrop-blur-xl p-8 text-center space-y-6">
            <div className="flex justify-center">
              {isAccepted ? (
                <div className="w-16 h-16 rounded-2xl bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400 shadow-[0_0_25px_rgba(16,185,129,0.3)]">
                  <CheckCircle2 className="w-8 h-8" />
                </div>
              ) : (
                <div className="w-16 h-16 rounded-2xl bg-cyan-500/20 border border-cyan-500/40 flex items-center justify-center text-cyan-400 shadow-[0_0_25px_rgba(34,211,238,0.3)]">
                  <Clock className="w-8 h-8" />
                </div>
              )}
            </div>

            <div className="space-y-2">
              <Badge variant={isAccepted ? 'success' : 'primary'} size="md">
                {isAccepted ? 'SQUAD REGISTERED' : 'SUBMISSION RECEIVED · PENDING APPROVAL'}
              </Badge>
              <h2 className="text-2xl font-bold font-display text-white tracking-wide">
                {submissionResult.team_name}
              </h2>
              <p className="text-xs text-slate-400 max-w-md mx-auto leading-relaxed">
                {isAccepted
                  ? 'Your squad and all 5 members have been verified and added to the official tournament roster!'
                  : 'Your squad submission has been safely recorded. Tournament organizers will review your submission before adding your squad to the active roster.'}
              </p>
            </div>

            <div className="bg-[#030712] border border-cyan-500/20 rounded-xl p-4 text-xs font-mono text-left space-y-2">
              <div className="flex justify-between border-b border-cyan-500/10 pb-2">
                <span className="text-slate-400">Team Leader</span>
                <span className="text-cyan-300 font-semibold">{submissionResult.leader_name}</span>
              </div>
              <div className="flex justify-between border-b border-cyan-500/10 pb-2">
                <span className="text-slate-400">Leader USN</span>
                <span className="text-cyan-300">{submissionResult.leader_usn}</span>
              </div>
              <div className="flex justify-between border-b border-cyan-500/10 pb-2">
                <span className="text-slate-400">Roster Size</span>
                <span className="text-emerald-400 font-semibold">5 / 5 Members Submitted</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Submission Reference</span>
                <span className="text-slate-500 text-[10px]">{submissionResult.external_submission_id}</span>
              </div>
            </div>

            <div className="pt-2 flex flex-col sm:flex-row gap-3 justify-center">
              <Link to="/">
                <Button variant="outline" size="sm" leftIcon={<ArrowLeft className="w-4 h-4" />}>
                  Back to Event HQ
                </Button>
              </Link>
              <Button
                variant="primary"
                size="sm"
                onClick={() => {
                  setSubmissionResult(null);
                  setTeamName('');
                  setLeader({ name: '', usn: '', email: '', phone: '' });
                  setMembers([
                    { name: '', usn: '', email: '', phone: '' },
                    { name: '', usn: '', email: '', phone: '' },
                    { name: '', usn: '', email: '', phone: '' },
                    { name: '', usn: '', email: '', phone: '' },
                  ]);
                  setConsentGiven(false);
                }}
              >
                Register Another Squad
              </Button>
            </div>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#030712] text-slate-100 py-10 px-4 sm:px-6 lg:px-8 relative overflow-hidden">
      {/* Background Cyber Ambient Glows */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[350px] bg-cyan-500/10 blur-[130px] pointer-events-none" />
      <div className="absolute bottom-0 right-0 w-[500px] h-[350px] bg-indigo-500/10 blur-[120px] pointer-events-none" />

      <div className="max-w-4xl mx-auto space-y-8 relative z-10">
        {/* Top Header */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 border-b border-cyan-500/20 pb-6">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 shadow-[0_0_20px_rgba(34,211,238,0.2)]">
              <Shield className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-lg font-black tracking-wider font-display text-white">
                  EVENT HQ
                </span>
                <span className="text-xs px-2 py-0.5 rounded bg-cyan-500/20 border border-cyan-500/40 text-cyan-300 font-mono">
                  BMSIT 2026
                </span>
              </div>
              <p className="text-xs text-slate-400 font-mono flex items-center gap-1.5 mt-0.5">
                <Building2 className="w-3.5 h-3.5 text-cyan-400" />
                Official Squad Self-Registration Portal
              </p>
            </div>
          </div>

          <Link to="/">
            <Button variant="outline" size="sm" leftIcon={<ArrowLeft className="w-4 h-4" />}>
              Back to Overview
            </Button>
          </Link>
        </div>

        {/* Info Banner */}
        <div className="p-4 rounded-xl bg-[#090d1a]/80 border border-cyan-500/20 text-xs text-slate-300 space-y-2 backdrop-blur-md">
          <div className="flex items-center gap-2 font-semibold text-cyan-300 font-display">
            <Users className="w-4 h-4 text-cyan-400" />
            Tournament Squad Registration Rules
          </div>
          <ul className="grid grid-cols-1 md:grid-cols-2 gap-2 text-[11px] text-slate-400">
            <li className="flex items-center gap-1.5">
              <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
              Exactly 5 participants required per squad (1 Leader + 4 Members).
            </li>
            <li className="flex items-center gap-1.5">
              <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
              All participants must provide a unique, valid BMSIT USN.
            </li>
            <li className="flex items-center gap-1.5">
              <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
              Tournament capacity capped at exactly 32 squads.
            </li>
            <li className="flex items-center gap-1.5">
              <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
              Submissions undergo Organizer verification before live roster placement.
            </li>
          </ul>
        </div>

        {submitError && (
          <div className="p-4 rounded-xl bg-rose-950/50 border border-rose-500/50 text-rose-300 text-xs flex items-center gap-2.5 shadow-[0_0_20px_rgba(244,63,94,0.15)]">
            <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0" />
            <div>
              <p className="font-semibold font-display">Registration Submission Failed</p>
              <p className="text-[11px] opacity-90 mt-0.5">{submitError}</p>
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Squad Details Card */}
          <Card className="border-cyan-500/20 bg-[#090d1a]/80 shadow-[0_0_25px_rgba(34,211,238,0.05)] backdrop-blur-md">
            <CardHeader
              title={
                <div className="flex items-center gap-2 text-slate-100 font-bold font-display text-sm tracking-wide">
                  <Shield className="w-4 h-4 text-cyan-400" />
                  1. Squad Identification
                </div>
              }
            />
            <CardContent>
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  Squad / Team Name <span className="text-rose-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g., Cyber Knights, Phantom Protocol, Bit Shifters"
                  value={teamName}
                  onChange={(e) => setTeamName(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-lg bg-[#030712] border border-cyan-500/30 text-slate-100 text-sm focus:outline-none focus:border-cyan-400 font-mono transition-colors"
                />
              </div>
            </CardContent>
          </Card>

          {/* Leader Section */}
          <Card className="border-amber-500/30 bg-[#090d1a]/80 shadow-[0_0_25px_rgba(245,158,11,0.06)] backdrop-blur-md">
            <CardHeader
              title={
                <div className="flex items-center justify-between w-full">
                  <div className="flex items-center gap-2 text-amber-300 font-bold font-display text-sm tracking-wide">
                    <Crown className="w-4 h-4 text-amber-400" />
                    2. Designated Team Leader
                  </div>
                  <Badge variant="warning" size="sm">
                    Required Lead
                  </Badge>
                </div>
              }
            />
            <CardContent className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-300 mb-1">
                  Full Name <span className="text-rose-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="Leader's Full Name"
                  value={leader.name}
                  onChange={(e) => setLeader({ ...leader, name: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg bg-[#030712] border border-cyan-500/30 text-slate-100 text-xs focus:outline-none focus:border-amber-400"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-300 mb-1">
                  BMSIT USN <span className="text-rose-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g., 1BY23CS001"
                  value={leader.usn}
                  onChange={(e) => setLeader({ ...leader, usn: e.target.value.toUpperCase() })}
                  className="w-full px-3 py-2 rounded-lg bg-[#030712] border border-cyan-500/30 text-slate-100 text-xs font-mono uppercase focus:outline-none focus:border-amber-400"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-300 mb-1">
                  Institutional Email <span className="text-rose-400">*</span>
                </label>
                <input
                  type="email"
                  required
                  placeholder="leader@bmsit.in"
                  value={leader.email}
                  onChange={(e) => setLeader({ ...leader, email: e.target.value.toLowerCase() })}
                  className="w-full px-3 py-2 rounded-lg bg-[#030712] border border-cyan-500/30 text-slate-100 text-xs font-mono lowercase focus:outline-none focus:border-amber-400"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-300 mb-1">
                  Contact Phone (WhatsApp)
                </label>
                <input
                  type="tel"
                  placeholder="10-digit mobile number"
                  value={leader.phone}
                  onChange={(e) => setLeader({ ...leader, phone: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg bg-[#030712] border border-cyan-500/30 text-slate-100 text-xs font-mono focus:outline-none focus:border-amber-400"
                />
              </div>
            </CardContent>
          </Card>

          {/* Members 2 through 5 */}
          <Card className="border-cyan-500/20 bg-[#090d1a]/80 shadow-[0_0_25px_rgba(34,211,238,0.05)] backdrop-blur-md">
            <CardHeader
              title={
                <div className="flex items-center justify-between w-full">
                  <div className="flex items-center gap-2 text-slate-100 font-bold font-display text-sm tracking-wide">
                    <Users className="w-4 h-4 text-cyan-400" />
                    3. Squad Members (4 Required)
                  </div>
                  <Badge variant="primary" size="sm">
                    Members 2 to 5
                  </Badge>
                </div>
              }
            />
            <CardContent className="space-y-6">
              {members.map((m, idx) => (
                <div
                  key={idx}
                  className="p-4 rounded-xl bg-[#030712]/60 border border-cyan-500/15 space-y-3"
                >
                  <div className="flex items-center justify-between text-xs border-b border-cyan-500/10 pb-2">
                    <span className="font-semibold text-cyan-300 font-display flex items-center gap-1.5">
                      <UserCheck className="w-3.5 h-3.5 text-cyan-400" />
                      Member {idx + 2} Details
                    </span>
                    <span className="text-[10px] text-slate-400 font-mono">Squad Member</span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
                    <div>
                      <label className="block text-[11px] font-medium text-slate-400 mb-1">
                        Full Name <span className="text-rose-400">*</span>
                      </label>
                      <input
                        type="text"
                        required
                        placeholder={`Member ${idx + 2} Name`}
                        value={m.name}
                        onChange={(e) => handleMemberChange(idx, 'name', e.target.value)}
                        className="w-full px-2.5 py-1.5 rounded-lg bg-[#030712] border border-cyan-500/30 text-slate-100 text-xs focus:outline-none focus:border-cyan-400"
                      />
                    </div>

                    <div>
                      <label className="block text-[11px] font-medium text-slate-400 mb-1">
                        USN <span className="text-rose-400">*</span>
                      </label>
                      <input
                        type="text"
                        required
                        placeholder="e.g., 1BY23CS002"
                        value={m.usn}
                        onChange={(e) => handleMemberChange(idx, 'usn', e.target.value.toUpperCase())}
                        className="w-full px-2.5 py-1.5 rounded-lg bg-[#030712] border border-cyan-500/30 text-slate-100 text-xs font-mono uppercase focus:outline-none focus:border-cyan-400"
                      />
                    </div>

                    <div>
                      <label className="block text-[11px] font-medium text-slate-400 mb-1">
                        College Email <span className="text-rose-400">*</span>
                      </label>
                      <input
                        type="email"
                        required
                        placeholder={`member${idx + 2}@bmsit.in`}
                        value={m.email}
                        onChange={(e) => handleMemberChange(idx, 'email', e.target.value.toLowerCase())}
                        className="w-full px-2.5 py-1.5 rounded-lg bg-[#030712] border border-cyan-500/30 text-slate-100 text-xs font-mono lowercase focus:outline-none focus:border-cyan-400"
                      />
                    </div>

                    <div>
                      <label className="block text-[11px] font-medium text-slate-400 mb-1">
                        Phone (Optional)
                      </label>
                      <input
                        type="tel"
                        placeholder="Mobile number"
                        value={m.phone}
                        onChange={(e) => handleMemberChange(idx, 'phone', e.target.value)}
                        className="w-full px-2.5 py-1.5 rounded-lg bg-[#030712] border border-cyan-500/30 text-slate-100 text-xs font-mono focus:outline-none focus:border-cyan-400"
                      />
                    </div>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Consent Checkbox */}
          <Card className="border-cyan-500/20 bg-[#090d1a]/80 backdrop-blur-md">
            <CardContent className="py-4">
              <label className="flex items-start gap-3 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={consentGiven}
                  onChange={(e) => setConsentGiven(e.target.checked)}
                  className="mt-1 w-4 h-4 rounded border-cyan-500/40 bg-[#030712] text-cyan-500 focus:ring-0 focus:ring-offset-0 cursor-pointer"
                />
                <span className="text-xs text-slate-300 leading-relaxed">
                  I certify that all 5 squad members are eligible students of BMSIT &amp; Management,
                  and agree to adhere to all tournament regulations, clue-hunt rules, and organizer decisions.
                  <span className="text-rose-400 ml-1">*</span>
                </span>
              </label>
            </CardContent>
          </Card>

          {/* Submission Bar */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-4 rounded-xl bg-[#090d1a]/90 border border-cyan-500/30 backdrop-blur-md">
            <div className="text-xs text-slate-400">
              {isValid ? (
                <span className="text-emerald-400 flex items-center gap-1.5 font-medium">
                  <CheckCircle2 className="w-4 h-4" />
                  All 5 member details verified. Ready for submission.
                </span>
              ) : (
                <span className="text-amber-400 flex items-center gap-1.5 font-medium">
                  <AlertTriangle className="w-4 h-4" />
                  {validationErrors[0] || 'Please complete all required fields.'}
                </span>
              )}
            </div>

            <Button
              type="submit"
              variant="primary"
              size="lg"
              disabled={!isValid || isSubmitting}
              isLoading={isSubmitting}
              leftIcon={<Send className="w-4 h-4" />}
            >
              Submit Squad Registration
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
