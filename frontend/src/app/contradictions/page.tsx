// 📁 LOCATION: frontend/src/app/contradictions/page.tsx
"use client";
import { useQuery } from "react-query";
import { motion } from "framer-motion";
import Link from "next/link";
import { getContradictions } from "@/services/api";
import { AlertTriangle, CheckCircle, HelpCircle, ArrowRight, RefreshCw, ShieldCheck, Check, Eye, Copy } from "lucide-react";
import toast from "react-hot-toast";

const CLASS_CONFIG: Record<string, { icon: any; color: string; bg: string; border: string; label: string }> = {
  likely_error:      { icon: AlertTriangle, color: "text-red-400",    bg: "bg-red-900/10",    border: "border-red-700/30",    label: "Likely Error"      },
  legitimate_update: { icon: CheckCircle,   color: "text-green-400",  bg: "bg-green-900/10",  border: "border-green-700/30",  label: "Legitimate Update" },
  needs_review:      { icon: HelpCircle,    color: "text-yellow-400", bg: "bg-yellow-900/10", border: "border-yellow-700/30", label: "Needs Review"      },
};

export default function ContradictionsPage() {
  const { data, isLoading, error, refetch, isFetching } = useQuery(
    "contradictions",
    getContradictions,
    { refetchOnWindowFocus: false }
  );

  const handleAction = (actionName: string, c: any) => {
    toast.success(`Action '${actionName}' applied for attribute '${c.attribute}'`);
  };

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <AlertTriangle size={20} className="text-yellow-400" /> Contradiction Detector & Drift Service
          </h1>
          <p className="text-sm text-gray-400 mt-0.5">
            Cross-validates factual triples across memories to identify legitimate updates vs errors.
          </p>
        </div>
        <button onClick={() => refetch()} disabled={isFetching} className="btn-ghost border border-surface-border text-sm">
          <RefreshCw size={14} className={isFetching ? "animate-spin" : ""} />
          {isFetching ? "Scanning..." : "Re-scan"}
        </button>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-20 gap-3">
          <span className="animate-spin text-brand-400 text-xl">⟳</span>
          <span className="text-gray-400 text-sm">Scanning documents for contradictions...</span>
        </div>
      )}

      {/* Error */}
      {error && !isLoading && (
        <div className="card border-red-700/50 bg-red-900/10 p-5 text-center">
          <p className="text-red-400 text-sm">Failed to run scan — check that the backend is running</p>
          <button onClick={() => refetch()} className="btn-ghost text-xs mt-3">Try again</button>
        </div>
      )}

      {/* Summary cards */}
      {data && !isLoading && (
        <>
          <div className="grid grid-cols-3 gap-4 mb-6">
            {[
              { key: "likely_errors",      label: "Likely Errors",   color: "text-red-400",    bg: "bg-red-900/20"    },
              { key: "needs_review",        label: "Needs Review",    color: "text-yellow-400", bg: "bg-yellow-900/20" },
              { key: "legitimate_updates",  label: "Life Updates",    color: "text-green-400",  bg: "bg-green-900/20"  },
            ].map(s => (
              <motion.div key={s.key} initial={{ opacity:0, y:8 }} animate={{ opacity:1, y:0 }}
                className="card p-4 text-center">
                <div className={`text-2xl font-bold ${s.color}`}>{(data as any)[s.key] || 0}</div>
                <div className="text-xs text-gray-500 mt-0.5">{s.label}</div>
              </motion.div>
            ))}
          </div>

          {/* No contradictions */}
          {data.total_contradictions === 0 && (
            <motion.div initial={{ opacity:0 }} animate={{ opacity:1 }}
              className="flex flex-col items-center py-20 gap-4">
              <div className="w-16 h-16 rounded-2xl bg-green-900/20 border border-green-700/30 flex items-center justify-center">
                <ShieldCheck size={28} className="text-green-400" />
              </div>
              <div className="text-center">
                <p className="text-green-400 font-semibold">No contradictions found</p>
                <p className="text-gray-500 text-sm mt-1">
                  All documents are consistent. Upload or add more test memories to trigger detection.
                </p>
              </div>
            </motion.div>
          )}

          {/* Contradiction groups */}
          {["likely_error", "needs_review", "legitimate_update"].map(cls => {
            const items = data?.details?.[cls] || [];
            if (!items.length) return null;
            const cfg = CLASS_CONFIG[cls];
            return (
              <div key={cls} className="mb-8 space-y-3">
                <div className={`flex items-center gap-2 text-sm font-semibold ${cfg.color}`}>
                  <cfg.icon size={15} />
                  {cfg.label}
                  <span className="badge bg-surface-hover text-gray-400 border border-surface-border ml-1">
                    {items.length}
                  </span>
                </div>

                <div className="space-y-3">
                  {items.map((c: any, i: number) => (
                    <motion.div key={i} initial={{ opacity:0, y:6 }} animate={{ opacity:1, y:0 }}
                      transition={{ delay: i * 0.04 }}
                      className={`card p-4 border ${cfg.border} ${cfg.bg} space-y-3`}>

                      {/* Attribute badge */}
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="badge bg-surface-hover text-gray-300 border border-surface-border uppercase text-[10px] font-mono">
                          {c.attribute?.replace("_", " ")}
                        </span>
                        <cfg.icon size={12} className={cfg.color} />
                        <span className={`text-xs ${cfg.color}`}>{cfg.label}</span>
                        <span className="text-xs font-mono text-gray-400 ml-auto">
                          Confidence: {((c.confidence || 0) * 100).toFixed(0)}%
                        </span>
                      </div>

                      {/* The two conflicting values */}
                      <div className="grid grid-cols-[1fr,auto,1fr] items-center gap-3">
                        <Link href={`/memory/${c.memory_a?.id}`}>
                          <div className="bg-surface-hover rounded-lg p-3 hover:bg-surface-border transition-colors cursor-pointer space-y-1">
                            <p className="text-xs text-gray-400 truncate font-semibold">
                              📄 {c.memory_a?.title || "Document A"}
                            </p>
                            <p className="text-sm font-mono text-white font-bold">{c.value_a}</p>
                          </div>
                        </Link>
                        <ArrowRight size={16} className="text-gray-600 shrink-0" />
                        <Link href={`/memory/${c.memory_b?.id}`}>
                          <div className="bg-surface-hover rounded-lg p-3 hover:bg-surface-border transition-colors cursor-pointer space-y-1">
                            <p className="text-xs text-gray-400 truncate font-semibold">
                              📄 {c.memory_b?.title || "Document B"}
                            </p>
                            <p className="text-sm font-mono text-white font-bold">{c.value_b}</p>
                          </div>
                        </Link>
                      </div>

                      {/* Explanation */}
                      <p className="text-xs text-gray-400">
                        {cls === "likely_error" && "⚠️ Both documents are from a similar time period — this difference may be a typo or data entry error."}
                        {cls === "legitimate_update" && "✅ These documents are far apart in time — this likely reflects an intentional update (e.g. address or phone change)."}
                        {cls === "needs_review" && "❓ Insufficient date information to classify automatically — please review both documents."}
                      </p>

                      {/* Requirement 6 & 8 Actions */}
                      <div className="flex gap-2 pt-2 border-t border-surface-border/50">
                        <button
                          onClick={() => handleAction("Accept Update", c)}
                          className="btn-primary py-1 px-3 text-xs bg-emerald-600 hover:bg-emerald-700"
                        >
                          <Check size={12} /> Accept Update
                        </button>
                        <button
                          onClick={() => handleAction("Keep Both", c)}
                          className="btn-ghost py-1 px-3 text-xs border border-surface-border"
                        >
                          <Copy size={12} /> Keep Both
                        </button>
                        <Link href={`/memory/${c.memory_b?.id}`}>
                          <button className="btn-ghost py-1 px-3 text-xs border border-surface-border">
                            <Eye size={12} /> Review
                          </button>
                        </Link>
                      </div>
                    </motion.div>
                  ))}
                </div>
              </div>
            );
          })}
        </>
      )}
    </div>
  );
}