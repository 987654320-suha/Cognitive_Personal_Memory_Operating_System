// 📁 LOCATION: frontend/src/app/search/page.tsx
"use client";
import { useState, useEffect, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { searchMemories, Memory } from "@/services/api";
import SearchBar from "@/components/Search/SearchBar";
import MemoryCard from "@/components/Memory/MemoryCard";
import { Filter, SlidersHorizontal, Loader2, FileSearch } from "lucide-react";

function SearchContent() {
  const searchParams = useSearchParams();
  const router       = useRouter();
  const [query,     setQuery]     = useState(searchParams?.get("q") || "");
  const [mode,      setMode]      = useState(searchParams?.get("mode") || "acma");
  const [results,   setResults]   = useState<Memory[]>([]);
  const [loading,   setLoading]   = useState(false);
  const [error,     setError]     = useState("");
  const [topK,      setTopK]      = useState(12);
  const [filterType, setFilterType] = useState("all");

  const doSearch = async (q: string, m = mode, k = topK) => {
    if (!q.trim()) return;
    setLoading(true);
    setError("");
    setQuery(q);
    setMode(m);
    router.replace(`/search?q=${encodeURIComponent(q)}&mode=${m}`, { scroll: false });
    try {
      const data = await searchMemories(q, m, k);
      setResults(data.results);
    } catch (e: any) {
      setError("Search failed. Check if the backend is running on port 8000.");
    } finally {
      setLoading(false);
    }
  };

  // Run search on initial load if q param exists
  useEffect(() => {
    const q = searchParams?.get("q");
    if (q) doSearch(q, searchParams?.get("mode") || "acma");
  }, []);

  // Filter by file type
  const fileTypes = ["all", ...Array.from(new Set(results.map(r => r.file_type).filter(Boolean)))];
  const filtered  = filterType === "all" ? results : results.filter(r => r.file_type === filterType);

  return (
    <div className="p-6 max-w-6xl mx-auto">
      {/* Search bar */}
      <div className="mb-6">
        <SearchBar onSearch={doSearch} loading={loading} />
      </div>

      {/* Results header */}
      {(results.length > 0 || loading) && (
        <div className="flex items-center justify-between mb-4 gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            {!loading && (
              <span className="text-sm text-gray-400">
                <span className="text-white font-semibold">{filtered.length}</span> results for&nbsp;
                <span className="text-brand-400">"{query}"</span>
              </span>
            )}
          </div>

          {/* File type filter chips */}
          <div className="flex items-center gap-2 flex-wrap">
            <Filter size={14} className="text-gray-500" />
            {fileTypes.map(t => (
              <button
                key={t}
                onClick={() => setFilterType(t)}
                className={`text-xs px-3 py-1 rounded-full border transition-all ${
                  filterType === t
                    ? "border-brand-500 bg-brand-600/20 text-brand-300"
                    : "border-surface-border text-gray-400 hover:border-brand-600/50 hover:text-white"
                }`}
              >
                {t.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-20 gap-3">
          <Loader2 size={24} className="animate-spin text-brand-400" />
          <span className="text-gray-400">Searching with ACMA engine...</span>
        </div>
      )}

      {/* Error */}
      {error && !loading && (
        <div className="card border-red-700/50 bg-red-900/10 p-4 text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && query && results.length === 0 && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col items-center py-20 gap-4">
          <FileSearch size={48} className="text-gray-700" />
          <p className="text-gray-400 text-sm">No memories found for "{query}"</p>
          <p className="text-gray-600 text-xs">Try uploading related documents first</p>
        </motion.div>
      )}

      {/* Landing state */}
      {!loading && !query && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col items-center py-20 gap-4">
          <FileSearch size={48} className="text-gray-700" />
          <p className="text-gray-400 text-sm">Type a query to search your memories</p>
          <p className="text-gray-600 text-xs">Try: "IELTS certificate", "resume", "Germany Masters"</p>
        </motion.div>
      )}

      {/* Results grid */}
      {!loading && filtered.length > 0 && (
        <motion.div
          initial={{ opacity: 0 }} animate={{ opacity: 1 }}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
        >
          {filtered.map((mem, i) => (
            <MemoryCard key={mem.id} memory={mem} query={query} showScore index={i} />
          ))}
        </motion.div>
      )}

      {/* Load more */}
      {filtered.length >= topK && !loading && (
        <div className="mt-6 flex justify-center">
          <button
            onClick={() => { setTopK(topK + 12); doSearch(query, mode, topK + 12); }}
            className="btn-ghost border border-surface-border"
          >
            Load more
          </button>
        </div>
      )}
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense>
      <SearchContent />
    </Suspense>
  );
}