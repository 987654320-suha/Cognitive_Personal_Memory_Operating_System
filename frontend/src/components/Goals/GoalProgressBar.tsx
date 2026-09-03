// 📁 LOCATION: frontend/src/components/Goals/GoalProgressBar.tsx
"use client";
import { motion } from "framer-motion";

interface Props {
  pct:     number;   // 0–100
  label?:  string;
  showPct?: boolean;
  height?: "sm" | "md" | "lg";
}

export default function GoalProgressBar({ pct, label, showPct = true, height = "md" }: Props) {
  const h      = height === "sm" ? "h-1" : height === "md" ? "h-2" : "h-3";
  const color  = pct >= 70 ? "from-green-500 to-green-400" : pct >= 40 ? "from-yellow-500 to-yellow-400" : "from-brand-600 to-brand-400";
  const tcolor = pct >= 70 ? "text-green-400" : pct >= 40 ? "text-yellow-400" : "text-brand-400";

  return (
    <div className="w-full">
      {(label || showPct) && (
        <div className="flex justify-between text-xs mb-1">
          {label && <span className="text-gray-400">{label}</span>}
          {showPct && <span className={`font-bold ${tcolor}`}>{pct.toFixed(0)}%</span>}
        </div>
      )}
      <div className={`${h} bg-surface-hover rounded-full overflow-hidden`}>
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${Math.min(pct, 100)}%` }}
          transition={{ duration: 0.7, ease: "easeOut" }}
          className={`h-full bg-gradient-to-r ${color} rounded-full`}
        />
      </div>
    </div>
  );
}
