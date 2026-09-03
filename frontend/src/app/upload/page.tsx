// 📁 LOCATION: frontend/src/app/upload/page.tsx
"use client";
import { useState } from "react";
import { useQuery } from "react-query";
import { motion } from "framer-motion";
import UploadZone from "@/components/UI/UploadZone";
import { getWatcherStatus, startWatcher, stopWatcher } from "@/services/api";
import { Folder, Radio, RadioTower, CheckCircle, AlertCircle } from "lucide-react";
import toast from "react-hot-toast";

export default function UploadPage() {
  const [watcherLoading, setWatcherLoading] = useState(false);
  const { data: watcher, refetch } = useQuery("watcher", getWatcherStatus, { refetchInterval: 5000 });

  const toggleWatcher = async () => {
    setWatcherLoading(true);
    try {
      if (watcher?.running) {
        await stopWatcher();
        toast.success("Folder watcher stopped");
      } else {
        await startWatcher();
        toast.success("Folder watcher started");
      }
      refetch();
    } catch {
      toast.error("Failed to toggle watcher");
    } finally {
      setWatcherLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <div className="mb-6">
        <h1 className="text-xl font-bold text-white">Upload & Import</h1>
        <p className="text-sm text-gray-400 mt-0.5">Add files to CogniSphere's memory</p>
      </div>

      {/* Manual upload */}
      <div className="mb-6">
        <h2 className="text-sm font-semibold text-white mb-3">Manual Upload</h2>
        <UploadZone />
      </div>

      {/* Auto folder watcher */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="card p-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <RadioTower size={16} className={watcher?.running ? "text-green-400" : "text-gray-500"} />
              <h2 className="text-sm font-semibold text-white">Folder Watcher</h2>
              {watcher?.running
                ? <span className="badge badge-green">Live</span>
                : <span className="badge bg-surface-hover text-gray-400 border border-surface-border">Off</span>
              }
            </div>
            <p className="text-xs text-gray-400">
              Automatically ingests new files from Desktop, Downloads, Documents, Pictures
            </p>
          </div>
          <button
            onClick={toggleWatcher}
            disabled={watcherLoading}
            className={watcher?.running ? "btn-ghost border border-red-700/50 text-red-400 hover:bg-red-900/20" : "btn-primary"}
          >
            {watcherLoading ? "..." : watcher?.running ? "Stop" : "Start"}
          </button>
        </div>

        {watcher?.watched_dirs?.length > 0 && (
          <div className="mt-4 pt-4 border-t border-surface-border">
            <p className="text-xs text-gray-500 mb-2">Watching directories:</p>
            <div className="space-y-1">
              {watcher.watched_dirs.map((dir: string) => (
                <div key={dir} className="flex items-center gap-2 text-xs text-gray-400">
                  <Folder size={12} className="text-brand-400" />
                  {dir}
                </div>
              ))}
            </div>
          </div>
        )}
      </motion.div>

      {/* Tips */}
      <div className="mt-6 card p-5">
        <h2 className="text-sm font-semibold text-white mb-3">Supported file types</h2>
        <div className="grid grid-cols-2 gap-2 text-xs text-gray-400">
          {[
            ["📄 PDF",   "Resumes, certificates, statements"],
            ["📝 DOCX",  "Word documents, reports"],
            ["🖼️ Images","JPG, PNG, WebP — auto OCR + object detection"],
            ["📃 TXT",   "Notes, text files"],
          ].map(([type, desc]) => (
            <div key={type} className="bg-surface-hover rounded-lg p-3">
              <p className="font-medium text-white mb-0.5">{type}</p>
              <p>{desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}