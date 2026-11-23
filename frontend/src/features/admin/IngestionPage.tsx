import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { PageHeader } from '../../components/ui/PageHeader';
import { StatCard } from '../../components/ui/StatCard';
import { Table, Column } from '../../components/ui/Table';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { Drawer } from '../../components/ui/Drawer';
import { PlayCircle, CheckCircle2, Clock, FileCheck, AlertCircle } from 'lucide-react';
import { format } from 'date-fns';
import { toast } from 'sonner';

interface IngestionRun {
  id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  total_files: number;
  processed_files: number;
  failed_files: number;
  started_at: string;
  finished_at: string | null;
  logs?: string[];
}

export const IngestionPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [selectedRun, setSelectedRun] = useState<IngestionRun | null>(null);

  const { data: runs = [], isLoading } = useQuery<IngestionRun[]>({
    queryKey: ['admin-ingestion-runs'],
    queryFn: async () => {
      const res = await api.get('/admin/ingestion/runs');
      return res.data;
    },
    // Poll every 2 seconds if any run is running or pending
    refetchInterval: (query) => {
      const hasActive = query.state.data?.some(
        (r) => r.status === 'running' || r.status === 'pending'
      );
      return hasActive ? 2000 : false;
    },
  });

  const startRunMutation = useMutation({
    mutationFn: async () => {
      const res = await api.post('/admin/ingestion/runs');
      return res.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['admin-ingestion-runs'] });
      toast.success(`Ingestion run #${data.id.slice(0, 8)} started`);
    },
    onError: () => {
      toast.error('Failed to start ingestion run');
    },
  });

  // Calculate summary stats
  const totalRuns = runs.length;
  const lastRun = runs[0];
  const totalFilesIngested = runs.reduce((acc, r) => acc + (r.processed_files || 0), 0);
  const successRate =
    totalRuns > 0
      ? Math.round(
          (runs.filter((r) => r.status === 'completed').length / totalRuns) * 100
        )
      : 100;

  const columns: Column<IngestionRun>[] = [
    {
      header: 'Run ID',
      accessorKey: 'id',
      cell: (r) => <span className="font-mono text-[12px]">{r.id.slice(0, 8)}</span>,
    },
    {
      header: 'Status',
      accessorKey: 'status',
      cell: (r) => (
        <Badge
          variant="status"
          status={r.status === 'completed' ? 'processed' : r.status === 'failed' ? 'failed' : 'pending'}
        >
          {r.status}
        </Badge>
      ),
    },
    {
      header: 'Total Files',
      accessorKey: 'total_files',
    },
    {
      header: 'Processed',
      accessorKey: 'processed_files',
      cell: (r) => <span className="text-[var(--pastel-mint-text)] font-medium">{r.processed_files}</span>,
    },
    {
      header: 'Failed',
      accessorKey: 'failed_files',
      cell: (r) => (
        <span className={r.failed_files > 0 ? 'text-[var(--pastel-rose-text)] font-medium' : ''}>
          {r.failed_files}
        </span>
      ),
    },
    {
      header: 'Started At',
      accessorKey: 'started_at',
      cell: (r) => (
        <span className="text-[12px] text-[var(--text-muted)]">
          {r.started_at ? format(new Date(r.started_at), 'MMM d, yyyy HH:mm') : '—'}
        </span>
      ),
    },
    {
      header: 'Actions',
      cell: (r) => (
        <Button
          variant="secondary"
          size="sm"
          onClick={() => setSelectedRun(r)}
        >
          View Details
        </Button>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Ingestion Runs"
        description="Monitor automated indexing, vector chunking, and worker status."
        action={
          <Button
            variant="primary"
            onClick={() => startRunMutation.mutate()}
            isLoading={startRunMutation.isPending}
            className="gap-2"
          >
            <PlayCircle size={16} strokeWidth={1.5} />
            Run Ingestion
          </Button>
        }
      />

      {/* 4 Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatCard
          label="Total Runs"
          value={totalRuns}
          icon={<Clock size={16} />}
        />
        <StatCard
          label="Last Run Status"
          value={lastRun ? lastRun.status : 'None'}
          icon={<CheckCircle2 size={16} />}
        />
        <StatCard
          label="Ingested Files"
          value={totalFilesIngested}
          icon={<FileCheck size={16} />}
        />
        <StatCard
          label="Success Rate"
          value={`${successRate}%`}
          icon={<AlertCircle size={16} />}
        />
      </div>

      {/* Runs Table */}
      <Table
        data={runs}
        columns={columns}
        isLoading={isLoading}
        emptyMessage="No ingestion runs recorded yet."
      />

      {/* Details Drawer */}
      <Drawer
        isOpen={!!selectedRun}
        onClose={() => setSelectedRun(null)}
        title={`Run Details #${selectedRun?.id.slice(0, 8)}`}
      >
        {selectedRun && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3 p-3 bg-[var(--surface-muted)] rounded-lg text-[13px]">
              <div>
                <span className="text-[var(--text-subtle)] block">Status:</span>
                <span className="font-medium capitalize">{selectedRun.status}</span>
              </div>
              <div>
                <span className="text-[var(--text-subtle)] block">Processed:</span>
                <span className="font-medium">{selectedRun.processed_files} / {selectedRun.total_files}</span>
              </div>
            </div>

            <div>
              <h4 className="text-[12px] uppercase font-semibold text-[var(--text-subtle)] tracking-wider mb-2">
                Execution Logs
              </h4>
              <div className="p-3 bg-[var(--surface)] border border-[var(--border)] rounded-lg font-mono text-[12px] space-y-1 max-h-96 overflow-y-auto">
                {selectedRun.logs && selectedRun.logs.length > 0 ? (
                  selectedRun.logs.map((line, idx) => (
                    <div key={idx} className="text-[var(--text-muted)]">
                      {line}
                    </div>
                  ))
                ) : (
                  <div className="text-[var(--text-subtle)] italic">
                    All chunks indexed into Qdrant and registered in Neon database successfully.
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </Drawer>
    </div>
  );
};
