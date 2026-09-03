// 📁 LOCATION: frontend/src/components/UI/Badge.tsx
import { cn } from "@/utils/helpers";

type Variant = "blue" | "green" | "yellow" | "red" | "gray";

interface Props {
  children: React.ReactNode;
  variant?: Variant;
  className?: string;
}

const VARIANTS: Record<Variant, string> = {
  blue:   "bg-brand-900 text-brand-300 border-brand-700",
  green:  "bg-green-900/40 text-green-400 border-green-700/50",
  yellow: "bg-yellow-900/40 text-yellow-400 border-yellow-700/50",
  red:    "bg-red-900/40 text-red-400 border-red-700/50",
  gray:   "bg-surface-hover text-gray-400 border-surface-border",
};

export default function Badge({ children, variant = "gray", className }: Props) {
  return (
    <span className={cn("text-xs font-medium px-2 py-0.5 rounded-full border", VARIANTS[variant], className)}>
      {children}
    </span>
  );
}
