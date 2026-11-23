import React, { createContext, useContext, useEffect, useState } from "react";
import { apiFetch, getAccessToken, setAccessToken, api } from "./api";

export interface Membership {
  department_id: string;
  department_code: string;
  department_name: string;
  role_level: number;
  department?: string;
  role?: string;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  name?: string;
  is_admin: boolean;
  is_active: boolean;
  memberships: Membership[];
}

export const roleLevelToName = (level: number): "member" | "manager" | "head" => {
  if (level >= 3) return "head";
  if (level === 2) return "manager";
  return "member";
};

const normalizeUser = (u: any): User => {
  const memberships = (u.memberships || []).map((m: any) => ({
    department_id: m.department_id || "",
    department_code: m.department_code || m.department || "HR",
    department_name: m.department_name || m.department || "HR",
    role_level: m.role_level ?? (m.role === "head" ? 3 : m.role === "manager" ? 2 : 1),
    department: m.department || m.department_code || "HR",
    role: m.role || roleLevelToName(m.role_level ?? 1),
  }));

  return {
    id: u.id,
    email: u.email,
    full_name: u.full_name || u.name || "",
    name: u.name || u.full_name || "",
    is_admin: !!u.is_admin,
    is_active: u.is_active ?? true,
    memberships,
  };
};

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  login: (emailOrToken: string, passwordOrUserData?: any, remember?: boolean) => Promise<User | void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Restore session via /auth/refresh cookie on page mount
  useEffect(() => {
    async function restoreSession() {
      try {
        const data = await apiFetch<{ access_token: string; user: any }>("/auth/refresh", {
          method: "POST",
        });
        setAccessToken(data.access_token);
        setUser(normalizeUser(data.user));
      } catch {
        setAccessToken(null);
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    }
    restoreSession();
  }, []);

  const login = async (
    emailOrToken: string,
    passwordOrUserData?: any,
    remember: boolean = false
  ): Promise<User | void> => {
    if (typeof passwordOrUserData === "string") {
      const resp = await api.post<{ access_token: string; user: any }>("/auth/login", {
        email: emailOrToken,
        password: passwordOrUserData,
        remember,
      });
      setAccessToken(resp.data.access_token);
      const normalized = normalizeUser(resp.data.user);
      setUser(normalized);
      return normalized;
    } else {
      setAccessToken(emailOrToken);
      const normalized = normalizeUser(passwordOrUserData || {});
      setUser(normalized);
      return normalized;
    }
  };

  const logout = async () => {
    try {
      await api.post("/auth/logout");
    } catch {
      // Ignore network errors on logout
    } finally {
      setAccessToken(null);
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};

export { getAccessToken };
