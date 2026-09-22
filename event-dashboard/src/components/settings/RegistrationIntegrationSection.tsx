import { useState, useEffect, useCallback } from 'react';
import {
  Webhook,
  Copy,
  Check,
  Eye,
  EyeOff,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  Play,
  FileCode,
  Users,
} from 'lucide-react';
import { Card, CardHeader, CardContent } from '../ui/Card';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { Modal } from '../ui/Modal';
import { backendApiService } from '../../services/backendApiService';
import { authService } from '../../services/authService';
import { isLiveMode } from '../../services/apiConfig';
import { IntegrationSettings, Submission } from '../../types/integration';

export function RegistrationIntegrationSection() {
  const [settings, setSettings] = useState<IntegrationSettings | null>(null);
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [_isLoading, setIsLoading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [showSecret, setShowSecret] = useState(false);
  const [copiedUrl, setCopiedUrl] = useState(false);
  const [copiedSecret, setCopiedSecret] = useState(false);
  const [copiedScript, setCopiedScript] = useState(false);
  const [showScriptModal, setShowScriptModal] = useState(false);
  const [selectedSubmission, setSelectedSubmission] = useState<Submission | null>(null);
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);
  const [simulating, setSimulating] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const isStaff = authService.isOrganizer() || authService.isMarshal();

  const loadData = useCallback(async () => {
    if (!isLiveMode() || !isStaff) return;
    setIsLoading(true);
    try {
      const [settingsRes, submissionsRes] = await Promise.all([
        backendApiService.getIntegrationSettings(),
        backendApiService.getSubmissions(),
      ]);

      if (settingsRes.success && settingsRes.data) {
        setSettings(settingsRes.data);
      }
      if (submissionsRes.success && submissionsRes.data) {
        setSubmissions(submissionsRes.data);
      }
    } catch (err: any) {
      console.error('Failed to load integration settings:', err);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [isStaff]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleCopy = (text: string, type: 'url' | 'secret' | 'script') => {
    navigator.clipboard.writeText(text);
    if (type === 'url') {
      setCopiedUrl(true);
      setTimeout(() => setCopiedUrl(false), 2000);
    } else if (type === 'secret') {
      setCopiedSecret(true);
      setTimeout(() => setCopiedSecret(false), 2000);
    } else {
      setCopiedScript(true);
      setTimeout(() => setCopiedScript(false), 2000);
    }
  };

  const handleToggleAutoApprove = async () => {
    if (!settings) return;
    const nextVal = !settings.registration_auto_approve;
    try {
      const res = await backendApiService.updateIntegrationSettings({
        registration_auto_approve: nextVal,
      });
      if (res.success && res.data) {
        setSettings(res.data);
        setSuccessMsg(
          nextVal
            ? 'Auto-approval enabled: Valid submissions will immediately register squads.'
            : 'Manual Review enabled: Submissions will remain PENDING until approved.'
        );
        setTimeout(() => setSuccessMsg(null), 4000);
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to update approval setting.');
      setTimeout(() => setErrorMsg(null), 4000);
    }
  };

  const handleRegenerateSecret = async () => {
    if (!window.confirm('Are you sure you want to regenerate the Google Forms Webhook Secret? Any existing Apps Scripts using the old secret will need to be updated.')) {
      return;
    }
    try {
      const res = await backendApiService.updateIntegrationSettings({
        regenerate_secret: true,
      });
      if (res.success && res.data) {
        setSettings(res.data);
        setSuccessMsg('Webhook secret regenerated successfully.');
        setTimeout(() => setSuccessMsg(null), 4000);
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to regenerate secret.');
      setTimeout(() => setErrorMsg(null), 4000);
    }
  };

  const handleAction = async (id: string, action: 'approve' | 'reject' | 'retry') => {
    setActionLoadingId(id);
    try {
      const res = await backendApiService.performSubmissionAction(id, action);
      if (res.success) {
        setSuccessMsg(res.message || `Submission ${action}d successfully.`);
        setTimeout(() => setSuccessMsg(null), 4000);
        await loadData();
      } else {
        setErrorMsg(res.message || `Failed to ${action} submission.`);
        setTimeout(() => setErrorMsg(null), 4000);
      }
    } catch (err: any) {
      setErrorMsg(err.message || `Failed to ${action} submission.`);
      setTimeout(() => setErrorMsg(null), 4000);
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleSimulateTest = async () => {
    setSimulating(true);
    try {
      const res = await backendApiService.simulateGoogleFormWebhook();
      if (res.success) {
        setSuccessMsg('Test submission received and queued in audit log!');
        setTimeout(() => setSuccessMsg(null), 4000);
        await loadData();
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Simulation failed.');
      setTimeout(() => setErrorMsg(null), 4000);
    } finally {
      setSimulating(false);
    }
  };

  const filteredSubmissions = submissions.filter((s) => {
    if (statusFilter === 'ALL') return true;
    return s.status === statusFilter;
  });

  const isLocalhost = typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');
  const webhookUrl = settings?.webhook_url || '';
  const webhookSecret = settings?.webhook_secret || '';

  const displayScriptUrl = isLocalhost
    ? "https://<MY_PUBLIC_HTTPS_DOMAIN>/api/v1/integrations/google-forms/webhook"
    : (webhookUrl || "https://<MY_PUBLIC_HTTPS_DOMAIN>/api/v1/integrations/google-forms/webhook");
  const displayScriptSecret = webhookSecret || "<COPIED_FROM_EVENT_SETTINGS>";

  const googleAppsScriptCode = `/**
 * EVENT HQ BMSIT 2026 — Google Forms Automatic Team Registration
 * 
 * CRITICAL REQUIREMENT:
 * Google Apps Script runs in Google's cloud. The WEBHOOK_URL MUST be publicly
 * accessible over HTTPS. Do NOT use localhost or 127.0.0.1.
 * 
 * Paste this script in Google Forms / Google Sheets:
 * Extensions > Apps Script
 * 
 * Setup Instructions:
 * 1. Ensure WEBHOOK_URL points to your live public HTTPS endpoint:
 *    Replace <MY_PUBLIC_HTTPS_DOMAIN> with your actual tunnel domain.
 * 2. Ensure WEBHOOK_SECRET matches your Event Settings secret token.
 * 3. Save script.
 * 4. In the left sidebar, click Triggers (alarm clock icon).
 * 5. Click "+ Add Trigger".
 * 6. Choose function: onFormSubmit.
 * 7. Event source: From form (or From spreadsheet).
 * 8. Event type: On form submit.
 * 9. Save and authorize permissions.
 */

const WEBHOOK_URL = "${displayScriptUrl}";
const WEBHOOK_SECRET = "${displayScriptSecret}";

function onFormSubmit(e) {
  try {
    let payload = {
      submission_id: "gform_" + Utilities.getUuid(),
      source: "google_forms"
    };

    if (e && e.response) {
      // Direct Google Form trigger
      payload.submission_id = "gform_" + e.response.getId();
      const itemResponses = e.response.getItemResponses();
      itemResponses.forEach(function(itemResponse) {
        const title = itemResponse.getItem().getTitle();
        const response = itemResponse.getResponse();
        payload[title] = response;
      });
    } else if (e && e.namedValues) {
      // Linked Google Sheet onFormSubmit trigger
      for (const key in e.namedValues) {
        payload[key] = e.namedValues[key][0];
      }
    }

    const options = {
      method: "post",
      contentType: "application/json",
      headers: {
        "X-Webhook-Secret": WEBHOOK_SECRET
      },
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    };

    const response = UrlFetchApp.fetch(WEBHOOK_URL, options);
    Logger.log("Event HQ Webhook Response: " + response.getContentText());
  } catch (err) {
    Logger.log("Error posting to Event HQ: " + err.toString());
  }
}`;

  return (
    <div className="space-y-6">
      {/* Toast notifications */}
      {successMsg && (
        <div className="p-3.5 rounded-xl bg-emerald-950/60 border border-emerald-500/40 text-emerald-300 text-xs flex items-center gap-2 shadow-[0_0_20px_rgba(16,185,129,0.15)]">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}
      {errorMsg && (
        <div className="p-3.5 rounded-xl bg-rose-950/60 border border-rose-500/40 text-rose-300 text-xs flex items-center gap-2 shadow-[0_0_20px_rgba(244,63,94,0.15)]">
          <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Main Integration Card */}
      <Card className="border-cyan-500/20 bg-[#090d1a]/80 shadow-[0_0_25px_rgba(34,211,238,0.06)] backdrop-blur-md">
        <CardHeader
          title={
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 w-full">
              <div className="flex items-center gap-2 text-slate-100 font-bold font-display tracking-wide text-sm">
                <Webhook className="w-4 h-4 text-cyan-400" />
                Google Forms &amp; External Registration Integration
              </div>
              <div className="flex items-center gap-2">
                <Badge variant={settings?.registration_auto_approve ? 'warning' : 'primary'} size="sm">
                  {settings?.registration_auto_approve ? 'Auto-Approve Enabled' : 'Manual Review (Default)'}
                </Badge>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setIsRefreshing(true);
                    loadData();
                  }}
                  isLoading={isRefreshing}
                  leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
                >
                  Sync
                </Button>
              </div>
            </div>
          }
        />
        <CardContent className="space-y-6 text-xs">
          {/* Webhook & Public Link Controls */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Webhook URL */}
            <div className="p-3.5 rounded-xl bg-[#030712] border border-cyan-500/20 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-slate-400 font-mono text-[11px] font-medium">
                  Google Forms Webhook URL
                </span>
                <button
                  type="button"
                  onClick={() => handleCopy(webhookUrl, 'url')}
                  className="flex items-center gap-1 text-[10px] text-cyan-400 hover:text-cyan-300 font-mono transition-colors"
                >
                  {copiedUrl ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                  {copiedUrl ? 'Copied' : 'Copy URL'}
                </button>
              </div>
              <div className="font-mono text-[11px] text-cyan-300 bg-[#090d1a] border border-cyan-500/30 px-2.5 py-1.5 rounded truncate select-all">
                {webhookUrl || 'Loading endpoint...'}
              </div>
              {isLocalhost && (
                <p className="text-[10px] text-amber-400 font-sans mt-1 leading-tight">
                  ⚠️ Localhost URL detected. Google Apps Script runs in Google's cloud and cannot reach 127.0.0.1. Replace this with your public HTTPS domain or tunnel URL.
                </p>
              )}
            </div>

            {/* Webhook Secret */}
            <div className="p-3.5 rounded-xl bg-[#030712] border border-cyan-500/20 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-slate-400 font-mono text-[11px] font-medium">
                  Webhook Secret Token
                </span>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setShowSecret(!showSecret)}
                    className="text-slate-400 hover:text-slate-200"
                    title={showSecret ? 'Hide secret' : 'Show secret'}
                  >
                    {showSecret ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
                  </button>
                  <button
                    type="button"
                    onClick={() => handleCopy(webhookSecret, 'secret')}
                    className="flex items-center gap-1 text-[10px] text-cyan-400 hover:text-cyan-300 font-mono transition-colors"
                  >
                    {copiedSecret ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                    {copiedSecret ? 'Copied' : 'Copy Secret'}
                  </button>
                </div>
              </div>
              <div className="font-mono text-[11px] text-emerald-300 bg-[#090d1a] border border-cyan-500/30 px-2.5 py-1.5 rounded truncate select-all">
                {showSecret ? webhookSecret : '••••••••••••••••••••••••••••••••'}
              </div>
            </div>
          </div>

          {/* Configuration & Action Buttons Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-cyan-500/10">
            <div className="flex items-center gap-3">
              <Button
                variant={settings?.registration_auto_approve ? 'danger' : 'primary'}
                size="sm"
                onClick={handleToggleAutoApprove}
              >
                {settings?.registration_auto_approve ? 'Switch to Manual Review' : 'Enable Auto-Approve'}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowScriptModal(true)}
                leftIcon={<FileCode className="w-3.5 h-3.5 text-cyan-400" />}
              >
                Google Apps Script Setup
              </Button>
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleRegenerateSecret}
                className="text-slate-400 hover:text-rose-300 text-[11px]"
              >
                Regenerate Secret
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleSimulateTest}
                isLoading={simulating}
                leftIcon={<Play className="w-3 h-3 text-amber-400" />}
                className="text-amber-300 border-amber-500/30 hover:bg-amber-500/10 text-[11px]"
              >
                Simulate Test Submission
              </Button>
            </div>
          </div>

          {/* Metrics Overview Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
            <div className="p-3 rounded-xl bg-[#030712] border border-cyan-500/20">
              <span className="text-[10px] text-slate-400 font-mono">Total Submissions</span>
              <p className="text-lg font-bold font-mono text-cyan-300 mt-0.5">
                {settings?.metrics.total_submissions ?? submissions.length}
              </p>
            </div>
            <div className="p-3 rounded-xl bg-[#030712] border border-emerald-500/20">
              <span className="text-[10px] text-emerald-400 font-mono">Accepted &amp; Added</span>
              <p className="text-lg font-bold font-mono text-emerald-300 mt-0.5">
                {settings?.metrics.accepted_count ?? submissions.filter((s) => s.status === 'ACCEPTED').length}
              </p>
            </div>
            <div className="p-3 rounded-xl bg-[#030712] border border-amber-500/20">
              <span className="text-[10px] text-amber-400 font-mono">Pending Review</span>
              <p className="text-lg font-bold font-mono text-amber-300 mt-0.5">
                {settings?.metrics.pending_count ?? submissions.filter((s) => s.status === 'PENDING').length}
              </p>
            </div>
            <div className="p-3 rounded-xl bg-[#030712] border border-rose-500/20">
              <span className="text-[10px] text-rose-400 font-mono">Rejected / Collisions</span>
              <p className="text-lg font-bold font-mono text-rose-300 mt-0.5">
                {settings?.metrics.rejected_count ?? submissions.filter((s) => s.status === 'REJECTED').length}
              </p>
            </div>
          </div>

          {/* Submissions Audit & Review Queue */}
          <div className="space-y-3 pt-4 border-t border-cyan-500/10">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div className="flex items-center gap-2 text-slate-200 font-semibold font-display">
                <Users className="w-4 h-4 text-cyan-400" />
                Submissions Audit &amp; Approval Queue ({filteredSubmissions.length})
              </div>
              <div className="flex items-center gap-1.5">
                {['ALL', 'PENDING', 'ACCEPTED', 'REJECTED'].map((filter) => (
                  <button
                    key={filter}
                    type="button"
                    onClick={() => setStatusFilter(filter)}
                    className={`px-2 py-1 rounded text-[10px] font-mono transition-colors ${
                      statusFilter === filter
                        ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-semibold'
                        : 'text-slate-400 hover:text-slate-200 border border-transparent'
                    }`}
                  >
                    {filter}
                  </button>
                ))}
              </div>
            </div>

            {filteredSubmissions.length === 0 ? (
              <div className="p-6 text-center rounded-xl bg-[#030712] border border-cyan-500/10 text-slate-500 font-mono text-xs">
                No submissions found matching filter "{statusFilter}".
              </div>
            ) : (
              <div className="overflow-x-auto rounded-xl border border-cyan-500/20 bg-[#030712]">
                <table className="w-full text-left text-xs">
                  <thead className="bg-[#090d1a] border-b border-cyan-500/20 font-mono text-[11px] text-slate-400">
                    <tr>
                      <th className="p-3">Submitted</th>
                      <th className="p-3">Source</th>
                      <th className="p-3">Squad Name</th>
                      <th className="p-3">Leader</th>
                      <th className="p-3">Status</th>
                      <th className="p-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-cyan-500/10 font-mono text-slate-300">
                    {filteredSubmissions.map((sub) => (
                      <tr key={sub.id} className="hover:bg-cyan-500/5 transition-colors">
                        <td className="p-3 text-slate-400 text-[11px] whitespace-nowrap">
                          {new Date(sub.submitted_at).toLocaleTimeString([], {
                            hour: '2-digit',
                            minute: '2-digit',
                            month: 'short',
                            day: 'numeric',
                          })}
                        </td>
                        <td className="p-3">
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-300">
                            {sub.source === 'google_forms' ? 'Google Forms' : 'Public Web'}
                          </span>
                        </td>
                        <td className="p-3 font-semibold text-slate-100 font-sans">
                          {sub.team_name}
                        </td>
                        <td className="p-3">
                          <span className="text-cyan-300">{sub.leader_name}</span>
                          <span className="block text-[10px] text-slate-400">{sub.leader_usn}</span>
                        </td>
                        <td className="p-3">
                          {sub.status === 'ACCEPTED' && (
                            <Badge variant="success" size="sm" dot>
                              Accepted
                            </Badge>
                          )}
                          {sub.status === 'PENDING' && (
                            <Badge variant="warning" size="sm" dot>
                              Pending Review
                            </Badge>
                          )}
                          {sub.status === 'REJECTED' && (
                            <Badge variant="danger" size="sm">
                              Rejected
                            </Badge>
                          )}
                          {sub.error_message && (
                            <span className="block text-[10px] text-rose-400 font-sans mt-1 max-w-[200px] truncate" title={sub.error_message}>
                              {sub.error_message}
                            </span>
                          )}
                        </td>
                        <td className="p-3 text-right whitespace-nowrap space-x-1.5">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setSelectedSubmission(sub)}
                            className="text-[10px] py-0.5 px-2"
                          >
                            Roster
                          </Button>

                          {sub.status === 'PENDING' && (
                            <>
                              <Button
                                variant="primary"
                                size="sm"
                                onClick={() => handleAction(sub.id, 'approve')}
                                isLoading={actionLoadingId === sub.id}
                                className="text-[10px] py-0.5 px-2 bg-emerald-600 hover:bg-emerald-500 border-emerald-500/50"
                              >
                                Approve
                              </Button>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => handleAction(sub.id, 'reject')}
                                isLoading={actionLoadingId === sub.id}
                                className="text-[10px] py-0.5 px-2 text-rose-400 border-rose-500/30 hover:bg-rose-500/10"
                              >
                                Reject
                              </Button>
                            </>
                          )}

                          {sub.status === 'REJECTED' && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleAction(sub.id, 'retry')}
                              isLoading={actionLoadingId === sub.id}
                              className="text-[10px] py-0.5 px-2 text-amber-300 border-amber-500/30 hover:bg-amber-500/10"
                            >
                              Retry
                            </Button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Roster Inspection Modal */}
      {selectedSubmission && (
        <Modal
          isOpen={true}
          onClose={() => setSelectedSubmission(null)}
          title={`Squad Submission Roster: ${selectedSubmission.team_name}`}
          maxWidth="2xl"
        >
          <div className="space-y-4 text-xs">
            <div className="p-3 rounded-xl bg-[#030712] border border-cyan-500/20 flex items-center justify-between">
              <div>
                <span className="text-slate-400 font-mono text-[10px]">Reference ID</span>
                <p className="font-mono text-cyan-300 font-semibold">{selectedSubmission.external_submission_id}</p>
              </div>
              <Badge
                variant={
                  selectedSubmission.status === 'ACCEPTED'
                    ? 'success'
                    : selectedSubmission.status === 'PENDING'
                    ? 'warning'
                    : 'danger'
                }
              >
                {selectedSubmission.status}
              </Badge>
            </div>

            {selectedSubmission.error_message && (
              <div className="p-3 rounded-xl bg-rose-950/40 border border-rose-500/40 text-rose-300 text-xs">
                <span className="font-semibold block font-display">Validation Note:</span>
                {selectedSubmission.error_message}
              </div>
            )}

            <div className="space-y-2">
              <h4 className="font-semibold text-slate-200 font-display">5 Submitted Squad Members:</h4>
              <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
                {(selectedSubmission.raw_payload?.members || []).map((m: any, idx: number) => (
                  <div
                    key={idx}
                    className="p-2.5 rounded-lg bg-[#030712] border border-cyan-500/10 flex items-center justify-between"
                  >
                    <div className="flex items-center gap-2">
                      <span className="w-5 h-5 rounded-full bg-cyan-500/20 text-cyan-400 flex items-center justify-center font-mono text-[10px]">
                        {idx + 1}
                      </span>
                      <div>
                        <span className="font-semibold text-slate-100">{m.name}</span>
                        <span className="text-slate-400 font-mono text-[11px] ml-2">({m.usn})</span>
                        <span className="block text-[10px] text-slate-400 font-mono">{m.email}</span>
                      </div>
                    </div>
                    <Badge variant={m.role === 'Leader' ? 'warning' : 'primary'} size="sm">
                      {m.role || 'Member'}
                    </Badge>
                  </div>
                ))}
              </div>
            </div>

            <div className="pt-3 border-t border-cyan-500/10 flex justify-end gap-2">
              <Button variant="outline" size="sm" onClick={() => setSelectedSubmission(null)}>
                Close
              </Button>
              {selectedSubmission.status === 'PENDING' && (
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => {
                    handleAction(selectedSubmission.id, 'approve');
                    setSelectedSubmission(null);
                  }}
                >
                  Approve &amp; Register Squad
                </Button>
              )}
            </div>
          </div>
        </Modal>
      )}

      {/* Google Apps Script Modal */}
      {showScriptModal && (
        <Modal
          isOpen={true}
          onClose={() => setShowScriptModal(false)}
          title="Google Forms / Sheets Apps Script Setup Guide"
          maxWidth="3xl"
        >
          <div className="space-y-4 text-xs">
            <div className="space-y-2 text-slate-300">
              <p>
                Follow these 4 simple steps to connect any Google Form to EVENT HQ:
              </p>
              <ol className="list-decimal list-inside space-y-1 text-slate-400 pl-1 font-sans">
                <li>Create your Google Form with: Squad Name, Leader Name/USN/Email, and Members 2-5.</li>
                <li>In Google Forms or the linked Google Sheet, open <strong className="text-cyan-300">Extensions &gt; Apps Script</strong>.</li>
                <li>Replace the code with the script below (Webhook URL &amp; Secret are already configured for you).</li>
                <li>Click <strong className="text-cyan-300">Triggers (clock icon)</strong> &gt; <strong className="text-cyan-300">Add Trigger</strong>: choose <code className="text-cyan-300">onFormSubmit</code> and Event Type <code className="text-cyan-300">On form submit</code>.</li>
              </ol>
            </div>

            <div className="relative">
              <div className="flex justify-between items-center bg-[#090d1a] border border-cyan-500/30 px-3 py-1.5 rounded-t-lg text-slate-400 font-mono text-[10px]">
                <span>google_forms_eventhq_webhook.gs</span>
                <button
                  type="button"
                  onClick={() => handleCopy(googleAppsScriptCode, 'script')}
                  className="flex items-center gap-1 text-cyan-400 hover:text-cyan-300"
                >
                  {copiedScript ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                  {copiedScript ? 'Copied' : 'Copy Script'}
                </button>
              </div>
              <pre className="p-3 bg-[#030712] border border-t-0 border-cyan-500/20 rounded-b-lg font-mono text-[11px] text-cyan-300 overflow-x-auto max-h-72 select-all">
                {googleAppsScriptCode}
              </pre>
            </div>

            <div className="pt-2 flex justify-end">
              <Button variant="outline" size="sm" onClick={() => setShowScriptModal(false)}>
                Done
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
