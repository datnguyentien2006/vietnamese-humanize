"use client";

import Link from "next/link";
import React, { createContext, useContext, useEffect, useState } from "react";
import { fetchHealth } from "../lib/api";
import { HealthResponse } from "../lib/types";

type Capabilities = HealthResponse["capabilities"];

interface CapabilitiesState {
  capabilities: Capabilities;
  /** True khi đã có kết quả từ /api/health (thành công hoặc lỗi mạng). */
  loaded: boolean;
}

const disabledCapabilities: Capabilities = { humanize: false, contributions: false };

const initialCapabilitiesState: CapabilitiesState = {
  capabilities: disabledCapabilities,
  loaded: false,
};

const CapabilityContext = createContext<CapabilitiesState>(initialCapabilitiesState);

export function CapabilityProvider({ children }: { children: React.ReactNode }) {
  const [capabilities, setCapabilities] = useState<Capabilities>(disabledCapabilities);
  const [loaded, setLoaded] = useState<boolean>(false);

  useEffect(() => {
    let active = true;

    fetchHealth()
      .then((health) => {
        if (!active) return;

        setCapabilities({
          humanize: health.capabilities.humanize === true,
          contributions: health.capabilities.contributions === true,
        });
        setLoaded(true);
      })
      .catch(() => {
        // Optional features remain disabled when health is unavailable.
        if (!active) return;
        setLoaded(true);
      });

    return () => {
      active = false;
    };
  }, []);

  return (
    <CapabilityContext.Provider value={{ capabilities, loaded }}>
      {children}
    </CapabilityContext.Provider>
  );
}

export function useCapabilities(): Capabilities {
  return useContext(CapabilityContext).capabilities;
}

/** Dùng khi cần biết health đã load xong hay chưa (vd: gate tính năng). */
export function useCapabilitiesStatus(): CapabilitiesState {
  return useContext(CapabilityContext);
}

export function CapabilityNav() {
  const capabilities = useCapabilities();

  return (
    <nav
      className="flex items-center space-x-3 text-xs sm:text-sm font-medium"
      aria-label="Điều hướng chính"
    >
      <Link
        href="/"
        className={
          capabilities.humanize === true
            ? "px-3 py-1.5 rounded-lg bg-gradient-to-r from-green-600 to-emerald-500 hover:from-green-500 hover:to-teal-400 text-white font-semibold shadow-glow-sm active:scale-[0.98] transition-all"
            : "px-3 py-1.5 rounded-lg text-muted hover:text-ink hover:bg-soft active:scale-[0.98] transition-all"
        }
      >
        Humanize văn bản
      </Link>
      {capabilities.contributions && (
        <Link
          href="/contribute"
          className="px-3.5 py-1.5 bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-500 hover:to-teal-400 text-white rounded-lg font-semibold shadow-glow-sm active:scale-[0.98] transition-all flex items-center space-x-1.5"
        >
          <svg
            className="w-4 h-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
            aria-hidden="true"
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
          </svg>
          <span>Góp mẫu văn bản</span>
        </Link>
      )}
    </nav>
  );
}
