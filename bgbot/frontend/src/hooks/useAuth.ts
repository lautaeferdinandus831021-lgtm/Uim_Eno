"use client";
import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import { User } from "@/lib/types";

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    const token = api.getToken();
    if (!token) { setLoading(false); return; }
    api.me().then(setUser).catch(() => api.setToken(null)).finally(() => setLoading(false));
  }, []);
  const login = useCallback(async (email: string, password: string) => {
    const d = await api.login(email, password);
    if (d.user) setUser(d.user);
    return d;
  }, []);
  const logout = useCallback(() => { api.logout(); setUser(null); }, []);
  return { user, loading, login, logout };
}
