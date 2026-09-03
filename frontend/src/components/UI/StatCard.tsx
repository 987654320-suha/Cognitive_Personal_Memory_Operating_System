// 📁 LOCATION: frontend/src/components/UI/StatCard.tsx
"use client";
import { motion } from "framer-motion";
import { LucideIcon } from "lucide-react";

interface Props {
  label:      string;
  value:      string | number;
  icon:       LucideIcon;
  color?:     string;
  subtext?:   string;
  index?:     number;
}

export default function StatCard({ label, value, icon: Icon, color = "text-brand-400", subtext, index = 0 }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      className="card p-4"
    >
      <div className="flex items-start justify-between mb-2">
        <Icon size={16} className={color} />
      </div>
      <div className="text-2xl font-bold text-white">{value}</div>
      <div className="text-xs text-gray-500 mt-0.5">{label}</div>
      {subtext && <div className="text-xs text-gray-600 mt-1">{subtext}</div>}
    </motion.div>
  );
}
