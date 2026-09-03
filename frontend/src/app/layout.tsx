// 📁 LOCATION: frontend/src/app/layout.tsx
import type { Metadata } from "next";
import { Toaster } from "react-hot-toast";
import { AppProvider } from "@/context/AppContext";
import Providers from "@/app/providers";
import Sidebar from "@/components/Layout/Sidebar";
import "@/styles/globals.css";

export const metadata: Metadata = {
  title:       "Cognisphere — Personal Cognitive Memory OS",
  description: "AI-powered personal document memory and retrieval system",
  icons:       { icon: "/favicon.ico" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="bg-surface text-white overflow-hidden">
        <Providers>
          <AppProvider>
            <div className="flex h-screen">
              <Sidebar />
              <main className="flex-1 overflow-y-auto min-w-0">
                {children}
              </main>
            </div>
            <Toaster
              position="top-right"
              toastOptions={{
                duration: 3000,
                style: {
                  background: "#16162a",
                  color:      "#f0f0ff",
                  border:     "1px solid #2a2a45",
                  fontSize:   "13px",
                },
              }}
            />
          </AppProvider>
        </Providers>
      </body>
    </html>
  );
}