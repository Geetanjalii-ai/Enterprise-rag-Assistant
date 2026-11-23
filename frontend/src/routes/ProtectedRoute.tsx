import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../lib/auth';

export const ProtectedRoute: React.FC = () => {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--bg)]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 rounded-full border-2 border-[var(--pastel-lavender-text)] border-t-transparent animate-spin" />
          <span className="text-[13px] text-[var(--text-muted)]">Verifying session...</span>
        </div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
};
