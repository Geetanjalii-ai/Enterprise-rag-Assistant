import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { Drawer } from '../../components/ui/Drawer';
import { Badge } from '../../components/ui/Badge';
import { Skeleton } from '../../components/ui/Skeleton';
import { FileText, Calendar, Tag, ShieldCheck } from 'lucide-react';

interface SourceDrawerProps {
  chunkId: string | null;
  onClose: () => void;
}

interface CitationData {
  chunk_id: string;
  document_id: string;
  document_title: string;
  department: string;
  version: string;
  effective_date: string | null;
  section: string;
  pages: number[];
  chunk_text: string;
  visibility: string;
}

export const SourceDrawer: React.FC<SourceDrawerProps> = ({ chunkId, onClose }) => {
  const { data: citation, isLoading, error } = useQuery<CitationData>({
    queryKey: ['citation', chunkId],
    queryFn: async () => {
      const res = await api.get(`/citations/${chunkId}`);
      return res.data;
    },
    enabled: !!chunkId,
  });

  return (
    <Drawer isOpen={!!chunkId} onClose={onClose} title="Source Reference" width="max-w-xl">
      {isLoading ? (
        <div className="space-y-4 py-4">
          <Skeleton className="h-6 w-3/4" />
          <Skeleton className="h-4 w-1/2" />
          <Skeleton className="h-32 w-full" />
        </div>
      ) : error || !citation ? (
        <div className="py-8 text-center text-[var(--text-muted)] text-[14px]">
          Unable to load citation data or you do not have permission to view it.
        </div>
      ) : (
        <div className="space-y-6">
          {/* Document metadata info */}
          <div className="p-4 bg-[var(--surface-muted)] rounded-xl border border-[var(--border)] space-y-3">
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-center gap-2">
                <FileText size={18} className="text-[var(--pastel-lavender-text)] shrink-0" />
                <h3 className="font-semibold text-[15px] text-[var(--text)] leading-snug">
                  {citation.document_title}
                </h3>
              </div>
              <Badge variant="status" status="active">
                v{citation.version}
              </Badge>
            </div>

            <div className="grid grid-cols-2 gap-2 text-[12px] text-[var(--text-muted)] pt-2 border-t border-[var(--border)]">
              <div className="flex items-center gap-1.5">
                <Tag size={13} className="text-[var(--text-subtle)]" />
                <span>Dept: <strong className="text-[var(--text)]">{citation.department}</strong></span>
              </div>
              <div className="flex items-center gap-1.5">
                <Calendar size={13} className="text-[var(--text-subtle)]" />
                <span>Date: <strong className="text-[var(--text)]">{citation.effective_date || 'N/A'}</strong></span>
              </div>
              <div className="flex items-center gap-1.5 col-span-2">
                <ShieldCheck size={13} className="text-[var(--text-subtle)]" />
                <span>
                  Section: <strong className="text-[var(--text)]">{citation.section || 'General'}</strong>
                  {citation.pages?.length > 0 && ` (p. ${citation.pages.join(', ')})`}
                </span>
              </div>
            </div>
          </div>

          {/* Extracted chunk text */}
          <div>
            <h4 className="text-[12px] uppercase font-semibold text-[var(--text-subtle)] tracking-wider mb-2">
              Verified Policy Excerpt
            </h4>
            <div className="p-4 bg-[var(--surface)] border border-[var(--border)] rounded-xl text-[14px] leading-relaxed text-[var(--text)] font-mono whitespace-pre-wrap select-text">
              {citation.chunk_text}
            </div>
          </div>
        </div>
      )}
    </Drawer>
  );
};
