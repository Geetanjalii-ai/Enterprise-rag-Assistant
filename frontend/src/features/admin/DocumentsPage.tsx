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
import { Search, Upload, RefreshCw, Archive, FileText, ShieldCheck, Tag, Calendar, Eye } from 'lucide-react';
import { format } from 'date-fns';
import { toast } from 'sonner';

interface DocumentItem {
  id: string;
  title: string;
  department_id: string;
  department_code: string;
  department_name: string;
  visibility: string;
  min_role_level: number;
  doc_type: string;
  version: string;
  status: 'active' | 'archived' | 'quarantined';
  effective_date: string | null;
  expiration_date: string | null;
  created_at: string;
}

const DEPARTMENTS = ['All', 'HR', 'Finance', 'IT', 'Engineering', 'Sales', 'Legal', 'Company-wide'];

export const DocumentsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState('All');
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  // Selected document for inspection drawer
  const [selectedDoc, setSelectedDoc] = useState<DocumentItem | null>(null);

  // Upload drawer state
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [uploadDept, setUploadDept] = useState('HR');
  const [visibility, setVisibility] = useState('department');
  const [minRole, setMinRole] = useState('member');
  const [isUploading, setIsUploading] = useState(false);

  const { data: documents = [], isLoading } = useQuery<DocumentItem[]>({
    queryKey: ['admin-documents', activeTab, statusFilter, search],
    queryFn: async () => {
      const res = await api.get('/admin/documents', {
        params: {
          department: activeTab === 'All' ? undefined : activeTab,
          status: statusFilter || undefined,
          search: search || undefined,
        },
      });
      return res.data;
    },
  });

  const archiveMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.post(`/admin/documents/${id}/archive`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-documents'] });
      toast.success('Document archived');
      if (selectedDoc) {
        setSelectedDoc((prev) => (prev ? { ...prev, status: 'archived' } : null));
      }
    },
  });

  const reingestMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.post(`/admin/documents/${id}/reingest`);
    },
    onSuccess: () => {
      toast.success('Document scheduled for vector re-indexing');
    },
  });

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      toast.error('Please choose a file');
      return;
    }

    const roleLevelMap: Record<string, number> = {
      member: 1,
      manager: 2,
      head: 3,
    };

    const formData = new FormData();
    formData.append('file', file);
    formData.append('title', title || file.name);
    formData.append('department', uploadDept);
    formData.append('visibility', visibility);
    formData.append('min_role_level', String(roleLevelMap[minRole] || 1));
    formData.append('version', '1.0');

    setIsUploading(true);
    try {
      await api.post('/admin/documents', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      toast.success('Document uploaded and queued for indexing');
      setIsUploadOpen(false);
      setFile(null);
      setTitle('');
      queryClient.invalidateQueries({ queryKey: ['admin-documents'] });
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Upload failed');
    } finally {
      setIsUploading(false);
    }
  };

  const roleName = (level: number) => {
    if (level >= 3) return 'head';
    if (level === 2) return 'manager';
    return 'member';
  };

  const columns: Column<DocumentItem>[] = [
    {
      header: 'Title',
      accessorKey: 'title',
      cell: (doc) => (
        <div
          className="cursor-pointer group py-0.5"
          onClick={() => setSelectedDoc(doc)}
        >
          <p className="font-medium text-[14px] text-[var(--text)] group-hover:text-[var(--ink)] flex items-center gap-1.5">
            <FileText size={15} className="text-[var(--text-subtle)] shrink-0" />
            <span className="group-hover:underline underline-offset-2">{doc.title}</span>
          </p>
          <p className="text-[12px] text-[var(--text-subtle)] pl-5">
            Version {doc.version} · {doc.doc_type || 'Policy'}
          </p>
        </div>
      ),
    },
    {
      header: 'Department',
      accessorKey: 'department_code',
      cell: (doc) => (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-[12px] font-medium bg-[var(--surface-muted)] text-[var(--text)]">
          {doc.department_code || doc.department_name}
        </span>
      ),
    },
    {
      header: 'Visibility',
      accessorKey: 'visibility',
      cell: (doc) => (
        <Badge variant="visibility" visibility={doc.visibility}>
          {doc.visibility}
        </Badge>
      ),
    },
    {
      header: 'Min Role',
      cell: (doc) => {
        const r = roleName(doc.min_role_level);
        return <Badge variant="role" role={r}>{r}</Badge>;
      },
    },
    {
      header: 'Status',
      accessorKey: 'status',
      cell: (doc) => <Badge variant="status" status={doc.status}>{doc.status}</Badge>,
    },
    {
      header: 'Actions',
      cell: (doc) => (
        <div className="flex items-center gap-1 justify-end">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setSelectedDoc(doc)}
            title="Inspect document"
          >
            <Eye size={14} />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => reingestMutation.mutate(doc.id)}
            title="Re-index into Vector Store"
          >
            <RefreshCw size={14} />
          </Button>
          {doc.status !== 'archived' && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => archiveMutation.mutate(doc.id)}
              title="Archive document"
            >
              <Archive size={14} className="text-[var(--pastel-rose-text)]" />
            </Button>
          )}
        </div>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Documents Management"
        description="Role-restricted repository of corporate policies, employee guidelines, and operations handbooks."
        action={
          <Button variant="primary" onClick={() => setIsUploadOpen(true)} className="gap-2">
            <Upload size={16} strokeWidth={1.5} />
            Upload Document
          </Button>
        }
      />

      {/* Department Segregation Tabs */}
      <div className="flex items-center gap-1.5 border-b border-[var(--border)] mb-5 overflow-x-auto pb-1">
        {DEPARTMENTS.map((dept) => {
          const isActive = activeTab === dept;
          return (
            <button
              key={dept}
              onClick={() => setActiveTab(dept)}
              className={`px-3.5 py-1.5 rounded-lg text-[13px] font-medium transition-colors whitespace-nowrap ${isActive
                  ? 'bg-[var(--ink)] text-white shadow-sm'
                  : 'text-[var(--text-muted)] hover:bg-[var(--surface-muted)] hover:text-[var(--text)]'
                }`}
            >
              {dept}
            </button>
          );
        })}
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-wrap items-center gap-3 mb-6 bg-[var(--surface)] p-3 rounded-xl border border-[var(--border)]">
        <div className="flex-1 min-w-[220px] relative">
          <Input
            placeholder="Search documents by title..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
          <Search size={16} className="absolute left-3 top-3 text-[var(--text-subtle)]" />
        </div>

        <Select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="w-36"
          options={[
            { value: '', label: 'All Statuses' },
            { value: 'active', label: 'Active' },
            { value: 'archived', label: 'Archived' },
            { value: 'quarantined', label: 'Quarantined' },
          ]}
        />
      </div>

      {/* Documents Table */}
      <Table
        data={documents}
        columns={columns}
        isLoading={isLoading}
        emptyMessage={`No documents found in ${activeTab} matching the filters.`}
      />

      {/* Document Detail / Inspection Drawer */}
      <Drawer
        isOpen={!!selectedDoc}
        onClose={() => setSelectedDoc(null)}
        title="Document Details"
        width="max-w-xl"
      >
        {selectedDoc && (
          <div className="space-y-6">
            <div className="p-4 bg-[var(--surface-muted)] rounded-xl border border-[var(--border)] space-y-3">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h3 className="font-semibold text-[16px] text-[var(--text)]">{selectedDoc.title}</h3>
                  <p className="text-[12px] text-[var(--text-subtle)] mt-0.5">
                    ID: <span className="font-mono">{selectedDoc.id}</span>
                  </p>
                </div>
                <Badge variant="status" status={selectedDoc.status}>
                  {selectedDoc.status}
                </Badge>
              </div>

              <div className="grid grid-cols-2 gap-3 pt-3 border-t border-[var(--border)] text-[13px]">
                <div className="flex items-center gap-2">
                  <Tag size={14} className="text-[var(--text-subtle)]" />
                  <span>
                    Dept: <strong className="text-[var(--text)]">{selectedDoc.department_code || selectedDoc.department_name}</strong>
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <ShieldCheck size={14} className="text-[var(--text-subtle)]" />
                  <span>
                    Visibility: <strong className="text-[var(--text)] capitalize">{selectedDoc.visibility}</strong>
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <ShieldCheck size={14} className="text-[var(--text-subtle)]" />
                  <span>
                    Min Role: <strong className="text-[var(--text)] capitalize">{roleName(selectedDoc.min_role_level)}</strong>
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <Calendar size={14} className="text-[var(--text-subtle)]" />
                  <span>
                    Created: <strong>{selectedDoc.created_at ? format(new Date(selectedDoc.created_at), 'MMM d, yyyy') : 'N/A'}</strong>
                  </span>
                </div>
              </div>
            </div>

            <div className="space-y-3">
              <h4 className="text-[12px] uppercase font-semibold text-[var(--text-subtle)] tracking-wider">
                Administrative Actions
              </h4>
              <div className="flex flex-col gap-2">
                <Button
                  variant="secondary"
                  className="w-full justify-start gap-2"
                  onClick={() => reingestMutation.mutate(selectedDoc.id)}
                >
                  <RefreshCw size={15} />
                  Re-index chunks into Vector Search (Qdrant)
                </Button>
                {selectedDoc.status !== 'archived' && (
                  <Button
                    variant="destructive-outline"
                    className="w-full justify-start gap-2"
                    onClick={() => archiveMutation.mutate(selectedDoc.id)}
                  >
                    <Archive size={15} />
                    Archive this document from active retrieval
                  </Button>
                )}
              </div>
            </div>
          </div>
        )}
      </Drawer>

      {/* Upload Drawer */}
      <Drawer
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        title="Upload Document"
      >
        <form onSubmit={handleUpload} className="space-y-4">
          <div>
            <label className="text-[13px] font-medium text-[var(--text)] block mb-1.5">
              Document File (PDF, DOCX, MD, TXT - max 20MB)
            </label>
            <input
              type="file"
              accept=".pdf,.docx,.md,.txt"
              onChange={(e) => {
                if (e.target.files?.[0]) {
                  setFile(e.target.files[0]);
                  if (!title) setTitle(e.target.files[0].name.replace(/\.[^/.]+$/, ''));
                }
              }}
              required
              className="w-full text-[13px] text-[var(--text-muted)] file:mr-3 file:py-2 file:px-3 file:rounded-lg file:border-0 file:text-[13px] file:font-medium file:bg-[var(--surface-muted)] file:text-[var(--text)] hover:file:bg-[var(--border)] cursor-pointer"
            />
          </div>

          <Input
            label="Title"
            placeholder="Document title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
          />

          <Select
            label="Department"
            value={uploadDept}
            onChange={(e) => setUploadDept(e.target.value)}
            options={[
              { value: 'HR', label: 'Human Resources (HR)' },
              { value: 'Finance', label: 'Finance & Accounting' },
              { value: 'IT', label: 'Information Technology (IT)' },
              { value: 'Engineering', label: 'Engineering' },
              { value: 'Sales', label: 'Sales & Marketing' },
              { value: 'Legal', label: 'Legal' },
            ]}
          />

          <Select
            label="Visibility"
            value={visibility}
            onChange={(e) => setVisibility(e.target.value)}
            options={[
              { value: 'department', label: 'Department only' },
              { value: 'company', label: 'Company-wide' },
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
              onClick={() => setIsUploadOpen(false)}
            >
              Cancel
            </Button>
            <Button type="submit" variant="primary" isLoading={isUploading}>
              Upload & Ingest
            </Button>
          </div>
        </form>
      </Drawer>
    </div>
  );
};
