import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { apiLogin, apiLogout, apiMe, getSettings } from "@/lib/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null); // null = checking, false = unauth, object = auth
  const [settings, setSettings] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const me = await apiMe();
      setUser(me);
    } catch {
      setUser(false);
    }
  }, []);

  const refreshSettings = useCallback(async () => {
    try {
      setSettings(await getSettings());
    } catch {
      setSettings(null);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // Load app settings (company names + roster) once the user is authenticated.
  useEffect(() => {
    if (user && user.role) refreshSettings();
  }, [user, refreshSettings]);

  const login = async (email, password) => {
    const u = await apiLogin(email, password);
    setUser(u);
    return u;
  };

  const logout = async () => {
    try {
      await apiLogout();
    } finally {
      setUser(false);
      setSettings(null);
    }
  };

  const isAdmin = !!user && user.role === "admin";
  const companyA = settings?.company_a || "MBS";
  const companyB = settings?.company_b || "MCORP";

  return (
    <AuthContext.Provider
      value={{ user, login, logout, refresh, isAdmin, settings, refreshSettings, companyA, companyB }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
