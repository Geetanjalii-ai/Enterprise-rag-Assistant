import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../lib/auth';
import { Avatar } from '../ui/Avatar';
import { Badge } from '../ui/Badge';
import { Shield, LogOut, ChevronUp } from 'lucide-react';

export const UserMenu: React.FC = () => {
  const { user, logout } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  if (!user) return null;

  const displayName = user.name || user.full_name || 'User';
  const primaryMembership = user.memberships[0];
  const deptRole = primaryMembership
    ? `${primaryMembership.department_code || primaryMembership.department} · ${primaryMembership.role}`
    : 'Member';

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <div className="relative w-full" ref={menuRef}>
      {isOpen && (
        <div className="absolute bottom-full left-0 right-0 mb-2 p-1.5 bg-[var(--surface)] border border-[var(--border)] rounded-xl shadow-[0_8px_24px_rgba(15,17,21,0.08)] z-50 animate-in fade-in zoom-in-95 duration-100">
          <div className="px-3 py-2 border-b border-[var(--border)]">
            <p className="text-[13px] font-medium text-[var(--text)] truncate">{displayName}</p>
            <p className="text-[12px] text-[var(--text-muted)] truncate">{user.email}</p>
          </div>
          <div className="py-1">
            {user.is_admin && (
              <button
                onClick={() => {
                  setIsOpen(false);
                  navigate('/admin');
                }}
                className="w-full flex items-center gap-2 px-3 py-2 text-[13px] text-[var(--text)] hover:bg-[var(--surface-muted)] rounded-lg transition-colors text-left"
              >
                <Shield size={16} strokeWidth={1.5} className="text-[var(--pastel-lavender-text)]" />
                Admin Console
              </button>
            )}
            <button
              onClick={handleLogout}
              className="w-full flex items-center gap-2 px-3 py-2 text-[13px] text-[var(--pastel-rose-text)] hover:bg-[var(--pastel-rose-bg)] rounded-lg transition-colors text-left"
            >
              <LogOut size={16} strokeWidth={1.5} />
              Sign out
            </button>
          </div>
        </div>
      )}

      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-2 rounded-xl hover:bg-[var(--surface-muted)] transition-colors text-left"
      >
        <div className="flex items-center gap-2.5 min-w-0">
          <Avatar name={displayName} size="sm" />
          <div className="min-w-0 flex-1">
            <p className="text-[13px] font-medium text-[var(--text)] truncate">{displayName}</p>
            <Badge variant="role" role={primaryMembership?.role || 'member'} className="mt-0.5 text-[10px] px-1.5 py-0 h-4">
              {deptRole}
            </Badge>
          </div>
        </div>
        <ChevronUp
          size={16}
          strokeWidth={1.5}
          className={`text-[var(--text-muted)] transition-transform duration-150 ${
            isOpen ? '' : 'rotate-180'
          }`}
        />
      </button>
    </div>
  );
};
