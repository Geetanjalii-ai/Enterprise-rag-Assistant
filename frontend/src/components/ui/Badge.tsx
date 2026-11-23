import React from "react";

export type BadgeVariant =
  | "active"
  | "archived"
  | "quarantined"
  | "pending"
  | "running"
  | "failed"
  | "processed"
  | "skipped"
  | "rejected"
  | "company"
  | "department"
  | "member"
  | "manager"
  | "head"
  | "answered"
  | "not_found"
  | "blocked"
  | "status"
  | "visibility"
  | "role"
  | "outcome"
  | "default";

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
  status?: string;
  visibility?: string;
  role?: string;
  outcome?: string;
  children: React.ReactNode;
}

export const Badge: React.FC<BadgeProps> = ({
  variant = "default",
  status,
  visibility,
  role,
  outcome,
  children,
  className = "",
  ...props
}) => {
  let effective = variant as string;
  if (status) effective = status;
  else if (visibility) effective = visibility;
  else if (role) effective = role;
  else if (outcome) effective = outcome;

  const styleMap: Record<string, string> = {
    active: "bg-[var(--pastel-mint-bg)] text-[var(--pastel-mint-text)]",
    processed: "bg-[var(--pastel-mint-bg)] text-[var(--pastel-mint-text)]",
    answered: "bg-[var(--pastel-mint-bg)] text-[var(--pastel-mint-text)]",
    completed: "bg-[var(--pastel-mint-bg)] text-[var(--pastel-mint-text)]",

    company: "bg-[var(--pastel-sky-bg)] text-[var(--pastel-sky-text)]",
    pending: "bg-[var(--pastel-sky-bg)] text-[var(--pastel-sky-text)]",
    running: "bg-[var(--pastel-sky-bg)] text-[var(--pastel-sky-text)]",

    department: "bg-[var(--pastel-lavender-bg)] text-[var(--pastel-lavender-text)]",
    head: "bg-[var(--pastel-lavender-bg)] text-[var(--pastel-lavender-text)]",

    manager: "bg-[var(--pastel-peach-bg)] text-[var(--pastel-peach-text)]",

    quarantined: "bg-[var(--pastel-rose-bg)] text-[var(--pastel-rose-text)]",
    failed: "bg-[var(--pastel-rose-bg)] text-[var(--pastel-rose-text)]",
    rejected: "bg-[var(--pastel-rose-bg)] text-[var(--pastel-rose-text)]",
    blocked: "bg-[var(--pastel-rose-bg)] text-[var(--pastel-rose-text)]",

    archived: "bg-[var(--surface-muted)] text-[var(--text-muted)]",
    skipped: "bg-[var(--surface-muted)] text-[var(--text-muted)]",
    member: "bg-[var(--surface-muted)] text-[var(--text-muted)]",
    not_found: "bg-[var(--pastel-amber-bg)] text-[var(--pastel-amber-text)]",
    default: "bg-[var(--surface-muted)] text-[var(--text-muted)]",
  };

  const selectedClass = styleMap[effective] || styleMap.default;

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium tracking-tight whitespace-nowrap ${selectedClass} ${className}`}
      {...props}
    >
      {children}
    </span>
  );
};
