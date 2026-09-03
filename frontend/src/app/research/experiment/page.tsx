"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { runExperiment, ExperimentResult } from "@/services/api";
import {
  Sliders,
  Play,
  Loader2,
  Award,
} from "lucide-react";
import toast from "react-hot-toast";

export default function ExperimentPage() {
  const [query, setQuery] = useState(
    "What programming language do I prefer for backend development?"
  );

  const [useFaiss, setUseFaiss] = useState(true);
  const [useBm25, setUseBm25] = useState(true);
  const [useTitle, setUseTitle] = useState(true);
  const [useRrf, setUseRrf] = useState(true);
  const [useAcma, setUseAcma] = useState(true);

  // ACMA factors
  const [acmaGoal, setAcmaGoal] = useState(true);
  const [acmaRelationship, setAcmaRelationship] = useState(true);
  const [acmaImportance, setAcmaImportance] = useState(true);
  const [acmaTemporal, setAcmaTemporal] = useState(true);
  const [acmaAccess, setAcmaAccess] = useState(true);
  const [acmaTitleBoost, setAcmaTitleBoost] = useState(true);

  const [topK, setTopK] = useState(5);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ExperimentResult | null>(null);

  // ------------------------------------------------------------
  // RUN EXPERIMENT
  // ------------------------------------------------------------

  const handleRunExperiment = async () => {
    if (!query.trim()) {
      toast.error("Please enter a test query.");
      return;
    }

    setLoading(true);

    try {
      const res = await runExperiment({
        query,
        use_faiss: useFaiss,
        use_bm25: useBm25,
        use_title: useTitle,
        use_rrf: useRrf,
        use_acma: useAcma,
        acma_goal: acmaGoal,
        acma_relationship: acmaRelationship,
        acma_importance: acmaImportance,
        acma_temporal: acmaTemporal,
        acma_access: acmaAccess,
        acma_title_boost: acmaTitleBoost,
        top_k: topK,
      });

      console.log("[Experiment] Backend response:", res);

      setResult(res);

      toast.success("Experiment Executed Successfully!");
    } catch (err: any) {
      console.error("[Experiment] Error:", err);

      toast.error(
        err?.response?.data?.detail ||
          "Failed to execute experiment."
      );
    } finally {
      setLoading(false);
    }
  };

  // ------------------------------------------------------------
  // PRESET BUTTON
  // ------------------------------------------------------------

  const PresetButton = ({
    title,
    desc,
    config,
  }: {
    title: string;
    desc: string;
    config: any;
  }) => (
    <button
      type="button"
      onClick={() => {
        setUseFaiss(config.faiss ?? true);
        setUseBm25(config.bm25 ?? true);
        setUseTitle(config.title ?? true);
        setUseRrf(config.rrf ?? true);
        setUseAcma(config.acma ?? true);

        setAcmaGoal(config.goal ?? true);
        setAcmaRelationship(config.rel ?? true);
        setAcmaImportance(config.imp ?? true);
        setAcmaTemporal(config.temp ?? true);
        setAcmaAccess(config.acc ?? true);
        setAcmaTitleBoost(config.boost ?? true);

        // Clear previous result when changing experiment
        setResult(null);
      }}
      className="card p-3 text-left hover:border-brand-500/50 transition-all cursor-pointer"
    >
      <p className="font-semibold text-white text-xs">
        {title}
      </p>

      <p className="text-[11px] text-gray-400 mt-0.5">
        {desc}
      </p>
    </button>
  );

  // ------------------------------------------------------------
  // NORMALIZE RESULTS
  //
  // Backend can return:
  //
  // Experiment A -> faiss_results
  // Experiment B -> rrf_results
  // Experiment C -> acma_results
  // Experiment F -> acma_results
  //
  // Therefore NEVER render only acma_results.
  // ------------------------------------------------------------

  const getDisplayResults = () => {
    if (!result) return [];

    const data: any = result as any;

    if (
      Array.isArray(data.acma_results) &&
      data.acma_results.length > 0
    ) {
      return data.acma_results;
    }

    if (
      Array.isArray(data.rrf_results) &&
      data.rrf_results.length > 0
    ) {
      return data.rrf_results;
    }

    if (
      Array.isArray(data.faiss_results) &&
      data.faiss_results.length > 0
    ) {
      return data.faiss_results;
    }

    if (
      Array.isArray(data.bm25_results) &&
      data.bm25_results.length > 0
    ) {
      return data.bm25_results;
    }

    if (
      Array.isArray(data.title_results) &&
      data.title_results.length > 0
    ) {
      return data.title_results;
    }

    return [];
  };

  const displayResults = getDisplayResults();

  // ------------------------------------------------------------
  // DETERMINE RESULT SOURCE
  // ------------------------------------------------------------

  const getResultSource = () => {
    if (!result) return "";

    const data: any = result as any;

    if (
      Array.isArray(data.acma_results) &&
      data.acma_results.length > 0
    ) {
      return "ACMA Final";
    }

    if (
      Array.isArray(data.rrf_results) &&
      data.rrf_results.length > 0
    ) {
      return "RRF Merged";
    }

    if (
      Array.isArray(data.faiss_results) &&
      data.faiss_results.length > 0
    ) {
      return "FAISS Vector";
    }

    if (
      Array.isArray(data.bm25_results) &&
      data.bm25_results.length > 0
    ) {
      return "BM25 Keyword";
    }

    if (
      Array.isArray(data.title_results) &&
      data.title_results.length > 0
    ) {
      return "Title/Filename";
    }

    return "No Results";
  };

  const resultSource = getResultSource();

  // ------------------------------------------------------------
  // SCORE
  // ------------------------------------------------------------

  const getScore = (memory: any) => {
    if (memory.activation_score !== undefined) {
      return Number(memory.activation_score);
    }

    if (memory.rrf_score !== undefined) {
      return Number(memory.rrf_score);
    }

    if (memory.score !== undefined) {
      return Number(memory.score);
    }

    if (memory.normalized !== undefined) {
      return Number(memory.normalized);
    }

    return 0;
  };

  // ------------------------------------------------------------
  // BREAKDOWN
  // ------------------------------------------------------------

  const getBreakdown = (memory: any) => {
    if (memory.components) {
      return [
        memory.components.semantic ?? 0,
        memory.components.goal ?? 0,
        memory.components.relationship ?? 0,
        memory.components.importance ?? 0,
        memory.components.temporal ?? 0,
        memory.components.access ?? 0,
      ];
    }

    return null;
  };

  // ------------------------------------------------------------
  // PAGE
  // ------------------------------------------------------------

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">

      {/* --------------------------------------------------------
          HEADER
      --------------------------------------------------------- */}

      <div>
        <div className="flex items-center gap-2 mb-1">
          <Sliders
            className="text-brand-400"
            size={24}
          />

          <h1 className="text-2xl font-bold text-white">
            Experiment Configuration (Ablation Study)
          </h1>
        </div>

        <p className="text-sm text-gray-400">
          Toggle individual algorithm modules to conduct
          controlled ablation experiments (Figure 9 & Table 1
          for paper).
        </p>
      </div>

      {/* --------------------------------------------------------
          PRESETS
      --------------------------------------------------------- */}

      <div>
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">
          Ablation Presets
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-3">

          <PresetButton
            title="Experiment A: FAISS Only"
            desc="Vector search only (semantic baseline)"
            config={{
              faiss: true,
              bm25: false,
              title: false,
              rrf: false,
              acma: false,
            }}
          />

          <PresetButton
            title="Experiment B: Hybrid RRF"
            desc="FAISS + BM25 + Title without ACMA"
            config={{
              faiss: true,
              bm25: true,
              title: true,
              rrf: true,
              acma: false,
            }}
          />

          <PresetButton
            title="Experiment C: Hybrid + Goal"
            desc="RRF + Goal relevance only"
            config={{
              faiss: true,
              bm25: true,
              title: true,
              rrf: true,
              acma: true,
              goal: true,
              rel: false,
              imp: false,
              temp: false,
              acc: false,
              boost: false,
            }}
          />

          <PresetButton
            title="Experiment F: Full ACMA Engine"
            desc="All retrieval channels + 6-factor ACMA"
            config={{
              faiss: true,
              bm25: true,
              title: true,
              rrf: true,
              acma: true,
              goal: true,
              rel: true,
              imp: true,
              temp: true,
              acc: true,
              boost: true,
            }}
          />

        </div>
      </div>

      {/* --------------------------------------------------------
          CONFIGURATION
      --------------------------------------------------------- */}

      <div className="card p-6 space-y-6">

        <h2 className="text-base font-bold text-white border-b border-surface-border pb-3">
          EXPERIMENT CONFIGURATION
        </h2>

        {/* Query */}

        <div>
          <label className="block text-xs font-semibold text-gray-300 mb-1 uppercase tracking-wide">
            Test Query
          </label>

          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="input text-sm"
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">

          {/* --------------------------------------------------
              RETRIEVAL CHANNELS
          --------------------------------------------------- */}

          <div className="space-y-3">

            <h3 className="text-xs font-bold text-brand-400 uppercase tracking-wide">
              1. Retrieval Channels
            </h3>

            <div className="space-y-2">

              <label className="flex items-center gap-2 text-sm text-gray-200 cursor-pointer">
                <input
                  type="checkbox"
                  checked={useFaiss}
                  onChange={(e) =>
                    setUseFaiss(e.target.checked)
                  }
                  className="accent-brand-500 rounded"
                />

                <span>FAISS (Vector Search)</span>
              </label>

              <label className="flex items-center gap-2 text-sm text-gray-200 cursor-pointer">
                <input
                  type="checkbox"
                  checked={useBm25}
                  onChange={(e) =>
                    setUseBm25(e.target.checked)
                  }
                  className="accent-brand-500 rounded"
                />

                <span>BM25 (Keyword Search)</span>
              </label>

              <label className="flex items-center gap-2 text-sm text-gray-200 cursor-pointer">
                <input
                  type="checkbox"
                  checked={useTitle}
                  onChange={(e) =>
                    setUseTitle(e.target.checked)
                  }
                  className="accent-brand-500 rounded"
                />

                <span>Filename / Title Match</span>
              </label>

            </div>
          </div>

          {/* --------------------------------------------------
              RRF
          --------------------------------------------------- */}

          <div className="space-y-3">

            <h3 className="text-xs font-bold text-purple-400 uppercase tracking-wide">
              2. Fusion Layer
            </h3>

            <label className="flex items-center gap-2 text-sm text-gray-200 cursor-pointer">

              <input
                type="checkbox"
                checked={useRrf}
                onChange={(e) =>
                  setUseRrf(e.target.checked)
                }
                className="accent-brand-500 rounded"
              />

              <span>
                Reciprocal Rank Fusion (RRF)
              </span>

            </label>

          </div>

          {/* --------------------------------------------------
              ACMA
          --------------------------------------------------- */}

          <div className="space-y-3">

            <div className="flex items-center justify-between">

              <h3 className="text-xs font-bold text-amber-400 uppercase tracking-wide">
                3. ACMA Factors
              </h3>

              <label className="flex items-center gap-1 text-xs text-brand-300 cursor-pointer">

                <input
                  type="checkbox"
                  checked={useAcma}
                  onChange={(e) =>
                    setUseAcma(e.target.checked)
                  }
                  className="accent-brand-500"
                />

                <span>Enable ACMA</span>

              </label>

            </div>

            <div
              className={`space-y-2 ${
                !useAcma
                  ? "opacity-40 pointer-events-none"
                  : ""
              }`}
            >

              <label className="flex items-center gap-2 text-xs text-gray-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={acmaGoal}
                  onChange={(e) =>
                    setAcmaGoal(e.target.checked)
                  }
                  className="accent-brand-500"
                />

                <span>Goal Relevance (0.15)</span>
              </label>

              <label className="flex items-center gap-2 text-xs text-gray-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={acmaRelationship}
                  onChange={(e) =>
                    setAcmaRelationship(e.target.checked)
                  }
                  className="accent-brand-500"
                />

                <span>Relationship Strength (0.10)</span>
              </label>

              <label className="flex items-center gap-2 text-xs text-gray-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={acmaImportance}
                  onChange={(e) =>
                    setAcmaImportance(e.target.checked)
                  }
                  className="accent-brand-500"
                />

                <span>Importance Score (0.05)</span>
              </label>

              <label className="flex items-center gap-2 text-xs text-gray-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={acmaTemporal}
                  onChange={(e) =>
                    setAcmaTemporal(e.target.checked)
                  }
                  className="accent-brand-500"
                />

                <span>Temporal Decay (0.10)</span>
              </label>

              <label className="flex items-center gap-2 text-xs text-gray-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={acmaAccess}
                  onChange={(e) =>
                    setAcmaAccess(e.target.checked)
                  }
                  className="accent-brand-500"
                />

                <span>Access Frequency (0.05)</span>
              </label>

              <label className="flex items-center gap-2 text-xs text-gray-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={acmaTitleBoost}
                  onChange={(e) =>
                    setAcmaTitleBoost(e.target.checked)
                  }
                  className="accent-brand-500"
                />

                <span>Title Boost (+0.30)</span>
              </label>

            </div>
          </div>
        </div>

        {/* ------------------------------------------------------
            CONTROLS
        ------------------------------------------------------- */}

        <div className="flex items-center justify-between pt-4 border-t border-surface-border">

          <div className="flex items-center gap-3 text-xs text-gray-300">

            <span>Top-K:</span>

            <input
              type="number"
              min={1}
              max={20}
              value={topK}
              onChange={(e) =>
                setTopK(parseInt(e.target.value) || 5)
              }
              className="bg-surface-hover border border-surface-border rounded px-2 py-1 w-16 text-center font-mono"
            />

          </div>

          <button
            onClick={handleRunExperiment}
            disabled={loading}
            className="btn-primary px-6 flex items-center gap-2"
          >

            {loading ? (
              <Loader2
                size={16}
                className="animate-spin"
              />
            ) : (
              <Play size={16} />
            )}

            {loading
              ? "Running Experiment..."
              : "Run Experiment"}

          </button>

        </div>
      </div>

      {/* ========================================================
          RESULTS
      ========================================================= */}

      {result && (
        <motion.div
          initial={{
            opacity: 0,
            y: 16,
          }}
          animate={{
            opacity: 1,
            y: 0,
          }}
          className="card p-6 space-y-4"
        >

          {/* Header */}

          <div className="flex items-center justify-between">

            <h2 className="text-base font-bold text-white flex items-center gap-2">

              <Award
                className="text-yellow-400"
                size={20}
              />

              Experiment Results & Retrieved Memories

            </h2>

            <span className="text-xs px-3 py-1 rounded-full bg-brand-500/10 border border-brand-500/30 text-brand-300">
              {resultSource}
            </span>

          </div>

          {/* Result count */}

          <div className="text-xs text-gray-400">
            Query:{" "}
            <span className="text-gray-200">
              {query}
            </span>

            <span className="mx-2">•</span>

            Retrieved:{" "}
            <span className="text-emerald-400 font-semibold">
              {displayResults.length}
            </span>

            <span className="mx-2">•</span>

            Top-K:{" "}
            <span className="text-gray-200">
              {topK}
            </span>
          </div>

          {/* ----------------------------------------------------
              EMPTY STATE
          ----------------------------------------------------- */}

          {displayResults.length === 0 ? (

            <div className="border border-surface-border rounded-lg p-8 text-center">

              <p className="text-gray-300 font-semibold">
                No results returned
              </p>

              <p className="text-xs text-gray-500 mt-2">
                The backend completed the experiment but did
                not return any retrieval results for the selected
                configuration.
              </p>

            </div>

          ) : (

            <div className="overflow-x-auto">

              <table className="w-full text-left text-xs border-collapse">

                <thead>

                  <tr className="border-b border-surface-border text-gray-400 uppercase text-[10px]">

                    <th className="py-2.5 px-3">
                      Rank
                    </th>

                    <th className="py-2.5 px-3">
                      Memory Title
                    </th>

                    <th className="py-2.5 px-3">
                      Description
                    </th>

                    <th className="py-2.5 px-3 font-mono">
                      Score
                    </th>

                    <th className="py-2.5 px-3 font-mono">
                      Breakdown (S/G/R/I/T/A)
                    </th>

                  </tr>

                </thead>

                <tbody className="divide-y divide-surface-border">

                  {displayResults.map(
                    (memory: any, i: number) => {

                      const score =
                        getScore(memory);

                      const breakdown =
                        getBreakdown(memory);

                      return (
                        <tr
                          key={
                            memory.id ??
                            `${memory.title}-${i}`
                          }
                          className="hover:bg-surface-hover/50"
                        >

                          {/* Rank */}

                          <td className="py-3 px-3 font-mono font-bold text-brand-400">
                            #{i + 1}
                          </td>

                          {/* Title */}

                          <td className="py-3 px-3 font-semibold text-white">
                            {memory.title ||
                              "Untitled Memory"}
                          </td>

                          {/* Description */}

                          <td className="py-3 px-3 text-gray-300 max-w-xs">
                            <div className="truncate">
                              {memory.description ||
                                "—"}
                            </div>
                          </td>

                          {/* Score */}

                          <td className="py-3 px-3 font-mono font-bold text-emerald-400 text-sm">

                            {Number.isFinite(score)
                              ? score.toFixed(4)
                              : "0.0000"}

                          </td>

                          {/* Breakdown */}

                          <td className="py-3 px-3 font-mono text-[11px] text-gray-400">

                            {breakdown ? (

                              <span>
                                {breakdown
                                  .map(
                                    (value: any) =>
                                      Number(
                                        value || 0
                                      ).toFixed(4)
                                  )
                                  .join(" / ")}
                              </span>

                            ) : memory.rrf_score !==
                              undefined ? (

                              <span className="text-emerald-400">
                                RRF:{" "}
                                {Number(
                                  memory.rrf_score
                                ).toFixed(6)}
                              </span>

                            ) : memory.score !==
                              undefined ? (

                              <span className="text-blue-400">
                                Score:{" "}
                                {Number(
                                  memory.score
                                ).toFixed(4)}
                              </span>

                            ) : (

                              <span>N/A</span>

                            )}

                          </td>

                        </tr>
                      );
                    }
                  )}

                </tbody>

              </table>

            </div>
          )}

          {/* ----------------------------------------------------
              DEBUG / PIPELINE SUMMARY
          ----------------------------------------------------- */}

          <div className="grid grid-cols-2 md:grid-cols-5 gap-2 pt-3 border-t border-surface-border">

            <div className="text-center p-2 rounded bg-surface-hover">
              <div className="text-[10px] text-gray-500 uppercase">
                FAISS
              </div>
              <div className="text-xs text-gray-200 font-semibold">
                {useFaiss ? "ON" : "OFF"}
              </div>
            </div>

            <div className="text-center p-2 rounded bg-surface-hover">
              <div className="text-[10px] text-gray-500 uppercase">
                BM25
              </div>
              <div className="text-xs text-gray-200 font-semibold">
                {useBm25 ? "ON" : "OFF"}
              </div>
            </div>

            <div className="text-center p-2 rounded bg-surface-hover">
              <div className="text-[10px] text-gray-500 uppercase">
                Title
              </div>
              <div className="text-xs text-gray-200 font-semibold">
                {useTitle ? "ON" : "OFF"}
              </div>
            </div>

            <div className="text-center p-2 rounded bg-surface-hover">
              <div className="text-[10px] text-gray-500 uppercase">
                RRF
              </div>
              <div className="text-xs text-gray-200 font-semibold">
                {useRrf ? "ON" : "OFF"}
              </div>
            </div>

            <div className="text-center p-2 rounded bg-surface-hover">
              <div className="text-[10px] text-gray-500 uppercase">
                ACMA
              </div>
              <div className="text-xs text-gray-200 font-semibold">
                {useAcma ? "ON" : "OFF"}
              </div>
            </div>

          </div>

        </motion.div>
      )}

    </div>
  );
}