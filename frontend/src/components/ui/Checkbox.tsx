import React from 'react';

interface CheckboxProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: React.ReactNode;
}

export const Checkbox = React.forwardRef<HTMLInputElement, CheckboxProps>(
  ({ label, className = '', id, ...props }, ref) => {
    const inputId = id || React.useId();

    return (
      <label htmlFor={inputId} className="inline-flex items-center gap-2 cursor-pointer select-none">
        <input
          type="checkbox"
          id={inputId}
          ref={ref}
          className={`w-4 h-4 rounded border-[var(--border-strong)] text-[var(--ink)] focus:ring-2 focus:ring-[var(--focus-ring)] focus:ring-offset-0 cursor-pointer ${className}`}
          {...props}
        />
        {label && <span className="text-[13px] text-[var(--text-muted)] font-normal">{label}</span>}
      </label>
    );
  }
);

Checkbox.displayName = 'Checkbox';
