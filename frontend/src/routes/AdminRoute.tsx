import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../lib/auth';
import { Button } from '../components/ui/Button';
import { ShieldAlert } from 'lucide-react';
import { Link } from 'react-router-dom';

export const AdminRoute: React.FC = () => {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return null;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (!user.is_admin) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--bg)] p-4">
        <div className="max-w-md w-full bg-[var(--surface)] border border-[var(--border)] rounded-2xl p-8 text-center shadow-sm">
          <div className="w-12 h-12 rounded-full bg-[var(--pastel-rose-bg)] text-[var(--pastel-rose-text)] flex items-center justify-center mx-auto mb-4">
            <ShieldAlert size={24} strokeWidth={1.5} />
          </div>
          <h2 className="text-[20px] font-semibold text-[var(--text)]">Access Restricted</h2>
          <p className="text-[14px] text-[var(--text-muted)] mt-2 mb-6">
            You need system administrator privileges to access this console.
          </p>
          <Link to="/chat">
            <Button variant="primary" className="w-full">
              Return to Chat
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  return <Outlet />;
};
