// 📁 LOCATION: frontend/src/components/Layout/Header.tsx
"use client";
import { useRouter } from "next/navigation";
import { Upload, Search } from "lucide-react";
import { useApp } from "@/context/AppContext";
import SearchBar from "@/components/Search/SearchBar";

interface Props {
  title?:       string;
  showSearch?:  boolean;
  children?:    React.ReactNode;
}

export default function Header({ title, showSearch = false, children }: Props) {
  const router = useRouter();
  const { uploadFiles } = useApp();

  const handleSearch = (q: string, mode: string) => {
    router.push(`/search?q=${encodeURIComponent(q)}&mode=${mode}`);
  };

  const handleFileClick = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.multiple = true;
    input.accept = ".pdf,.docx,.jpg,.jpeg,.png,.webp,.txt";
    input.onchange = e => {
      const files = Array.from((e.target as HTMLInputElement).files || []);
      if (files.length) uploadFiles(files);
    };
    input.click();
  };

  return (
    <div className="flex items-center gap-4 px-6 py-4 border-b border-surface-border sticky top-0 bg-surface z-30 backdrop-blur-sm">
      {title && (
        <h1 className="text-lg font-bold text-white shrink-0">{title}</h1>
      )}

      {showSearch && (
        <div className="flex-1 max-w-lg">
          <SearchBar onSearch={handleSearch} />
        </div>
      )}

      <div className="ml-auto flex items-center gap-2">
        {children}
        <button onClick={handleFileClick} className="btn-primary text-sm">
          <Upload size={15} /> Upload
        </button>
      </div>
    </div>
  );
}
