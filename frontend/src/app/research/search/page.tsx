// 📁 LOCATION: frontend/src/app/research/search/page.tsx
"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { runExperiment, ExperimentResult } from "@/services/api";
import { FlaskConical, Search, Loader2, Info } from "lucide-react";
import toast from "react-hot-toast";

export default function ResearchSearchPage() {
  const [query, setQuery] = useState("What backend technology does CogniSphere use?");
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<ExperimentResult | null>(null);

  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    try {
      const res = await runExperiment({
        query,
        use_faiss: true,
        use_bm25: true,
        use_title: true,
        use_rrf: true,
        use_acma: true,
        top_k: 5,
      });
      setData(res);
    } catch (err: any) {
      toast.error("Failed to run pipeline search.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <FlaskConical className="text-brand-400" size={24} />
          <h1 className="text-2xl font-bold text-white">Research & Pipeline Search</h1>
        </div>
        <p className="text-sm text-gray-400">
          Inspect every layer of retrieval in real-time: FAISS Vector → BM25 Keyword → Title Boost → RRF Fusion → ACMA Re-ranking.
        </p>
      </div>

      {/* Query Bar */}
      <form onSubmit={handleSearch} className="flex gap-3">
        <div className="relative flex-1">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Type query to inspect pipeline..."
            className="input pl-10 py-3 text-sm"
          />
          <Search className="absolute left-3 top-3.5 text-gray-500" size={18} />
        </div>
        <button type="submit" disabled={loading} className="btn-primary px-6">
          {loading ? <Loader2 size={18} className="animate-spin" /> : "Run Pipeline Inspection"}
        </button>
      </form>

      {/* Results Multi-Column Layout */}
      {data && (
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
          {/* 1. FAISS Results */}
          <div className="card p-4 space-y-3 border-blue-900/40 bg-blue-950/10">
            <div className="border-b border-surface-border pb-2">
              <h3 className="font-bold text-sm text-blue-400">1. FAISS (Vector)</h3>
              <p className="text-[11px] text-gray-400">Cosine Similarity</p>
            </div>
            <div className="space-y-2">
              {data.faiss_results.length === 0 ? (
                <p className="text-xs text-gray-500">No matches</p>
              ) : (
                data.faiss_results.map((r, i) => (
                  <div key={i} className="bg-surface-card p-2.5 rounded border border-surface-border text-xs">
                    <p className="font-semibold text-white truncate">{r.title}</p>
                    <span className="text-[11px] text-blue-300 font-mono">Score: {r.score}</span>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* 2. BM25 Results */}
          <div className="card p-4 space-y-3 border-purple-900/40 bg-purple-950/10">
            <div className="border-b border-surface-border pb-2">
              <h3 className="font-bold text-sm text-purple-400">2. BM25 (Keyword)</h3>
              <p className="text-[11px] text-gray-400">Lexical Scoring</p>
            </div>
            <div className="space-y-2">
              {data.bm25_results.length === 0 ? (
                <p className="text-xs text-gray-500">No matches</p>
              ) : (
                data.bm25_results.map((r, i) => (
                  <div key={i} className="bg-surface-card p-2.5 rounded border border-surface-border text-xs">
                    <p className="font-semibold text-white truncate">{r.title}</p>
                    <span className="text-[11px] text-purple-300 font-mono">Score: {r.score}</span>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* 3. Filename/Title Match */}
          <div className="card p-4 space-y-3 border-amber-900/40 bg-amber-950/10">
            <div className="border-b border-surface-border pb-2">
              <h3 className="font-bold text-sm text-amber-400">3. Title/Filename</h3>
              <p className="text-[11px] text-gray-400">Exact String Match</p>
            </div>
            <div className="space-y-2">
              {data.title_results.length === 0 ? (
                <p className="text-xs text-gray-500">No matches</p>
              ) : (
                data.title_results.map((r, i) => (
                  <div key={i} className="bg-surface-card p-2.5 rounded border border-surface-border text-xs">
                    <p className="font-semibold text-white truncate">{r.title}</p>
                    <span className="text-[11px] text-amber-300 font-mono">Score: {r.score}</span>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* 4. RRF Merged */}
          <div className="card p-4 space-y-3 border-emerald-900/40 bg-emerald-950/10">
            <div className="border-b border-surface-border pb-2">
              <h3 className="font-bold text-sm text-emerald-400">4. RRF Merged</h3>
              <p className="text-[11px] text-gray-400">Reciprocal Rank Fusion</p>
            </div>
            <div className="space-y-2">
              {data.rrf_results.length === 0 ? (
                <p className="text-xs text-gray-500">No matches</p>
              ) : (
                data.rrf_results.map((r, i) => (
                  <div key={i} className="bg-surface-card p-2.5 rounded border border-surface-border text-xs">
                    <p className="font-semibold text-white truncate">{i + 1}. {r.title}</p>
                    <span className="text-[11px] text-emerald-300 font-mono">RRF: {r.rrf_score}</span>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* 5. ACMA Final Re-ranking */}
          <div className="card p-4 space-y-3 border-brand-900/40 bg-brand-950/20">
            <div className="border-b border-surface-border pb-2">
              <h3 className="font-bold text-sm text-brand-300">5. ACMA Final</h3>
              <p className="text-[11px] text-gray-400">6-Factor Activation</p>
            </div>
            <div className="space-y-2">
              {data.acma_results.length === 0 ? (
                <p className="text-xs text-gray-500">No matches</p>
              ) : (
                data.acma_results.map((r, i) => (
                  <div key={i} className="bg-surface-card p-2.5 rounded border border-brand-500/30 text-xs space-y-1">
                    <div className="flex justify-between items-center">
                      <p className="font-bold text-white truncate">{i + 1}. {r.title}</p>
                      <span className="text-xs font-mono font-bold text-brand-400">
                        {r.activation_score}
                      </span>
                    </div>
                    {r.components && (
                      <div className="text-[10px] text-gray-400 grid grid-cols-2 gap-x-2 font-mono">
                        <span>Sem: {r.components.semantic}</span>
                        <span>Goal: {r.components.goal}</span>
                        <span>Imp: {r.components.importance}</span>
                        <span>Temp: {r.components.temporal}</span>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
