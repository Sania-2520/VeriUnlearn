"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import AuthGuard from "../../components/AuthGuard";

interface Message {
  id: number;
  role: string;
  content: string;
  created_at: string;
}

interface Conversation {
  id: number;
  title: string;
  message_count: number;
  created_at: string;
}

export default function WorkspacePage() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConv, setActiveConv] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const [renamingId, setRenamingId] = useState<number | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const accumulatedRef = useRef("");

  const getAuthHeaders = () => ({
    "Content-Type": "application/json",
    Authorization: `Bearer ${localStorage.getItem("access_token")}`,
  });

  const fetchConversations = async () => {
    try {
      const res = await fetch("/api/chat/conversations", {
        headers: getAuthHeaders(),
      });
      if (res.ok) {
        setConversations(await res.json());
      }
    } catch {}
  };

  const fetchMessages = async (convId: number) => {
    try {
      const res = await fetch(`/api/chat/conversations/${convId}/messages`, {
        headers: getAuthHeaders(),
      });
      if (res.ok) {
        setMessages(await res.json());
      }
    } catch {}
  };

  const createConversation = async () => {
    try {
      const res = await fetch("/api/chat/conversations", {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify({ title: "New Chat" }),
      });
      if (res.ok) {
        const conv = await res.json();
        setActiveConv(conv.id);
        fetchConversations();
        setMessages([]);
      }
    } catch {}
  };

  const sendMessageStreaming = useCallback(async (convId: number, msg: string) => {
    abortRef.current = new AbortController();
    accumulatedRef.current = "";

    const userMsg: Message = {
      id: Date.now(),
      role: "user",
      content: msg,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);
    setStreamingContent("");

    try {
      const res = await fetch(`/api/chat/conversations/${convId}/messages`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify({ message: msg, stream: true }),
        signal: abortRef.current.signal,
      });

      if (!res.ok || !res.body) {
        throw new Error("Stream not available");
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const data = JSON.parse(line.slice(6));
            if (data.token) {
              accumulatedRef.current += data.token;
              setStreamingContent(accumulatedRef.current);
            }
            if (data.done) {
              const assistantMsg: Message = {
                id: data.message_id || Date.now() + 1,
                role: "assistant",
                content: accumulatedRef.current,
                created_at: new Date().toISOString(),
              };
              setMessages((prev) => [...prev, assistantMsg]);
              setStreamingContent("");
              accumulatedRef.current = "";
            }
          } catch {}
        }
      }
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      setStreamingContent("");
      accumulatedRef.current = "";
    }
    setLoading(false);
    abortRef.current = null;
  }, []);

  const renameConversation = async (id: number, title: string) => {
    const res = await fetch(`/api/chat/conversations/${id}`, {
      method: "PATCH",
      headers: getAuthHeaders(),
      body: JSON.stringify({ title }),
    });
    if (res.ok) fetchConversations();
  };

  const deleteConversation = async (id: number) => {
    const res = await fetch(`/api/chat/conversations/${id}`, {
      method: "DELETE",
      headers: getAuthHeaders(),
    });
    if (res.ok) {
      if (activeConv === id) {
        setActiveConv(null);
        setMessages([]);
      }
      fetchConversations();
    }
  };

  const sendMessage = () => {
    if (!input.trim() || !activeConv) return;
    const msg = input;
    sendMessageStreaming(activeConv, msg);
  };

  useEffect(() => {
    fetchConversations();
  }, []);

  useEffect(() => {
    if (activeConv) fetchMessages(activeConv);
  }, [activeConv]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent]);

  return (
    <AuthGuard>
    <div className="flex h-screen bg-white">
      <aside className="w-72 border-r border-gray-200 flex flex-col">
        <div className="p-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">VeriUnlearn</h2>
        </div>
        <div className="p-3">
          <button
            onClick={createConversation}
            className="w-full rounded-lg bg-primary-600 px-4 py-2 text-sm text-white font-medium hover:bg-primary-700"
          >
            New Chat
          </button>
        </div>
        <nav className="flex-1 overflow-y-auto p-2 space-y-1">
          {conversations.map((conv) => (
            <div key={conv.id} className="group relative">
              {renamingId === conv.id ? (
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    renameConversation(conv.id, renameValue);
                    setRenamingId(null);
                  }}
                  className="flex gap-1"
                >
                  <input
                    type="text"
                    value={renameValue}
                    onChange={(e) => setRenameValue(e.target.value)}
                    className="w-full rounded px-2 py-1.5 text-sm border border-primary-300 focus:outline-none focus:ring-1 focus:ring-primary-500"
                    autoFocus
                    onBlur={() => setRenamingId(null)}
                  />
                </form>
              ) : (
                <button
                  onClick={() => setActiveConv(conv.id)}
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                    activeConv === conv.id
                      ? "bg-primary-50 text-primary-700"
                      : "text-gray-700 hover:bg-gray-100"
                  }`}
                >
                  <div className="truncate font-medium pr-12">{conv.title}</div>
                  <div className="text-xs text-gray-400">{conv.message_count} messages</div>
                  <div className="absolute right-1 top-1 hidden group-hover:flex gap-0.5">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setRenamingId(conv.id);
                        setRenameValue(conv.title);
                      }}
                      className="p-1 text-gray-400 hover:text-gray-600 rounded"
                      title="Rename"
                    >
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                      </svg>
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        if (confirm("Delete this conversation?")) deleteConversation(conv.id);
                      }}
                      className="p-1 text-gray-400 hover:text-red-500 rounded"
                      title="Delete"
                    >
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                </button>
              )}
            </div>
          ))}
        </nav>
        <div className="p-4 border-t border-gray-200">
          <a
            href="/privacy"
            className="text-sm text-gray-500 hover:text-gray-700"
          >
            Privacy Center
          </a>
        </div>
      </aside>

      <main className="flex-1 flex flex-col">
        {activeConv ? (
          <>
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[70%] rounded-xl px-4 py-2.5 ${
                      msg.role === "user"
                        ? "bg-primary-600 text-white"
                        : "bg-gray-100 text-gray-900"
                    }`}
                  >
                    <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                  </div>
                </div>
              ))}
              {streamingContent && (
                <div className="flex justify-start">
                  <div className="bg-gray-100 rounded-xl px-4 py-2.5 max-w-[70%]">
                    <p className="text-sm whitespace-pre-wrap">{streamingContent}</p>
                  </div>
                </div>
              )}
              {loading && !streamingContent && (
                <div className="flex justify-start">
                  <div className="bg-gray-100 rounded-xl px-4 py-2.5">
                    <div className="flex space-x-1">
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-100" />
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-200" />
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            <div className="border-t border-gray-200 p-4">
              <div className="flex space-x-3">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendMessage()}
                  disabled={!!streamingContent}
                  placeholder={streamingContent ? "Generating..." : "Type your message..."}
                  className="flex-1 rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:bg-gray-50 disabled:text-gray-400"
                />
                {loading && streamingContent ? (
                  <button
                    onClick={() => { abortRef.current?.abort(); setLoading(false); setStreamingContent(""); accumulatedRef.current = ""; }}
                    className="rounded-lg bg-red-500 px-4 py-2.5 text-white text-sm font-medium hover:bg-red-600"
                  >
                    Stop
                  </button>
                ) : (
                  <button
                    onClick={sendMessage}
                    disabled={loading || !input.trim()}
                    className="rounded-lg bg-primary-600 px-4 py-2.5 text-white text-sm font-medium hover:bg-primary-700 disabled:opacity-50"
                  >
                    Send
                  </button>
                )}
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-gray-400">
            <div className="text-center space-y-2">
              <p className="text-lg">Select a conversation or start a new chat</p>
            </div>
          </div>
        )}
      </main>
    </div>
    </AuthGuard>
  );
}
