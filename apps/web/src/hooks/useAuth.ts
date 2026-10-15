"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { authApi, clearAuth } from "@/lib/api";

/**
 * Hook autentikasi.
 * Dengan cookie HttpOnly, browser otomatis mengirim cookie ke API.
 * Kita verifikasi sesi aktif dengan memanggil /auth/me saat mount.
 */
export function useAuth() {
  const router = useRouter();

  useEffect(() => {
    // Verifikasi sesi via API (cookie dikirim otomatis browser)
    authApi.me().catch(() => {
      // Jika /me gagal (401) → sesi tidak valid → redirect ke login
      router.push("/login");
    });
  }, [router]);
}

export async function logout(router: ReturnType<typeof useRouter>) {
  try {
    await authApi.logout();
  } catch {
    // Tetap logout meski request gagal
  }
  clearAuth();
  router.push("/login");
}
