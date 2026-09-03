// 📁 LOCATION: frontend/src/services/api.ts
import axios from "axios";

let rawBase = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").trim();

// Normalize Render internal service name or missing FQDN (e.g. "cognisphere-backend-ya2y" -> "https://cognisphere-backend-ya2y.onrender.com")
if (!rawBase.includes(".") && !rawBase.startsWith("localhost") && !rawBase.startsWith("127.0.0.1") && !rawBase.includes(":")) {
  rawBase = `${rawBase}.onrender.com`;
}

if (!rawBase.startsWith("http://") && !rawBase.startsWith("https://")) {
  rawBase = (rawBase.startsWith("localhost") || rawBase.startsWith("127.0.0.1"))
    ? `http://${rawBase}`
    : `https://${rawBase}`;
}

export const API_BASE_URL = rawBase.replace(/\/+$/, "");

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000,
});

// ── Types ─────────────────────────────────────────────────────────────────────

export interface Memory {
  id:               number;
  title:            string;
  description:      string;
  source:           string;
  file_type:        string;
  image:            string | null;
  date:             string | null;
  location:         string | null;
  objects:          string[];
  importance_score: number;
  access_count:     number;
  version?:         number;
  parent_id?:       number | null;
  goals?:           Goal[];
  // ACMA fields (present in search results)
  activation_score?:   number;
  activation_reason?:  string;
  matched_goals?:      string[];
  components?: {
    semantic:     number;
    goal:         number;
    relationship: number;
    importance:   number;
    temporal:     number;
    access:       number;
    title_boost?: number;
  };
}

export interface MemoryHistoryEntry {
  id:               number;
  memory_id:        number;
  version:          number;
  title:            string;
  description:      string;
  importance_score: number;
  source:           string;
  file_type:        string;
  date:             string | null;
  archived_at:      string | null;
  change_reason:    string;
}

export interface Goal {
  id:          number;
  name:        string;
  description: string;
  status:      string;
  progress:    number;
  parent_id:   number | null;
}

export interface SearchResult {
  query:   string;
  mode:    string;
  count:   number;
  results: Memory[];
}

export interface ChatResponse {
  answer:        string;
  session_id:    string;
  memories_used: { id: number; title: string; activation_score: number; activation_reason: string; matched_goals?: string[]; components?: Memory["components"] }[];
  goal_context:  string[];
}

export interface GoalProgress {
  goal:            Goal;
  total_memories:  number;
  present:         { id: number; title: string; date: string }[];
  missing_hints:   string[];
  completion_pct:  number;
}

export interface Trajectory {
  goal_name:                 string;
  sequence:                  { document: string; acquired: boolean; acquired_date: string | null; expected_order: number }[];
  velocity_days_per_doc:     number | null;
  next_recommended:          string | null;
  projected_completion_date: string | null;
  confidence:                number;
}

export interface Stats {
  totals:           { memories: number; goals: number; goal_memory_edges: number };
  goals:            { by_status: Record<string, number>; active: number; completed: number };
  files:            { by_type: Record<string, number>; embedding_coverage: string; object_detection_coverage: string };
  acma:             { avg_importance_score: number; total_retrievals: number; most_accessed: { id: number; title: string; access_count: number }[] };
  recent_memories:  { id: number; title: string; date: string }[];
}

export interface ExperimentConfig {
  query:             string;
  use_faiss?:        boolean;
  use_bm25?:         boolean;
  use_title?:        boolean;
  use_rrf?:          boolean;
  use_acma?:         boolean;
  acma_goal?:        boolean;
  acma_relationship?: boolean;
  acma_importance?:  boolean;
  acma_temporal?:    boolean;
  acma_access?:      boolean;
  acma_title_boost?: boolean;
  weight_semantic?:      number | null;
  weight_goal?:          number | null;
  weight_relationship?:  number | null;
  weight_importance?:    number | null;
  weight_temporal?:      number | null;
  weight_access?:        number | null;
  top_k?:            number;
}

export interface ExperimentResult {
  config:        ExperimentConfig;
  faiss_results: any[];
  bm25_results:  any[];
  title_results: any[];
  rrf_results:   any[];
  acma_results:  Memory[];
}

// ── Search ────────────────────────────────────────────────────────────────────

export const checkHealth = () => api.get("/health").then(r => r.data);

export const searchMemories = (q: string, mode = "acma", top_k = 10) =>
  api.get<SearchResult>("/search/", { params: { q, mode, top_k } }).then(r => r.data);

export const searchContent = searchMemories;

export const explainActivation = (memory_id: number, q: string) =>
  api.get(`/search/explain/${memory_id}`, { params: { q } }).then(r => r.data);

