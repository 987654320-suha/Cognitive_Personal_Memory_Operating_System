// 📁 LOCATION: frontend/src/components/Layout/AppShell.tsx
"use client";
import React from "react";
import { usePathname } from "next/navigation";
import Sidebar from "@/components/Layout/Sidebar";
import ProtectedRoute from "@/components/Auth/ProtectedRoute";

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname   = usePathname();
  const isAuthPage = pathname === "/login" || pathname === "/register";

  return (
    <ProtectedRoute>
      {isAuthPage ? (
        <main className="min-h-screen w-screen overflow-y-auto bg-surface">
          {children}
        </main>
      ) : (
        <div className="flex h-screen">
          <Sidebar />
          <main className="flex-1 overflow-y-auto min-w-0 bg-surface">
            {children}
          </main>
        </div>
      )}
    </ProtectedRoute>
  );
}
