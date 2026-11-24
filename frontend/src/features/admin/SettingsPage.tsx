import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { PageHeader } from '../../components/ui/PageHeader';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { Select } from '../../components/ui/Select';
import { Badge } from '../../components/ui/Badge';
import {
  Cpu,
  ShieldCheck,
  Activity,
  Database,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Save,
  Server,
  Zap,
} from 'lucide-react';
import { toast } from 'sonner';

interface SystemSettings {
  app_env: string;
  log_level: string;
  cors_origins: string;
  access_token_minutes: number;
  refresh_token_days: number;
  groq_model: string;
  groq_fallback_model: string;
  llm_context_token_budget: number;
  enable_guardrails: boolean;
  guard_model_name: string;
  prompt_guard_model: string;
  embedding_model: string;
  embedding_dim: number;
  reranker_model: string;
  sparse_model: string;
  langsmith_tracing: boolean;
  langsmith_project: string;
  langsmith_agent_id: string;
  langsmith_endpoint: string;
  storage_backend: string;
  qdrant_collection: string;
  b2_bucket_name: string;
  local_storage_dir: string;
}

interface ServiceHealth {
  service: string;
  status: 'operational' | 'degraded' | 'down' | 'idle';
  latency_ms: number;
  detail: string;
}

const TABS = [
  { id: 'rag', label: 'RAG & Models', icon: Cpu },
  { id: 'guardrails', label: 'Safety & Guardrails', icon: ShieldCheck },
  { id: 'observability', label: 'Observability & Tracing', icon: Activity },
  { id: 'storage', label: 'Storage & Database', icon: Database },
  { id: 'diagnostics', label: 'System Diagnostics', icon: Server },
];

