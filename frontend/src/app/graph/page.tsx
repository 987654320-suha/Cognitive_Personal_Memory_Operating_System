// 📁 LOCATION: frontend/src/app/search/page.tsx
"use client";
import { useState, useEffect, useRef, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { Search, Filter, X } from "lucide-react";
import { useQuery } from "react-query";
import { searchContent } from "@/services/api";
import { smartTitle, fileTypeIcon } from "@/utils/helpers";
import toast from "react-hot-toast";

// This component needs to be wrapped in Suspense because it uses useSearchParams
function SearchResults() {
  const searchParams = useSearchParams();
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [filterType, setFilterType] = useState("all");
  const [query, setQuery] = useState("");
  const hasSearched = useRef(false);

  const doSearch = async (searchQuery: string, mode: string = "acma") => {
    if (!searchQuery.trim()) {
      setResults([]);
      return;
    }
    
    setLoading(true);
    try {
      const data = await searchContent(searchQuery, mode);
      setResults(data.results || []);
    } catch (error) {
      toast.error("Search failed");
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  // Handle initial search from URL params
  useEffect(() => {
    if (hasSearched.current) return;

    const q = searchParams?.get("q");
    if (q) {
      hasSearched.current = true;
      setQuery(q);
      doSearch(q, searchParams?.get("mode") || "acma");
    }
  }, [searchParams]);

  // Handle search input
  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      doSearch(query, "acma");
      // Update URL without reload
      const url = new URL(window.location.href);
      url.searchParams.set("q", query);
      window.history.pushState({}, "", url.toString());
    }
  };

  const filteredResults = filterType === "all" 
    ? results 
    : results.filter(r => r.file_type === filterType);

  const fileTypes = [...new Set(results.map(r => r.file_type))];

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Search Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-4">Search</h1>
        
        <form onSubmit={handleSearch} className="flex gap-2">
          <div className="flex-1 relative">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search your knowledge base..."
              className="w-full px-4 py-3 bg-surface-card border border-surface-border rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-brand-500"
            />
            {query && (
              <button
                type="button"
                onClick={() => setQuery("")}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white"
              >
                <X size={18} />
              </button>
            )}
          </div>
          <button
            type="submit"
            disabled={loading}
            className="px-6 py-3 bg-brand-600 hover:bg-brand-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <Search size={18} />
            Search
          </button>
        </form>
      </div>

      {/* Results Stats */}
      {results.length > 0 && (
        <div className="flex items-center justify-between mb-6">
          <p className="text-sm text-gray-400">
            Found {results.length} result{results.length !== 1 ? "s" : ""}
          </p>
          
          {/* Filter */}
          {fileTypes.length > 0 && (
            <div className="flex items-center gap-2">
              <Filter size={14} className="text-gray-400" />
              <select
                value={filterType}
                onChange={(e) => setFilterType(e.target.value)}
                className="bg-surface-card text-sm text-white border border-surface-border rounded-md px-3 py-1.5 focus:outline-none focus:border-brand-500"
              >
                <option value="all">All Types</option>
                {fileTypes.map(type => (
                  <option key={type} value={type}>
                    {type.charAt(0).toUpperCase() + type.slice(1)}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
      )}

      {/* Results Grid */}
      {loading ? (
        <div className="flex justify-center items-center py-20">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-500" />
        </div>
      ) : filteredResults.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredResults.map((item) => (
            <motion.div
              key={item.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="p-4 bg-surface-card border border-surface-border rounded-lg hover:border-brand-500 transition-colors cursor-pointer"
            >
              <div className="flex items-start gap-3">
                <span className="text-2xl">{fileTypeIcon(item.file_type)}</span>
                <div className="flex-1 min-w-0">
                  <h3 className="text-sm font-semibold text-white truncate">
                    {smartTitle(item.source || "", item.title)}
                  </h3>
                  <p className="text-xs text-gray-500 mt-1">
                    {item.file_type} • {item.source || "Unknown source"}
                  </p>
                  {item.importance && (
                    <div className="mt-2">
                      <div className="h-1 bg-surface-border rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-brand-600 rounded-full" 
                          style={{ width: `${(item.importance) * 100}%` }}
                        />
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      ) : results.length > 0 && filteredResults.length === 0 ? (
        <div className="text-center py-20">
          <p className="text-gray-400">No results match your filter</p>
        </div>
      ) : query && !loading && (
        <div className="text-center py-20">
          <Search size={48} className="mx-auto text-gray-700 mb-4" />
          <p className="text-gray-400">No results found for "{query}"</p>
          <p className="text-sm text-gray-600 mt-2">Try adjusting your search terms</p>
        </div>
      )}

      {/* Initial state */}
      {!query && !loading && results.length === 0 && (
        <div className="text-center py-20">
          <Search size={48} className="mx-auto text-gray-700 mb-4" />
          <p className="text-gray-400">Search your knowledge base</p>
          <p className="text-sm text-gray-600 mt-2">Enter a query to get started</p>
        </div>
      )}
    </div>
  );
}

// Main export with Suspense
export default function SearchPage() {
  return (
    <Suspense fallback={
      <div className="flex justify-center items-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-500" />
      </div>
    }>
      <SearchResults />
    </Suspense>
  );
}