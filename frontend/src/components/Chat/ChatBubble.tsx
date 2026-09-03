// 📁 LOCATION: frontend/src/components/Chat/ChatBubble.tsx
"use client";
import { motion } from "framer-motion";
import ReactMarkdown from "react-markdown";
import Link from "next/link";
import { Brain, User, Cpu, Target } from "lucide-react";
import { smartTitle } from "@/utils/helpers";

interface Props {
  role:          "user" | "assistant";
  content:       string;
  memories_used?: any[];
  goal_context?:  string[];
  index:          number;
}

export default function ChatBubble({ role, content, memories_used, goal_context, index }: Props) {
  const isUser = role === "user";

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.03 }}
      className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}
    >
      {/* Avatar */}
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${isUser ? "bg-surface-hover" : "bg-brand-600"}`}>
        {isUser ? <User size={14} className="text-gray-300" /> : <Brain size={14} className="text-white" />}
      </div>

      <div className={`flex-1 max-w-2xl space-y-2 ${isUser ? "items-end flex flex-col" : ""}`}>
        {/* Message bubble */}
        <div className={`rounded-xl px-4 py-3 text-sm leading-relaxed ${
          isUser
            ? "bg-brand-600 text-white"
            : "bg-surface-card border border-surface-border text-gray-200"
        }`}>
          {isUser
            ? content
            : <ReactMarkdown className="prose prose-invert prose-sm max-w-none">{content}</ReactMarkdown>
          }
        </div>

        {/* Memory sources */}
        {memories_used && memories_used.length > 0 && (
          <div className="w-full">
            <p className="text-xs text-gray-500 flex items-center gap-1 mb-1">
              <Cpu size={10} /> Retrieved from {memories_used.length} memor{memories_used.length > 1 ? "ies" : "y"}
            </p>
            <div className="space-y-1">
              {memories_used.map((m: any) => (
                <Link key={m.id} href={`/memory/${m.id}`}>
                  <div className="flex items-center gap-2 bg-surface-hover rounded-lg px-3 py-1.5 text-xs hover:bg-surface-border transition-colors cursor-pointer">
                    <span className="text-white font-medium">{smartTitle("", m.title)}</span>
                    <span className="text-gray-600">·</span>
                    <span className="text-brand-400">{(m.activation_score * 100).toFixed(0)}% match</span>
                    {m.activation_reason && (
                      <span className="text-gray-500 truncate">{m.activation_reason}</span>
                    )}
                  </div>
                </Link>
              ))}
            </div>
          </div>
        )}

        {/* Goals */}
        {goal_context && goal_context.length > 0 && (
          <div className="flex items-center gap-1.5 flex-wrap">
            <Target size={11} className="text-yellow-500" />
            {goal_context.map(g => (
              <span key={g} className="badge badge-yellow">{g}</span>
            ))}
          </div>
        )}
      </div>
    </motion.div>
  );
}