export const SettingsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState('rag');

  // Form state
  const [form, setForm] = useState<Partial<SystemSettings>>({});

  const { data: settings, isLoading } = useQuery<SystemSettings>({
    queryKey: ['admin-settings'],
    queryFn: async () => {
      const res = await api.get('/admin/settings');
      return res.data;
    },
  });

  // Sync initial query values to local form state
  React.useEffect(() => {
    if (settings) {
      setForm(settings);
    }
  }, [settings]);

  const updateMutation = useMutation({
    mutationFn: async (payload: Partial<SystemSettings>) => {
      await api.patch('/admin/settings', payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-settings'] });
      toast.success('System configuration updated successfully');
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || 'Failed to update settings');
    },
  });

  const {
    data: diagnostics,
    isLoading: isDiagLoading,
    refetch: runDiagnostics,
  } = useQuery<{ services: ServiceHealth[]; timestamp: string }>({
    queryKey: ['admin-diagnostics'],
    queryFn: async () => {
      const res = await api.post('/admin/settings/test-connectivity');
      return res.data;
    },
    enabled: activeTab === 'diagnostics',
  });

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    updateMutation.mutate({
      groq_model: form.groq_model,
      groq_fallback_model: form.groq_fallback_model,
      llm_context_token_budget: Number(form.llm_context_token_budget),
      enable_guardrails: Boolean(form.enable_guardrails),
      guard_model_name: form.guard_model_name,
      prompt_guard_model: form.prompt_guard_model,
      langsmith_tracing: Boolean(form.langsmith_tracing),
      langsmith_project: form.langsmith_project,
      log_level: form.log_level,
    });
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Settings & Diagnostics"
        description="Configure runtime RAG parameters, model providers, security guardrails, distributed tracing, and verify system connectivity."
        action={
          <Button
            variant="primary"
            className="gap-2"
            onClick={handleSave}
            isLoading={updateMutation.isPending}
          >
            <Save size={16} strokeWidth={1.5} />
            Save Configuration
          </Button>
        }
      />

      {/* Tabs */}
      <div className="flex items-center gap-1.5 border-b border-[var(--border)] overflow-x-auto pb-1">
        {TABS.map((t) => {
          const Icon = t.icon;
          const isActive = activeTab === t.id;
          return (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-[13px] font-medium transition-colors whitespace-nowrap ${
                isActive
                  ? 'bg-[var(--ink)] text-white shadow-sm'
                  : 'text-[var(--text-muted)] hover:bg-[var(--surface-muted)] hover:text-[var(--text)]'
              }`}
            >
              <Icon size={15} strokeWidth={1.5} />
              {t.label}
            </button>
          );
        })}
      </div>

      {isLoading ? (
        <div className="p-12 text-center text-[var(--text-subtle)] text-[14px]">
          Loading system configuration...
        </div>
      ) : (
        <div className="bg-[var(--surface)] border border-[var(--border)] rounded-2xl p-6 shadow-sm">
          {/* TAB 1: RAG & Models */}
          {activeTab === 'rag' && (
            <div className="space-y-6">
              <div>
                <h3 className="font-semibold text-[16px] text-[var(--text)]">LLM Generation Engine</h3>
                <p className="text-[13px] text-[var(--text-subtle)] mt-0.5">
                  Tune primary response generation, failover models, and context window budgets.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Select
                  label="Primary Generation Model (Groq)"
                  value={form.groq_model || 'qwen/qwen3.8-27b'}
                  onChange={(e) => setForm({ ...form, groq_model: e.target.value })}
                  options={[
                    { value: 'qwen/qwen3.8-27b', label: 'Qwen 3.8 27B (Fast, high enterprise reasoning)' },
                    { value: 'llama-3.3-70b-versatile', label: 'Llama 3.3 70B Versatile' },
                    { value: 'llama-3.1-8b-instant', label: 'Llama 3.1 8B Instant (Ultra-fast)' },
                    { value: 'mixtral-8x7b-32768', label: 'Mixtral 8x7B (32k context)' },
                  ]}
                />

                <Select
                  label="Fallback Generation Model"
                  value={form.groq_fallback_model || 'qwen/qwen3.8-27b'}
                  onChange={(e) => setForm({ ...form, groq_fallback_model: e.target.value })}
                  options={[
                    { value: 'qwen/qwen3.8-27b', label: 'Qwen 3.8 27B' },
                    { value: 'llama-3.3-70b-versatile', label: 'Llama 3.3 70B' },
                    { value: 'llama-3.1-8b-instant', label: 'Llama 3.1 8B' },
                  ]}
                />

                <Input
                  label="Context Window Token Budget"
                  type="number"
                  placeholder="3000"
                  value={form.llm_context_token_budget ?? 3000}
                  onChange={(e) => setForm({ ...form, llm_context_token_budget: Number(e.target.value) })}
                />

                <Select
                  label="Application Logging Level"
                  value={form.log_level || 'INFO'}
                  onChange={(e) => setForm({ ...form, log_level: e.target.value })}
                  options={[
                    { value: 'DEBUG', label: 'DEBUG (Detailed traces & payloads)' },
                    { value: 'INFO', label: 'INFO (Normal production logging)' },
                    { value: 'WARNING', label: 'WARNING (Warnings and errors only)' },
                    { value: 'ERROR', label: 'ERROR (Critical failures)' },
                  ]}
                />
              </div>

              <div className="pt-4 border-t border-[var(--border)]">
                <h4 className="font-medium text-[14px] text-[var(--text)] mb-3">Vector & Embedding Specifications</h4>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div className="p-3 bg-[var(--surface-muted)] rounded-xl border border-[var(--border)]">
                    <span className="text-[11px] text-[var(--text-subtle)] uppercase tracking-wider block">Dense Model</span>
                    <strong className="text-[13px] text-[var(--text)] mt-0.5 block">{settings?.embedding_model}</strong>
                    <span className="text-[11px] text-[var(--text-subtle)]">{settings?.embedding_dim} dimensions</span>
                  </div>
                  <div className="p-3 bg-[var(--surface-muted)] rounded-xl border border-[var(--border)]">
                    <span className="text-[11px] text-[var(--text-subtle)] uppercase tracking-wider block">Sparse Model</span>
                    <strong className="text-[13px] text-[var(--text)] mt-0.5 block">{settings?.sparse_model}</strong>
                    <span className="text-[11px] text-[var(--text-subtle)]">FastEmbed BM25</span>
                  </div>
                  <div className="p-3 bg-[var(--surface-muted)] rounded-xl border border-[var(--border)]">
                    <span className="text-[11px] text-[var(--text-subtle)] uppercase tracking-wider block">Cross-Encoder</span>
                    <strong className="text-[13px] text-[var(--text)] mt-0.5 block">{settings?.reranker_model}</strong>
                    <span className="text-[11px] text-[var(--text-subtle)]">Multilingual Reranker</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: Safety & Guardrails */}
          {activeTab === 'guardrails' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-[16px] text-[var(--text)]">Safety & Input/Output Guardrails</h3>
                  <p className="text-[13px] text-[var(--text-subtle)] mt-0.5">
                    Prevent prompt injections, jailbreaks, and credential leaks before answers reach the employee.
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[13px] font-medium text-[var(--text)]">Guardrails Status:</span>
                  <button
                    type="button"
                    onClick={() => setForm({ ...form, enable_guardrails: !form.enable_guardrails })}
                    className={`px-3 py-1.5 rounded-lg text-[12px] font-semibold transition-colors ${
                      form.enable_guardrails
                        ? 'bg-[var(--pastel-mint-bg)] text-[var(--pastel-mint-text)] border border-emerald-300'
                        : 'bg-[var(--pastel-rose-bg)] text-[var(--pastel-rose-text)] border border-rose-300'
                    }`}
                  >
                    {form.enable_guardrails ? 'ENABLED (100% Protection)' : 'DISABLED'}
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Input
                  label="Input Prompt Guard Model"
                  value={form.prompt_guard_model || 'meta-llama/llama-prompt-guard-2-86m'}
                  onChange={(e) => setForm({ ...form, prompt_guard_model: e.target.value })}
                />

                <Input
                  label="Output Safeguard Model"
                  value={form.guard_model_name || 'openai/gpt-oss-safeguard-20b'}
                  onChange={(e) => setForm({ ...form, guard_model_name: e.target.value })}
                />
              </div>

              <div className="p-4 bg-[var(--surface-muted)] rounded-xl border border-[var(--border)] text-[13px] space-y-2">
                <div className="flex items-center gap-2 font-medium text-[var(--text)]">
                  <ShieldCheck size={16} className="text-emerald-600" />
                  Dual-Layer Guardrail Architecture Active
                </div>
                <p className="text-[var(--text-subtle)] leading-relaxed">
                  1. <strong>Input Inspection:</strong> Incoming queries are evaluated for prompt jailbreaks, adversarial prefixes, and system-prompt leak attempts.<br />
                  2. <strong>Output Redaction:</strong> Model responses are scanned to prevent accidental generation of internal API keys, passwords, or PII.
                </p>
              </div>
            </div>
          )}

          {/* TAB 3: Observability & Tracing */}
          {activeTab === 'observability' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-[16px] text-[var(--text)]">LangSmith Distributed Tracing</h3>
                  <p className="text-[13px] text-[var(--text-subtle)] mt-0.5">
                    Live telemetry tracing of embeddings, hybrid retriever queries, and LLM completions.
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[13px] font-medium text-[var(--text)]">Tracing:</span>
                  <button
                    type="button"
                    onClick={() => setForm({ ...form, langsmith_tracing: !form.langsmith_tracing })}
                    className={`px-3 py-1.5 rounded-lg text-[12px] font-semibold transition-colors ${
                      form.langsmith_tracing
                        ? 'bg-[var(--pastel-lavender-bg)] text-[var(--pastel-lavender-text)] border border-purple-300'
                        : 'bg-[var(--surface-muted)] text-[var(--text-subtle)] border border-gray-300'
                    }`}
                  >
                    {form.langsmith_tracing ? 'LIVE TRACING ON' : 'DISABLED'}
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Input
                  label="LangSmith Project Name"
                  value={form.langsmith_project || 'tracy-development'}
                  onChange={(e) => setForm({ ...form, langsmith_project: e.target.value })}
                />

                <Input
                  label="LangSmith Agent ID"
                  value={form.langsmith_agent_id || 'tracy'}
                  disabled
                />

                <Input
                  label="LangSmith Endpoint"
                  value={form.langsmith_endpoint || 'https://api.smith.langchain.com'}
                  disabled
                  className="md:col-span-2"
                />
              </div>

              <div className="p-4 bg-[var(--surface-muted)] rounded-xl border border-[var(--border)] flex items-center justify-between">
                <div>
                  <h4 className="font-medium text-[13px] text-[var(--text)]">Cloud Dashboard Access</h4>
                  <p className="text-[12px] text-[var(--text-subtle)]">
                    Inspect individual span latencies, token graphs, and user runs directly in LangSmith.
                  </p>
                </div>
                <a
                  href="https://smith.langchain.com"
                  target="_blank"
                  rel="noreferrer"
                  className="px-3 py-1.5 rounded-lg bg-[var(--ink)] text-white text-[12px] font-medium hover:opacity-90 transition-opacity"
                >
                  Open LangSmith
                </a>
              </div>
            </div>
          )}

          {/* TAB 4: Storage & Database */}
          {activeTab === 'storage' && (
            <div className="space-y-6">
              <div>
                <h3 className="font-semibold text-[16px] text-[var(--text)]">Storage & Vector Store Backend</h3>
                <p className="text-[13px] text-[var(--text-subtle)] mt-0.5">
                  Object storage buckets and vector database collections.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-[13px] font-medium text-[var(--text)] block mb-1.5">Storage Backend</label>
                  <div className="p-2.5 bg-[var(--surface-muted)] border border-[var(--border)] rounded-lg text-[13px] font-mono text-[var(--text)]">
                    {settings?.storage_backend === 'b2' ? 'Backblaze B2 (S3-Compatible Cloud)' : 'Local File System'}
                  </div>
                </div>

                <div>
                  <label className="text-[13px] font-medium text-[var(--text)] block mb-1.5">Qdrant Collection</label>
                  <div className="p-2.5 bg-[var(--surface-muted)] border border-[var(--border)] rounded-lg text-[13px] font-mono text-[var(--text)]">
                    {settings?.qdrant_collection}
                  </div>
                </div>

                <div>
                  <label className="text-[13px] font-medium text-[var(--text)] block mb-1.5">Cloud Storage Bucket</label>
                  <div className="p-2.5 bg-[var(--surface-muted)] border border-[var(--border)] rounded-lg text-[13px] font-mono text-[var(--text)]">
                    {settings?.b2_bucket_name || 'N/A'}
                  </div>
                </div>

                <div>
                  <label className="text-[13px] font-medium text-[var(--text)] block mb-1.5">Local Storage Path</label>
                  <div className="p-2.5 bg-[var(--surface-muted)] border border-[var(--border)] rounded-lg text-[13px] font-mono text-[var(--text)]">
                    {settings?.local_storage_dir}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 5: Live System Diagnostics */}
          {activeTab === 'diagnostics' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-[16px] text-[var(--text)]">End-to-End Service Health</h3>
                  <p className="text-[13px] text-[var(--text-subtle)] mt-0.5">
                    Live ping and connectivity tests across database, vector search, embeddings, LLM cloud, and storage.
                  </p>
                </div>
                <Button
                  variant="secondary"
                  className="gap-2"
                  onClick={() => runDiagnostics()}
                  isLoading={isDiagLoading}
                >
                  <RefreshCw size={15} />
                  Run Diagnostics
                </Button>
              </div>

              {isDiagLoading ? (
                <div className="p-8 text-center text-[var(--text-subtle)] text-[14px]">
                  Testing connections to Neon, Qdrant, Jina, Groq, and Storage...
                </div>
              ) : diagnostics?.services ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {diagnostics.services.map((svc) => {
                    const isOk = svc.status === 'operational';
                    return (
                      <div
                        key={svc.service}
                        className="p-4 bg-[var(--surface-muted)] rounded-xl border border-[var(--border)] flex items-start justify-between gap-3"
                      >
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            {isOk ? (
                              <CheckCircle2 size={16} className="text-emerald-500" />
                            ) : (
                              <AlertCircle size={16} className="text-amber-500" />
                            )}
                            <strong className="text-[14px] text-[var(--text)]">{svc.service}</strong>
                          </div>
                          <p className="text-[12px] text-[var(--text-subtle)] pl-6">{svc.detail}</p>
                        </div>
                        <div className="text-right shrink-0">
                          <Badge variant="status" status={isOk ? 'active' : 'quarantined'}>
                            {svc.status}
                          </Badge>
                          {svc.latency_ms > 0 && (
                            <p className="text-[11px] text-[var(--text-subtle)] mt-1 font-mono flex items-center justify-end gap-1">
                              <Zap size={11} /> {svc.latency_ms} ms
                            </p>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="p-8 text-center text-[var(--text-subtle)] text-[14px]">
                  Click "Run Diagnostics" to check service connectivity.
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
