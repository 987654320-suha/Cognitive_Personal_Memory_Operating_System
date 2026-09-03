// 📁 LOCATION: frontend/src/context/AppContext.tsx
"use client";
import React, { createContext, useContext, useState, useCallback } from "react";
import toast from "react-hot-toast";
import { uploadFile } from "@/services/api";

interface AppContextType {
  // Upload
  uploading:    boolean;
  uploadStage:  string;
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
  const [uploadStage,  setUploadStage]  = useState("");
  const [sidebarOpen,  setSidebarOpen]  = useState(true);
  const [lastQuery,    setLastQuery]    = useState("");

  const uploadFiles = useCallback(async (files: File[]) => {
    setUploading(true);
    let success = 0;
    let failed  = 0;
    for (const file of files) {
      try {
        setUploadStage(`Uploading ${file.name}...`);
        const res = await uploadFile(file, (stage, message) => {
          setUploadStage(`${file.name}: ${message || stage}`);
        });
        console.log(`[Upload] Ingested ${file.name}:`, res);
        success++;
      } catch (err: any) {
        failed++;
        const detail = err?.response?.data?.detail || err?.message || "Upload error";
        console.error(`[Upload] Failed to upload ${file.name}:`, detail);
        toast.error(`Failed to ingest ${file.name}: ${detail}`);
      }
    }
    setUploading(false);
    setUploadStage("");
    if (success > 0) toast.success(`${success} file${success > 1 ? "s" : ""} ingested into CogniSphere`);
  }, []);

  return (
    <AppContext.Provider value={{ uploading, uploadStage, uploadFiles, sidebarOpen, setSidebarOpen, lastQuery, setLastQuery }}>
      {children}
    </AppContext.Provider>
  );
}

export const useApp = () => {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useApp must be used within AppProvider");
  return ctx;
};