"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { chatApi, ApiError, ConversationSummary } from "@/lib/api";
import { authApi } from "@/lib/api";
import { Navbar } from "@/components/Navbar";

export default function HistoryPage() {
  const router = useRouter();
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    authApi.me().catch(() => router.push("/login"));
    loadHistory();
  }, [router]);

  async function loadHistory() {
    setLoading(true);
    try {
      const data = await chatApi.listConversations();
      setConversations(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Gagal memuat riwayat.");
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Hapus percakapan ini?")) return;
    try {
      await chatApi.deleteConversation(id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Gagal menghapus.");
    }
  }

  function formatDate(iso: string) {
    return new Date(iso).toLocaleString("id-ID", {
      day: "numeric", month: "short", year: "numeric",
      hour: "2-digit", minute: "2-digit",
    });
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />

      <main className="mx-auto max-w-3xl px-6 py-8">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-lg font-semibold text-gray-900">Riwayat Percakapan</h1>
          <span className="text-sm text-gray-400">{conversations.length} percakapan</span>
        </div>

        {error && (
          <div role="alert" className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 border border-red-200 flex items-center justify-between">
            <span>{error}</span>
            <button onClick={() => setError(null)} className="ml-2 underline">Tutup</button>
          </div>
        )}

        {loading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-16 rounded-xl bg-white border border-gray-200 animate-pulse" />
            ))}
          </div>
        ) : conversations.length === 0 ? (
          <div className="text-center py-16">
            <div className="w-16 h-16 bg-gray-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                  d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                />
              </svg>
            </div>
            <p className="text-gray-500 font-medium">Belum ada percakapan</p>
            <p className="text-sm text-gray-400 mt-1">Mulai chat untuk membuat percakapan pertama.</p>
            <a href="/chat" className="mt-4 inline-block rounded-lg bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 transition-colors">
              Mulai Chat
            </a>
          </div>
        ) : (
          <ul className="space-y-2" aria-label="Daftar percakapan">
            {conversations.map((conv) => (
              <li
                key={conv.id}
                className="group flex items-center justify-between rounded-xl bg-white border border-gray-200 px-4 py-3 hover:border-blue-200 hover:shadow-sm transition-all"
              >
                <button
                  onClick={() => router.push(`/chat?conv=${conv.id}`)}
                  className="min-w-0 flex-1 text-left"
                  aria-label={`Buka percakapan: ${conv.title ?? "Tanpa judul"}`}
                >
                  <div className="flex items-center gap-2">
                    <svg className="w-4 h-4 text-blue-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                        d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                      />
                    </svg>
                    <p className="truncate text-sm font-medium text-gray-800">
                      {conv.title ?? "Percakapan tanpa judul"}
                    </p>
                  </div>
                  <p className="text-xs text-gray-400 mt-0.5 ml-6">{formatDate(conv.updated_at)}</p>
                </button>
                <button
                  onClick={() => handleDelete(conv.id)}
                  className="ml-3 shrink-0 text-xs text-red-400 hover:text-red-600 opacity-0 group-hover:opacity-100 transition-opacity"
                  aria-label={`Hapus percakapan`}
                >
                  Hapus
                </button>
              </li>
            ))}
          </ul>
        )}
      </main>
    </div>
  );
}
