import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { PageHeader } from '../../components/ui/PageHeader';
import { Table, Column } from '../../components/ui/Table';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { Select } from '../../components/ui/Select';
import { Drawer } from '../../components/ui/Drawer';
import { format } from 'date-fns';
import { ChevronLeft, ChevronRight, Eye } from 'lucide-react';

interface AuditLogItem {
  id: string;
  user_email: string;
  action: string;
  resource_type: string;
  resource_id?: string;
  outcome: 'answered' | 'blocked' | 'not_found' | 'error' | 'success';
  timestamp: string;
  metadata?: Record<string, any>;
}

export const AuditPage: React.FC = () => {
  const [page, setPage] = useState(1);
  const [outcome, setOutcome] = useState('');
  const [selectedEntry, setSelectedEntry] = useState<AuditLogItem | null>(null);

  const { data, isLoading } = useQuery<{ items: AuditLogItem[]; total: number }>({
    queryKey: ['admin-audit', page, outcome],
    queryFn: async () => {
      const res = await api.get('/admin/audit', {
        params: {
          page,
          outcome: outcome || undefined,
          limit: 25,
        },
      });
      return res.data;
    },
  });

  const logs = data?.items || [];
  const total = data?.total || 0;
  const totalPages = Math.ceil(total / 25) || 1;

  const columns: Column<AuditLogItem>[] = [
    {
      header: 'Timestamp',
      accessorKey: 'timestamp',
      cell: (item) => (
        <span className="text-[12px] text-[var(--text-muted)]">
          {item.timestamp ? format(new Date(item.timestamp), 'MMM d, yyyy HH:mm:ss') : '—'}
        </span>
      ),
    },
    {
      header: 'User',
      accessorKey: 'user_email',
      cell: (item) => <span className="font-medium text-[13px]">{item.user_email}</span>,
    },
    {
      header: 'Action',
      accessorKey: 'action',
      cell: (item) => (
        <span className="font-mono text-[12px] text-[var(--text-muted)]">{item.action}</span>
      ),
    },
    {
      header: 'Outcome',
      accessorKey: 'outcome',
      cell: (item) => (
        <Badge
          variant="outcome"
          outcome={item.outcome === 'success' ? 'answered' : (item.outcome as any)}
        >
          {item.outcome}
        </Badge>
      ),
    },
    {
      header: 'Details',
      cell: (item) => (
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setSelectedEntry(item)}
          title="Inspect audit event"
        >
          <Eye size={14} />
        </Button>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Audit Log"
        description="Tamper-evident record of query resolutions, ACL checks, and administrative activities."
      />

      {/* Filter */}
      <div className="flex items-center justify-between mb-4 bg-[var(--surface)] p-3 rounded-xl border border-[var(--border)]">
        <div className="flex items-center gap-3">
          <Select
            value={outcome}
            onChange={(e) => {
              setOutcome(e.target.value);
              setPage(1);
            }}
            className="w-44"
            options={[
              { value: '', label: 'All Outcomes' },
              { value: 'answered', label: 'Answered' },
              { value: 'blocked', label: 'Blocked' },
              { value: 'not_found', label: 'Not Found' },
              { value: 'error', label: 'Error' },
            ]}
          />
        </div>

        {/* Pagination buttons */}
        <div className="flex items-center gap-2 text-[13px] text-[var(--text-muted)]">
          <span>Page {page} of {totalPages}</span>
          <Button
            variant="secondary"
            size="sm"
            disabled={page <= 1}
            onClick={() => setPage(page - 1)}
          >
            <ChevronLeft size={14} />
          </Button>
          <Button
            variant="secondary"
            size="sm"
            disabled={page >= totalPages}
            onClick={() => setPage(page + 1)}
          >
            <ChevronRight size={14} />
          </Button>
        </div>
      </div>

      <Table
        data={logs}
        columns={columns}
        isLoading={isLoading}
        emptyMessage="No audit log events recorded yet."
      />

      {/* Detail Drawer */}
      <Drawer
        isOpen={!!selectedEntry}
        onClose={() => setSelectedEntry(null)}
        title="Audit Event Details"
      >
        {selectedEntry && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3 p-3 bg-[var(--surface-muted)] rounded-lg text-[13px]">
              <div>
                <span className="text-[var(--text-subtle)] block">User:</span>
                <span className="font-medium">{selectedEntry.user_email}</span>
              </div>
              <div>
                <span className="text-[var(--text-subtle)] block">Outcome:</span>
                <Badge
                  variant="outcome"
                  outcome={selectedEntry.outcome === 'success' ? 'answered' : (selectedEntry.outcome as any)}
                >
                  {selectedEntry.outcome}
                </Badge>
              </div>
              <div>
                <span className="text-[var(--text-subtle)] block">Action:</span>
                <span className="font-mono">{selectedEntry.action}</span>
              </div>
              <div>
                <span className="text-[var(--text-subtle)] block">Timestamp:</span>
                <span>{selectedEntry.timestamp}</span>
              </div>
            </div>

            <div>
              <h4 className="text-[12px] uppercase font-semibold text-[var(--text-subtle)] tracking-wider mb-2">
                Metadata & Payload
              </h4>
              <pre className="p-3 bg-[var(--surface)] border border-[var(--border)] rounded-lg font-mono text-[12px] overflow-x-auto text-[var(--text-muted)]">
                {JSON.stringify(selectedEntry.metadata || {}, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </Drawer>
    </div>
  );
};
