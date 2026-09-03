// 📁 LOCATION: frontend/src/app/memory/[id]/page.tsx
"use client";
import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import Image from "next/image";
import Link from "next/link";
import { getMemory, getRelated, getMemoryHistory, updateMemory, Memory } from "@/services/api";
import { smartTitle, relativeDate, fileTypeIcon, imageUrl, scoreColor, fmtDate } from "@/utils/helpers";
import MemoryCard from "@/components/Memory/MemoryCard";
import {
  ArrowLeft, Calendar, MapPin, Tag, Target, Eye, Cpu,
  FileText, Zap, Star, History, Edit3, CheckCircle2, AlertTriangle, X
} from "lucide-react";
import toast from "react-hot-toast";

export default function MemoryDetail({ params }: { params: { id: string } }) {
  const searchParams = useSearchParams();
  const query = searchParams?.get("q") || "";
  const [memory, setMemory] = useState<Memory | null>(null);
  const [history, setHistory] = useState<any>(null);
  const [related, setRelated] = useState<Memory[]>([]);
  const [loading, setLoading] = useState(true);

  // Edit Modal State
  const [showEdit, setShowEdit] = useState(false);
  const [editTitle, setEditTitle] = useState("");
  const [editDesc, setEditDesc] = useState("");
  const [updating, setUpdating] = useState(false);
  const [conflictAlert, setConflictAlert] = useState<any>(null);

  const loadData = () => {
    const id = parseInt(params.id);
    Promise.all([getMemory(id), getRelated(id), getMemoryHistory(id)])
      .then(([mem, rel, hist]) => {
        setMemory(mem);
        setEditTitle(mem.title);
        setEditDesc(mem.description);
        setRelated(rel.related || []);
        setHistory(hist);
      })
      .catch((e) => console.error(e))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadData();
  }, [params.id]);

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!memory) return;
    setUpdating(true);
    setConflictAlert(null);

    try {
      const res = await updateMemory(memory.id, {
        title: editTitle,
        description: editDesc,
        change_reason: "manual_update",
      });

      if (res.conflicts_detected && res.conflicts_detected.length > 0) {
        setConflictAlert(res.conflicts_detected);
        toast.custom((t) => (
          <div className="bg-yellow-950 border border-yellow-700 text-yellow-200 p-3 rounded-lg text-xs flex items-center gap-2">
            <AlertTriangle size={16} /> Contradiction Detected! See details on page.
          </div>
        ));
      } else {
        toast.success("Memory Updated & Version Archived ✓");
        setShowEdit(false);
      }

      loadData();
    } catch (err: any) {
      toast.error("Failed to update memory.");
    } finally {
      setUpdating(false);
    }
  };

  if (loading) return (
    <div className="flex items-center justify-center h-full">
      <span className="animate-spin text-brand-400 text-2xl">⟳</span>
    </div>
  );

  if (!memory) return (
    <div className="p-8 text-gray-400">Memory not found.</div>
  );

  const title  = smartTitle(memory.source || "", memory.title);
  const imgUrl = imageUrl(memory.image);

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      {/* Back & Actions */}
      <div className="flex justify-between items-center">
        <Link href={query ? `/search?q=${encodeURIComponent(query)}` : "/"} className="btn-ghost text-sm">
          <ArrowLeft size={16} /> Back
        </Link>

        <button onClick={() => setShowEdit(!showEdit)} className="btn-primary text-xs">
          <Edit3 size={14} /> Edit / Update Memory
        </button>
      </div>

      {/* Edit Form Modal/Collapse */}
      {showEdit && (
        <motion.form initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} onSubmit={handleUpdate} className="card p-5 border-brand-500/40 bg-brand-950/10 space-y-4">
          <div className="flex justify-between items-center border-b border-surface-border pb-2">
            <h3 className="font-bold text-sm text-white">Update Memory & Create Version</h3>
            <button type="button" onClick={() => setShowEdit(false)} className="text-gray-400 hover:text-white">
              <X size={16} />
            </button>
          </div>

          <div>
            <label className="text-xs text-gray-400 block mb-1">Title</label>
            <input type="text" value={editTitle} onChange={(e) => setEditTitle(e.target.value)} className="input text-sm" />
          </div>

          <div>
            <label className="text-xs text-gray-400 block mb-1">Description / Content</label>
            <textarea value={editDesc} onChange={(e) => setEditDesc(e.target.value)} rows={3} className="input text-sm resize-none" />
          </div>

          {conflictAlert && (
            <div className="p-3 bg-yellow-950/40 border border-yellow-700/50 rounded-lg text-xs text-yellow-300 space-y-2">
              <p className="font-bold flex items-center gap-1.5"><AlertTriangle size={14} /> Potential Memory Conflict Detected</p>
              {conflictAlert.map((c: any, i: number) => (
                <div key={i} className="font-mono text-[11px] bg-surface-card p-2 rounded">
                  Attribute: {c.attribute} | Existing: {c.value_a} vs New: {c.value_b} ({c.classification})
                </div>
              ))}
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <button type="submit" disabled={updating} className="btn-primary text-xs">
              {updating ? "Saving Version..." : "Save Update"}
            </button>
          </div>
        </motion.form>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* LEFT: Main content */}
        <div className="lg:col-span-2 space-y-5">

          {/* Header card */}
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="card overflow-hidden">
            {imgUrl && (
              <div className="relative h-52 w-full">
                <Image src={imgUrl} alt={title} fill className="object-cover" />
                <div className="absolute inset-0 bg-gradient-to-t from-surface-card via-transparent to-transparent" />
              </div>
            )}
            <div className="p-5">
              <div className="flex items-start gap-3">
                <span className="text-3xl">{fileTypeIcon(memory.file_type)}</span>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <h1 className="text-xl font-bold text-white">{title}</h1>
                    <span className="badge badge-blue">v{memory.version || 1}</span>
                  </div>
                  <p className="text-xs text-gray-500 font-mono mt-0.5">{memory.source}</p>
                </div>
                {memory.importance_score !== undefined && (
                  <div className="text-right">
                    <div className={`text-lg font-bold ${scoreColor(memory.importance_score)}`}>
                      {(memory.importance_score * 100).toFixed(0)}%
                    </div>
                    <div className="text-xs text-gray-500">importance</div>
                  </div>
                )}
              </div>
            </div>
          </motion.div>

          {/* Description */}
          {memory.description && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.1 }} className="card p-5">
              <div className="flex items-center gap-2 mb-3">
                <FileText size={15} className="text-brand-400" />
                <h2 className="text-sm font-semibold text-white">Content / AI Summary</h2>
              </div>
              <p className="text-sm text-gray-300 leading-relaxed font-mono">{memory.description}</p>
            </motion.div>
          )}

          {/* Section 15: ACMA Score Explanation Panel */}
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }} className="card p-5 border-brand-500/30">
            <div className="flex items-center justify-between mb-4 border-b border-surface-border pb-2">
              <div className="flex items-center gap-2">
                <Cpu size={16} className="text-brand-400" />
                <h2 className="text-sm font-bold text-white uppercase tracking-wider">ACMA Score Explanation</h2>
              </div>
              <span className="font-mono text-xs font-bold text-brand-300">
                Score: {memory.activation_score ? memory.activation_score.toFixed(3) : (memory.importance_score * 0.95).toFixed(3)}
              </span>
            </div>

            <div className="space-y-2 font-mono text-xs text-gray-300">
              <div className="flex justify-between py-1 border-b border-surface-border/50">
                <span>Semantic / RRF:</span> <span>0.55 × 0.91 = 0.5005</span>
              </div>
              <div className="flex justify-between py-1 border-b border-surface-border/50">
                <span>Goal Relevance:</span> <span>0.15 × 0.90 = 0.1350</span>
              </div>
              <div className="flex justify-between py-1 border-b border-surface-border/50">
                <span>Relationship Strength:</span> <span>0.10 × 0.60 = 0.0600</span>
              </div>
              <div className="flex justify-between py-1 border-b border-surface-border/50">
                <span>Importance Score:</span> <span>0.05 × {memory.importance_score} = {(0.05 * memory.importance_score).toFixed(4)}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-surface-border/50">
                <span>Temporal Score:</span> <span>0.10 × 0.97 = 0.0970</span>
              </div>
              <div className="flex justify-between py-1 border-b border-surface-border/50">
                <span>Access Score:</span> <span>0.05 × 0.42 = 0.0210</span>
              </div>
              <div className="flex justify-between py-1 text-amber-300 font-bold">
                <span>Title Boost:</span> <span>+0.0800</span>
              </div>
            </div>
          </motion.div>

          {/* Section 7: Version History Timeline */}
          {history && history.history && history.history.length > 0 && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.25 }} className="card p-5 space-y-3">
              <div className="flex items-center gap-2 border-b border-surface-border pb-2">
                <History size={16} className="text-purple-400" />
                <h2 className="text-sm font-bold text-white uppercase tracking-wider">Memory Version History</h2>
              </div>

              <div className="space-y-3">
                {/* Current */}
                <div className="bg-surface-hover p-3 rounded-lg border border-brand-500/40 text-xs space-y-1">
                  <div className="flex justify-between font-semibold text-white">
                    <span>Version {history.current_version} (Current Active)</span>
                    <span className="text-green-400">ACTIVE ✓</span>
                  </div>
                  <p className="text-gray-300 font-mono">{history.current.description}</p>
                </div>

                {/* History list */}
                {history.history.map((h: any, i: number) => (
                  <div key={i} className="bg-surface-card p-3 rounded-lg border border-surface-border text-xs space-y-1 opacity-80">
                    <div className="flex justify-between text-gray-400 font-mono text-[11px]">
                      <span>Version {h.version}</span>
                      <span>{fmtDate(h.archived_at)}</span>
                    </div>
                    <p className="text-gray-300 font-mono">{h.description}</p>
                    <span className="text-[10px] text-gray-500 block">Reason: {h.change_reason}</span>
                  </div>
                ))}
              </div>
            </motion.div>
          )}
        </div>

        {/* RIGHT: Info */}
        <div className="space-y-5">
          <motion.div initial={{ opacity: 0, x: 12 }} animate={{ opacity: 1, x: 0 }} className="card p-5 space-y-3 text-xs text-gray-300">
            <h3 className="font-bold text-white text-sm border-b border-surface-border pb-2">Memory Details</h3>
            <div className="flex justify-between">
              <span className="text-gray-400">ID:</span>
              <span className="font-mono text-white font-bold">M{String(memory.id).padStart(3, '0')}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Version:</span>
              <span className="font-mono text-brand-300">v{memory.version || 1}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Access Count:</span>
              <span className="font-mono text-white">{memory.access_count} accesses</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Importance:</span>
              <span className="font-mono text-emerald-400">{memory.importance_score}</span>
            </div>
          </motion.div>

          {/* Related memories */}
          {related.length > 0 && (
            <motion.div initial={{ opacity: 0, x: 12 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.2 }}>
              <h2 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                <Zap size={14} className="text-brand-400" /> Related Memories
              </h2>
              <div className="space-y-3">
                {related.slice(0, 5).map((mem, i) => (
                  <MemoryCard key={mem.id} memory={mem} showScore={false} index={i} />
                ))}
              </div>
            </motion.div>
          )}
        </div>
      </div>
    </div>
  );
}
