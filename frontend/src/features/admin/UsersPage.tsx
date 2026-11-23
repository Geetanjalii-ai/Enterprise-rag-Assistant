import React, { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { PageHeader } from '../../components/ui/PageHeader';
import { Table, Column } from '../../components/ui/Table';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { Drawer } from '../../components/ui/Drawer';
import { Input } from '../../components/ui/Input';
import { Select } from '../../components/ui/Select';
import { Checkbox } from '../../components/ui/Checkbox';
import { UserPlus, Copy, Check, ShieldCheck, Edit2, Shield } from 'lucide-react';
import { toast } from 'sonner';

interface UserItem {
  id: string;
  full_name: string;
  name?: string;
  email: string;
  is_admin: boolean;
  is_active: boolean;
  memberships: {
    department_id?: string;
    department_code?: string;
    department_name?: string;
    department?: string;
    role?: string;
    role_level?: number;
  }[];
}

const DEPARTMENTS = [
  { value: 'HR', label: 'Human Resources (HR)' },
  { value: 'Finance', label: 'Finance & Accounting' },
  { value: 'IT', label: 'Information Technology (IT)' },
  { value: 'Engineering', label: 'Engineering' },
  { value: 'Sales', label: 'Sales & Marketing' },
  { value: 'Legal', label: 'Legal' },
];

const ROLES = [
  { value: 'member', label: 'Member (Level 1)' },
  { value: 'manager', label: 'Manager (Level 2)' },
  { value: 'head', label: 'Department Head (Level 3)' },
];

export const UsersPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<UserItem | null>(null);
  const [tempPassword, setTempPassword] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // Add Form state
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [department, setDepartment] = useState('HR');
  const [role, setRole] = useState('member');
  const [isAdmin, setIsAdmin] = useState(false);
  const [isCreating, setIsCreating] = useState(false);

  // Edit Form state
  const [editFullName, setEditFullName] = useState('');
  const [editDept, setEditDept] = useState('HR');
  const [editRole, setEditRole] = useState('member');
  const [editIsAdmin, setEditIsAdmin] = useState(false);
  const [editIsActive, setEditIsActive] = useState(true);
  const [isUpdating, setIsUpdating] = useState(false);

  const { data: users = [], isLoading } = useQuery<UserItem[]>({
    queryKey: ['admin-users'],
    queryFn: async () => {
      const res = await api.get('/admin/users');
      return res.data;
    },
  });

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !email.trim()) {
      toast.error('Please fill in name and email');
      return;
    }

    setIsCreating(true);
    try {
      const res = await api.post('/admin/users', {
        full_name: name.trim(),
        email: email.trim(),
        department,
        role,
        is_admin: isAdmin,
      });

      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
      setTempPassword(res.data.temporary_password);
      toast.success('User account created');
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to create user');
    } finally {
      setIsCreating(false);
    }
  };

  const handleStartEdit = (user: UserItem) => {
    setEditingUser(user);
    setEditFullName(user.full_name || user.name || '');
    setEditIsAdmin(user.is_admin);
    setEditIsActive(user.is_active);

    const mem = user.memberships[0];
    if (mem) {
      const code = mem.department || mem.department_code || 'HR';
      setEditDept(code);
      const roleStr = mem.role || (mem.role_level && mem.role_level >= 3 ? 'head' : (mem.role_level === 2 ? 'manager' : 'member')) || 'member';
      setEditRole(roleStr);
    } else {
      setEditDept('HR');
      setEditRole('member');
    }
  };

  const handleUpdateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingUser) return;

    setIsUpdating(true);
    try {
      await api.patch(`/admin/users/${editingUser.id}`, {
        full_name: editFullName.trim(),
        is_admin: editIsAdmin,
        is_active: editIsActive,
        department: editDept,
        role: editRole,
      });

      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
      toast.success('User permissions updated successfully');
      setEditingUser(null);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to update user');
    } finally {
      setIsUpdating(false);
    }
  };

  const handleCloseDrawer = () => {
    setIsAddOpen(false);
    setTempPassword(null);
    setName('');
    setEmail('');
    setIsAdmin(false);
  };

  const handleCopyPassword = () => {
    if (tempPassword) {
      navigator.clipboard.writeText(tempPassword);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
      toast.success('Password copied to clipboard');
    }
  };

  const columns: Column<UserItem>[] = [
    {
      header: 'Employee',
      accessorKey: 'full_name',
      cell: (u) => (
        <div>
          <p className="font-medium text-[14px] text-[var(--text)]">
            {u.full_name || u.name}
          </p>
          <p className="text-[12px] text-[var(--text-subtle)]">{u.email}</p>
        </div>
      ),
    },
    {
      header: 'Department & Role',
      cell: (u) => (
        <div className="flex flex-wrap gap-1">
          {u.memberships.length > 0 ? (
            u.memberships.map((m, idx) => {
              const deptName = m.department || m.department_code || m.department_name || 'General';
              const roleName = m.role || (m.role_level && m.role_level >= 3 ? 'head' : (m.role_level === 2 ? 'manager' : 'member')) || 'member';
              return (
                <Badge key={idx} variant="role" role={roleName}>
                  {deptName} · {roleName}
                </Badge>
              );
            })
          ) : (
            <span className="text-[12px] text-[var(--text-subtle)]">No department assigned</span>
          )}
        </div>
      ),
    },
    {
      header: 'Privileges',
      cell: (u) =>
        u.is_admin ? (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[12px] font-medium bg-[var(--pastel-lavender-bg)] text-[var(--pastel-lavender-text)]">
            <Shield size={12} />
            Administrator
          </span>
        ) : (
          <span className="text-[13px] text-[var(--text-muted)]">Standard User</span>
        ),
    },
    {
      header: 'Account Status',
      cell: (u) => (
        <Badge variant="status" status={u.is_active ? 'active' : 'archived'}>
          {u.is_active ? 'Active' : 'Disabled'}
        </Badge>
      ),
    },
    {
      header: 'Actions',
      cell: (u) => (
        <div className="flex justify-end">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => handleStartEdit(u)}
            className="gap-1.5"
            title="Edit User Permissions"
          >
            <Edit2 size={14} />
            Edit
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Users & Permissions"
        description="Admin-only user provisioning, department assignments, and access control management."
        action={
          <Button variant="primary" onClick={() => setIsAddOpen(true)} className="gap-2">
            <UserPlus size={16} strokeWidth={1.5} />
            Add User
          </Button>
        }
      />

      <Table
        data={users}
        columns={columns}
        isLoading={isLoading}
        emptyMessage="No users registered in system."
      />

      {/* Add User Drawer */}
      <Drawer
        isOpen={isAddOpen}
        onClose={handleCloseDrawer}
        title="Create User Account"
      >
        {tempPassword ? (
          <div className="space-y-4">
            <div className="p-4 bg-[var(--pastel-mint-bg)] border border-[var(--pastel-mint-text)]/20 rounded-xl text-center">
              <ShieldCheck size={28} className="mx-auto text-[var(--pastel-mint-text)] mb-2" />
              <h3 className="font-semibold text-[15px] text-[var(--text)]">
                Account Successfully Created
              </h3>
              <p className="text-[12px] text-[var(--text-muted)] mt-1">
                Please securely copy the temporary password below. It will only be shown once.
              </p>

              <div className="mt-4 p-3 bg-[var(--surface)] border border-[var(--border)] rounded-lg flex items-center justify-between font-mono text-[14px]">
                <span className="select-all font-semibold">{tempPassword}</span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleCopyPassword}
                  className="gap-1.5"
                >
                  {copied ? <Check size={14} className="text-green-600" /> : <Copy size={14} />}
                  {copied ? 'Copied' : 'Copy'}
                </Button>
              </div>
            </div>

            <Button
              variant="secondary"
              className="w-full"
              onClick={handleCloseDrawer}
            >
              Done
            </Button>
          </div>
        ) : (
          <form onSubmit={handleCreateUser} className="space-y-4">
            <Input
              label="Full Name"
              placeholder="e.g. Jane Doe"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />

            <Input
              label="Work Email"
              type="email"
              placeholder="jane@company.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />

            <Select
              label="Department"
              value={department}
              onChange={(e) => setDepartment(e.target.value)}
              options={DEPARTMENTS}
            />

            <Select
              label="Role Level"
              value={role}
              onChange={(e) => setRole(e.target.value)}
              options={ROLES}
            />

            <div className="pt-2">
              <Checkbox
                label="Grant System Administrator privileges"
                checked={isAdmin}
                onChange={(e) => setIsAdmin(e.target.checked)}
              />
            </div>

            <div className="pt-4 flex justify-end gap-2">
              <Button
                type="button"
                variant="secondary"
                onClick={handleCloseDrawer}
              >
                Cancel
              </Button>
              <Button type="submit" variant="primary" isLoading={isCreating}>
                Create User
              </Button>
            </div>
          </form>
        )}
      </Drawer>

      {/* Edit User Drawer */}
      <Drawer
        isOpen={!!editingUser}
        onClose={() => setEditingUser(null)}
        title="Edit User Permissions"
      >
        {editingUser && (
          <form onSubmit={handleUpdateUser} className="space-y-4">
            <div>
              <p className="text-[12px] text-[var(--text-subtle)] uppercase tracking-wider font-semibold mb-1">
                Account Email
              </p>
              <p className="text-[14px] font-mono text-[var(--text)] bg-[var(--surface-muted)] p-2.5 rounded-lg border border-[var(--border)]">
                {editingUser.email}
              </p>
            </div>

            <Input
              label="Full Name"
              value={editFullName}
              onChange={(e) => setEditFullName(e.target.value)}
              required
            />

            <Select
              label="Department"
              value={editDept}
              onChange={(e) => setEditDept(e.target.value)}
              options={DEPARTMENTS}
            />

            <Select
              label="Role Level"
              value={editRole}
              onChange={(e) => setEditRole(e.target.value)}
              options={ROLES}
            />

            <div className="pt-2 space-y-2">
              <Checkbox
                label="System Administrator access"
                checked={editIsAdmin}
                onChange={(e) => setEditIsAdmin(e.target.checked)}
              />

              <Checkbox
                label="Account is Active (uncheck to disable login)"
                checked={editIsActive}
                onChange={(e) => setEditIsActive(e.target.checked)}
              />
            </div>

            <div className="pt-4 flex justify-end gap-2">
              <Button
                type="button"
                variant="secondary"
                onClick={() => setEditingUser(null)}
              >
                Cancel
              </Button>
              <Button type="submit" variant="primary" isLoading={isUpdating}>
                Save Changes
              </Button>
            </div>
          </form>
        )}
      </Drawer>
    </div>
  );
};
