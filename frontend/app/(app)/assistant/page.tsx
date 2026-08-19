"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  Send,
  Plus,
  Sparkles,
  AlertTriangle,
  Trash2,
  MessageSquare,
  Loader2,
} from "lucide-react";
import { API_URL, api, getToken } from "@/lib/api";
import { cn } from "@/lib/utils";

interface Msg {
  role: "user" | "assistant";
  content: string;
}

const SUGGESTIONS = [
  "What is machine unlearning and how does it protect privacy?",
  "Explain the difference between SISA and certified removal.",
  "How does a Merkle-tree deletion proof work?",
  "What are the GDPR Article 17 requirements?",
];

export default function AssistantPage() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<{ configured: boolean; model: string } | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    api
      .get<{ configured: boolean; model: string }>("/api/v1/assistant/status")
      .then(setStatus)
      .catch(() => setStatus({ configured: false, model: "unknown" }));
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, streaming]);

  const streamChat = useCallback(async () => {
    const text = input.trim();
    if (!text || streaming) return;
    setInput("");
    setError(null);
    setStreaming(true);
    const history: Msg[] = [...messages, { role: "user", content: text }];
    setMessages(history);
    setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

    const controller = new AbortController();
    abortRef.current = controller;
    try {
      const res = await fetch(`${API_URL}/api/v1/assistant/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${getToken()}` },
        body: JSON.stringify({ messages: history }),
        signal: controller.signal,
      });
      if (!res.ok || !res.body) {
        setError(`Request failed (${res.status})`);
        return;
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const frames = buffer.split("\n\n");
        buffer = frames.pop() ?? "";
        for (const frame of frames) {
          if (!frame.startsWith("data: ")) continue;
          const data = frame.slice(6).trim();
          if (data === "[DONE]") return;
          try {
            const parsed = JSON.parse(data);
            if (parsed.error) {
              setError(parsed.error);
              return;
            }
            const chunk = parsed.chunk ?? "";
            const parsedChunk = JSON.parse(chunk);
            const delta =
              parsedChunk.choices?.[0]?.delta?.content ??
              parsedChunk.choices?.[0]?.message?.content ??
              "";
            if (delta) {
              setMessages((prev) => {
                const next = [...prev];
                next[next.length - 1] = {
                  role: "assistant",
                  content: next[next.length - 1].content + delta,
                };
                return next;
              });
            }
          } catch {
            /* ignore malformed frames */
          }
        }
      }
    } catch (err) {
      if ((err as Error).name !== "AbortError") setError((err as Error).message);
    } finally {
      setStreaming(false);
      abortRef.current = null;
    }
  }, [input, messages, streaming]);

  const newChat = useCallback(() => {
    abortRef.current?.abort();
    setMessages([]);
    setError(null);
    setInput("");
    setStreaming(false);
  }, []);

  const stop = useCallback(() => abortRef.current?.abort(), []);

  const lastUser = [...messages].reverse().find((m) => m.role === "user")?.content;

  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col">
      {/* header */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-cyan-400" />
          <h1 className="text-lg font-semibold text-slate-100">Assistant</h1>
          {status && (
            <span className="mono ml-2 rounded-full border border-slate-700 bg-slate-800/60 px-2.5 py-0.5 text-[10px] text-slate-400">
              {status.configured ? status.model : "not configured"}
            </span>
          )}
        </div>
        <button
          onClick={newChat}
          className="inline-flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-300 transition-colors hover:bg-slate-800/60"
        >
          <Plus className="h-3.5 w-3.5" /> New chat
        </button>
      </div>

      {/* messages */}
      <div ref={scrollRef} className="glass flex-1 space-y-6 overflow-y-auto rounded-xl p-6">
        {messages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-cyan-500 to-violet-500 shadow-[0_0_40px_-8px_rgba(34,211,238,0.6)]">
              <MessageSquare className="h-8 w-8 text-slate-950" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-slate-100">How can I help?</h2>
              <p className="mt-1 max-w-md text-sm text-slate-400">
                Ask me anything about machine unlearning, privacy compliance, SISA, or the
                VeriUnlearn platform.
              </p>
            </div>
            <div className="mt-2 grid w-full max-w-lg gap-2 sm:grid-cols-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => setInput(s)}
                  className="rounded-lg border border-slate-700/80 bg-slate-800/40 px-3 py-2.5 text-left text-xs text-slate-300 transition-all hover:border-cyan-500/40 hover:bg-slate-800/70"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <div
            key={i}
            className={cn(
              "flex",
              m.role === "user" ? "justify-end" : "justify-start"
            )}
          >
            <div
              className={cn(
                "max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-3 text-sm leading-relaxed",
                m.role === "user"
                  ? "rounded-br-md bg-cyan-500/90 text-slate-950"
                  : "rounded-bl-md border border-slate-700/60 bg-slate-800/60 text-slate-200"
              )}
            >
              {m.content}
              {m.role === "assistant" && i === messages.length - 1 && streaming && (
                <span className="ml-1 inline-block h-4 w-1.5 animate-pulse rounded-sm bg-cyan-400 align-middle" />
              )}
            </div>
          </div>
        ))}

        {error && (
          <div className="flex items-start gap-2 rounded-lg border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-300">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* input */}
      <div className="mt-4">
        {status && !status.configured && (
          <p className="mb-2 flex items-center gap-2 text-xs text-amber-300/90">
            <AlertTriangle className="h-3.5 w-3.5" />
            LLM not configured — set <code className="mono rounded bg-slate-800 px-1.5 py-0.5">LLM_BASE_URL</code>,{" "}
            <code className="mono rounded bg-slate-800 px-1.5 py-0.5">LLM_API_KEY</code> and{" "}
            <code className="mono rounded bg-slate-800 px-1.5 py-0.5">LLM_MODEL</code> in{" "}
            <code className="mono rounded bg-slate-800 px-1.5 py-0.5">backend/.env</code>.
          </p>
        )}
        <div className="flex items-end gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                streamChat();
              }
            }}
            rows={1}
            placeholder="Ask anything…"
            className="max-h-40 min-h-[48px] flex-1 resize-none rounded-xl border border-slate-700 bg-slate-900/60 px-4 py-3 text-sm text-slate-100 placeholder:text-slate-500 focus:border-cyan-500/50 focus:outline-none focus:ring-2 focus:ring-cyan-500/20"
          />
          <button
            onClick={streaming ? stop : streamChat}
            disabled={(!input.trim() && !streaming) || (streaming === false && !input.trim())}
            className="inline-flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-cyan-500 text-slate-950 shadow-[0_0_20px_-4px_rgba(34,211,238,0.6)] transition-all hover:bg-cyan-400 disabled:opacity-40"
            aria-label={streaming ? "Stop" : "Send"}
          >
            {streaming ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <Send className="h-5 w-5" />
            )}
          </button>
        </div>
        <p className="mono mt-2 text-center text-[10px] text-slate-600">
          {lastUser ? `Replying to: ${lastUser.slice(0, 60)}` : "VeriUnlearn Assistant"}
        </p>
      </div>
    </div>
  );
}