import React from 'react';
import { Outlet, NavLink, Link } from 'react-router-dom';
import { APP_NAME } from '../../content/brand';
import { UserMenu } from '../../components/layout/UserMenu';
import {
  FileText,
  PlayCircle,
  AlertTriangle,
  Users,
  Shield,
  Activity,
  Settings,
  ArrowLeft,
  Sparkles,
} from 'lucide-react';

export const AdminLayout: React.FC = () => {
  const navItems = [
    { to: '/admin/documents', label: 'Documents', icon: FileText },
    { to: '/admin/ingestion', label: 'Ingestion Runs', icon: PlayCircle },
    { to: '/admin/quarantine', label: 'Quarantine', icon: AlertTriangle },
    { to: '/admin/users', label: 'Users & Roles', icon: Users },
    { to: '/admin/monitoring', label: 'Monitoring & Logs', icon: Activity },
    { to: '/admin/audit', label: 'Audit Log', icon: Shield },
    { to: '/admin/settings', label: 'Settings', icon: Settings },
  ];

  return (
    <div className="flex h-screen bg-[var(--bg)] text-[var(--text)] overflow-hidden">
      {/* Admin Sidebar */}
      <aside className="w-[260px] bg-[var(--surface)] border-r border-[var(--border)] flex flex-col justify-between shrink-0">
        <div>
          {/* Header */}
          <div className="p-4 border-b border-[var(--border)]">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-7 h-7 rounded-lg bg-[var(--ink)] flex items-center justify-center text-white shadow-sm">
                <Sparkles size={16} strokeWidth={1.5} />
              </div>
              <span className="font-semibold text-[15px] tracking-tight">{APP_NAME}</span>
            </div>
            <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-[var(--pastel-lavender-bg)] text-[var(--pastel-lavender-text)] text-[11px] font-semibold tracking-wider uppercase">
              <Shield size={12} />
              Admin Console
            </div>
          </div>

          {/* Navigation */}
          <nav className="p-3 space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    `flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] font-medium transition-colors ${isActive
                      ? 'bg-[var(--surface-muted)] text-[var(--text)] font-semibold'
                      : 'text-[var(--text-muted)] hover:bg-[var(--surface-muted)] hover:text-[var(--text)]'
                    }`
                  }
                >
                  <Icon size={16} strokeWidth={1.5} />
                  {item.label}
                </NavLink>
              );
            })}
          </nav>
        </div>

        {/* Footer with Return to chat & User */}
        <div className="p-3 border-t border-[var(--border)] space-y-2">
          <Link
            to="/chat"
            className="flex items-center gap-2 px-3 py-2 text-[13px] font-medium text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--surface-muted)] rounded-lg transition-colors"
          >
            <ArrowLeft size={16} strokeWidth={1.5} />
            Back to Chat
          </Link>
          <UserMenu />
        </div>
      </aside>

      {/* Main Admin Area */}
      <main className="flex-1 overflow-y-auto bg-[var(--bg)] p-8">
        <div className="max-w-6xl mx-auto">
          <Outlet />
        </div>
      </main>
    </div>
  );
};
