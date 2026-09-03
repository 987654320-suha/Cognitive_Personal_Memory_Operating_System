// 📁 LOCATION: frontend/src/app/goals/page.tsx
"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "react-query";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import { getGoals, getTrajectories, createGoal } from "@/services/api";
import { fmtDate, scoreColor } from "@/utils/helpers";
import { Target, Plus, TrendingUp, Calendar, Clock, Loader2, ChevronRight, CheckCircle, AlertCircle } from "lucide-react";
import toast from "react-hot-toast";

const STATUS_COLORS: Record<string, string> = {
  active:    "badge-green",
  completed: "badge-blue",
  paused:    "badge-yellow",
};

export default function GoalsPage() {
  const qc = useQueryClient();
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [showForm, setShowForm] = useState(false);

  const { data: goals, isLoading: goalsLoading } = useQuery("goals", getGoals);
  const { data: trajectories } = useQuery("trajectories", getTrajectories);

  const addGoal = useMutation(
    () => createGoal(newName.trim(), newDesc.trim()),
    {
      onSuccess: () => {
        qc.invalidateQueries("goals");
        qc.invalidateQueries("trajectories");
        setNewName(""); setNewDesc(""); setShowForm(false);
        toast.success("Goal created!");
      },
      onError: (e: any) => {
        toast.error(e?.response?.data?.detail || "Failed to create goal");
      },
    }
  );

  // Build trajectory lookup: goal_name → trajectory
  const trajMap: Record<string, any> = {};
  (trajectories?.trajectories || []).forEach((t: any) => { trajMap[t.goal_name] = t; });

  return (
    <div className="p-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Target size={20} className="text-yellow-400" /> Goals
          </h1>
          <p className="text-sm text-gray-400 mt-0.5">
            Track life goals and see AI-predicted progress timelines
          </p>
        </div>
        <button onClick={() => setShowForm(s => !s)} className="btn-primary">
          <Plus size={16} /> New Goal
        </button>
      </div>

      {/* Create form */}
      <AnimatePresence>
        {showForm && (
          <motion.div initial={{ opacity:0, height:0 }} animate={{ opacity:1, height:"auto" }}
            exit={{ opacity:0, height:0 }} className="overflow-hidden mb-5">
            <div className="card p-5">
              <h2 className="text-sm font-semibold text-white mb-4">Create New Goal</h2>
              <div className="space-y-3">
                <input
                  className="input"
                  placeholder="Goal name (e.g. Germany Masters, Career 2025)"
                  value={newName}
                  onChange={e => setNewName(e.target.value)}
                  onKeyDown={e => e.key === "Enter" && newName.trim() && addGoal.mutate()}
                />
                <textarea
                  className="input resize-none h-20"
                  placeholder="Description — what does completing this goal mean? (optional)"
                  value={newDesc}
                  onChange={e => setNewDesc(e.target.value)}
                />
                <div className="flex gap-2">
                  <button
                    onClick={() => addGoal.mutate()}
                    disabled={!newName.trim() || addGoal.isLoading}
                    className="btn-primary"
                  >
                    {addGoal.isLoading && <Loader2 size={14} className="animate-spin" />}
                    Create Goal
                  </button>
                  <button onClick={() => setShowForm(false)} className="btn-ghost">Cancel</button>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Loading */}
      {goalsLoading && (
        <div className="flex justify-center py-16">
          <Loader2 size={24} className="animate-spin text-brand-400" />
        </div>
      )}

      {/* Goals list */}
      <div className="space-y-4">
        {(goals || []).map((goal: any, i: number) => {
          const traj = trajMap[goal.name];
          const acquired = traj?.sequence?.filter((s: any) => s.acquired).length || 0;
          const total    = traj?.sequence?.length || 0;
          const pct      = total > 0 ? Math.round((acquired / total) * 100) : 0;

          return (
            <motion.div key={goal.id} initial={{ opacity:0, y:10 }} animate={{ opacity:1, y:0 }}
              transition={{ delay: i * 0.06 }}>
              <Link href={`/goals/${goal.id}`}>
                <div className="card p-5 hover:border-brand-600/40 hover:bg-surface-hover transition-all cursor-pointer group">

                  {/* Goal header */}
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-3 flex-1 min-w-0">
                      <div className="w-9 h-9 rounded-xl bg-yellow-500/10 border border-yellow-500/30 flex items-center justify-center shrink-0 mt-0.5">
                        <Target size={16} className="text-yellow-400" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap mb-0.5">
                          <h3 className="font-semibold text-white group-hover:text-brand-300 transition-colors">
                            {goal.name}
                          </h3>
                          <span className={`badge ${STATUS_COLORS[goal.status] || "badge-blue"}`}>
                            {goal.status}
                          </span>
                        </div>
                        {goal.description && (
                          <p className="text-xs text-gray-400 truncate">{goal.description}</p>
                        )}
                      </div>
                    </div>
                    <ChevronRight size={16} className="text-gray-600 group-hover:text-brand-400 transition-colors shrink-0 mt-1" />
                  </div>

                  {/* Progress bar (from trajectory) */}
                  {total > 0 && (
                    <div className="mt-4">
                      <div className="flex items-center justify-between text-xs mb-1.5">
                        <span className="text-gray-500">{acquired}/{total} documents</span>
                        <span className={`font-bold ${scoreColor(pct / 100)}`}>{pct}%</span>
                      </div>
                      <div className="h-1.5 bg-surface-hover rounded-full overflow-hidden">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${pct}%` }}
                          transition={{ duration: 0.7, ease: "easeOut" }}
                          className={`h-full rounded-full ${pct >= 70 ? "bg-green-500" : pct >= 40 ? "bg-yellow-500" : "bg-brand-600"}`}
                        />
                      </div>
                    </div>
                  )}

                  {/* Trajectory preview */}
                  {traj && (
                    <div className="mt-3 pt-3 border-t border-surface-border">
                      <div className="flex items-center gap-4 flex-wrap text-xs text-gray-500">
                        {/* Sequence dots */}
                        <div className="flex items-center gap-1">
                          {(traj.sequence || []).slice(0, 10).map((step: any, si: number) => (
                            <div key={si} title={step.document}
                              className={`w-2.5 h-2.5 rounded-full border ${
                                step.acquired
                                  ? "bg-green-500 border-green-500"
                                  : "bg-surface-hover border-surface-border"
                              }`}
                            />
                          ))}
                          {traj.sequence?.length > 10 && (
                            <span className="text-[10px] text-gray-600">+{traj.sequence.length - 10}</span>
                          )}
                        </div>

                        {traj.next_recommended && (
                          <div className="flex items-center gap-1 text-brand-400">
                            <Clock size={10} />
                            <span>Next: {traj.next_recommended}</span>
                          </div>
                        )}

                        {traj.projected_completion_date && (
                          <div className="flex items-center gap-1 text-gray-500">
                            <Calendar size={10} />
                            <span>Est: {fmtDate(traj.projected_completion_date)}</span>
                          </div>
                        )}

                        {!traj.next_recommended && total > 0 && (
                          <div className="flex items-center gap-1 text-green-400">
                            <CheckCircle size={10} />
                            <span>All documents present!</span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </Link>
            </motion.div>
          );
        })}
      </div>

      {/* Empty state */}
      {!goalsLoading && (!goals || goals.length === 0) && (
        <motion.div initial={{ opacity:0 }} animate={{ opacity:1 }}
          className="flex flex-col items-center py-20 gap-4">
          <div className="w-16 h-16 rounded-2xl bg-yellow-900/20 border border-yellow-700/30 flex items-center justify-center">
            <Target size={28} className="text-yellow-500" />
          </div>
          <div className="text-center">
            <p className="text-gray-300 font-medium">No goals yet</p>
            <p className="text-gray-500 text-sm mt-1">
              Create goals to track your document progress and get AI predictions
            </p>
          </div>
          <button onClick={() => setShowForm(true)} className="btn-primary">
            <Plus size={14} /> Create your first goal
          </button>
        </motion.div>
      )}
    </div>
  );
}