// 📁 LOCATION: frontend/src/components/Layout/Sidebar.tsx
"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search, LayoutDashboard, Clock, Target, MessageSquare,
  Network, AlertTriangle, Upload, Settings,
  ChevronLeft, Layers, PlusCircle, FlaskConical, BarChart3,
  Sliders, LogOut, FolderCheck,
} from "lucide-react";
import { useApp } from "@/context/AppContext";
import { useAuth } from "@/context/AuthContext";
import { cn } from "@/utils/helpers";

const NAV = [
  { href: "/",                   icon: LayoutDashboard, label: "Dashboard"          },
  { href: "/chat",               icon: MessageSquare,   label: "AI Chat"            },
  { href: "/search",             icon: Search,          label: "Search"             },
  { href: "/memory/add",         icon: PlusCircle,      label: "Add Memory"         },
  { href: "/goals",              icon: Target,          label: "Goals"              },
  { href: "/upload",             icon: Upload,          label: "Upload"             },
  { href: "/watcher",            icon: FolderCheck,     label: "Watcher Sync"       },
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
  const { user, logout } = useAuth();

  return (
    <motion.aside
      initial={false}
      animate={{ width: sidebarOpen ? 220 : 58 }}
      transition={{ duration: 0.22, ease: "easeInOut" }}
      className="h-screen bg-surface-card border-r border-surface-border flex flex-col overflow-hidden shrink-0"
    >
      {/* Header / Brand */}
      <div className="flex items-center justify-between px-3.5 py-3 border-b border-surface-border">
        <Link href="/" className="flex items-center gap-2 min-w-0">
          <div className="w-7 h-7 rounded-lg bg-brand-600 flex items-center justify-center shrink-0">
            <Layers size={15} className="text-white" />
          </div>
          <AnimatePresence>
            {sidebarOpen && (
              <motion.span
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: "auto" }}
                exit={{ opacity: 0, width: 0 }}
                className="font-semibold text-sm tracking-tight text-white whitespace-nowrap overflow-hidden"
              >
                CogniSphere
              </motion.span>
            )}
          </AnimatePresence>
        </Link>
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="text-gray-500 hover:text-white p-1 rounded transition-colors cursor-pointer"
        >
          <ChevronLeft
            size={16}
            className={cn("transition-transform duration-200", !sidebarOpen && "rotate-180")}
          />
        </button>
      </div>

      {/* Nav items */}
      <nav className="flex-1 px-1.5 py-2 space-y-0.5 overflow-y-auto">
        {NAV.map(({ href, icon: Icon, label }) => {
          const active = pathname === href || (href !== "/" && (pathname?.startsWith(href) ?? false));
          return (
            <Link key={href} href={href}>
              <motion.div
                whileHover={{ x: 2 }}
                className={cn(
                  "flex items-center gap-2.5 px-2.5 py-2 rounded-lg transition-all text-xs font-medium cursor-pointer",
                  active
                    ? "bg-brand-600/15 text-brand-400 border border-brand-500/20 font-semibold"
                    : "text-gray-400 hover:text-white hover:bg-surface-hover",
                )}
              >
                <Icon size={16} className={cn("shrink-0", active ? "text-brand-400" : "text-gray-400")} />
                <AnimatePresence>
                  {sidebarOpen && (
                    <motion.span
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="text-xs font-medium whitespace-nowrap overflow-hidden"
                    >
                      {label}
                    </motion.span>
                  )}
                </AnimatePresence>
              </motion.div>
            </Link>
          );
        })}
      </nav>

      {/* User profile & Settings footer */}
      <div className="px-1.5 py-2 border-t border-surface-border space-y-1">
        {user && (
          <div className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-surface/50 border border-surface-border">
            <div className="w-5 h-5 rounded-full bg-brand-500/30 text-brand-300 flex items-center justify-center text-[10px] font-bold shrink-0">
              {user.email.charAt(0).toUpperCase()}
            </div>
            {sidebarOpen && (
              <span className="text-[11px] text-gray-300 truncate max-w-[130px]" title={user.email}>
                {user.email}
              </span>
            )}
          </div>
        )}

        <Link href="/settings">
          <div className={cn(
            "flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-surface-hover transition-all cursor-pointer",
            pathname === "/settings" && "bg-surface-hover text-white",
          )}>
            <Settings size={15} className="shrink-0" />
            {sidebarOpen && <span className="text-xs">Settings</span>}
          </div>
        </Link>

        <button
          onClick={logout}
          title="Sign Out"
          className="w-full flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 transition-all text-xs cursor-pointer"
        >
          <LogOut size={15} className="shrink-0" />
          {sidebarOpen && <span>Sign Out</span>}
        </button>
      </div>
    </motion.aside>
  );
}