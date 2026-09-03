// 📁 LOCATION: frontend/src/components/Layout/Sidebar.tsx
"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search, LayoutDashboard, Clock, Target, MessageSquare,
  Network, AlertTriangle, TrendingUp, Upload, Settings,
  ChevronLeft, Layers, PlusCircle, FlaskConical, BarChart3,
  Sliders,
} from "lucide-react";
import { useApp } from "@/context/AppContext";
import { cn } from "@/utils/helpers";

const NAV = [
  { href: "/",                   icon: LayoutDashboard, label: "Dashboard"          },
  { href: "/chat",               icon: MessageSquare,   label: "AI Chat"            },
  { href: "/search",             icon: Search,          label: "Search"             },
  { href: "/memory/add",         icon: PlusCircle,      label: "Add Memory"         },
  { href: "/goals",              icon: Target,          label: "Goals"              },
  { href: "/upload",             icon: Upload,          label: "Upload"             },
  { href: "/contradictions",     icon: AlertTriangle,   label: "Contradictions"     },
  { href: "/timeline",           icon: Clock,           label: "Timeline"           },
  { href: "/graph",              icon: Network,         label: "Memory Graph"       },
  { href: "/analytics",          icon: BarChart3,       label: "Analytics"          },
  { href: "/research/search",    icon: FlaskConical,    label: "Research Search"    },
  { href: "/research/experiment",icon: Sliders,         label: "Experiments"        },
];

export default function Sidebar() {
  const pathname  = usePathname();
  const { sidebarOpen, setSidebarOpen } = useApp();

  return (
    <motion.aside
      initial={false}
      animate={{ width: sidebarOpen ? 220 : 58 }}
      transition={{ duration: 0.22, ease: "easeInOut" }}
      className="h-screen bg-surface-card border-r border-surface-border flex flex-col overflow-hidden shrink-0"
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-3 py-4 border-b border-surface-border">
        <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center shrink-0">
          <Layers size={16} className="text-white" />
        </div>
        <AnimatePresence>
          {sidebarOpen && (
            <motion.div initial={{ opacity:0 }} animate={{ opacity:1 }} exit={{ opacity:0 }}
              className="flex-1 min-w-0">
              <p className="font-bold text-white text-sm leading-none">Cognisphere</p>
              <p className="text-[10px] text-gray-500 mt-0.5">Memory OS</p>
            </motion.div>
          )}
        </AnimatePresence>
        <button onClick={() => setSidebarOpen(!sidebarOpen)}
          className={cn("text-gray-500 hover:text-white transition-colors shrink-0", !sidebarOpen && "mx-auto")}>
          <motion.div animate={{ rotate: sidebarOpen ? 0 : 180 }}>
            <ChevronLeft size={15} />
          </motion.div>
        </button>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-2 space-y-0.5 px-1.5 overflow-y-auto overflow-x-hidden">
        {NAV.map(({ href, icon: Icon, label }) => {
          const active = href === "/" ? pathname === "/" : pathname?.startsWith(href);
          return (
            <Link key={href} href={href}>
              <motion.div whileHover={{ x: 1 }}
                className={cn(
                  "flex items-center gap-2.5 px-2.5 py-2 rounded-lg cursor-pointer transition-all",
                  active
                    ? "bg-brand-600/20 text-brand-400 border border-brand-600/30"
                    : "text-gray-400 hover:text-white hover:bg-surface-hover"
                )}>
                <Icon size={16} className="shrink-0" />
                <AnimatePresence>
                  {sidebarOpen && (
                    <motion.span initial={{ opacity:0 }} animate={{ opacity:1 }} exit={{ opacity:0 }}
                      className="text-xs font-medium whitespace-nowrap">
                      {label}
                    </motion.span>
                  )}
                </AnimatePresence>
              </motion.div>
            </Link>
          );
        })}
      </nav>

      {/* Settings */}
      <div className="px-1.5 py-2 border-t border-surface-border">
        <Link href="/settings">
          <div className={cn(
            "flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-gray-500 hover:text-white hover:bg-surface-hover transition-all",
          )}>
            <Settings size={16} className="shrink-0" />
            {sidebarOpen && <span className="text-xs">Settings</span>}
          </div>
        </Link>
      </div>
    </motion.aside>
  );
}