import React from "react";

interface StatCardProps {
  label: string;
  value: string | number;
  subtext?: string;
  chipVariant?: "mint" | "sky" | "rose" | "gray";
  icon?: React.ReactNode;
}

export const StatCard: React.FC<StatCardProps> = ({ label, value, subtext, icon }) => {
  return (
    <div className="p-4 bg-surface rounded-sm border border-border flex items-center justify-between">
      <div>
        <p className="text-xs font-medium text-text-muted uppercase tracking-wider">{label}</p>
        <p className="text-2xl font-semibold text-text mt-1">{value}</p>
        {subtext && <p className="text-xs text-text-subtle mt-0.5">{subtext}</p>}
      </div>
      {icon && <div className="text-text-muted">{icon}</div>}
    </div>
  );
};
