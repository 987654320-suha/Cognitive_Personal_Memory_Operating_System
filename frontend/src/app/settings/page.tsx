// 📁 LOCATION: frontend/src/app/settings/page.tsx
"use client";
import { useState } from "react";
import { motion } from "framer-motion";
import { useQuery } from "react-query";
import { getWatcherStatus, startWatcher, stopWatcher, rebuildGraph, API_BASE_URL } from "@/services/api";
import { Settings, Database, Radio, Network, Trash2, RefreshCw, Info } from "lucide-react";
import toast from "react-hot-toast";
import axios from "axios";

const API = API_BASE_URL;

export default function SettingsPage() {
  const [rebuilding, setRebuilding] = useState(false);
  const { data: watcher, refetch: refetchWatcher } = useQuery("watcher-settings", getWatcherStatus);

  const handleRebuildIndex = async () => {
    setRebuilding(true);
    try {
      await axios.post(`${API}/index/rebuild`);
      toast.success("Index rebuild started in background");
    } catch { toast.error("Failed to rebuild index"); }
    finally { setRebuilding(false); }
  };

  const handleRebuildGraph = async () => {
    try {
      await rebuildGraph();
      toast.success("Graph rebuild started");
    } catch { toast.error("Failed to rebuild graph"); }
  };

  const handleSaveIndex = async () => {
    try {
      await axios.post(`${API}/index/save`);
      toast.success("FAISS index saved to disk");
    } catch { toast.error("Failed to save index"); }
  };

  const toggleWatcher = async () => {
    try {
      if (watcher?.running) { await stopWatcher(); toast.success("Watcher stopped"); }
      else                  { await startWatcher(); toast.success("Watcher started"); }
      refetchWatcher();
    } catch { toast.error("Failed to toggle watcher"); }
  };

  const Section = ({ icon: Icon, title, children }: any) => (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="card p-5 mb-4">
      <h2 className="text-sm font-semibold text-white flex items-center gap-2 mb-4">
        <Icon size={15} className="text-brand-400" /> {title}
      </h2>
      {children}
    </motion.div>
  );

  const ActionRow = ({ label, desc, action, danger = false }: any) => (
    <div className="flex items-center justify-between py-3 border-b border-surface-border last:border-0">
      <div>
        <p className="text-sm font-medium text-white">{label}</p>
        <p className="text-xs text-gray-500 mt-0.5">{desc}</p>
      </div>
      <button onClick={action} className={danger ? "btn-ghost border border-red-700/50 text-red-400 text-xs" : "btn-ghost border border-surface-border text-xs"}>
        {label}
      </button>
    </div>
  );

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <div className="mb-6">
        <h1 className="text-xl font-bold text-white flex items-center gap-2">
          <Settings size={20} className="text-brand-400" /> Settings
        </h1>
      </div>

      <Section icon={Database} title="FAISS Index">
        <ActionRow
          label="Rebuild Index"
          desc="Rebuilds the vector search index from all DB memories. Run after bulk import."
          action={handleRebuildIndex}
        />
        <ActionRow
          label="Save Index to Disk"
          desc="Persists the current FAISS index so it survives server restarts."
          action={handleSaveIndex}
        />
      </Section>

      <Section icon={Network} title="Memory Graph">
        <ActionRow
          label="Rebuild Graph"
          desc="Recomputes all memory relationship edges. Run after adding many new files."
          action={handleRebuildGraph}
        />
      </Section>

      <Section icon={Radio} title="Folder Watcher">
        <div className="flex items-center justify-between py-3">
          <div>
            <p className="text-sm font-medium text-white">Auto-ingest new files</p>
            <p className="text-xs text-gray-500 mt-0.5">
              Status: {watcher?.running
                ? <span className="text-green-400">Running</span>
                : <span className="text-gray-400">Stopped</span>}
            </p>
          </div>
          <button onClick={toggleWatcher} className={watcher?.running ? "btn-ghost border border-red-700/50 text-red-400 text-xs" : "btn-primary text-xs"}>
            {watcher?.running ? "Stop" : "Start"}
          </button>
        </div>
        {watcher?.watched_dirs?.map((d: string) => (
          <p key={d} className="text-xs text-gray-600 py-0.5">📁 {d}</p>
        ))}
      </Section>

      <Section icon={Info} title="About">
        <div className="space-y-2 text-sm text-gray-400">
          <div className="flex justify-between">
            <span>System</span>
            <span className="text-white font-medium">NexusMind v2.0</span>
          </div>
          <div className="flex justify-between">
            <span>Search Engine</span>
            <span className="text-brand-400 font-medium">ACMA + GAMA</span>
          </div>
          <div className="flex justify-between">
            <span>Backend</span>
            <span className="text-white">{API}</span>
          </div>
        </div>
      </Section>
    </div>
  );
}
