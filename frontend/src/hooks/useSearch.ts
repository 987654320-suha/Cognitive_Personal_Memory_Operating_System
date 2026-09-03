// 📁 LOCATION: frontend/src/hooks/useSearch.ts
import { useState, useCallback } from "react";
import { searchMemories, Memory } from "@/services/api";

interface UseSearchReturn {
  results:   Memory[];
  loading:   boolean;
  error:     string;
  query:     string;
  mode:      string;
  search:    (q: string, m?: string, k?: number) => Promise<void>;
  clear:     () => void;
}

export function useSearch(defaultMode = "acma"): UseSearchReturn {
  const [results, setResults] = useState<Memory[]>([]);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState("");
  const [query,   setQuery]   = useState("");
  const [mode,    setMode]    = useState(defaultMode);

  const search = useCallback(async (q: string, m = defaultMode, k = 12) => {
    if (!q.trim()) return;
    setLoading(true);
    setError("");
    setQuery(q);
    setMode(m);
    try {
      const data = await searchMemories(q, m, k);
      setResults(data.results);
    } catch (e: any) {
      setError("Search failed — check the backend connection");
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, [defaultMode]);

  const clear = useCallback(() => {
    setResults([]);
    setQuery("");
    setError("");
  }, []);

  return { results, loading, error, query, mode, search, clear };
}
