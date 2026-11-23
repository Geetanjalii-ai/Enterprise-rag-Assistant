import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { api } from '../../lib/api';
import { ThumbsUp, ThumbsDown, BookOpen } from 'lucide-react';
import { toast } from 'sonner';

export interface CitationItem {
  id?: string;
  chunk_id: string;
  document_title: string;
  section?: string;
  page?: number;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: CitationItem[];
  feedback?: 'up' | 'down' | null;
}

interface MessageItemProps {
  message: ChatMessage;
  isStreaming?: boolean;
  onSelectCitation: (chunkId: string) => void;
}

export const MessageItem: React.FC<MessageItemProps> = ({
  message,
  isStreaming,
  onSelectCitation,
}) => {
  const isUser = message.role === 'user';
  const [feedback, setFeedback] = useState<'up' | 'down' | null>(message.feedback || null);

  const handleFeedback = async (rating: 'up' | 'down') => {
    if (feedback === rating || !message.id) return;
    try {
      await api.post(`/messages/${message.id}/feedback`, { rating });
      setFeedback(rating);
      toast.success('Thank you for your feedback');
    } catch {
      toast.error('Could not save feedback');
    }
  };

  if (isUser) {
    return (
      <div className="flex justify-end mb-4 px-4">
        <div className="max-w-[75%] px-4 py-2.5 rounded-2xl bg-[var(--pastel-lavender-bg)] text-[var(--pastel-lavender-text)] text-[15px] leading-[24px] font-normal shadow-sm">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start mb-6 px-4 group">
      <div className="max-w-[85%] text-[15px] leading-[24px] text-[var(--text)]">
        {/* Markdown Content */}
        <div className="prose prose-sm max-w-none text-[var(--text)] prose-p:my-2 prose-headings:font-semibold prose-a:text-[var(--pastel-sky-text)] prose-code:bg-[var(--surface-muted)] prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:before:content-none prose-code:after:content-none">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {message.content}
          </ReactMarkdown>
          {isStreaming && (
            <span className="inline-block w-2 h-4 bg-[var(--ink)] ml-1 animate-pulse align-middle" />
          )}
        </div>

        {/* Citations section */}
        {message.citations && message.citations.length > 0 && (
          <div className="mt-3 pt-3 border-t border-[var(--border)]">
            <span className="text-[11px] font-semibold tracking-wider uppercase text-[var(--text-subtle)] block mb-1.5">
              Sources:
            </span>
            <div className="flex flex-wrap gap-1.5">
              {message.citations.map((c, idx) => (
                <button
                  key={c.chunk_id || idx}
                  onClick={() => onSelectCitation(c.chunk_id)}
                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[12px] font-medium bg-[var(--surface-muted)] border border-[var(--border)] text-[var(--text)] hover:border-[var(--pastel-lavender-text)] hover:bg-[var(--pastel-lavender-bg)] hover:text-[var(--pastel-lavender-text)] transition-colors"
                >
                  <BookOpen size={12} strokeWidth={1.5} />
                  <span>{c.document_title || `Doc citation`}</span>
                  {c.section && <span className="opacity-70 text-[11px]">· {c.section}</span>}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Actions bar (feedback) */}
        {!isStreaming && (
          <div className="flex items-center gap-1.5 mt-2 opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              onClick={() => handleFeedback('up')}
              className={`p-1 rounded text-[var(--text-subtle)] hover:text-[var(--pastel-mint-text)] hover:bg-[var(--surface-muted)] transition-colors ${
                feedback === 'up' ? 'text-[var(--pastel-mint-text)] font-semibold' : ''
              }`}
              title="Helpful"
            >
              <ThumbsUp size={14} strokeWidth={1.5} />
            </button>
            <button
              onClick={() => handleFeedback('down')}
              className={`p-1 rounded text-[var(--text-subtle)] hover:text-[var(--pastel-rose-text)] hover:bg-[var(--surface-muted)] transition-colors ${
                feedback === 'down' ? 'text-[var(--pastel-rose-text)] font-semibold' : ''
              }`}
              title="Not helpful"
            >
              <ThumbsDown size={14} strokeWidth={1.5} />
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
