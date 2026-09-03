// 📁 LOCATION: frontend/src/components/Memory/MemoryGrid.tsx
"use client";
import { motion } from "framer-motion";
import { FileSearch } from "lucide-react";
import { Memory } from "@/services/api";
import MemoryCard from "./MemoryCard";

interface Props {
  memories:    Memory[];
  query?:      string;
  showScore?:  boolean;
  emptyText?:  string;
  loading?:    boolean;
  columns?:    2 | 3 | 4;
}

const COLS: Record<number, string> = {
  2: "grid-cols-1 md:grid-cols-2",
  3: "grid-cols-1 md:grid-cols-2 lg:grid-cols-3",
  4: "grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4",
};

export default function MemoryGrid({
  memories, query, showScore, emptyText = "No memories found", loading, columns = 3
}: Props) {
  if (loading) return (
    <div className={`grid ${COLS[columns]} gap-4`}>
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="card h-48 skeleton" />
      ))}
    </div>
  );

  if (!memories?.length) return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
      className="flex flex-col items-center py-16 gap-3">
      <FileSearch size={40} className="text-gray-700" />
      <p className="text-gray-400 text-sm">{emptyText}</p>
    </motion.div>
  );

  return (
    <div className={`grid ${COLS[columns]} gap-4`}>
      {memories.map((mem, i) => (
        <MemoryCard key={mem.id} memory={mem} query={query} showScore={showScore} index={i} />
      ))}
    </div>
  );
}
