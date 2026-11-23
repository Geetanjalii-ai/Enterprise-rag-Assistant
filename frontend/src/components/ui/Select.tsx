import React from 'react';

interface SelectOption {
  value: string;
  label: string;
}

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  options?: SelectOption[];
}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ label, error, options, children, className = '', ...props }, ref) => {
    return (
      <div className="w-full flex flex-col gap-1.5">
        {label && (
          <label className="text-[13px] font-medium text-[var(--text)]">
            {label}
          </label>
        )}
        <select
          ref={ref}
          className={`w-full h-10 px-3 text-[14px] bg-[var(--surface)] text-[var(--text)] border rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring)] disabled:opacity-50 disabled:cursor-not-allowed ${
            error ? 'border-[var(--pastel-rose-text)]' : 'border-[var(--border)] focus:border-transparent'
          } ${className}`}
          {...props}
        >
          {options
            ? options.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))
            : children}
        </select>
        {error && <span className="text-[12px] text-[var(--pastel-rose-text)]">{error}</span>}
      </div>
    );
  }
);

Select.displayName = 'Select';
