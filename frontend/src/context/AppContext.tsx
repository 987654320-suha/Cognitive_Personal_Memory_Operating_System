// 📁 LOCATION: frontend/src/context/AppContext.tsx
"use client";
import React, { createContext, useContext, useState, useCallback } from "react";
import toast from "react-hot-toast";
import { uploadFile } from "@/services/api";

interface AppContextType {
  // Upload
  uploading:    boolean;
  uploadFiles:  (files: File[]) => Promise<void>;
  // Sidebar
  sidebarOpen:  boolean;
  setSidebarOpen: (v: boolean) => void;
  // Search query (shared between pages)
  lastQuery:    string;
  setLastQuery: (q: string) => void;
}

const AppContext = createContext<AppContextType | null>(null);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [uploading,    setUploading]    = useState(false);
  const [sidebarOpen,  setSidebarOpen]  = useState(true);
  const [lastQuery,    setLastQuery]    = useState("");

  const uploadFiles = useCallback(async (files: File[]) => {
    setUploading(true);
    let success = 0;
    let failed  = 0;
    for (const file of files) {
      try {
        await uploadFile(file);
        success++;
      } catch {
        failed++;
      }
    }
    setUploading(false);
    if (success > 0) toast.success(`${success} file${success > 1 ? "s" : ""} ingested`);
    if (failed  > 0) toast.error(`${failed} file${failed > 1 ? "s" : ""} failed`);
  }, []);

  return (
    <AppContext.Provider value={{ uploading, uploadFiles, sidebarOpen, setSidebarOpen, lastQuery, setLastQuery }}>
      {children}
    </AppContext.Provider>
  );
}

export const useApp = () => {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useApp must be used within AppProvider");
  return ctx;
};