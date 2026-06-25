import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { apiLogin, apiLogout, apiMe } from "@/lib/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null); // null = checking, false = unauth, object = auth

  const refresh = useCallback(async () => {
    try {
      const me = await apiMe();
      setUser(me);
    } catch {
      setUser(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

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
    }
  };

  const isAdmin = !!user && user.role === "admin";

  return (
    <AuthContext.Provider value={{ user, login, logout, refresh, isAdmin }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
