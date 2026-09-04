// 📁 LOCATION: frontend/src/app/watcher/page.tsx
"use client";
import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "react-query";
import { motion } from "framer-motion";
import {
  FolderCheck, HardDrive, Folder, Plus, Trash2, Pause, Play,
  ShieldCheck, AlertCircle, RefreshCw, Radio, CheckCircle2,
  XCircle, Clock, Laptop
} from "lucide-react";
import toast from "react-hot-toast";
import {
  getWatcherStatus,
  startWatcher,
  stopWatcher,
  getWatcherLocations,
  addWatcherLocation,
  pauseWatcherLocation,
  resumeWatcherLocation,
  deleteWatcherLocation,
  WatcherLocation,
} from "@/services/api";

export default function WatcherPage() {
  const queryClient = useQueryClient();
  const [newPath, setNewPath] = useState("");
  const [newName, setNewName] = useState("");
  const [newType, setNewType] = useState("custom");
  const [isAdding, setIsAdding] = useState(false);

  // Queries
  const { data: status, refetch: refetchStatus } = useQuery("watcher-status", getWatcherStatus, {
    refetchInterval: 5000,
  });

  const { data: locations = [], isLoading: loadingLocations } = useQuery(
    "watcher-locations",
    getWatcherLocations
  );

  // Toggle watcher mutation
  const toggleWatcherMutation = useMutation(
    async () => {
      if (status?.running) {
        return await stopWatcher();
      } else {
        return await startWatcher();
      }
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries("watcher-status");
        toast.success(status?.running ? "Watcher stopped" : "Watcher started");
      },
      onError: (err: any) => {
        toast.error(err?.response?.data?.error || "Failed to toggle watcher");
      },
    }
  );

  // Add location mutation
  const addLocationMutation = useMutation(
    async () => {
      if (!newPath.trim() || !newName.trim()) return;
      return await addWatcherLocation({
        path: newPath.trim(),
        display_name: newName.trim(),
        location_type: newType,
        permission_status: "granted",
        enabled: true,
      });
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries("watcher-locations");
        queryClient.invalidateQueries("watcher-status");
        setNewPath("");
        setNewName("");
        setIsAdding(false);
        toast.success("Folder authorized successfully!");
      },
      onError: (err: any) => {
        toast.error(err?.response?.data?.detail || "Failed to authorize folder");
      },
    }
  );

  // Pause location mutation
  const pauseMutation = useMutation(
    async (id: number) => await pauseWatcherLocation(id),
    {
      onSuccess: () => {
        queryClient.invalidateQueries("watcher-locations");
        toast.success("Folder sync paused");
      },
    }
  );

  // Resume location mutation
  const resumeMutation = useMutation(
    async (id: number) => await resumeWatcherLocation(id),
    {
      onSuccess: () => {
        queryClient.invalidateQueries("watcher-locations");
        toast.success("Folder sync resumed");
      },
    }
  );

  // Delete/Revoke mutation
  const deleteMutation = useMutation(
    async (id: number) => await deleteWatcherLocation(id),
    {
      onSuccess: () => {
        queryClient.invalidateQueries("watcher-locations");
        toast.success("Folder permission revoked");
      },
    }
  );

  const standardLocations = locations.filter((loc) => loc.location_type === "standard");
  const customLocations = locations.filter((loc) => loc.location_type !== "standard");

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      {/* ── Page Header ───────────────────────────────────────────── */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <FolderCheck size={22} className="text-brand-400" /> Desktop Watcher & Folder Permissions
          </h1>
          <p className="text-xs text-gray-400 mt-1">
            Explicitly authorize local drives and directories for continuous cognitive synchronization.
          </p>
        </div>

        <button
          onClick={() => toggleWatcherMutation.mutate()}
          disabled={toggleWatcherMutation.isLoading}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
            status?.running
              ? "bg-rose-500/20 text-rose-300 border border-rose-500/40 hover:bg-rose-500/30"
              : "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 hover:bg-emerald-500/30"
          }`}
        >
          <Radio size={14} className={status?.running ? "animate-pulse text-emerald-400" : "text-gray-400"} />
          {status?.running ? "Stop Watcher" : "Start Watcher"}
        </button>
      </div>

      {/* ── Architectural Notice ────────────────────────────────────── */}
      <div className="bg-[#16162a]/90 border border-[#2a2a45] rounded-2xl p-4.5 flex items-start gap-3.5">
        <ShieldCheck size={20} className="text-brand-400 shrink-0 mt-0.5" />
        <div className="text-xs space-y-1">
          <p className="font-semibold text-gray-200">Zero-Trust Local Permissions Architecture</p>
          <p className="text-gray-400 leading-relaxed">
            Web browsers are sandboxed and cannot silently access your filesystem. CogniSphere operates through
            explicit local user permissions. Only directories with <span className="text-brand-300 font-medium">Granted</span> status
            are scanned and ingested by your local Desktop Agent.
          </p>
        </div>
      </div>

      {/* ── Standard User Folders ───────────────────────────────────── */}
      <div className="card p-5 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-surface-border">
          <div>
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <Folder size={16} className="text-brand-400" /> Standard User Folders
            </h2>
            <p className="text-[11px] text-gray-400 mt-0.5">
              Core system user directories available for synchronization.
            </p>
          </div>
          <span className="text-xs px-2.5 py-1 rounded-full bg-surface border border-surface-border text-gray-300">
            {standardLocations.filter((l) => l.enabled).length} of {standardLocations.length} Active
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {standardLocations.map((loc) => (
            <div
              key={loc.id}
              className={`p-3.5 rounded-xl border transition-all flex items-center justify-between ${
                loc.enabled
                  ? "bg-surface-card border-brand-500/30 shadow-sm"
                  : "bg-surface/50 border-surface-border opacity-70"
              }`}
            >
              <div className="flex items-center gap-3 min-w-0">
                <div
                  className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 ${
                    loc.enabled ? "bg-brand-500/20 text-brand-300" : "bg-gray-800 text-gray-500"
                  }`}
                >
                  <Folder size={18} />
                </div>
                <div className="min-w-0">
                  <p className="text-xs font-semibold text-white truncate">{loc.display_name}</p>
                  <p className="text-[10px] text-gray-400 truncate font-mono mt-0.5" title={loc.path}>
                    {loc.path}
                  </p>
                  <div className="flex items-center gap-2 mt-1">
                    <span
                      className={`text-[9px] font-semibold px-1.5 py-0.5 rounded ${
                        loc.enabled
                          ? "bg-emerald-500/20 text-emerald-300"
                          : "bg-amber-500/20 text-amber-300"
                      }`}
                    >
                      {loc.enabled ? "Active" : "Paused"}
                    </span>
                    {loc.last_scan_at && (
                      <span className="text-[9px] text-gray-500 flex items-center gap-1">
                        <Clock size={10} /> Scanned
                      </span>
                    )}
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-1.5 ml-2">
                {loc.enabled ? (
                  <button
                    onClick={() => pauseMutation.mutate(loc.id)}
                    title="Pause sync"
                    className="p-1.5 text-gray-400 hover:text-amber-400 hover:bg-surface-hover rounded-lg transition-colors cursor-pointer"
                  >
                    <Pause size={14} />
                  </button>
                ) : (
                  <button
                    onClick={() => resumeMutation.mutate(loc.id)}
                    title="Resume sync"
                    className="p-1.5 text-gray-400 hover:text-emerald-400 hover:bg-surface-hover rounded-lg transition-colors cursor-pointer"
                  >
                    <Play size={14} />
                  </button>
                )}
                <button
                  onClick={() => deleteMutation.mutate(loc.id)}
                  title="Revoke permission"
                  className="p-1.5 text-gray-400 hover:text-rose-400 hover:bg-surface-hover rounded-lg transition-colors cursor-pointer"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Custom Folders & Drives ─────────────────────────────────── */}
      <div className="card p-5 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-surface-border">
          <div>
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <HardDrive size={16} className="text-purple-400" /> Custom Folders & Extra Drives
            </h2>
            <p className="text-[11px] text-gray-400 mt-0.5">
              Authorize specific projects, USB drives, or custom directory locations.
            </p>
          </div>

          <button
            onClick={() => setIsAdding(!isAdding)}
            className="btn-primary text-xs py-1.5 px-3 flex items-center gap-1.5 cursor-pointer"
          >
            <Plus size={14} /> Authorize Folder
          </button>
        </div>

        {/* Add Folder Modal/Form */}
        {isAdding && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            className="p-4 rounded-xl bg-surface border border-surface-border space-y-3"
          >
            <p className="text-xs font-semibold text-white">Grant New Directory Permission</p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label className="block text-[10px] text-gray-400 font-medium uppercase mb-1">
                  Folder / Drive Path
                </label>
                <input
                  type="text"
                  placeholder="e.g. D:\Projects or /Users/name/work"
                  value={newPath}
                  onChange={(e) => setNewPath(e.target.value)}
                  className="w-full bg-surface-card border border-surface-border rounded-lg px-3 py-1.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-brand-500"
                />
              </div>

              <div>
                <label className="block text-[10px] text-gray-400 font-medium uppercase mb-1">
                  Display Name
                </label>
                <input
                  type="text"
                  placeholder="e.g. Work Projects"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  className="w-full bg-surface-card border border-surface-border rounded-lg px-3 py-1.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-brand-500"
                />
              </div>
            </div>

            <div className="flex items-center justify-between pt-1">
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-gray-400 uppercase">Type:</span>
                <select
                  value={newType}
                  onChange={(e) => setNewType(e.target.value)}
                  className="bg-surface-card border border-surface-border rounded-lg px-2 py-1 text-xs text-white focus:outline-none"
                >
                  <option value="custom">Custom Folder</option>
                  <option value="drive">External Drive</option>
                </select>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setIsAdding(false)}
                  className="btn-ghost text-xs py-1 px-3 border border-surface-border"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={() => addLocationMutation.mutate()}
                  disabled={!newPath.trim() || !newName.trim() || addLocationMutation.isLoading}
                  className="btn-primary text-xs py-1 px-3 disabled:opacity-50"
                >
                  {addLocationMutation.isLoading ? "Authorizing..." : "Grant Permission"}
                </button>
              </div>
            </div>
          </motion.div>
        )}

        {/* Custom locations list */}
        {customLocations.length === 0 ? (
          <div className="text-center py-6 text-gray-500 text-xs">
            No custom folders authorized yet. Click "Authorize Folder" to add extra directories.
          </div>
        ) : (
          <div className="space-y-2">
            {customLocations.map((loc) => (
              <div
                key={loc.id}
                className="p-3.5 rounded-xl bg-surface-card border border-surface-border flex items-center justify-between"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-8 h-8 rounded-lg bg-purple-500/20 text-purple-300 flex items-center justify-center shrink-0">
                    {loc.location_type === "drive" ? <HardDrive size={16} /> : <Folder size={16} />}
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs font-semibold text-white truncate">{loc.display_name}</p>
                    <p className="text-[10px] text-gray-400 truncate font-mono mt-0.5">{loc.path}</p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span
                    className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                      loc.enabled
                        ? "bg-emerald-500/20 text-emerald-300"
                        : "bg-amber-500/20 text-amber-300"
                    }`}
                  >
                    {loc.enabled ? "Active" : "Paused"}
                  </span>

                  {loc.enabled ? (
                    <button
                      onClick={() => pauseMutation.mutate(loc.id)}
                      title="Pause sync"
                      className="p-1.5 text-gray-400 hover:text-amber-400 hover:bg-surface-hover rounded-lg transition-colors cursor-pointer"
                    >
                      <Pause size={14} />
                    </button>
                  ) : (
                    <button
                      onClick={() => resumeMutation.mutate(loc.id)}
                      title="Resume sync"
                      className="p-1.5 text-gray-400 hover:text-emerald-400 hover:bg-surface-hover rounded-lg transition-colors cursor-pointer"
                    >
                      <Play size={14} />
                    </button>
                  )}

                  <button
                    onClick={() => deleteMutation.mutate(loc.id)}
                    title="Revoke permission"
                    className="p-1.5 text-gray-400 hover:text-rose-400 hover:bg-surface-hover rounded-lg transition-colors cursor-pointer"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
