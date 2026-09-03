// 📁 LOCATION: frontend/src/components/Search/SearchBar.tsx
"use client";
import { useState, useRef, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Search, X, Sparkles, Zap, Type, Clock } from "lucide-react";
import { useApp } from "@/context/AppContext";
import axios from "axios";
import { API_BASE_URL } from "@/services/api";

const API = API_BASE_URL;

interface Props {
  onSearch:   (query: string, mode: string) => void;
  loading?:   boolean;
  autoFocus?: boolean;
  large?:     boolean;
}

const MODES = [
  { id:"acma",    icon:Sparkles, label:"Smart",   desc:"Best accuracy — BM25 + AI + filename" },
  { id:"fast",    icon:Zap,      label:"Fast",    desc:"Exact keyword match" },
  { id:"semantic",icon:Sparkles, label:"Semantic",desc:"Concept & meaning search" },
];

const EXAMPLES = [
  "resume", "IELTS certificate", "bank statement",
  "Germany Masters documents", "passport", "project files",
];

export default function SearchBar({ onSearch, loading, autoFocus, large }: Props) {
  const [query,     setQuery]     = useState("");
  const [mode,      setMode]      = useState("acma");
  const [showSugg,  setShowSugg]  = useState(false);
  const [showModes, setShowModes] = useState(false);
  const [suggest,   setSuggest]   = useState<any[]>([]);
  const inputRef   = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<any>(null);
  const { setLastQuery } = useApp();

  useEffect(() => { if (autoFocus) inputRef.current?.focus(); }, [autoFocus]);

  // Live autocomplete
  const fetchSuggestions = useCallback(async (q: string) => {
    if (q.length < 2) { setSuggest([]); return; }
    try {
      const res = await axios.get(`${API}/search/suggest`, { params: { q } });
      setSuggest(res.data || []);
    } catch { setSuggest([]); }
  }, []);

  const handleChange = (val: string) => {
    setQuery(val);
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => fetchSuggestions(val), 200);
  };

  const submit = (q = query) => {
    const trimmed = q.trim();
    if (!trimmed) return;
    setLastQuery(trimmed);
    setShowSugg(false);
    setSuggest([]);
    onSearch(trimmed, mode);
  };

  const showDropdown = showSugg && (suggest.length > 0 || query.length < 2);

  return (
    <div className="relative w-full">
      <div className={`relative flex items-center gap-2 card px-3 ${large ? "py-4" : "py-2.5"} focus-within:border-brand-500 focus-within:ring-1 focus-within:ring-brand-500/40 transition-all`}>
        <Search size={large ? 20 : 16} className="text-gray-500 shrink-0" />

        <input
          ref={inputRef}
          value={query}
          onChange={e => handleChange(e.target.value)}
          onFocus={() => setShowSugg(true)}
          onBlur={() => setTimeout(() => setShowSugg(false), 180)}
          onKeyDown={e => { if (e.key === "Enter") submit(); if (e.key === "Escape") setShowSugg(false); }}
          placeholder={large ? "Search your memories... (e.g. resume, IELTS, passport)" : "Search..."}
          className={`flex-1 bg-transparent text-white placeholder-gray-500 focus:outline-none ${large ? "text-base" : "text-sm"}`}
        />

        {query && (
          <button onClick={() => { setQuery(""); setSuggest([]); }} className="text-gray-500 hover:text-white">
            <X size={14} />
          </button>
        )}

        {/* Mode picker */}
        <div className="relative">
          <button
            onClick={() => setShowModes(!showModes)}
            className="flex items-center gap-1 text-xs font-medium text-gray-400 hover:text-white bg-surface-hover px-2.5 py-1.5 rounded-md transition-colors whitespace-nowrap"
          >
            {MODES.find(m => m.id === mode)?.label} <span className="text-gray-600">▾</span>
          </button>
          <AnimatePresence>
            {showModes && (
              <motion.div initial={{ opacity:0, y:-6 }} animate={{ opacity:1, y:0 }} exit={{ opacity:0, y:-6 }}
                className="absolute right-0 top-full mt-1 w-56 card shadow-2xl z-50 p-1">
                {MODES.map(m => (
                  <button key={m.id} onClick={() => { setMode(m.id); setShowModes(false); }}
                    className={`w-full flex items-start gap-2 px-3 py-2.5 rounded-lg text-left text-xs transition-colors ${mode===m.id ? "bg-brand-600/20 text-brand-300" : "text-gray-400 hover:bg-surface-hover hover:text-white"}`}>
                    <m.icon size={13} className="mt-0.5 shrink-0" />
                    <div>
                      <p className="font-semibold">{m.label}</p>
                      <p className="opacity-60 text-[11px] leading-snug">{m.desc}</p>
                    </div>
                  </button>
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <button onClick={() => submit()} disabled={!query.trim() || loading}
          className="btn-primary text-xs px-3 py-1.5 shrink-0">
          {loading ? <span className="animate-spin inline-block">⟳</span> : "Search"}
        </button>
      </div>

      {/* Dropdown */}
      <AnimatePresence>
        {showDropdown && (
          <motion.div initial={{ opacity:0, y:-4 }} animate={{ opacity:1, y:0 }} exit={{ opacity:0, y:-4 }}
            className="absolute top-full left-0 right-0 mt-1 card shadow-2xl z-40 overflow-hidden">
            {suggest.length > 0 ? (
              <>
                <p className="text-[10px] text-gray-500 px-4 pt-2 pb-1">Suggestions</p>
                {suggest.map((s: any) => (
                  <button key={s.id} onMouseDown={() => { setQuery(s.title); submit(s.title); }}
                    className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-surface-hover transition-colors text-left">
                    <Search size={12} className="text-gray-600 shrink-0" />
                    <span className="text-sm text-white">{s.title}</span>
                    <span className="ml-auto text-[10px] text-gray-600 uppercase">{s.file_type}</span>
                  </button>
                ))}
              </>
            ) : (
              <>
                <p className="text-[10px] text-gray-500 px-4 pt-2 pb-1">Try searching for</p>
                {EXAMPLES.map(ex => (
                  <button key={ex} onMouseDown={() => { setQuery(ex); submit(ex); }}
                    className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-surface-hover transition-colors text-left">
                    <Clock size={12} className="text-gray-600 shrink-0" />
                    <span className="text-sm text-gray-300">{ex}</span>
                  </button>
                ))}
              </>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
