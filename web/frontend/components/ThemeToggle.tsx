"use client";

import React, { useCallback, useSyncExternalStore } from "react";

/**
 * Nút chuyển giao diện sáng/tối.
 * Theme được khởi tạo sớm bằng script inline trong layout (tránh nhấp nháy),
 * component này đọc trạng thái từ documentElement qua useSyncExternalStore
 * và ghi lại lựa chọn vào localStorage.
 */
const STORAGE_KEY = "vh-theme";

const themeStore = {
  listeners: new Set<() => void>(),
  subscribe(listener: () => void): () => void {
    themeStore.listeners.add(listener);
    return () => {
      themeStore.listeners.delete(listener);
    };
  },
  emit() {
    themeStore.listeners.forEach((l) => l());
  },
};

function getSnapshot(): boolean {
  return document.documentElement.classList.contains("dark");
}

function getServerSnapshot(): boolean {
  // Trên server (và lúc hydrate) chưa biết theme → icon mặc định mặt trăng,
  // re-render ngay sau hydrate sẽ hiển thị đúng trạng thái.
  return false;
}

export function ThemeToggle() {
  const dark = useSyncExternalStore(
    themeStore.subscribe,
    getSnapshot,
    getServerSnapshot
  );

  const toggle = useCallback(() => {
    const next = !getSnapshot();
    document.documentElement.classList.toggle("dark", next);
    try {
      window.localStorage.setItem(STORAGE_KEY, next ? "dark" : "light");
    } catch {
      // localStorage có thể bị chặn — bỏ qua, theme chỉ sống trong phiên.
    }
    themeStore.emit();
  }, []);

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={dark ? "Chuyển sang giao diện sáng" : "Chuyển sang giao diện tối"}
      title={dark ? "Giao diện sáng" : "Giao diện tối"}
      className="inline-flex h-9 w-9 items-center justify-center rounded-xl border border-line bg-card text-muted hover:text-ink hover:border-green-400 dark:hover:border-green-700 hover:shadow-sm active:scale-95 transition-all"
    >
      {dark ? (
        // Mặt trời — đang ở giao diện tối, bấm để quay lại sáng
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} strokeLinecap="round">
          <circle cx="12" cy="12" r="4" />
          <path d="M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.4 5.4l1.4 1.4M17.2 17.2l1.4 1.4M5.4 18.6l1.4-1.4M17.2 6.8l1.4-1.4" />
        </svg>
      ) : (
        // Mặt trăng — đang ở giao diện sáng, bấm để chuyển sang tối
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} strokeLinejoin="round">
          <path d="M20.25 14.15A8.25 8.25 0 0 1 9.85 3.75a8.25 8.25 0 1 0 10.4 10.4z" />
        </svg>
      )}
    </button>
  );
}
