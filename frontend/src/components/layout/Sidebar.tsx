import React, { useState } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { APP_NAME } from '../../content/brand';
import { UserMenu } from './UserMenu';
import { Button } from '../ui/Button';
import { Plus, MessageSquare, Trash2, Edit2, Check, X, Sparkles } from 'lucide-react';
import { isToday, isWithinInterval, subDays } from 'date-fns';

interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

interface SidebarProps {
  mobileOpen: boolean;
  onCloseMobile: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ mobileOpen, onCloseMobile }) => {
  const navigate = useNavigate();
  const { conversationId } = useParams();
  const queryClient = useQueryClient();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');

  const { data: conversations = [], isLoading } = useQuery<Conversation[]>({
    queryKey: ['conversations'],
    queryFn: async () => {
      const res = await api.get('/conversations');
      return res.data;
    },
  });

  const renameMutation = useMutation({
    mutationFn: async ({ id, title }: { id: string; title: string }) => {
      await api.patch(`/conversations/${id}`, { title });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
      setEditingId(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/conversations/${id}`);
    },
    onSuccess: (_, deletedId) => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
      if (conversationId === deletedId) {
        navigate('/chat');
      }
    },
  });

  const handleStartRename = (e: React.MouseEvent, conv: Conversation) => {
    e.stopPropagation();
    setEditingId(conv.id);
    setEditTitle(conv.title);
  };

  const handleSaveRename = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (editTitle.trim()) {
      renameMutation.mutate({ id, title: editTitle.trim() });
    } else {
      setEditingId(null);
    }
  };

  const handleDelete = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (confirm('Delete this conversation?')) {
      deleteMutation.mutate(id);
    }
  };

  const groupConversations = () => {
    const today: Conversation[] = [];
    const past7Days: Conversation[] = [];
    const older: Conversation[] = [];
    const now = new Date();
    const sevenDaysAgo = subDays(now, 7);

    conversations.forEach((conv) => {
      const date = new Date(conv.updated_at || conv.created_at);
      if (isToday(date)) {
        today.push(conv);
      } else if (isWithinInterval(date, { start: sevenDaysAgo, end: now })) {
        past7Days.push(conv);
      } else {
        older.push(conv);
      }
    });

    return { today, past7Days, older };
  };

  const { today, past7Days, older } = groupConversations();

  const renderGroup = (label: string, items: Conversation[]) => {
    if (items.length === 0) return null;
    return (
      <div className="mb-4">
        <h3 className="px-3 text-[11px] font-semibold tracking-wider uppercase text-[var(--text-subtle)] mb-1.5">
          {label}
        </h3>
        <div className="space-y-0.5">
          {items.map((conv) => {
            const isActive = conv.id === conversationId;
            const isEditing = editingId === conv.id;

            return (
              <div
                key={conv.id}
                onClick={() => {
                  if (!isEditing) {
                    navigate(`/chat/${conv.id}`);
                    onCloseMobile();
                  }
                }}
                className={`group relative flex items-center justify-between px-3 py-2 rounded-lg text-[13px] cursor-pointer transition-colors ${
                  isActive
                    ? 'bg-[var(--surface-muted)] text-[var(--text)] font-medium'
                    : 'text-[var(--text-muted)] hover:bg-[var(--surface-muted)] hover:text-[var(--text)]'
                }`}
              >
                {isEditing ? (
                  <div className="flex items-center gap-1 w-full" onClick={(e) => e.stopPropagation()}>
                    <input
                      type="text"
                      value={editTitle}
                      onChange={(e) => setEditTitle(e.target.value)}
                      className="w-full text-[13px] px-1 py-0.5 bg-[var(--surface)] border border-[var(--border-strong)] rounded focus:outline-none"
                      autoFocus
                    />
                    <button
                      onClick={(e) => handleSaveRename(e, conv.id)}
                      className="p-1 text-[var(--pastel-mint-text)] hover:opacity-80"
                    >
                      <Check size={14} />
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setEditingId(null);
                      }}
                      className="p-1 text-[var(--text-subtle)] hover:opacity-80"
                    >
                      <X size={14} />
                    </button>
                  </div>
                ) : (
                  <>
                    <div className="flex items-center gap-2 truncate pr-2">
                      <MessageSquare size={14} strokeWidth={1.5} className="shrink-0 text-[var(--text-subtle)]" />
                      <span className="truncate">{conv.title}</span>
                    </div>
                    <div className="hidden group-hover:flex items-center gap-1 shrink-0">
                      <button
                        onClick={(e) => handleStartRename(e, conv)}
                        className="p-1 text-[var(--text-subtle)] hover:text-[var(--text)] rounded"
                        title="Rename"
                      >
                        <Edit2 size={13} strokeWidth={1.5} />
                      </button>
                      <button
                        onClick={(e) => handleDelete(e, conv.id)}
                        className="p-1 text-[var(--text-subtle)] hover:text-[var(--pastel-rose-text)] rounded"
                        title="Delete"
                      >
                        <Trash2 size={13} strokeWidth={1.5} />
                      </button>
                    </div>
                  </>
                )}
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  const sidebarContent = (
    <div className="flex flex-col h-full bg-[var(--surface)] border-r border-[var(--border)] w-[260px]">
      {/* Brand & New Chat */}
      <div className="p-4 border-b border-[var(--border)]">
        <Link to="/chat" className="flex items-center gap-2 mb-4 group">
          <div className="w-7 h-7 rounded-lg bg-[var(--ink)] flex items-center justify-center text-white shadow-sm">
            <Sparkles size={16} strokeWidth={1.5} />
          </div>
          <span className="font-semibold text-[15px] text-[var(--text)] tracking-tight">
            {APP_NAME}
          </span>
        </Link>
        <Button
          variant="secondary"
          size="sm"
          className="w-full justify-start gap-2"
          onClick={() => {
            navigate('/chat');
            onCloseMobile();
          }}
        >
          <Plus size={16} strokeWidth={1.5} />
          New chat
        </Button>
      </div>

      {/* Conversation list */}
      <div className="flex-1 overflow-y-auto p-3">
        {isLoading ? (
          <div className="space-y-2 p-2">
            <div className="h-4 bg-[var(--surface-muted)] rounded animate-pulse" />
            <div className="h-4 bg-[var(--surface-muted)] rounded animate-pulse w-3/4" />
            <div className="h-4 bg-[var(--surface-muted)] rounded animate-pulse w-1/2" />
          </div>
        ) : conversations.length === 0 ? (
          <div className="text-center py-8 text-[12px] text-[var(--text-subtle)]">
            No conversations yet
          </div>
        ) : (
          <>
            {renderGroup('Today', today)}
            {renderGroup('Previous 7 days', past7Days)}
            {renderGroup('Older', older)}
          </>
        )}
      </div>

      {/* User profile card */}
      <div className="p-3 border-t border-[var(--border)]">
        <UserMenu />
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop sidebar */}
      <aside className="hidden md:block h-screen shrink-0">{sidebarContent}</aside>

      {/* Mobile slide-over drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 md:hidden flex">
          <div className="fixed inset-0 bg-black/40 backdrop-blur-sm" onClick={onCloseMobile} />
          <div className="relative z-10 animate-in slide-in-from-left duration-200">
            {sidebarContent}
          </div>
        </div>
      )}
    </>
  );
};
