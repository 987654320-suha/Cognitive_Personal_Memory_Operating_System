// 📁 LOCATION: frontend/src/app/goals/[id]/page.tsx
"use client";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import {
  getGoalProgress, getTrajectory, updateGoalStatus,
  GoalProgress, Trajectory,
} from "@/services/api";
import { smartTitle, fmtDate, scoreColor } from "@/utils/helpers";
import {
  ArrowLeft, Target, CheckCircle, AlertCircle,
  Clock, TrendingUp, Calendar, Loader2, Search,
} from "lucide-react";
import toast from "react-hot-toast";

export default function GoalDetail({ params }: { params: { id: string } }) {
  const id = parseInt(params.id);
  const [progress,   setProgress]   = useState<GoalProgress | null>(null);
  const [trajectory, setTrajectory] = useState<Trajectory | null>(null);
  const [loading,    setLoading]    = useState(true);
  const [error,      setError]      = useState("");

  useEffect(() => {
    setLoading(true);
    Promise.all([getGoalProgress(id), getTrajectory(id)])
      .then(([p, t]) => { setProgress(p); setTrajectory(t); })
      .catch(e => setError(e?.response?.data?.detail || "Failed to load goal"))
      .finally(() => setLoading(false));
  }, [id]);

  const changeStatus = async (status: string) => {
    try {
      await updateGoalStatus(id, status);
      const updated = await getGoalProgress(id);
      setProgress(updated);
      toast.success(`Goal marked as ${status}`);
    } catch { toast.error("Failed to update status"); }
  };

  if (loading) return (
    <div className="flex items-center justify-center h-full gap-3">
      <Loader2 size={20} className="animate-spin text-brand-400" />
      <span className="text-gray-400 text-sm">Loading goal...</span>
    </div>
  );

  if (error || !progress) return (
    <div className="p-8 text-center">
      <p className="text-red-400 text-sm">{error || "Goal not found"}</p>
      <Link href="/goals" className="btn-ghost text-xs mt-4 inline-flex">← Back to Goals</Link>
    </div>
  );

  const goal = progress.goal;
  const pct  = Math.min(progress.completion_pct, 100);
  const barC = pct >= 70 ? "bg-green-500" : pct >= 40 ? "bg-yellow-500" : "bg-brand-600";

  return (
    <div className="p-6 max-w-4xl mx-auto">
      {/* Back */}
      <Link href="/goals" className="btn-ghost mb-5 w-fit text-sm">
        <ArrowLeft size={14} /> Goals
      </Link>

      {/* Header card */}
      <motion.div initial={{ opacity:0, y:10 }} animate={{ opacity:1, y:0 }} className="card p-6 mb-5">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-xl bg-yellow-500/10 border border-yellow-500/30 flex items-center justify-center">
              <Target size={22} className="text-yellow-400" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">{goal.name}</h1>
              {goal.description && (
                <p className="text-sm text-gray-400 mt-0.5">{goal.description}</p>
              )}
              <div className="flex items-center gap-2 mt-2 flex-wrap">
                <span className={`badge ${goal.status === "active" ? "badge-green" : goal.status === "completed" ? "badge-blue" : "badge-yellow"}`}>
                  {goal.status}
                </span>
                <span className="text-xs text-gray-500">{progress.total_memories} documents linked</span>
              </div>
            </div>
          </div>
          <div className="flex gap-2 flex-wrap">
            {goal.status !== "completed" && (
              <button onClick={() => changeStatus("completed")} className="btn-ghost border border-green-700/50 text-green-400 text-xs">
                <CheckCircle size={13} /> Complete
              </button>
            )}
            {goal.status === "active" && (
              <button onClick={() => changeStatus("paused")} className="btn-ghost text-xs">Pause</button>
            )}
            {goal.status === "paused" && (
              <button onClick={() => changeStatus("active")} className="btn-primary text-xs">Resume</button>
            )}
          </div>
        </div>

        {/* Progress */}
        <div className="mt-5">
          <div className="flex justify-between text-sm mb-2">
            <span className="text-gray-400">Overall completion</span>
            <span className={`font-bold ${scoreColor(pct / 100)}`}>{pct.toFixed(0)}%</span>
          </div>
          <div className="h-2.5 bg-surface-hover rounded-full overflow-hidden">
            <motion.div initial={{ width:0 }} animate={{ width:`${pct}%` }}
              transition={{ duration:0.8, ease:"easeOut" }}
              className={`h-full ${barC} rounded-full`} />
          </div>
        </div>
      </motion.div>

      {/* Trajectory timeline */}
      {trajectory && trajectory.sequence && trajectory.sequence.length > 0 && (
        <motion.div initial={{ opacity:0 }} animate={{ opacity:1 }} transition={{ delay:0.1 }} className="card p-5 mb-5">
          <h2 className="text-sm font-semibold text-white mb-1 flex items-center gap-2">
            <TrendingUp size={14} className="text-brand-400" /> Document Checklist & Trajectory
          </h2>

          {/* Stats row */}
          <div className="grid grid-cols-3 gap-3 mb-5 mt-4">
            <div className="bg-surface-hover rounded-lg p-3 text-center">
              <p className="text-xs text-gray-500 mb-1">Velocity</p>
              <p className="text-sm font-semibold text-white">
                {trajectory.velocity_days_per_doc
                  ? `${trajectory.velocity_days_per_doc.toFixed(0)} days/doc`
                  : "–"}
              </p>
            </div>
            <div className="bg-surface-hover rounded-lg p-3 text-center">
              <p className="text-xs text-gray-500 mb-1">Next Required</p>
              <p className="text-xs font-semibold text-brand-300 leading-tight">
                {trajectory.next_recommended || "✓ All done"}
              </p>
            </div>
            <div className="bg-surface-hover rounded-lg p-3 text-center">
              <p className="text-xs text-gray-500 mb-1">Est. Completion</p>
              <p className="text-sm font-semibold text-white">
                {trajectory.projected_completion_date
                  ? fmtDate(trajectory.projected_completion_date)
                  : "–"}
              </p>
            </div>
          </div>

          {/* Step-by-step checklist */}
          <div className="space-y-2">
            {trajectory.sequence.map((step, i) => (
              <div key={i} className={`flex items-center gap-3 p-2.5 rounded-lg ${
                step.acquired ? "bg-green-900/10" : "bg-surface-hover"
              }`}>
                <div className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 text-xs font-bold ${
                  step.acquired ? "bg-green-500 text-white" : "bg-surface-border text-gray-500 border border-surface-border"
                }`}>
                  {step.acquired ? "✓" : i + 1}
                </div>
                <div className="flex-1 min-w-0">
                  <span className={`text-sm ${step.acquired ? "text-gray-400 line-through" : "text-white"}`}>
                    {step.document}
                  </span>
                  {step.acquired_date && (
                    <span className="text-xs text-gray-500 ml-2">{fmtDate(step.acquired_date)}</span>
                  )}
                </div>
                {!step.acquired && (
                  <Link href={`/search?q=${encodeURIComponent(step.document)}&mode=acma`}
                    className="text-xs text-brand-400 hover:text-brand-300 flex items-center gap-1 shrink-0">
                    <Search size={11} /> Find
                  </Link>
                )}
              </div>
            ))}
          </div>
        </motion.div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* Present */}
        <motion.div initial={{ opacity:0 }} animate={{ opacity:1 }} transition={{ delay:0.15 }} className="card p-5">
          <h2 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <CheckCircle size={14} className="text-green-400" />
            Found Documents
            <span className="badge badge-green ml-auto">{progress.present.length}</span>
          </h2>
          <div className="space-y-2">
            {progress.present.map((mem: any) => (
              <Link key={mem.id} href={`/memory/${mem.id}`}>
                <div className="flex items-center gap-3 p-2.5 rounded-lg hover:bg-surface-hover transition-colors">
                  <CheckCircle size={13} className="text-green-400 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-white truncate">{smartTitle("", mem.title)}</p>
                    {mem.date && <p className="text-xs text-gray-500">{fmtDate(mem.date)}</p>}
                  </div>
                </div>
              </Link>
            ))}
            {progress.present.length === 0 && (
              <p className="text-sm text-gray-500 text-center py-6">
                No documents linked yet.<br/>
                <Link href="/upload" className="text-brand-400 text-xs">Upload documents →</Link>
              </p>
            )}
          </div>
        </motion.div>

        {/* Missing */}
        <motion.div initial={{ opacity:0 }} animate={{ opacity:1 }} transition={{ delay:0.2 }} className="card p-5">
          <h2 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <AlertCircle size={14} className="text-red-400" />
            Missing Documents
            <span className="badge badge-red ml-auto">{progress.missing_hints.length}</span>
          </h2>
          <div className="space-y-2">
            {progress.missing_hints.map((hint: string, i: number) => (
              <div key={i} className="flex items-center gap-3 p-2.5 rounded-lg bg-red-900/10 border border-red-700/20">
                <AlertCircle size={13} className="text-red-400 shrink-0" />
                <p className="text-sm text-gray-300 flex-1">{hint}</p>
                <Link href={`/search?q=${encodeURIComponent(hint)}&mode=acma`}
                  className="text-xs text-brand-400 hover:text-brand-300 shrink-0 flex items-center gap-1">
                  <Search size={10} /> Search
                </Link>
              </div>
            ))}
            {progress.missing_hints.length === 0 && (
              <div className="flex items-center justify-center py-6 gap-2 text-green-400">
                <CheckCircle size={16} />
                <span className="text-sm">All documents accounted for!</span>
              </div>
            )}
          </div>
        </motion.div>
      </div>
    </div>
  );
}