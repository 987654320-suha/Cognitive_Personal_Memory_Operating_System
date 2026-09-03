// 📁 LOCATION: frontend/src/components/Memory/MemoryCard.tsx
"use client";
import { motion } from "framer-motion";
import Image from "next/image";
import Link from "next/link";
import { Clock, Tag, Target, Eye, Cpu } from "lucide-react";
import { Memory } from "@/services/api";
import { smartTitle, relativeDate, fileTypeIcon, fileTypeColor, scoreColor, imageUrl, cn } from "@/utils/helpers";

interface Props {
  memory: Memory;
  query?: string;
  showScore?: boolean;
  index?: number;
}

export default function MemoryCard({ memory, query, showScore, index = 0 }: Props) {
  const title    = smartTitle(memory.source || "", memory.title);
  const imgUrl   = imageUrl(memory.image);
  const typeIcon = fileTypeIcon(memory.file_type);
  const score    = memory.activation_score;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.04, duration: 0.3 }}
    >
      <Link href={`/memory/${memory.id}${query ? `?q=${encodeURIComponent(query)}` : ""}`}>
        <div className="card hover:border-brand-600/50 hover:bg-surface-hover transition-all duration-200 cursor-pointer group overflow-hidden">

          {/* Image thumbnail if available */}
          {imgUrl && (
            <div className="relative h-36 w-full overflow-hidden bg-surface-hover">
              <Image src={imgUrl} alt={title} fill className="object-cover opacity-80 group-hover:opacity-100 transition-opacity" />
              <div className="absolute inset-0 bg-gradient-to-t from-surface-card/80 to-transparent" />
              <span className="absolute bottom-2 left-3 text-xl">{typeIcon}</span>
            </div>
          )}

          <div className="p-4">
            {/* Header row */}
            <div className="flex items-start justify-between gap-2 mb-2">
              <div className="flex items-center gap-2 min-w-0">
                {!imgUrl && <span className="text-lg shrink-0">{typeIcon}</span>}
                <h3 className="font-semibold text-white text-sm leading-snug truncate group-hover:text-brand-300 transition-colors">
                  {title}
                </h3>
              </div>
              {showScore && score !== undefined && (
                <span className={`text-xs font-mono font-bold shrink-0 ${scoreColor(score)}`}>
                  {(score * 100).toFixed(0)}%
                </span>
              )}
            </div>

            {/* Description */}
            {memory.description && (
              <p className="text-xs text-gray-400 line-clamp-2 mb-3 leading-relaxed">
                {memory.description}
              </p>
            )}

            {/* Activation reason (from ACMA — shown only in search results) */}
            {memory.activation_reason && (
              <div className="flex items-start gap-1.5 mb-3 bg-brand-900/20 border border-brand-700/30 rounded-lg px-2.5 py-1.5">
                <Cpu size={11} className="text-brand-400 mt-0.5 shrink-0" />
                <p className="text-xs text-brand-300 leading-snug">{memory.activation_reason}</p>
              </div>
            )}

            {/* Objects detected */}
            {memory.objects?.length > 0 && (
              <div className="flex flex-wrap gap-1 mb-3">
                {memory.objects.slice(0, 4).map(obj => (
                  <span key={obj} className="badge badge-blue">{obj}</span>
                ))}
                {memory.objects.length > 4 && (
                  <span className="badge bg-surface-hover text-gray-400">+{memory.objects.length - 4}</span>
                )}
              </div>
            )}

            {/* Matched goals */}
            {(memory.matched_goals?.length ?? 0) > 0 && (
              <div className="flex items-center gap-1 mb-3 flex-wrap">
                <Target size={11} className="text-yellow-500" />
                {(memory.matched_goals ?? []).map(g => (
                  <span key={g} className="badge badge-yellow">{g}</span>
                ))}
              </div>
            )}

            {/* Footer */}
            <div className="flex items-center justify-between text-xs text-gray-500">
              <div className="flex items-center gap-1">
                <Clock size={11} />
                {relativeDate(memory.date)}
              </div>
              <div className="flex items-center gap-2">
                {memory.access_count > 0 && (
                  <div className="flex items-center gap-1">
                    <Eye size={11} />
                    {memory.access_count}
                  </div>
                )}
                <span className={cn("uppercase text-[10px] font-mono", fileTypeColor(memory.file_type))}>
                  {memory.file_type}
                </span>
              </div>
            </div>

            {/* ACMA component bars (shown on hover if score exists) */}
            {showScore && memory.components && (
              <div className="mt-3 pt-3 border-t border-surface-border space-y-1 opacity-0 group-hover:opacity-100 transition-opacity">
                {Object.entries(memory.components).map(([key, val]) => (
                  <div key={key} className="flex items-center gap-2">
                    <span className="text-[10px] text-gray-500 w-20 capitalize">{key}</span>
                    <div className="flex-1 h-1 bg-surface-hover rounded-full overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${(val as number) * 100}%` }}
                        className="h-full bg-brand-600 rounded-full"
                      />
                    </div>
                    <span className="text-[10px] text-gray-500 w-8 text-right">{((val as number) * 100).toFixed(0)}%</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </Link>
    </motion.div>
  );
}