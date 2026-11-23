import React from 'react';

export const Skeleton: React.FC<{ className?: string }> = ({ className = '' }) => {
  return (
    <div
      className={`animate-pulse bg-[var(--surface-muted)] rounded ${className}`}
    />
  );
};
