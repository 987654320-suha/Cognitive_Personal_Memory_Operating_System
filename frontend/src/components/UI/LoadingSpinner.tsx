// 📁 LOCATION: frontend/src/components/UI/LoadingSpinner.tsx
import { Loader2 } from "lucide-react";

interface Props { size?: number; text?: string; className?: string; }

export default function LoadingSpinner({ size = 24, text, className }: Props) {
  return (
    <div className={`flex flex-col items-center justify-center gap-3 ${className}`}>
      <Loader2 size={size} className="animate-spin text-brand-400" />
      {text && <p className="text-sm text-gray-400">{text}</p>}
    </div>
  );
}
