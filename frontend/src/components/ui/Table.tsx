import React from "react";

export interface Column<T> {
  header: string;
  accessorKey?: keyof T;
  cell?: (row: T) => React.ReactNode;
  className?: string;
}

interface TableProps<T> {
  columns: Column<T>[];
  data: T[];
  isLoading?: boolean;
  emptyMessage?: string;
}

export function Table<T>({ columns, data, isLoading, emptyMessage = "No records found" }: TableProps<T>) {
  if (isLoading) {
    return (
      <div className="w-full border border-border rounded-sm overflow-hidden bg-surface">
        <div className="animate-pulse p-6 space-y-4">
          <div className="h-6 bg-surface-muted rounded w-1/3" />
          <div className="h-10 bg-surface-muted rounded w-full" />
          <div className="h-10 bg-surface-muted rounded w-full" />
          <div className="h-10 bg-surface-muted rounded w-full" />
        </div>
      </div>
    );
  }

  return (
    <div className="w-full overflow-x-auto border border-border rounded-sm bg-surface">
      <table className="w-full text-left text-sm border-collapse">
        <thead>
          <tr className="border-b border-border bg-surface-muted text-xs font-semibold text-text-muted sticky top-0">
            {columns.map((col, idx) => (
              <th key={idx} className={`px-4 py-3 whitespace-nowrap ${col.className || ""}`}>
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {data.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="px-4 py-8 text-center text-text-muted">
                {emptyMessage}
              </td>
            </tr>
          ) : (
            data.map((row, rowIdx) => (
              <tr key={rowIdx} className="hover:bg-surface-muted transition-colors">
                {columns.map((col, colIdx) => (
                  <td key={colIdx} className={`px-4 py-3 whitespace-nowrap text-text ${col.className || ""}`}>
                    {col.cell ? col.cell(row) : (row[col.accessorKey as keyof T] as unknown as React.ReactNode)}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
