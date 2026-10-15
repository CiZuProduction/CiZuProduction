"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { documentApi, ApiError, DocumentOut } from "@/lib/api";
import { authApi } from "@/lib/api";
import { Navbar } from "@/components/Navbar";

const STATUS_LABEL: Record<string, { label: string; className: string }> = {
  uploaded: { label: "Diunggah", className: "bg-gray-100 text-gray-600" },
  queued: { label: "Antrian", className: "bg-yellow-100 text-yellow-700" },
  processing: { label: "Diproses", className: "bg-blue-100 text-blue-700" },
  completed: { label: "Selesai", className: "bg-green-100 text-green-700" },
  failed: { label: "Gagal", className: "bg-red-100 text-red-700" },
  needs_review: { label: "Perlu Review", className: "bg-orange-100 text-orange-700" },
};

// Status yang masih "in progress" — perlu polling
const PENDING_STATUSES = new Set(["uploaded", "queued", "processing"]);

export default function DocumentsPage() {
  const router = useRouter();
  const [documents, setDocuments] = useState<DocumentOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    authApi.me().catch(() => router.push("/login"));
    loadDocuments();
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [router]);

  // Auto-polling setiap 5 detik jika ada dokumen yang masih diproses
  useEffect(() => {
    const hasPending = documents.some((d) => PENDING_STATUSES.has(d.ingest_status));

    if (hasPending && !pollRef.current) {
      pollRef.current = setInterval(async () => {
        try {
          const res = await documentApi.list();
          setDocuments(res.items);
          // Stop polling jika tidak ada yang pending lagi
          if (!res.items.some((d) => PENDING_STATUSES.has(d.ingest_status))) {
            if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
          }
        } catch { /* silent fail */ }
      }, 5000);
    } else if (!hasPending && pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, [documents]);

  async function loadDocuments() {
    setLoading(true);
    try {
      const res = await documentApi.list();
      setDocuments(res.items);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Gagal memuat dokumen.");
    } finally {
      setLoading(false);
    }
  }

  async function uploadFile(file: File) {
    setUploadError(null);
    setUploading(true);
    setUploadProgress(true);
    try {
      await documentApi.upload(file);
      await loadDocuments();
    } catch (err) {
      setUploadError(err instanceof ApiError ? err.message : "Upload gagal.");
    } finally {
      setUploading(false);
      setUploadProgress(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) await uploadFile(file);
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) uploadFile(file);
  }

  async function handleDelete(id: string, name: string) {
    if (!confirm(`Hapus "${name}"? Tindakan ini tidak dapat dibatalkan.`)) return;
    try {
      await documentApi.delete(id);
      setDocuments((prev) => prev.filter((d) => d.id !== id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Gagal menghapus.");
    }
  }

  async function handleReprocess(id: string) {
    try {
      await documentApi.reprocess(id);
      await loadDocuments();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Gagal proses ulang.");
    }
  }

  function formatBytes(bytes: number) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  const completedCount = documents.filter((d) => d.ingest_status === "completed").length;
  const processingCount = documents.filter((d) => PENDING_STATUSES.has(d.ingest_status)).length;

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />

      <main className="mx-auto max-w-4xl px-6 py-8">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-lg font-semibold text-gray-900">Dokumen</h1>
          <div className="flex items-center gap-3 text-sm text-gray-400">
            {processingCount > 0 && (
              <span className="flex items-center gap-1.5 text-blue-600">
                <svg className="animate-spin h-3.5 w-3.5" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                </svg>
                {processingCount} sedang diproses
              </span>
            )}
            <span>{completedCount}/{documents.length} siap</span>
          </div>
        </div>

        {/* Upload area — support drag & drop */}
        <div
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          className={`mb-6 rounded-xl border-2 border-dashed p-8 text-center transition-colors ${
            isDragging ? "border-blue-400 bg-blue-50" : "border-gray-300 bg-white"
          }`}
        >
          {uploadProgress ? (
            <div className="flex flex-col items-center gap-2">
              <svg className="animate-spin h-8 w-8 text-blue-500" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
              </svg>
              <p className="text-sm text-blue-600 font-medium">Mengunggah dokumen…</p>
            </div>
          ) : (
            <>
              <svg className="w-10 h-10 text-gray-400 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                  d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                />
              </svg>
              <p className="text-sm font-medium text-gray-700 mb-1">
                Seret file ke sini atau
              </p>
              <label htmlFor="file-upload" className="cursor-pointer">
                <span className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors">
                  Pilih File
                </span>
              </label>
              <p className="mt-2 text-xs text-gray-400">PDF, PNG, JPG, JPEG • Maks 25 MB</p>
            </>
          )}
          {uploadError && (
            <p role="alert" className="mt-3 text-sm text-red-600">{uploadError}</p>
          )}
          <input
            ref={fileInputRef}
            id="file-upload"
            type="file"
            accept=".pdf,.png,.jpg,.jpeg"
            className="sr-only"
            onChange={handleFileChange}
            disabled={uploading}
          />
        </div>

        {/* Error */}
        {error && (
          <div role="alert" className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 border border-red-200 flex items-center justify-between">
            <span>{error}</span>
            <button onClick={() => setError(null)} className="ml-2 underline">Tutup</button>
          </div>
        )}

        {/* Document list */}
        {loading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-16 rounded-xl bg-white border border-gray-200 animate-pulse" />
            ))}
          </div>
        ) : documents.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-gray-400">Belum ada dokumen. Upload sekarang.</p>
          </div>
        ) : (
          <ul className="space-y-2" aria-label="Daftar dokumen">
            {documents.map((doc) => {
              const status = STATUS_LABEL[doc.ingest_status] ?? { label: doc.ingest_status, className: "bg-gray-100 text-gray-600" };
              const isPending = PENDING_STATUSES.has(doc.ingest_status);
              return (
                <li key={doc.id} className="group flex items-center justify-between rounded-xl bg-white border border-gray-200 px-4 py-3 hover:shadow-sm transition-all">
                  <div className="flex items-center gap-3 min-w-0 flex-1">
                    {/* File icon */}
                    <div className="w-9 h-9 bg-red-50 rounded-lg flex items-center justify-center shrink-0">
                      <svg className="w-5 h-5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                          d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                        />
                      </svg>
                    </div>
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-gray-800">{doc.original_filename}</p>
                      <p className="text-xs text-gray-400 mt-0.5">
                        {formatBytes(doc.file_size_bytes)}
                        {doc.page_count ? ` • ${doc.page_count} hal.` : ""}
                      </p>
                    </div>
                  </div>

                  <div className="ml-4 flex items-center gap-2 shrink-0">
                    {/* Spinner untuk dokumen yang sedang diproses */}
                    {isPending && (
                      <svg className="animate-spin h-3.5 w-3.5 text-blue-400" viewBox="0 0 24 24" fill="none">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                      </svg>
                    )}
                    <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${status.className}`}>
                      {status.label}
                    </span>
                    {(doc.ingest_status === "failed" || doc.ingest_status === "needs_review") && (
                      <button
                        onClick={() => handleReprocess(doc.id)}
                        className="text-xs text-blue-600 hover:underline"
                        aria-label={`Proses ulang ${doc.original_filename}`}
                      >
                        Proses ulang
                      </button>
                    )}
                    <button
                      onClick={() => handleDelete(doc.id, doc.original_filename)}
                      className="text-xs text-red-400 hover:text-red-600 opacity-0 group-hover:opacity-100 transition-opacity"
                      aria-label={`Hapus ${doc.original_filename}`}
                    >
                      Hapus
                    </button>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </main>
    </div>
  );
}
