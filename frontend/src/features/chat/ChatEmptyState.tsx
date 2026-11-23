import React from 'react';
import { useAuth } from '../../lib/auth';
import { BRAND_STRINGS } from '../../content/brand';
import { Sparkles, ArrowRight } from 'lucide-react';

interface ChatEmptyStateProps {
  onSelectSuggestion: (text: string) => void;
}

export const ChatEmptyState: React.FC<ChatEmptyStateProps> = ({ onSelectSuggestion }) => {
  const { user } = useAuth();
  const firstName = user?.name ? user.name.split(' ')[0] : 'there';

  return (
    <div className="flex-1 flex flex-col items-center justify-center p-6 text-center relative overflow-hidden select-none">
      {/* Soft chat greeting glow */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            'radial-gradient(60% 50% at 50% 30%, #E9E4FA 0%, rgba(233,228,250,0) 70%)',
        }}
      />

      <div className="relative z-10 flex flex-col items-center max-w-xl">
        {/* Sparkle Orb */}
        <div className="w-12 h-12 rounded-full bg-[var(--surface)] border border-[var(--border)] shadow-sm flex items-center justify-center text-[var(--pastel-lavender-text)] mb-4">
          <Sparkles size={22} strokeWidth={1.5} />
        </div>

        {/* Greeting Title */}
        <h1 className="text-[32px] font-semibold tracking-tight text-[var(--text)] mb-2">
          Hi {firstName}, what can I help with?
        </h1>
        <p className="text-[14px] text-[var(--text-muted)] mb-8">
          Ask questions across company guidelines, employee handbooks, and operational docs.
        </p>

        {/* Suggestion cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 w-full text-left">
          {BRAND_STRINGS.chat.suggestions.map((item) => (
            <button
              key={item}
              onClick={() => onSelectSuggestion(item)}
              className="p-3.5 bg-[var(--surface)] border border-[var(--border)] rounded-xl hover:border-[var(--border-strong)] hover:shadow-sm transition-all text-left flex flex-col justify-between group"
            >
              <span className="text-[13px] font-medium text-[var(--text)] leading-snug">
                {item}
              </span>
              <div className="flex items-center justify-end mt-3 text-[var(--text-subtle)] group-hover:text-[var(--ink)] transition-colors">
                <ArrowRight size={14} />
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};
