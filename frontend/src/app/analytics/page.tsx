// 📁 LOCATION: frontend/src/app/analytics/page.tsx
"use client";

import { useQuery } from "react-query";
import { motion } from "framer-motion";
import { getStats } from "@/services/api";
import { BarChart3, Database, Target, TrendingUp, AlertTriangle, Activity } from "lucide-react";

export default function AnalyticsPage() {
  const { data: stats, isLoading } = useQuery("stats", getStats, { refetchInterval: 15000 });

  if (isLoading) {
    return (
      <div className="p-6 max-w-6xl mx-auto flex items-center justify-center py-20 text-gray-400">
        Loading analytics...
      </div>
    );
  }

  const totals = stats?.totals || { memories: 0, goals: 0, goal_memory_edges: 0 };
  const acma = stats?.acma || { avg_importance_score: 0.5, total_retrievals: 0, most_accessed: [] };
  const files = stats?.files || { by_type: {}, embedding_coverage: "0/0", object_detection_coverage: "0/0" };

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <BarChart3 className="text-brand-400" size={24} />
          <h1 className="text-2xl font-bold text-white">Memory Analytics</h1>
        </div>
        <p className="text-sm text-gray-400">
          System health, memory distribution, access frequency, and ACMA retrieval statistics (for Figure 11 & Qualitative Analysis).
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="card p-4 space-y-1">
          <span className="text-xs text-gray-400 flex items-center gap-1.5">
            <Database size={14} className="text-brand-400" /> Total Memories
          </span>
          <p className="text-2xl font-bold text-white">{totals.memories}</p>
          <span className="text-[11px] text-gray-500">Active memory store</span>
        </div>

        <div className="card p-4 space-y-1">
          <span className="text-xs text-gray-400 flex items-center gap-1.5">
            <TrendingUp size={14} className="text-emerald-400" /> Avg Importance
          </span>
          <p className="text-2xl font-bold text-emerald-400">
            {acma.avg_importance_score}
          </p>
          <span className="text-[11px] text-gray-500">0.0 to 1.0 importance scale</span>
        </div>

        <div className="card p-4 space-y-1">
          <span className="text-xs text-gray-400 flex items-center gap-1.5">
            <Activity size={14} className="text-purple-400" /> Total Retrievals
          </span>
          <p className="text-2xl font-bold text-purple-400">
            {acma.total_retrievals}
          </p>
          <span className="text-[11px] text-gray-500">Access count accumulator</span>
        </div>

        <div className="card p-4 space-y-1">
          <span className="text-xs text-gray-400 flex items-center gap-1.5">
            <Target size={14} className="text-yellow-400" /> Active Goals
          </span>
          <p className="text-2xl font-bold text-yellow-400">
            {totals.goals}
          </p>
          <span className="text-[11px] text-gray-500">{totals.goal_memory_edges} goal-linked memories</span>
        </div>
      </div>

      {/* Main Analytics Content */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Most Accessed Memories */}
        <div className="card p-5 space-y-4">
          <h2 className="text-sm font-bold text-white uppercase tracking-wide border-b border-surface-border pb-2">
            Most Accessed Memories (Frequency)
          </h2>
          <div className="space-y-2">
            {(!acma.most_accessed || acma.most_accessed.length === 0) ? (
              <p className="text-xs text-gray-500">No retrieval activity yet.</p>
            ) : (
              acma.most_accessed.map((m: any, i: number) => (
                <div key={m.id} className="flex justify-between items-center bg-surface-hover p-2.5 rounded border border-surface-border text-xs">
                  <span className="font-medium text-white truncate max-w-xs">{i + 1}. {m.title}</span>
                  <span className="font-mono text-brand-400 font-bold bg-brand-950/40 px-2 py-0.5 rounded border border-brand-800/40">
                    {m.access_count} accesses
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* File Type Breakdown */}
        <div className="card p-5 space-y-4">
          <h2 className="text-sm font-bold text-white uppercase tracking-wide border-b border-surface-border pb-2">
            Document Type Breakdown
          </h2>
          <div className="space-y-3">
            {Object.entries(files.by_type || {}).map(([type, count]: [string, any]) => {
              const pct = totals.memories ? Math.round((count / totals.memories) * 100) : 0;
              return (
                <div key={type} className="space-y-1 text-xs">
                  <div className="flex justify-between text-gray-300">
                    <span className="uppercase font-semibold">{type}</span>
                    <span className="font-mono text-gray-400">{count} files ({pct}%)</span>
                  </div>
                  <div className="w-full bg-surface-hover h-2 rounded-full overflow-hidden">
                    <div className="bg-brand-500 h-full rounded-full" style={{ width: `${pct}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Coverage Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="card p-4 flex items-center justify-between border-brand-500/20">
          <div>
            <p className="text-xs text-gray-400">Embedding Vector Coverage</p>
            <p className="text-lg font-bold text-white font-mono mt-0.5">{files.embedding_coverage}</p>
          </div>
          <span className="badge badge-blue">768-dim mpnet</span>
        </div>

        <div className="card p-4 flex items-center justify-between border-purple-500/20">
          <div>
            <p className="text-xs text-gray-400">Object Detection Coverage</p>
            <p className="text-lg font-bold text-white font-mono mt-0.5">{files.object_detection_coverage}</p>
          </div>
          <span className="badge badge-purple">YOLOv8 Nano</span>
        </div>
      </div>
    </div>
  );
}
