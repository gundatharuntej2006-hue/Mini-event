import { useState, useEffect } from 'react';
import { Server, ShieldCheck, Activity, CheckCircle2, AlertTriangle, Database } from 'lucide-react';
import { Card, CardHeader, CardContent } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { PageHeader } from '../components/ui/PageHeader';
import { API_CONFIG, isLiveMode } from '../services/apiConfig';
import { apiClient } from '../services/apiClient';
import { RegistrationIntegrationSection } from '../components/settings/RegistrationIntegrationSection';

interface HealthResponse {
  status: string;
  database: string;
  version: string;
}

export function SettingsPage() {
  const [liveActive, setLiveActive] = useState(isLiveMode());
  const [isPinging, setIsPinging] = useState(false);
  const [pingResult, setPingResult] = useState<{
    success: boolean;
    latencyMs?: number;
    message?: string;
    details?: HealthResponse;
  } | null>(null);

  useEffect(() => {
    const handleModeChange = () => {
      setLiveActive(isLiveMode());
    };
    window.addEventListener('app_mode_change', handleModeChange);
    return () => window.removeEventListener('app_mode_change', handleModeChange);
  }, []);

  const handlePingBackend = async () => {
    setIsPinging(true);
    const start = performance.now();
    try {
      const res = await apiClient.get<HealthResponse>('/health');
      const elapsed = Math.round(performance.now() - start);
      if (res.success && res.data) {
        setPingResult({
          success: true,
          latencyMs: elapsed,
          message: res.message || 'FastAPI service online and database connected.',
          details: res.data,
        });
      } else {
        setPingResult({
          success: false,
          latencyMs: elapsed,
          message: res.message || 'Unexpected response format from backend.',
        });
      }
    } catch (err: any) {
      const elapsed = Math.round(performance.now() - start);
      setPingResult({
        success: false,
        latencyMs: elapsed,
        message: err.message || 'Backend connection failed or server unreachable.',
      });
    } finally {
      setIsPinging(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <PageHeader
        title="System Settings & Service Connectivity"
        subtitle="Backend API endpoints, environment parameters, operational flags, and database health telemetry"
        badge={
          <Badge variant="primary" size="sm">
            System Configuration
          </Badge>
        }
      />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Backend Connectivity Status */}
        <Card className="border-cyan-500/20 bg-[#090d1a]/80 shadow-[0_0_25px_rgba(34,211,238,0.06)] backdrop-blur-md">
          <CardHeader
            title={
              <div className="flex items-center gap-2 text-slate-100 font-bold font-display tracking-wide">
                <Server className="w-4 h-4 text-cyan-400" />
                Backend Connection Diagnostics
              </div>
            }
          />
          <CardContent className="space-y-4 text-xs">
            <div className="flex items-center justify-between py-2 border-b border-cyan-500/10">
              <span className="text-slate-400 font-mono">Configured Base URL</span>
              <span className="font-mono font-semibold text-cyan-300 bg-[#030712] border border-cyan-500/30 px-2 py-0.5 rounded">
                {API_CONFIG.baseUrl}
              </span>
            </div>

            <div className="flex items-center justify-between py-2 border-b border-cyan-500/10">
              <span className="text-slate-400 font-mono">API Prefix</span>
              <span className="font-mono font-semibold text-cyan-300 bg-[#030712] border border-cyan-500/30 px-2 py-0.5 rounded">
                {API_CONFIG.apiPrefix}
              </span>
            </div>

            <div className="flex items-center justify-between py-2 border-b border-cyan-500/10">
              <span className="text-slate-400 font-mono">Active Mode State</span>
              {liveActive ? (
                <Badge variant="success" size="sm" dot>
                  Live API (FastAPI Connected)
                </Badge>
              ) : (
                <Badge variant="warning" size="sm">
                  Demo Mode (Local Persistence)
                </Badge>
              )}
            </div>

            <div className="flex items-center justify-between py-2 border-b border-cyan-500/10">
              <span className="text-slate-400 font-mono">Target Framework</span>
              <span className="font-mono text-slate-300">
                Python FastAPI + SQLAlchemy + SQLite / PostgreSQL
              </span>
            </div>

            {/* Health Ping Result Display */}
            {pingResult && (
              <div
                className={`p-3.5 rounded-xl border text-xs space-y-1.5 backdrop-blur-md ${
                  pingResult.success
                    ? 'bg-emerald-950/40 border-emerald-500/40 text-emerald-300 shadow-[0_0_15px_rgba(16,185,129,0.15)]'
                    : 'bg-rose-950/40 border-rose-500/40 text-rose-300 shadow-[0_0_15px_rgba(244,63,94,0.15)]'
                }`}
              >
                <div className="flex items-center justify-between font-semibold">
                  <span className="flex items-center gap-1.5 font-display tracking-wider">
                    {pingResult.success ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    ) : (
                      <AlertTriangle className="w-4 h-4 text-rose-400" />
                    )}
                    {pingResult.success ? 'Health Check Passed' : 'Health Check Failed'}
                  </span>
                  <span className="font-mono text-[11px] font-normal text-cyan-400">
                    {pingResult.latencyMs}ms
                  </span>
                </div>
                <p className="text-[11px] opacity-90 font-sans">{pingResult.message}</p>
                {pingResult.details && (
                  <div className="pt-1.5 border-t border-emerald-500/20 flex items-center gap-4 text-[11px] font-mono text-emerald-200">
                    <span>Database: {pingResult.details.database}</span>
                    <span>Version: {pingResult.details.version}</span>
                  </div>
                )}
              </div>
            )}

            <div className="pt-2">
              <Button
                variant="outline"
                size="sm"
                className="w-full text-xs"
                onClick={handlePingBackend}
                isLoading={isPinging}
                leftIcon={<Activity className="w-3.5 h-3.5" />}
              >
                Ping FastAPI Health Endpoint (/api/v1/health)
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Event Rules & Configuration */}
        <Card className="border-cyan-500/20 bg-[#090d1a]/80 shadow-[0_0_25px_rgba(34,211,238,0.06)] backdrop-blur-md">
          <CardHeader
            title={
              <div className="flex items-center gap-2 text-slate-100 font-bold font-display tracking-wide">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                Tournament Master Parameters
              </div>
            }
          />
          <CardContent className="space-y-4 text-xs">
            <div className="flex items-center justify-between py-2 border-b border-cyan-500/10">
              <span className="text-slate-400 font-mono">Designated Institution</span>
              <span className="font-semibold text-slate-100 font-display">
                BMSIT &amp; Management
              </span>
            </div>

            <div className="flex items-center justify-between py-2 border-b border-cyan-500/10">
              <span className="text-slate-400 font-mono">Participating Teams</span>
              <span className="font-mono font-medium text-cyan-300">
                32 Teams (160 Students)
              </span>
            </div>

            <div className="flex items-center justify-between py-2 border-b border-cyan-500/10">
              <span className="text-slate-400 font-mono">Members Per Squad</span>
              <span className="font-mono font-medium text-cyan-300">
                5 Members Strictly Enforced
              </span>
            </div>

            <div className="flex items-center justify-between py-2 border-b border-cyan-500/10">
              <span className="text-slate-400 font-mono">Elimination Cutoffs</span>
              <span className="font-mono font-medium text-cyan-400">
                32 &rarr; 24 &rarr; 12 &rarr; 8 &rarr; 3
              </span>
            </div>

            <div className="flex items-center justify-between py-2 border-b border-cyan-500/10">
              <span className="text-slate-400 font-mono">Secret Agent Quota</span>
              <span className="font-mono font-medium text-purple-400">
                1 per Squad (32 Embedded Operatives)
              </span>
            </div>

            <div className="flex items-center justify-between py-2 border-b border-cyan-500/10">
              <span className="text-slate-400 font-mono">Database Engine</span>
              <span className="font-mono text-slate-300 flex items-center gap-1.5">
                <Database className="w-3.5 h-3.5 text-cyan-400" />
                SQLite (Development) / PostgreSQL (Production)
              </span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Google Forms & External Registration Integration Section */}
      <RegistrationIntegrationSection />
    </div>
  );
}
