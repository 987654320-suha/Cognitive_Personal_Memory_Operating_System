// 📁 LOCATION: frontend/src/app/layout.tsx
import type { Metadata } from "next";
import { Toaster } from "react-hot-toast";
import { AppProvider } from "@/context/AppContext";
import Providers from "@/app/providers";
import { AuthProvider } from "@/context/AuthContext";
import AppShell from "@/components/Layout/AppShell";
import "@/styles/globals.css";

export const metadata: Metadata = {
  title:       "CogniSphere — Personal Cognitive Memory OS",
  description: "AI-powered personal document memory and retrieval system",
  icons:       { icon: "/favicon.ico" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="bg-surface text-white overflow-hidden">
        <Providers>
          <AuthProvider>
            <AppProvider>
              <AppShell>
                {children}
              </AppShell>
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
          </AuthProvider>
        </Providers>
      </body>
    </html>
  );
}