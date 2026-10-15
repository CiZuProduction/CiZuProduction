"use client";

import { useRouter, usePathname } from "next/navigation";
import { logout } from "@/hooks/useAuth";
import { authApi } from "@/lib/api";

interface NavbarProps {
  conversationId?: string;
  onNewChat?: () => void;
}

export function Navbar({ conversationId, onNewChat }: NavbarProps) {
  const router = useRouter();
  const pathname = usePathname();

  const navLinks = [
    { href: "/chat", label: "Chat" },
    { href: "/documents", label: "Dokumen" },
    { href: "/history", label: "Riwayat" },
    { href: "/dashboard", label: "Dashboard" },
  ];

  return (
    <header className="flex items-center justify-between border-b border-gray-200 bg-white px-4 py-3 shadow-sm">
      <div className="flex items-center gap-3">
        <a href="/chat" className="text-base font-semibold text-gray-900 hover:text-blue-600 transition-colors">
          AI Chatbot
        </a>
        {conversationId && (
          <span className="text-xs text-gray-400 font-mono hidden sm:block">
            {conversationId.slice(0, 8)}…
          </span>
        )}
      </div>

      <nav className="flex items-center gap-1" aria-label="Navigasi utama">
        {navLinks.map((link) => (
          <a
            key={link.href}
            href={link.href}
            className={`rounded-lg px-3 py-1.5 text-sm transition-colors ${
              pathname === link.href
                ? "bg-blue-50 text-blue-600 font-medium"
                : "text-gray-600 hover:bg-gray-100"
            }`}
          >
            {link.label}
          </a>
        ))}

        {onNewChat && (
          <button
            onClick={onNewChat}
            className="rounded-lg px-3 py-1.5 text-sm text-blue-600 hover:bg-blue-50 transition-colors border border-blue-200"
          >
            + Chat baru
          </button>
        )}

        <button
          onClick={() => logout(router)}
          className="rounded-lg px-3 py-1.5 text-sm text-gray-500 hover:bg-gray-100 transition-colors"
          aria-label="Keluar dari akun"
        >
          Keluar
        </button>
      </nav>
    </header>
  );
}
