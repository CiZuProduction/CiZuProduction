"use client";

import { useState, useRef, useEffect, KeyboardEvent, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { chatApi, ApiError, MessageOut } from "@/lib/api";
import { authApi } from "@/lib/api";
import { ChatMessage } from "@/components/ChatMessage";
import { Navbar } from "@/components/Navbar";

function ChatPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [messages, setMessages] = useState<MessageOut[]>([]);
  const [question, setQuestion] = useState("");
  const [sending, setSending] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conversationId, setConversationId] = useState<string | undefined>();
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // ── Auth + load konversasi dari query param ─────────────────────────
  useEffect(() => {
    // Verifikasi sesi via cookie — /me akan 401 jika belum login
    authApi.me().catch(() => router.push("/login"));

    // Load konversasi jika ada ?conv= di URL (dari halaman history)
    const convId = searchParams.get("conv");
    if (convId) {
      setConversationId(convId);
      loadConversation(convId);
    }
  }, [router, searchParams]);

  // ── Auto-scroll ke pesan terbaru ────────────────────────────────────
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function loadConversation(id: string) {
    setLoadingHistory(true);
    try {
      const detail = await chatApi.getConversation(id);
      setMessages(detail.messages);
    } catch {
      setError("Gagal memuat percakapan.");
    } finally {
      setLoadingHistory(false);
    }
  }

  async function handleSend() {
    const trimmed = question.trim();
    if (!trimmed || sending) return;

    const userMsg: MessageOut = {
      id: crypto.randomUUID(),
      role: "user",
      content: trimmed,
      created_at: new Date().toISOString(),
      sources: [],
    };

    setMessages((prev) => [...prev, userMsg]);
    setQuestion("");
    setSending(true);
    setError(null);

    try {
      const res = await chatApi.sendMessage(trimmed, conversationId);
      setConversationId(res.conversation_id);

      const assistantMsg: MessageOut = {
        id: res.message_id,
        role: "assistant",
        content: res.answer,
        created_at: new Date().toISOString(),
        sources: res.sources,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Gagal mendapatkan jawaban. Coba lagi."
      );
      setMessages((prev) => prev.filter((m) => m.id !== userMsg.id));
      setQuestion(trimmed);
    } finally {
      setSending(false);
      inputRef.current?.focus();
    }
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  function handleNewChat() {
    setMessages([]);
    setConversationId(undefined);
    setError(null);
    setQuestion("");
    // Hapus query param dari URL
    router.push("/chat");
    inputRef.current?.focus();
  }

  return (
    <div className="flex h-screen flex-col bg-gray-50">
      <Navbar conversationId={conversationId} onNewChat={handleNewChat} />

      {/* Messages area */}
      <main
        className="flex-1 overflow-y-auto px-4 py-6"
        aria-label="Area percakapan"
        aria-live="polite"
        aria-atomic="false"
      >
        {/* Loading history */}
        {loadingHistory && (
          <div className="flex justify-center py-8">
            <div className="flex items-center gap-2 text-sm text-gray-400">
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Memuat percakapan…
            </div>
          </div>
        )}

        {/* Empty state */}
        {!loadingHistory && messages.length === 0 && (
          <div className="flex h-full items-center justify-center">
            <div className="text-center max-w-sm">
              <div className="w-16 h-16 bg-blue-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                    d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                  />
                </svg>
              </div>
              <p className="text-xl font-semibold text-gray-700 mb-2">Tanyakan sesuatu</p>
              <p className="text-sm text-gray-400">
                Upload dokumen terlebih dahulu, lalu ajukan pertanyaan berbasis dokumen Anda.
              </p>
            </div>
          </div>
        )}

        <div className="mx-auto max-w-2xl space-y-4">
          {messages.map((msg) => (
            <ChatMessage key={msg.id} message={msg} />
          ))}

          {/* Typing indicator */}
          {sending && (
            <div className="flex gap-3 justify-start" aria-label="AI sedang memproses">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-600 text-white text-xs font-bold">
                AI
              </div>
              <div className="rounded-2xl rounded-tl-sm bg-white border border-gray-200 px-4 py-3 shadow-sm">
                <div className="flex gap-1" aria-hidden="true">
                  <span className="h-2 w-2 rounded-full bg-gray-400 animate-bounce [animation-delay:-0.3s]" />
                  <span className="h-2 w-2 rounded-full bg-gray-400 animate-bounce [animation-delay:-0.15s]" />
                  <span className="h-2 w-2 rounded-full bg-gray-400 animate-bounce" />
                </div>
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </main>

      {/* Error banner */}
      {error && (
        <div
          role="alert"
          className="mx-4 mb-2 rounded-lg bg-red-50 px-4 py-2.5 text-sm text-red-700 border border-red-200 flex items-center justify-between"
        >
          <span>{error}</span>
          <button
            onClick={() => setError(null)}
            className="ml-2 underline text-red-600 shrink-0"
            aria-label="Tutup pesan error"
          >
            Tutup
          </button>
        </div>
      )}

      {/* Input area */}
      <div className="border-t border-gray-200 bg-white px-4 py-3">
        <div className="mx-auto max-w-2xl">
          <div className="flex gap-2 items-end">
            <label htmlFor="chat-input" className="sr-only">Ketik pertanyaan Anda</label>
            <textarea
              ref={inputRef}
              id="chat-input"
              rows={1}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={sending || loadingHistory}
              maxLength={4096}
              placeholder="Ketik pertanyaan… (Enter untuk kirim, Shift+Enter untuk baris baru)"
              className="flex-1 resize-none rounded-xl border border-gray-300 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 max-h-32 overflow-y-auto"
              style={{ minHeight: "44px" }}
              aria-multiline="true"
            />
            <button
              onClick={handleSend}
              disabled={sending || loadingHistory || !question.trim()}
              className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              aria-label="Kirim pertanyaan"
            >
              <svg aria-hidden="true" className="h-5 w-5 rotate-90" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            </button>
          </div>
          <p className="mt-1 text-right text-xs text-gray-400" aria-live="polite">
            {question.length}/4096
          </p>
        </div>
      </div>
    </div>
  );
}

export default function ChatPage() {
  return (
    <Suspense fallback={<div className="flex h-screen items-center justify-center text-gray-400">Memuat…</div>}>
      <ChatPageContent />
    </Suspense>
  );
}
