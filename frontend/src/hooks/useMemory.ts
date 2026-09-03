// 📁 LOCATION: frontend/src/hooks/useMemory.ts
import { useState, useEffect } from "react";
import { getMemory, getRelated, Memory } from "@/services/api";

interface UseMemoryReturn {
  memory:  Memory | null;
  related: Memory[];
  loading: boolean;
  error:   string;
  refetch: () => void;
}

export function useMemory(id: number): UseMemoryReturn {
  const [memory,  setMemory]  = useState<Memory | null>(null);
  const [related, setRelated] = useState<Memory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState("");
  const [tick,    setTick]    = useState(0);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    setError("");
    Promise.all([getMemory(id), getRelated(id)])
      .then(([mem, rel]) => {
        setMemory(mem);
        setRelated(rel.related || []);
      })
      .catch(() => setError("Failed to load memory"))
      .finally(() => setLoading(false));
  }, [id, tick]);

  const refetch = () => setTick(t => t + 1);

  return { memory, related, loading, error, refetch };
}
