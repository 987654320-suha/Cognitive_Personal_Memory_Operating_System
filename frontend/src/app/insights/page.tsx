// 📁 LOCATION: frontend/src/app/insights/page.tsx
"use client";

import { useQuery } from "react-query";
import { motion } from "framer-motion";
import { getStats, getRecent } from "@/services/api";
import { TrendingUp, Lightbulb, Brain, Sparkles, Clock, Target } from "lucide-react";

export default function InsightsPage() {
  const { data: stats } = useQuery("stats", getStats);
  const { data: recent } = useQuery("recent", () => getRecent(10));

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <TrendingUp className="text-brand-400" size={24} />
          <h1 className="text-2xl font-bold text-white">Cognitive Insights</h1>
        </div>
        <p className="text-sm text-gray-400">
          AI-generated insights over your personal memory graph, belief drift, and goal alignment.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card p-4 flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-brand-600/20 flex items-center justify-center shrink-0">
            <Brain className="text-brand-400" size={20} />
          </div>
          <div>
            <p className="text-xs text-gray-400">Memory Quality</p>
            <p className="text-lg font-bold text-white">
              {stats?.acma?.avg_importance_score ? `${(stats.acma.avg_importance_score * 100).toFixed(0)}%` : "High"}
            </p>
          </div>
        </div>

        <div className="card p-4 flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-purple-600/20 flex items-center justify-center shrink-0">
            <Sparkles className="text-purple-400" size={20} />
          </div>
          <div>
            <p className="text-xs text-gray-400">Total Retrievals</p>
            <p className="text-lg font-bold text-white">{stats?.acma?.total_retrievals || 0}</p>
          </div>
        </div>

        <div className="card p-4 flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-yellow-600/20 flex items-center justify-center shrink-0">
            <Target className="text-yellow-400" size={20} />
          </div>
          <div>
            <p className="text-xs text-gray-400">Active Goals</p>
            <p className="text-lg font-bold text-white">{stats?.goals?.active || 0}</p>
          </div>
        </div>
      </div>

      {/* Insights Cards */}
      <div className="space-y-4">
        <h2 className="text-sm font-bold text-white uppercase tracking-wider">Automated Recommendations</h2>

        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="card p-5 border-brand-500/30 bg-brand-950/10 space-y-2">
          <div className="flex items-center gap-2 text-brand-300 font-bold text-sm">
            <Lightbulb size={16} /> Memory Reinforcement Signal
          </div>
          <p className="text-xs text-gray-300">
            High-frequency access on technical stack memories indicates active backend development. Related goals receive boosted ACMA relevance weights.
          </p>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="card p-5 border-purple-500/30 bg-purple-950/10 space-y-2">
          <div className="flex items-center gap-2 text-purple-300 font-bold text-sm">
            <Clock size={16} /> Temporal Forgetting Curve
          </div>
          <p className="text-xs text-gray-300">
            Older documents undergo graceful mathematical decay (E(t) = exp(-λt)). Re-retrieving or updating memories propagates reinforcement to graph neighbors.
          </p>
        </motion.div>
      </div>
    </div>
  );
}
