// 📁 LOCATION: frontend/src/components/Auth/ProtectedRoute.tsx
"use client";
import React, { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuth } from "@/context/AuthContext";

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router   = useRouter();
  const pathname = usePathname();

  const isAuthPage = pathname === "/login" || pathname === "/register";

  useEffect(() => {
    if (!loading) {
      if (!user && !isAuthPage) {
        router.replace("/login");
      } else if (user && isAuthPage) {
        router.replace("/");
      }
    }
  }, [user, loading, isAuthPage, router]);

  if (loading) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-surface">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-brand-600/20 border border-brand-500/40 flex items-center justify-center animate-pulse">
            <span className="text-brand-400 font-bold text-xl">C</span>
          </div>
          <p className="text-sm font-medium text-gray-400">Loading CogniSphere...</p>
        </div>
      </div>
    );
  }

  // If not logged in and on protected page, don't flash content before redirect
  if (!user && !isAuthPage) {
    return null;
  }

  return <>{children}</>;
}
