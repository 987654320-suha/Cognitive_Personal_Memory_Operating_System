// 📁 LOCATION: frontend/src/hooks/useChat.ts
import { useState, useCallback } from "react";
import { sendChat } from "@/services/api";
import toast from "react-hot-toast";

export interface ChatMessage {
  role:          "user" | "assistant";
  content:       string;
  memories_used?: any[];
  goal_context?:  string[];
}

interface UseChatReturn {
  messages:   ChatMessage[];
  sessionId:  string | undefined;
  loading:    boolean;
  send:       (text: string) => Promise<void>;
  clear:      () => void;
}

export function useChat(): UseChatReturn {
  const [messages,  setMessages]  = useState<ChatMessage[]>([]);
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [loading,   setLoading]   = useState(false);

  const send = useCallback(async (text: string) => {
    const q = text.trim();
    if (!q || loading) return;

    setMessages(prev => [...prev, { role: "user", content: q }]);
    setLoading(true);

    try {
      const res = await sendChat(q, sessionId);
      setSessionId(res.session_id);
      setMessages(prev => [...prev, {
        role:          "assistant",
        content:       res.answer,
        memories_used: res.memories_used,
        goal_context:  res.goal_context,
      }]);
    } catch {
      toast.error("Chat error — is the backend running?");
      setMessages(prev => [...prev, { role: "assistant", content: "Sorry, I could not connect to the backend." }]);
    } finally {
      setLoading(false);
    }
  }, [sessionId, loading]);

  const clear = useCallback(() => {
    setMessages([]);
    setSessionId(undefined);
  }, []);

  return { messages, sessionId, loading, send, clear };
}
