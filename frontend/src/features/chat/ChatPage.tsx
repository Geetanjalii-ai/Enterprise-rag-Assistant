import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { streamChatMessage } from '../../lib/sse';
import { ChatEmptyState } from './ChatEmptyState';
import { MessageItem, ChatMessage, CitationItem } from './MessageItem';
import { ChatInput } from './ChatInput';
import { SourceDrawer } from './SourceDrawer';
import { toast } from 'sonner';

export const ChatPage: React.FC = () => {
  const { conversationId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [activeChunkId, setActiveChunkId] = useState<string | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const lastLoadedConvId = useRef<string | undefined>(undefined);

  // Load conversation details & messages if id provided
  const { data: convData, isLoading } = useQuery({
    queryKey: ['conversation', conversationId],
    queryFn: async () => {
      const res = await api.get(`/conversations/${conversationId}`);
      return res.data;
    },
    enabled: !!conversationId,
  });

  useEffect(() => {
    // Only synchronize from server when NOT actively streaming and conversation changes
    if (convData && convData.messages && !isStreaming) {
      if (lastLoadedConvId.current !== conversationId || messages.length === 0) {
        lastLoadedConvId.current = conversationId;
        setMessages(
          convData.messages.map((m: any) => ({
            id: m.id,
            role: m.role,
            content: m.content,
            citations: m.citations,
            feedback: m.feedback,
          }))
        );
      }
    } else if (!conversationId && !isStreaming) {
      lastLoadedConvId.current = undefined;
      setMessages([]);
    }
  }, [convData, conversationId, isStreaming]);

  useEffect(() => {
    // Scroll to bottom on message updates
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollTop = scrollContainerRef.current.scrollHeight;
    }
  }, [messages, isStreaming]);

  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setIsStreaming(false);
    }
  };

  const handleSendMessage = async (textToSend?: string) => {
    const text = textToSend || input;
    if (!text.trim() || isStreaming) return;

    setInput('');
    let currentConvId = conversationId;

    // Create a new conversation if on /chat
    if (!currentConvId) {
      try {
        const res = await api.post('/conversations', {
          title: text.slice(0, 40),
        });
        currentConvId = res.data.id;
        lastLoadedConvId.current = currentConvId;
        queryClient.invalidateQueries({ queryKey: ['conversations'] });
        navigate(`/chat/${currentConvId}`, { replace: true });
      } catch {
        toast.error('Failed to create conversation');
        return;
      }
    }

    if (!currentConvId) return;

    // Add user message to state
    const userMsg: ChatMessage = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content: text,
    };
    const assistantMsgPlaceholder: ChatMessage = {
      id: `assistant-stream-${Date.now()}`,
      role: 'assistant',
      content: '',
      citations: [],
    };

    setMessages((prev) => [...prev, userMsg, assistantMsgPlaceholder]);
    setIsStreaming(true);

    abortControllerRef.current = new AbortController();

    try {
      await streamChatMessage({
        conversationId: currentConvId,
        content: text,
        signal: abortControllerRef.current.signal,
        onToken: (token: string) => {
          setMessages((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            if (last && last.role === 'assistant') {
              next[next.length - 1] = {
                ...last,
                content: last.content + token,
              };
            }
            return next;
          });
        },
        onCitations: (citations: CitationItem[]) => {
          setMessages((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            if (last && last.role === 'assistant') {
              next[next.length - 1] = {
                ...last,
                citations,
              };
            }
            return next;
          });
        },
        onDone: (savedId: string) => {
          setIsStreaming(false);
          setMessages((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            if (last && last.role === 'assistant') {
              next[next.length - 1] = {
                ...last,
                id: savedId,
              };
            }
            return next;
          });
          queryClient.invalidateQueries({ queryKey: ['conversations'] });
        },
        onError: (errMessage: string) => {
          toast.error(errMessage || 'An error occurred during streaming');
          setIsStreaming(false);
          setMessages((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            if (last && last.role === 'assistant' && !last.content) {
              next.pop();
            }
            return next;
          });
        },
      });
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        toast.error('Error sending message');
      }
      setIsStreaming(false);
    }
  };

  const isBlank = !conversationId && messages.length === 0;

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-[var(--bg)]">
      {/* Main chat viewport */}
      <div
        ref={scrollContainerRef}
        className="flex-1 overflow-y-auto flex flex-col justify-between"
      >
        {isBlank ? (
          <ChatEmptyState onSelectSuggestion={(s) => handleSendMessage(s)} />
        ) : (
          <div className="w-full max-w-3xl mx-auto py-6">
            {messages.map((m, index) => (
              <MessageItem
                key={m.id || index}
                message={m}
                isStreaming={isStreaming && index === messages.length - 1 && m.role === 'assistant'}
                onSelectCitation={(cid) => setActiveChunkId(cid)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Input area */}
      <ChatInput
        input={input}
        setInput={setInput}
        onSubmit={() => handleSendMessage()}
        isStreaming={isStreaming}
        onStop={handleStop}
        disabled={isLoading}
      />

      {/* Right Drawer for citation excerpts */}
      <SourceDrawer
        chunkId={activeChunkId}
        onClose={() => setActiveChunkId(null)}
      />
    </div>
  );
};
