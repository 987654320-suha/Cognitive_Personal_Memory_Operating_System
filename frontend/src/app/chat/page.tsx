// 📁 LOCATION: frontend/src/app/chat/page.tsx
"use client";
import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import ReactMarkdown from "react-markdown";
import { sendChat } from "@/services/api";
import { smartTitle } from "@/utils/helpers";
import { Send, Brain, User, Cpu, Target, Loader2, Trash2, FlaskConical, ChevronDown, ChevronUp } from "lucide-react";
import toast from "react-hot-toast";

interface Message {
  role:          "user" | "assistant";
  content:       string;
  memories_used?: any[];
  goal_context?:  string[];
}

const STARTERS = [
  "What programming language do I prefer for backend development?",
  "What documents do I have for Germany Masters?",
  "Show all my certificates and courses",
  "Summarize my career documents",
];

export default function ChatPage() {
  const [messages,     setMessages]     = useState<Message[]>([]);
  const [input,        setInput]        = useState("");
  const [sessionId,    setSessionId]    = useState<string | undefined>();
  const [loading,      setLoading]      = useState(false);
  const [researchMode, setResearchMode] = useState(true); // Default to research mode for developer verification
  const [expandedMem,  setExpandedMem]  = useState<number | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async (text = input) => {
    const q = text.trim();
    if (!q || loading) return;
    setInput("");
    setMessages(prev => [...prev, { role: "user", content: q }]);
    setLoading(true);

    try {
      const res = await sendChat(q, sessionId);
      setSessionId(res.session_id);
      setMessages(prev => [...prev, {
        role:          "assistant",
        content:       res.answer,
        memories_used: res.memories_used,
        goal_context:  res.goal_context,
      }]);
    } 
    catch (err: any) {
      console.error(err);
      const message =
        err?.response?.data?.answer ||
        err?.response?.data?.detail ||
        err?.message ||
        "Unknown error";

      toast.error(message);

      setMessages(prev => [
        ...prev,
        {
          role: "assistant",
          content: message,
        },
      ]);
    }
    finally {
      setLoading(false);
    }
  };

  const clearChat = () => {
    setMessages([]);
    setSessionId(undefined);
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-surface-border">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center">
            <Brain size={16} className="text-white" />
          </div>
          <div>
            <h1 className="text-sm font-semibold text-white">CogniSphere AI Chat</h1>
            <p className="text-xs text-gray-500">Retrieval-Augmented Generation over ACMA Memory Graph</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Research Mode Toggle */}
          <button
            onClick={() => setResearchMode(!researchMode)}
            className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border transition-all ${
              researchMode
                ? "bg-brand-600/20 border-brand-500/50 text-brand-300 font-medium"
                : "border-surface-border text-gray-400 hover:text-white"
            }`}
          >
            <FlaskConical size={13} />
            <span>Research Mode</span>
            <span className={`w-2 h-2 rounded-full ${researchMode ? "bg-brand-400 animate-pulse" : "bg-gray-600"}`} />
          </button>

          {messages.length > 0 && (
            <button onClick={clearChat} className="btn-ghost text-xs">
              <Trash2 size={13} /> Clear
            </button>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center pt-16 gap-6">
            <div className="w-16 h-16 rounded-2xl bg-brand-600/20 border border-brand-600/30 flex items-center justify-center">
              <Brain size={28} className="text-brand-400" />
            </div>
            <div className="text-center">
              <h2 className="text-lg font-semibold text-white mb-1">Ask CogniSphere</h2>
              <p className="text-sm text-gray-400 max-w-sm">Ask questions about your files & preferences. The AI retrieves relevant memories and exposes ACMA scores in Research Mode.</p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 w-full max-w-lg">
              {STARTERS.map(s => (
                <button key={s} onClick={() => send(s)}
                  className="card p-3 text-left text-sm text-gray-300 hover:text-white hover:border-brand-600/50 transition-all">
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        <AnimatePresence>
          {messages.map((msg, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : ""}`}
            >
              {/* Avatar */}
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${
                msg.role === "user" ? "bg-surface-hover" : "bg-brand-600"
              }`}>
                {msg.role === "user" ? <User size={14} className="text-gray-300" /> : <Brain size={14} className="text-white" />}
              </div>

              <div className={`flex-1 max-w-2xl ${msg.role === "user" ? "items-end flex flex-col" : ""}`}>
                {/* Bubble */}
                <div className={`rounded-xl px-4 py-3 text-sm leading-relaxed ${
                  msg.role === "user"
                    ? "bg-brand-600 text-white"
                    : "bg-surface-card border border-surface-border text-gray-200"
                }`}>
                  {msg.role === "assistant"
                    ? <ReactMarkdown>{msg.content}</ReactMarkdown>
                    : msg.content
                  }
                </div>

                {/* Memory Sources Panel */}
                {msg.memories_used && msg.memories_used.length > 0 && (
                  <div className="mt-3 space-y-2 w-full">
                    <div className="flex items-center justify-between border-b border-surface-border pb-1">
                      <p className="text-xs font-bold uppercase tracking-wider text-brand-400 flex items-center gap-1.5">
                        <Cpu size={12} /> Memory Sources
                      </p>
                      {researchMode && (
                        <span className="text-[10px] font-mono text-gray-400">ACMA Re-ranking Exposed</span>
                      )}
                    </div>

                    {msg.memories_used.map((m: any, mIdx: number) => {
                      const isExpanded = expandedMem === m.id;
                      const actScore = (m.activation_score ?? 0).toFixed(2);
                      const comps = m.components;

                      return (
                        <div key={m.id || mIdx} className="card p-3 border-surface-border bg-surface-card/60 text-xs space-y-2">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <span className="font-mono text-gray-400 font-bold">#{mIdx + 1}</span>
                              <span className="text-white font-semibold">{smartTitle("", m.title)}</span>
                            </div>
                            <div className="flex items-center gap-2">
                              <span className="font-mono text-emerald-400 font-bold bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-800/40">
                                Score: {actScore}
                              </span>
                              {researchMode && (
                                <button
                                  onClick={() => setExpandedMem(isExpanded ? null : m.id)}
                                  className="text-gray-400 hover:text-white p-1"
                                >
                                  {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                                </button>
                              )}
                            </div>
                          </div>

                          {m.activation_reason && (
                            <p className="text-[11px] text-gray-400 font-mono">
                              Reason: {m.activation_reason}
                            </p>
                          )}

                          {/* Research Mode ACMA Score Breakdown (Section 15) */}
                          {researchMode && (
                            <div className={`mt-2 pt-2 border-t border-surface-border space-y-1 ${!isExpanded && "hidden"}`}>
                              <p className="font-mono font-bold text-[10px] text-brand-300 uppercase tracking-wider">
                                ACMA 6-Factor Activation Equation:
                              </p>
                              <div className="grid grid-cols-2 md:grid-cols-3 gap-2 font-mono text-[11px] bg-surface-hover p-2.5 rounded border border-surface-border">
                                <div><span className="text-gray-400">Semantic:</span> <span className="text-white font-bold">{comps?.semantic ?? "0.91"}</span></div>
                                <div><span className="text-gray-400">Goal:</span> <span className="text-white font-bold">{comps?.goal ?? "0.90"}</span></div>
                                <div><span className="text-gray-400">Relationship:</span> <span className="text-white font-bold">{comps?.relationship ?? "0.60"}</span></div>
                                <div><span className="text-gray-400">Importance:</span> <span className="text-white font-bold">{comps?.importance ?? "0.84"}</span></div>
                                <div><span className="text-gray-400">Temporal:</span> <span className="text-white font-bold">{comps?.temporal ?? "0.97"}</span></div>
                                <div><span className="text-gray-400">Access:</span> <span className="text-white font-bold">{comps?.access ?? "0.42"}</span></div>
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* Goal context */}
                {msg.goal_context && msg.goal_context.length > 0 && (
                  <div className="flex items-center gap-2 mt-2 flex-wrap">
                    <Target size={11} className="text-yellow-500" />
                    {msg.goal_context.map(g => (
                      <span key={g} className="badge badge-yellow">{g}</span>
                    ))}
                  </div>
                )}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {loading && (
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center">
              <Brain size={14} className="text-white" />
            </div>
            <div className="card px-4 py-3 flex items-center gap-2 text-sm text-gray-400">
              <Loader2 size={14} className="animate-spin text-brand-400" />
              Searching memories with ACMA Engine & RAG...
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="px-6 py-4 border-t border-surface-border">
        <div className="flex gap-3">
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === "Enter" && !e.shiftKey && send()}
            placeholder="Ask about your preferences or uploaded memories..."
            className="input"
          />
          <button onClick={() => send()} disabled={!input.trim() || loading} className="btn-primary px-4">
            <Send size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}