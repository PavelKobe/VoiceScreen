import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api, ApiError } from "@/lib/api";
import type { ClientBrief, MeResponse, User } from "./types";

interface AuthState {
  user: User | null;
  client: ClientBrief | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [client, setClient] = useState<ClientBrief | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchMe = useCallback(async () => {
    try {
      const me = await api<MeResponse>("/auth/me");
      setUser(me.user);
      setClient(me.client);
    } catch (err) {
      if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
        setUser(null);
        setClient(null);
      } else {
        throw err;
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchMe();
  }, [fetchMe]);

  const login = useCallback(
    async (email: string, password: string) => {
      await api<User>("/auth/login", {
        method: "POST",
        body: { email, password },
      });
      await fetchMe();
    },
    [fetchMe],
  );

  const logout = useCallback(async () => {
    await api<void>("/auth/logout", { method: "POST" });
    setUser(null);
    setClient(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, client, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
