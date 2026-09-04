// 📁 LOCATION: frontend/src/context/AuthContext.tsx
"use client";
import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { useRouter, usePathname } from "next/navigation";
import toast from "react-hot-toast";
import {
  UserProfile,
  loginUser,
  registerUser,
  logoutUser,
  getMe,
  changeUserPassword,
} from "@/services/api";

interface AuthContextType {
  user:           UserProfile | null;
  loading:        boolean;
  login:          (email: string, password: string) => Promise<void>;
  register:       (email: string, password: string) => Promise<void>;
  logout:         () => Promise<void>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<void>;
  refreshUser:    () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser]       = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const router                = useRouter();
  const pathname              = usePathname();

  const refreshUser = useCallback(async () => {
    try {
      const profile = await getMe();
      setUser(profile);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const login = async (email: string, password: string) => {
    try {
      const res = await loginUser(email, password);
      setUser(res.user);
      toast.success("Welcome back to CogniSphere!");
      router.push("/");
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || "Invalid email or password";
      toast.error(msg);
      throw err;
    }
  };

  const register = async (email: string, password: string) => {
    try {
      const res = await registerUser(email, password);
      setUser(res.user);
      toast.success("Account created successfully!");
      router.push("/");
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || "Registration failed";
      toast.error(msg);
      throw err;
    }
  };

  const logout = async () => {
    try {
      await logoutUser();
    } catch {
      // Ignore network errors on logout
    } finally {
      setUser(null);
      toast.success("Logged out successfully");
      router.push("/login");
    }
  };

  const changePassword = async (currentPassword: string, newPassword: string) => {
    try {
      await changeUserPassword(currentPassword, newPassword);
      toast.success("Password changed successfully!");
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || "Password change failed";
      toast.error(msg);
      throw err;
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        register,
        logout,
        changePassword,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
};
