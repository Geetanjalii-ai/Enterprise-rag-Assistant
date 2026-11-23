import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { PageHeader } from '../../components/ui/PageHeader';
import { Table, Column } from '../../components/ui/Table';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { Drawer } from '../../components/ui/Drawer';
import { Input } from '../../components/ui/Input';
import { Select } from '../../components/ui/Select';
import { ConfirmDialog } from '../../components/ui/ConfirmDialog';
import { AlertTriangle, Check, Trash2 } from 'lucide-react';
import { toast } from 'sonner';

interface QuarantinedDoc {
  id: string;
  file_name: string;
  quarantine_reason: string;
  department: string;
  visibility: string;
  min_role: string;
  created_at: string;
}

export const QuarantinePage: React.FC = () => {
  const queryClient = useQueryClient();
  const [selectedDoc, setSelectedDoc] = useState<QuarantinedDoc | null>(null);
  const [rejectingDoc, setRejectingDoc] = useState<QuarantinedDoc | null>(null);

  // Corrected labels form state
  const [title, setTitle] = useState('');
  const [dept, setDept] = useState('HR');
  const [visibility, setVisibility] = useState('company');
  const [minRole, setMinRole] = useState('member');

  const { data: quarantineList = [], isLoading } = useQuery<QuarantinedDoc[]>({
    queryKey: ['admin-quarantine'],
    queryFn: async () => {
      const res = await api.get('/admin/quarantine');
      return res.data;
    },
  });

  const releaseMutation = useMutation({
    mutationFn: async () => {
      if (!selectedDoc) return;
      await api.post(`/admin/quarantine/${selectedDoc.id}/release`, {
        title,
        department: dept,
        visibility,
        min_role: minRole,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-quarantine'] });
      toast.success('Document released from quarantine and scheduled for indexing');
      setSelectedDoc(null);
    },
    onError: () => {
      toast.error('Failed to release document');
    },
  });

  const rejectMutation = useMutation({
    mutationFn: async () => {
      if (!rejectingDoc) return;
      await api.post(`/admin/quarantine/${rejectingDoc.id}/reject`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-quarantine'] });
      toast.success('Quarantined document discarded');
      setRejectingDoc(null);
    },
    onError: () => {
      toast.error('Failed to discard document');
    },
  });

  const handleOpenRelease = (doc: QuarantinedDoc) => {
    setSelectedDoc(doc);
    setTitle(doc.file_name.replace(/\.[^/.]+$/, ''));
    setDept(doc.department || 'HR');
    setVisibility(doc.visibility || 'company');
    setMinRole(doc.min_role || 'member');
  };

  const columns: Column<QuarantinedDoc>[] = [
    {
      header: 'File Name',
      accessorKey: 'file_name',
      cell: (doc) => <span className="font-medium text-[var(--text)]">{doc.file_name}</span>,
    },
    {
      header: 'Quarantine Reason',
      accessorKey: 'quarantine_reason',
      cell: (doc) => (
        <Badge variant="status" status="quarantined">
          {doc.quarantine_reason || 'Missing metadata / Corrupt text'}
        </Badge>
      ),
    },
    {
      header: 'Department',
      accessorKey: 'department',
    },
    {
      header: 'Actions',
      cell: (doc) => (
        <div className="flex items-center gap-2 justify-end">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => handleOpenRelease(doc)}
            className="gap-1 text-[var(--pastel-mint-text)]"
          >
            <Check size={14} />
            Fix & Release
          </Button>
          <Button
            variant="destructive-outline"
            size="sm"
            onClick={() => setRejectingDoc(doc)}
          >
            <Trash2 size={14} />
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Quarantine"
        description="Review documents flagged for missing metadata, classification anomalies, or parsing issues."
      />

      <Table
        data={quarantineList}
        columns={columns}
        isLoading={isLoading}
        emptyMessage="No documents in quarantine. Everything is healthy."
      />

      {/* Release Drawer */}
      <Drawer
        isOpen={!!selectedDoc}
        onClose={() => setSelectedDoc(null)}
        title="Correct Labels & Release"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            releaseMutation.mutate();
          }}
          className="space-y-4"
        >
          <div className="p-3 bg-[var(--pastel-rose-bg)] border border-[var(--pastel-rose-text)]/20 rounded-lg text-[13px] text-[var(--pastel-rose-text)] flex items-start gap-2">
            <AlertTriangle size={16} className="shrink-0 mt-0.5" />
            <div>
              <strong>Reason:</strong> {selectedDoc?.quarantine_reason || 'Missing metadata'}
            </div>
          </div>

          <Input
            label="Document Title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
          />

          <Select
            label="Department"
            value={dept}
            onChange={(e) => setDept(e.target.value)}
            options={[
              { value: 'HR', label: 'HR' },
              { value: 'IT', label: 'IT' },
              { value: 'Finance', label: 'Finance' },
              { value: 'Legal', label: 'Legal' },
              { value: 'Company-wide', label: 'Company-wide' },
            ]}
          />

          <Select
            label="Visibility"
            value={visibility}
            onChange={(e) => setVisibility(e.target.value)}
            options={[
              { value: 'company', label: 'Company-wide' },
              { value: 'department', label: 'Department only' },
            ]}
          />

          <Select
            label="Minimum Role"
            value={minRole}
            onChange={(e) => setMinRole(e.target.value)}
            options={[
              { value: 'member', label: 'Member' },
              { value: 'manager', label: 'Manager' },
              { value: 'head', label: 'Department Head' },
            ]}
          />

          <div className="pt-4 flex justify-end gap-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setSelectedDoc(null)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              isLoading={releaseMutation.isPending}
            >
              Release & Ingest
            </Button>
          </div>
        </form>
      </Drawer>

      {/* Reject Confirmation */}
      <ConfirmDialog
        isOpen={!!rejectingDoc}
        onCancel={() => setRejectingDoc(null)}
        onConfirm={() => rejectMutation.mutate()}
        title="Discard Quarantined Document"
        description={`Are you sure you want to permanently discard "${rejectingDoc?.file_name}"? This action cannot be undone.`}
        confirmLabel="Discard Document"
        variant="destructive-outline"
      />
    </div>
  );
};
