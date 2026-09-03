// 📁 LOCATION: frontend/src/app/settings/page.tsx
"use client";
import { useState } from "react";
import { motion } from "framer-motion";
import { useQuery } from "react-query";
import {
  getWatcherStatus, startWatcher, stopWatcher, rebuildGraph,
  getSyncDevices, unpairDevice, updateDeviceFolders, pairDevice,
  SyncDevice, WatchedFolder, API_BASE_URL
} from "@/services/api";
import {
  Settings, Database, Radio, Network, Trash2, RefreshCw,
  Info, Monitor, Folder, Plus, Pause, Play, CheckCircle,
  Copy, Laptop, HardDrive
} from "lucide-react";
import toast from "react-hot-toast";
import axios from "axios";

const API = API_BASE_URL;

export default function SettingsPage() {
  const [rebuilding, setRebuilding] = useState(false);
  const [pairedInfo, setPairedInfo] = useState<any>(null);

  const { data: watcher, refetch: refetchWatcher } = useQuery("watcher-settings", getWatcherStatus);
  const { data: syncOverview, refetch: refetchSync } = useQuery("sync-devices", getSyncDevices, { refetchInterval: 8000 });

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

  const handlePairNewDevice = async () => {
    try {
      const res = await pairDevice("Windows PC", "Windows");
      setPairedInfo(res);
      toast.success("Pairing token generated!");
      refetchSync();
    } catch (err: any) {
      toast.error("Failed to generate pairing token");
    }
  };

  const handleDisconnectDevice = async (deviceId: string) => {
    if (!confirm("Are you sure you want to disconnect this device?")) return;
    try {
      await unpairDevice(deviceId);
      toast.success("Device disconnected");
      refetchSync();
    } catch {
      toast.error("Failed to disconnect device");
    }
  };

  const handleToggleFolder = async (device: SyncDevice, folderId: string, currentEnabled: boolean) => {
    const updated = device.watched_folders.map(f =>
      f.id === folderId ? { ...f, enabled: !currentEnabled } : f
    );
    try {
      await updateDeviceFolders(device.device_id, updated);
      toast.success(!currentEnabled ? "Folder monitoring resumed" : "Folder monitoring paused");
      refetchSync();
    } catch {
      toast.error("Failed to update folder state");
    }
  };

  const handleRemoveFolder = async (device: SyncDevice, folderId: string) => {
    const updated = device.watched_folders.filter(f => f.id !== folderId);
    try {
      await updateDeviceFolders(device.device_id, updated);
      toast.success("Folder removed from monitoring");
      refetchSync();
    } catch {
      toast.error("Failed to remove folder");
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success("Copied to clipboard!");
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

  const devices = syncOverview?.devices || [];

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <div className="mb-6">
        <h1 className="text-xl font-bold text-white flex items-center gap-2">
          <Settings size={20} className="text-brand-400" /> Settings
        </h1>
        <p className="text-xs text-gray-400 mt-1">Configure CogniSphere memory, desktop synchronization, and search indices.</p>
      </div>

      {/* ── Desktop Sync & Connected Computers ─────────────────────────── */}
      <Section icon={Laptop} title="Connected Computer (Desktop Agent)">
        {devices.length === 0 ? (
          <div className="bg-surface-hover/60 border border-surface-border rounded-xl p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm font-semibold text-white mb-1">No Desktop Agent Connected</p>
                <p className="text-xs text-gray-400 mb-4 leading-relaxed">
                  Connect your Windows computer to synchronize authorized local folders
                  (Desktop, Documents, Downloads, Pictures, etc.) directly into CogniSphere.
                </p>
              </div>
              <button onClick={handlePairNewDevice} className="btn-primary text-xs flex items-center gap-1.5 whitespace-nowrap">
                <Plus size={13} /> Pair New Agent
              </button>
            </div>

            {pairedInfo ? (
              <div className="mt-3 p-3.5 bg-black/40 border border-brand-500/40 rounded-lg">
                <p className="text-xs font-semibold text-brand-300 mb-1.5 flex items-center gap-1.5">
                  <CheckCircle size={13} /> Pairing Credentials Generated:
                </p>
                <p className="text-xs text-gray-300 font-mono break-all mb-1">Device ID: {pairedInfo.device_id}</p>
                <p className="text-xs text-gray-300 font-mono break-all mb-3">Token: {pairedInfo.auth_token}</p>
                <p className="text-xs text-gray-400 mb-2">Run this in your terminal to connect your computer:</p>
                <div className="flex items-center justify-between bg-black/60 px-3 py-2 rounded text-xs font-mono text-brand-300 border border-surface-border">
                  <span>python desktop_agent/agent.py --server {API}</span>
                  <button onClick={() => copyToClipboard(`python desktop_agent/agent.py --server ${API}`)} className="text-gray-400 hover:text-white ml-2">
                    <Copy size={13} />
                  </button>
                </div>
              </div>
            ) : (
              <div className="mt-2 text-xs text-gray-500 bg-surface/50 p-3 rounded border border-surface-border">
                <span className="font-medium text-gray-400">Quick Start:</span> Run <code className="text-brand-300">python desktop_agent/agent.py --server {API}</code> on your local computer to start the setup wizard.
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            {devices.map((device: SyncDevice) => {
              const isLive = device.status === "connected" || device.status === "watching";
              return (
                <div key={device.device_id} className="bg-surface-hover/60 border border-surface-border rounded-xl p-5">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-lg bg-brand-600/20 border border-brand-500/30 flex items-center justify-center">
                        <Monitor size={17} className="text-brand-400" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <p className="text-sm font-bold text-white">{device.device_name}</p>
                          <span className={`inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full border ${
                            isLive
                              ? "bg-green-900/20 border-green-700/30 text-green-400"
                              : "bg-gray-800 border-gray-700 text-gray-400"
                          }`}>
                            <span className={`w-1.5 h-1.5 rounded-full ${isLive ? "bg-green-400 animate-pulse" : "bg-gray-400"}`} />
                            {isLive ? "Connected" : "Disconnected"}
                          </span>
                        </div>
                        <p className="text-xs text-gray-400 mt-0.5">
                          {device.os_info} • Indexed files: <span className="text-white font-medium">{device.indexed_files_count ?? 0}</span> • Last sync: {device.last_sync ? new Date(device.last_sync).toLocaleTimeString() : "Never"}
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={() => handleDisconnectDevice(device.device_id)}
                      className="btn-ghost border border-red-800/40 text-red-400 hover:bg-red-950/20 text-xs px-2.5 py-1"
                    >
                      Disconnect
                    </button>
                  </div>

                  {/* Watched Folders */}
                  <div className="mt-4 pt-3 border-t border-surface-border">
                    <p className="text-xs font-semibold text-gray-400 mb-2.5 flex items-center gap-1.5">
                      <HardDrive size={13} className="text-brand-400" /> Watched Folders
                    </p>
                    {device.watched_folders?.length === 0 ? (
                      <p className="text-xs text-gray-500 italic">No folders configured yet. Run the desktop agent to select folders.</p>
                    ) : (
                      <div className="space-y-2">
                        {device.watched_folders.map(f => (
                          <div key={f.id} className="flex items-center justify-between p-2.5 rounded-lg bg-black/20 border border-surface-border/60">
                            <div className="flex items-center gap-2.5">
                              <Folder size={14} className={f.enabled ? "text-brand-400" : "text-gray-500"} />
                              <div>
                                <p className={`text-xs font-medium ${f.enabled ? "text-white" : "text-gray-400"}`}>{f.name}</p>
                                <p className="text-[11px] text-gray-500 truncate max-w-sm">{f.path}</p>
                              </div>
                            </div>
                            <div className="flex items-center gap-2">
                              <span className="text-[11px] text-gray-400">{f.file_count ?? 0} files</span>
                              <button
                                onClick={() => handleToggleFolder(device, f.id, f.enabled)}
                                className={`text-[11px] px-2 py-0.5 rounded border transition-colors ${
                                  f.enabled
                                    ? "border-yellow-700/40 text-yellow-400 hover:bg-yellow-950/20"
                                    : "border-green-700/40 text-green-400 hover:bg-green-950/20"
                                }`}
                              >
                                {f.enabled ? "Pause" : "Resume"}
                              </button>
                              <button
                                onClick={() => handleRemoveFolder(device, f.id)}
                                className="text-gray-500 hover:text-red-400 p-1"
                                title="Remove folder"
                              >
                                <Trash2 size={12} />
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </Section>

      {/* ── Vector Index & Graph ────────────────────────────────────────── */}
      <Section icon={Database} title="FAISS Vector Index">
        <ActionRow
          label="Rebuild Index"
          desc="Rebuilds the vector search index from all DB memories. Run after bulk sync."
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
          desc="Recomputes all memory relationship edges. Run after adding new desktop files."
          action={handleRebuildGraph}
        />
      </Section>

      <Section icon={Radio} title="Server Local Watcher">
        <div className="flex items-center justify-between py-3">
          <div>
            <p className="text-sm font-medium text-white">Server-side file monitor</p>
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
      </Section>

      <Section icon={Info} title="About">
        <div className="space-y-2 text-sm text-gray-400">
          <div className="flex justify-between">
            <span>System</span>
            <span className="text-white font-medium">CogniSphere v2.0</span>
          </div>
          <div className="flex justify-between">
            <span>Engine</span>
            <span className="text-brand-400 font-medium">ACMA + GAMA</span>
          </div>
          <div className="flex justify-between">
            <span>Backend</span>
            <span className="text-white font-mono text-xs">{API}</span>
          </div>
        </div>
      </Section>
    </div>
  );
}
