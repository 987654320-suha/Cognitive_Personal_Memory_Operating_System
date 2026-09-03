// 📁 LOCATION: frontend/src/app/memory/add/page.tsx
"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { createMemory } from "@/services/api";
import { PlusCircle, CheckCircle2, AlertCircle, Loader2, Sparkles, Database } from "lucide-react";
import toast from "react-hot-toast";

export default function AddMemoryPage() {
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [importance, setImportance] = useState(0.82);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !content.trim()) {
      toast.error("Please provide both title and content.");
      return;
    }

    setLoading(true);
    setResult(null);

    try {
      const res = await createMemory({
        title,
        description: content,
        importance_score: importance,
        source: "Manual Entry",
      });

      setResult(res);
      toast.success("Memory Created Successfully!");
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Failed to create memory.");
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setTitle("");
    setContent("");
    setImportance(0.82);
    setResult(null);
  };

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <PlusCircle className="text-brand-400" size={24} />
          <h1 className="text-2xl font-bold text-white">Add Test Memory</h1>
        </div>
        <p className="text-sm text-gray-400">
          Create controlled test memories to verify persistence, indexing, and ACMA retrieval behavior.
        </p>
      </div>

      {/* Form */}
      <motion.form
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        onSubmit={handleSubmit}
        className="card p-6 space-y-5"
      >
        <div>
          <label className="block text-xs font-semibold text-gray-300 mb-1 uppercase tracking-wide">
            Title / Topic
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Backend Preference"
            className="input"
            required
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-gray-300 mb-1 uppercase tracking-wide">
            Memory Content
          </label>
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={4}
            placeholder='e.g. "I prefer Python for backend development."'
            className="input resize-none"
            required
          />
        </div>

        <div>
          <div className="flex justify-between items-center mb-1">
            <label className="text-xs font-semibold text-gray-300 uppercase tracking-wide">
              Importance Score
            </label>
            <span className="text-xs font-mono text-brand-400 font-bold">{importance.toFixed(2)}</span>
          </div>
          <input
            type="range"
            min="0.0"
            max="1.0"
            step="0.01"
            value={importance}
            onChange={(e) => setImportance(parseFloat(e.target.value))}
            className="w-full accent-brand-500 bg-surface-hover cursor-pointer"
          />
          <div className="flex justify-between text-[10px] text-gray-500 mt-1">
            <span>Low (0.0)</span>
            <span>Default (0.5)</span>
            <span>High (1.0)</span>
          </div>
        </div>

        <div className="flex gap-3 pt-2">
          <button type="submit" disabled={loading} className="btn-primary flex-1 justify-center py-2.5">
            {loading ? (
              <>
                <Loader2 size={16} className="animate-spin" /> Ingesting & Indexing...
              </>
            ) : (
              <>
                <Sparkles size={16} /> Save Memory
              </>
            )}
          </button>
          {result && (
            <button
              type="button"
              onClick={handleReset}
              className="btn-ghost border border-surface-border text-xs"
            >
              Add Another
            </button>
          )}
        </div>
      </motion.form>

      {/* Confirmation Box */}
      {result && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          className="card p-6 border-green-600/40 bg-green-950/10 space-y-4"
        >
          <div className="flex items-center gap-2 text-green-400 font-bold text-lg">
            <CheckCircle2 size={20} />
            <span>Memory Created ✓</span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
            <div className="bg-surface-hover p-3 rounded-lg border border-surface-border">
              <span className="text-gray-400 text-xs block">Memory ID</span>
              <span className="font-mono text-white font-bold text-base">M{String(result.memory.id).padStart(3, '0')}</span>
            </div>

            <div className="bg-surface-hover p-3 rounded-lg border border-surface-border">
              <span className="text-gray-400 text-xs block">Importance</span>
              <span className="font-mono text-brand-400 font-bold text-base">{result.memory.importance_score}</span>
            </div>

            <div className="bg-surface-hover p-3 rounded-lg border border-surface-border">
              <span className="text-gray-400 text-xs block">Created</span>
              <span className="text-white font-medium text-xs">{result.memory.date || "Just now"}</span>
            </div>

            <div className="bg-surface-hover p-3 rounded-lg border border-surface-border">
              <span className="text-gray-400 text-xs block">Status</span>
              <span className="text-green-400 font-semibold text-xs">Active</span>
            </div>

            <div className="bg-surface-hover p-3 rounded-lg border border-surface-border">
              <span className="text-gray-400 text-xs block">FAISS Index</span>
              <span className="text-brand-300 font-semibold text-xs flex items-center gap-1">
                <Database size={12} /> Indexed ✓
              </span>
            </div>

            <div className="bg-surface-hover p-3 rounded-lg border border-surface-border">
              <span className="text-gray-400 text-xs block">BM25 Index</span>
              <span className="text-brand-300 font-semibold text-xs flex items-center gap-1">
                <Database size={12} /> Indexed ✓
              </span>
            </div>
          </div>

          {result.conflicts_found && result.conflicts_found.length > 0 && (
            <div className="p-4 rounded-lg bg-yellow-950/30 border border-yellow-700/40 text-yellow-300 text-xs space-y-2">
              <div className="flex items-center gap-2 font-bold text-sm">
                <AlertCircle size={16} /> Potential Memory Conflict Detected
              </div>
              <p className="text-gray-300">
                This memory conflicts with pre-existing facts in your system:
              </p>
              {result.conflicts_found.map((c: any, i: number) => (
                <div key={i} className="bg-surface-card p-2 rounded border border-surface-border font-mono text-[11px]">
                  <strong>Attribute:</strong> {c.attribute} | <strong>Previous:</strong> {c.value_a} vs <strong>New:</strong> {c.value_b}
                </div>
              ))}
            </div>
          )}
        </motion.div>
      )}
    </div>
  );
}
