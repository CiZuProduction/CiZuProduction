"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { documentApi, chatApi, ApiError, DocumentOut, ConversationSummary } from "@/lib/api";
import { authApi } from "@/lib/api";
import { Navbar } from "@/components/Navbar";

interface Stats {
  totalDocuments: number;
  completedDocuments: number;
  processingDocuments: number;
  failedDocuments: number;
  totalConversations: number;
}

export default function DashboardPage() {
  const router = useRouter();
  const [stats, setStats] = useState<Stats | null>(null);
  const [recentDocs, setRecentDocs] = useState<DocumentOut[]>([]);
  const [recentConvs, setRecentConvs] = useState<ConversationSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    authApi.me().catch(() => router.push("/login"));
    loadData();
  }, [router]);

  async function loadData() {
    setLoading(true);
    try {
      const [docsRes, convsRes] = await Promise.all([
        documentApi.list(1, 5),
        chatApi.listConversations(1, 5),
      ]);

      const all = docsRes.items;
      setStats({
        totalDocuments: docsRes.total,
        completedDocuments: all.filter((d) => d.ingest_status === "completed").length,
        processingDocuments: all.filter((d) => ["queued", "processing", "uploaded"].includes(d.ingest_status)).length,
        failedDocuments: all.filter((d) => d.ingest_status === "failed").length,
        totalConversations: convsRes.length,
      });
      setRecentDocs(docsRes.items);
      setRecentConvs(convsRes.slice(0, 3));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Gagal memuat data.");
    } finally {
      setLoading(false);
    }
  }

  function formatDate(iso: string) {
    return new Date(iso).toLocaleString("id-ID", {
      day: "numeric", month: "short", hour: "2-digit", minute: "2-digit",
    });
  }

  const statCards = stats ? [
    { label: "Total Dokumen", value: stats.totalDocuments, icon: "📄", color: "bg-blue-50 text-blue-600" },
    { label: "Siap Digunakan", value: stats.completedDocuments, icon: "✅", color: "bg-green-50 text-green-600" },
    { label: "Sedang Diproses", value: stats.processingDocuments, icon: "⏳", color: "bg-yellow-50 text-yellow-600" },
    { label: "Total Percakapan", value: stats.totalConversations, icon: "💬", color: "bg-purple-50 text-purple-600" },
  ] : [];

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />

      <main className="mx-auto max-w-5xl px-6 py-8">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-lg font-semibold text-gray-900">Dashboard</h1>
          <button
            onClick={loadData}
            className="text-sm text-blue-600 hover:underline"
          >
            Refresh
          </button>
        </div>

        {error && (
          <div role="alert" className="mb-6 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 border border-red-200">
            {error}
          </div>
        )}

        {/* Stats grid */}
        {loading ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-24 rounded-xl bg-white border border-gray-200 animate-pulse" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            {statCards.map((card) => (
              <div key={card.label} className="bg-white rounded-xl border border-gray-200 p-4 hover:shadow-sm transition-shadow">
                <div className={`w-10 h-10 rounded-lg flex items-center justify-center text-xl mb-3 ${card.color}`}>
                  {card.icon}
                </div>
                <p className="text-2xl font-bold text-gray-900">{card.value}</p>
                <p className="text-xs text-gray-500 mt-0.5">{card.label}</p>
              </div>
            ))}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Recent documents */}
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-gray-700">Dokumen Terbaru</h2>
              <a href="/documents" className="text-xs text-blue-600 hover:underline">Lihat semua</a>
            </div>

            {recentDocs.length === 0 ? (
              <p className="text-sm text-gray-400 text-center py-4">Belum ada dokumen</p>
            ) : (
              <ul className="space-y-2">
                {recentDocs.map((doc) => (
                  <li key={doc.id} className="flex items-center justify-between">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="text-base">📄</span>
                      <span className="text-sm text-gray-700 truncate">{doc.original_filename}</span>
                    </div>
                    <span className={`shrink-0 ml-2 rounded-full px-2 py-0.5 text-xs font-medium ${
                      doc.ingest_status === "completed" ? "bg-green-100 text-green-700" :
                      doc.ingest_status === "failed" ? "bg-red-100 text-red-700" :
                      "bg-yellow-100 text-yellow-700"
                    }`}>
                      {doc.ingest_status === "completed" ? "Selesai" :
                       doc.ingest_status === "failed" ? "Gagal" : "Proses"}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* Recent conversations */}
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-gray-700">Percakapan Terbaru</h2>
              <a href="/history" className="text-xs text-blue-600 hover:underline">Lihat semua</a>
            </div>

            {recentConvs.length === 0 ? (
              <p className="text-sm text-gray-400 text-center py-4">Belum ada percakapan</p>
            ) : (
              <ul className="space-y-2">
                {recentConvs.map((conv) => (
                  <li key={conv.id}>
                    <a
                      href={`/chat?conv=${conv.id}`}
                      className="flex items-center justify-between group"
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="text-base">💬</span>
                        <span className="text-sm text-gray-700 truncate group-hover:text-blue-600 transition-colors">
                          {conv.title ?? "Percakapan tanpa judul"}
                        </span>
                      </div>
                      <span className="shrink-0 ml-2 text-xs text-gray-400">
                        {formatDate(conv.updated_at)}
                      </span>
                    </a>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        {/* Quick actions */}
        <div className="mt-6 bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Aksi Cepat</h2>
          <div className="flex flex-wrap gap-3">
            <a
              href="/chat"
              className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 transition-colors"
            >
              <span>💬</span> Mulai Chat Baru
            </a>
            <a
              href="/documents"
              className="flex items-center gap-2 rounded-lg bg-gray-100 px-4 py-2 text-sm text-gray-700 hover:bg-gray-200 transition-colors"
            >
              <span>📤</span> Upload Dokumen
            </a>
            <a
              href="/history"
              className="flex items-center gap-2 rounded-lg bg-gray-100 px-4 py-2 text-sm text-gray-700 hover:bg-gray-200 transition-colors"
            >
              <span>📋</span> Lihat Riwayat
            </a>
          </div>
        </div>
      </main>
    </div>
  );
}
