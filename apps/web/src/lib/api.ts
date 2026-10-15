/**
 * API client terpusat.
 *
 * Auth strategy (dual mode):
 * - Cookie HttpOnly: diset oleh backend saat login, dikirim browser otomatis
 * - Bearer token: disimpan di memory untuk Swagger/tools, BUKAN localStorage
 *
 * Browser production: cookie saja (lebih aman XSS)
 * API client / Swagger: Bearer header
 */

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

// Token in-memory — hanya untuk fallback API client, tidak persisten
let _token: string | null = null;

export function setToken(token: string | null): void {
  _token = token;
}

export function getToken(): string | null {
  return _token;
}

export function clearAuth(): void {
  _token = null;
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...options.headers,
  };

  // Kirim Bearer hanya jika ada — cookie dikirim otomatis oleh browser
  if (_token) {
    headers["Authorization"] = `Bearer ${_token}`;
  }

  const response = await fetch(`${API_BASE}${path}`, {
    method: options.method ?? "GET",
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
    credentials: "include", // penting: sertakan cookie HttpOnly
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: response.statusText }));
    throw new ApiError(response.status, errorData.detail ?? "Terjadi kesalahan");
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// ── Auth ──────────────────────────────────────────────────────────────────

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface UserProfile {
  id: string;
  email: string;
  full_name: string | null;
  role: string;
  is_active: boolean;
}

export const authApi = {
  login: (email: string, password: string) =>
    request<LoginResponse>("/api/v1/auth/login", {
      method: "POST",
      body: { email, password },
    }),

  logout: () =>
    request<void>("/api/v1/auth/logout", { method: "POST" }),

  me: () => request<UserProfile>("/api/v1/auth/me"),
};

// ── Chat ──────────────────────────────────────────────────────────────────

export interface SourceItem {
  document_id: string;
  document_name: string;
  page: number | null;
  chunk_id: string;
  relevance_score: number | null;
}

export interface ChatResponse {
  conversation_id: string;
  message_id: string;
  answer: string;
  sources: SourceItem[];
  status: string;
}

export interface ConversationSummary {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
}

export interface MessageOut {
  id: string;
  role: string;
  content: string;
  created_at: string;
  sources: SourceItem[];
}

export interface ConversationDetail extends ConversationSummary {
  messages: MessageOut[];
}

export const chatApi = {
  sendMessage: (question: string, conversationId?: string) =>
    request<ChatResponse>("/api/v1/chat", {
      method: "POST",
      body: { question, conversation_id: conversationId ?? null },
    }),

  listConversations: (page = 1, pageSize = 20) =>
    request<ConversationSummary[]>(
      `/api/v1/chat/conversations?page=${page}&page_size=${pageSize}`
    ),

  getConversation: (id: string) =>
    request<ConversationDetail>(`/api/v1/chat/conversations/${id}`),

  deleteConversation: (id: string) =>
    request<void>(`/api/v1/chat/conversations/${id}`, { method: "DELETE" }),
};

// ── Documents ─────────────────────────────────────────────────────────────

export interface DocumentOut {
  id: string;
  original_filename: string;
  file_size_bytes: number;
  mime_type: string;
  ingest_status: string;
  page_count: number | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentListResponse {
  items: DocumentOut[];
  total: number;
  page: number;
  page_size: number;
}

export const documentApi = {
  upload: async (file: File) => {
    const formData = new FormData();
    formData.append("file", file);

    const headers: Record<string, string> = {};
    if (_token) headers["Authorization"] = `Bearer ${_token}`;

    const response = await fetch(`${API_BASE}/api/v1/documents`, {
      method: "POST",
      headers,
      body: formData,
      credentials: "include", // cookie
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: response.statusText }));
      throw new ApiError(response.status, err.detail ?? "Upload gagal");
    }
    return response.json();
  },

  list: (page = 1, pageSize = 20) =>
    request<DocumentListResponse>(
      `/api/v1/documents?page=${page}&page_size=${pageSize}`
    ),

  get: (id: string) => request<DocumentOut>(`/api/v1/documents/${id}`),

  delete: (id: string) =>
    request<void>(`/api/v1/documents/${id}`, { method: "DELETE" }),

  reprocess: (id: string) =>
    request<{ message: string }>(`/api/v1/documents/${id}/reprocess`, {
      method: "POST",
    }),
};
