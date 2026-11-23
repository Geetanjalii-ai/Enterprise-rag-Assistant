import React from 'react';

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ label, error, className = '', ...props }, ref) => {
    return (
      <div className="w-full flex flex-col gap-1.5">
        {label && (
          <label className="text-[13px] font-medium text-[var(--text)]">
            {label}
          </label>
        )}
        <textarea
          ref={ref}
          className={`w-full px-3 py-2 text-[14px] bg-[var(--surface)] text-[var(--text)] border rounded-lg transition-colors placeholder:text-[var(--text-subtle)] focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring)] disabled:opacity-50 disabled:cursor-not-allowed ${
            error ? 'border-[var(--pastel-rose-text)]' : 'border-[var(--border)] focus:border-transparent'
          } ${className}`}
          {...props}
        />
        {error && <span className="text-[12px] text-[var(--pastel-rose-text)]">{error}</span>}
      </div>
    );
  }
);

Textarea.displayName = 'Textarea';
