import React from "react";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  error?: string;
  label?: string;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ error, label, className = "", id, ...props }, ref) => {
    const generatedId = React.useId();
    const inputId = id || props.name || generatedId;

    return (
      <div className="w-full flex flex-col gap-1.5">
        {label && (
          <label htmlFor={inputId} className="text-[13px] font-medium leading-[18px] text-text">
            {label}
          </label>
        )}
        <input
          id={inputId}
          ref={ref}
          className={`h-10 w-full rounded-sm border bg-surface px-3 text-sm text-text placeholder:text-text-subtle transition-colors focus-visible:outline-2 focus-visible:outline-focus-ring focus-visible:outline-offset-2 disabled:cursor-not-allowed disabled:bg-surface-muted ${
            error ? "border-rose" : "border-border hover:border-border-strong"
          } ${className}`}
          {...props}
        />
        {error && <span className="text-xs text-rose-text">{error}</span>}
      </div>
    );
  }
);
Input.displayName = "Input";