// ── Memories ──────────────────────────────────────────────────────────────────

export const getMemories    = ()   => api.get<Memory[]>("/memories/").then(r => r.data);
export const getMemory      = (id: number) => api.get<Memory>(`/memories/${id}`).then(r => r.data);
export const deleteMemory   = (id: number) => api.delete(`/memories/${id}`).then(r => r.data);
export const getRelated     = (id: number) => api.get(`/memory-details/${id}/related`).then(r => r.data);

export const createMemory = (payload: {
  title: string;
  description: string;
  importance_score?: number;
  source?: string;
  date?: string;
}) => api.post("/memories/", payload).then(r => r.data);

export const updateMemory = (id: number, payload: {
  title?: string;
  description?: string;
  importance_score?: number;
  date?: string;
  change_reason?: string;
}) => api.put(`/memories/${id}/update`, payload).then(r => r.data);

export const getMemoryHistory = (id: number) =>
  api.get(`/memories/${id}/history`).then(r => r.data);

export const updateImportance = (id: number, importance_score: number) =>
  api.patch(`/memories/${id}/importance`, { importance_score }).then(r => r.data);

// ── Upload ────────────────────────────────────────────────────────────────────

export const uploadFile = (file: File) => {
  const form = new FormData();
  form.append("file", file);
  return api.post("/upload/", form, { headers: { "Content-Type": "multipart/form-data" } }).then(r => r.data);
};

// ── Chat ──────────────────────────────────────────────────────────────────────

export const sendChat = async (
  query: string,
  session_id?: string,
  history?: any[]
) => {
  try {
    const res = await api.post<ChatResponse>("/chat/", {
      query,
      session_id,
      history,
    });

    return res.data;
  } catch (err: any) {
    console.error("CHAT ERROR:", err.response?.data);
    console.error(err);

    throw err;
  }
};

export const getChatHistory = (session_id: string) =>
  api.get(`/chat/history/${session_id}`).then(r => r.data);

// ── Goals ─────────────────────────────────────────────────────────────────────

export const getGoals       = ()              => api.get<Goal[]>("/goals/").then(r => r.data);
export const createGoal     = (name: string, description: string) =>
  api.post("/goals/", { name, description }).then(r => r.data);
export const getGoalProgress = (id: number)  => api.get<GoalProgress>(`/goals/${id}/progress`).then(r => r.data);
export const updateGoalStatus = (id: number, status: string) =>
  api.patch(`/goals/${id}/status`, { status }).then(r => r.data);
export const deleteGoal = (id: number) => api.delete(`/goals/${id}`).then(r => r.data);

// ── Trajectories ──────────────────────────────────────────────────────────────

export const getTrajectories = () => api.get<{ trajectories: Trajectory[] }>("/trajectories/").then(r => r.data);
export const getTrajectory   = (id: number) => api.get<Trajectory>(`/trajectories/${id}`).then(r => r.data);

// ── Timeline ──────────────────────────────────────────────────────────────────

export const getTimeline = (limit = 100) => api.get("/timeline/", { params: { limit } }).then(r => r.data);
export const getRecent   = (limit = 20)  => api.get("/timeline/recent", { params: { limit } }).then(r => r.data);

// ── Stats ─────────────────────────────────────────────────────────────────────

export const getStats = () => api.get<Stats>("/stats/").then(r => r.data);

// ── Graph ─────────────────────────────────────────────────────────────────────

export const getGraph      = ()              => api.get("/graph/").then(r => r.data);
export const getNeighbors  = (id: number)    => api.get(`/graph/neighbors/${id}`).then(r => r.data);
export const rebuildGraph  = ()              => api.post("/graph/rebuild").then(r => r.data);

// ── Contradictions ────────────────────────────────────────────────────────────

export const getContradictions = () => api.get("/contradictions/").then(r => r.data);

// ── Watcher ───────────────────────────────────────────────────────────────────

export const getWatcherStatus = () => api.get("/watcher/status").then(r => r.data);
export const startWatcher     = () => api.post("/watcher/start").then(r => r.data);
export const stopWatcher      = () => api.post("/watcher/stop").then(r => r.data);

// ── Decay ─────────────────────────────────────────────────────────────────────

export const getDecayScore    = (id: number) => api.get(`/decay/score/${id}`).then(r => r.data);
export const reinforceMemory  = (id: number) => api.post(`/decay/reinforce/${id}`).then(r => r.data);

// ── Experiment / Ablation ─────────────────────────────────────────────────────

export const runExperiment = (config: ExperimentConfig) =>
  api.post<ExperimentResult>("/experiment/search", config).then(r => r.data);
