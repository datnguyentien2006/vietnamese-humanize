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
            ? "px-3 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-700 text-white font-semibold shadow-sm shadow-sky-600/20 transition-all"
            : "px-3 py-1.5 rounded-lg text-slate-600 hover:text-sky-600 hover:bg-slate-100/80 transition-all"
        }
      >
        Humanize văn bản
      </Link>
      {capabilities.contributions && (
        <Link
          href="/contribute"
          className="px-3.5 py-1.5 bg-sky-600 hover:bg-sky-700 text-white rounded-lg font-semibold shadow-sm shadow-sky-600/20 active:scale-[0.98] transition-all flex items-center space-x-1.5"
        >
          <svg
            className="w-4 h-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2.5}
            aria-hidden="true"
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          <span>Góp mẫu văn bản</span>
        </Link>
      )}
    </nav>
  );
}
