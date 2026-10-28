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
      className="inline-flex h-9 w-9 items-center justify-center rounded-xl border border-line bg-card text-muted hover:text-ink hover:border-sky-300 dark:hover:border-sky-700 hover:shadow-sm active:scale-95 transition-all"
    >
      {dark ? (
        // Mặt trời — đang ở giao diện tối, bấm để quay lại sáng
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M12 3v2.25m6.364.386l-1.591 1.591M21 12h-2.25m-.386 6.364l-1.591-1.591M12 18.75V21m-4.773-4.227l-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0z"
          />
        </svg>
      ) : (
        // Mặt trăng — đang ở giao diện sáng, bấm để chuyển sang tối
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M21.752 15.002A9.72 9.72 0 0 1 18 15.75c-5.385 0-9.75-4.365-9.75-9.75 0-1.33.266-2.597.748-3.752A9.753 9.753 0 0 0 3 11.25C3 16.635 7.365 21 12.75 21a9.753 9.753 0 0 0 9.002-5.998z"
          />
        </svg>
      )}
    </button>
  );
}
