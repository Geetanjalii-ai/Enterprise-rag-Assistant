import React, { useRef, useEffect } from 'react';
import { ArrowUp, Square } from 'lucide-react';

interface ChatInputProps {
  input: string;
  setInput: (value: string) => void;
  onSubmit: (e?: React.FormEvent) => void;
  isStreaming: boolean;
  onStop: () => void;
  placeholder?: string;
  disabled?: boolean;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  input,
  setInput,
  onSubmit,
  isStreaming,
  onStop,
  placeholder = 'Ask a question about HR, IT, Finance policies...',
  disabled = false,
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
    }
  }, [input]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!isStreaming && input.trim()) {
        onSubmit();
      }
    }
  };

  return (
    <div className="w-full max-w-3xl mx-auto px-4 pb-4">
      <div className="relative bg-[var(--surface)] border border-[var(--border-strong)] rounded-2xl shadow-sm focus-within:border-[var(--ink)] focus-within:ring-2 focus-within:ring-[var(--focus-ring)] transition-all">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          rows={1}
          className="w-full resize-none bg-transparent px-4 pt-3.5 pb-10 text-[15px] leading-[24px] text-[var(--text)] placeholder:text-[var(--text-subtle)] focus:outline-none max-h-[180px] min-h-[52px]"
        />

        <div className="absolute right-2.5 bottom-2.5 flex items-center gap-2">
          {isStreaming ? (
            <button
              type="button"
              onClick={onStop}
              className="w-8 h-8 rounded-full bg-[var(--ink)] text-white flex items-center justify-center hover:bg-[var(--ink-hover)] transition-colors shadow-sm"
              title="Stop response"
            >
              <Square size={14} fill="currentColor" />
            </button>
          ) : (
            <button
              type="button"
              onClick={() => onSubmit()}
              disabled={!input.trim() || disabled}
              className="w-8 h-8 rounded-full bg-[var(--ink)] text-white flex items-center justify-center hover:bg-[var(--ink-hover)] transition-colors disabled:opacity-30 disabled:cursor-not-allowed shadow-sm"
              title="Send message"
            >
              <ArrowUp size={16} strokeWidth={2} />
            </button>
          )}
        </div>
      </div>
      <p className="text-[11px] text-center text-[var(--text-subtle)] mt-2">
        Answers cite verified company documents. Meridian Assist can make mistakes.
      </p>
    </div>
  );
};
