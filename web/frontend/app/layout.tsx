import { Analytics } from "@vercel/analytics/react";
import type { Metadata } from "next";
import Link from "next/link";
import React from "react";
import { CapabilityNav, CapabilityProvider } from "../components/CapabilityNav";
import { ThemeToggle } from "../components/ThemeToggle";
import "./globals.css";

/** Đặt theme tối/sớm trước khi hydrate để tránh nhấp nháy giao diện. */
const themeInitScript = `(function(){try{var t=localStorage.getItem('vh-theme');var d=t?t==='dark':window.matchMedia('(prefers-color-scheme: dark)').matches;if(d)document.documentElement.classList.add('dark');}catch(e){}})()`;

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://vietnamese-humanizer-g1o9.vercel.app";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "Vietnamese Writing Skills - Rà soát & Gọt giũa Văn phong Tiếng Việt",
    template: "%s | Vietnamese Writing Skills",
  },
  description:
    "Công cụ rà soát và gợi ý gọt giũa văn phong tiếng Việt cho người viết và biên tập viên. Nêu tín hiệu sáo rỗng, gọt dịch thuật ngữ và gợi ý viết lại tự nhiên.",
  keywords: [
    "rà soát văn phong tiếng việt",
    "gọt giũa văn phong",
    "humanizer tiếng việt",
    "kiểm tra văn phong",
    "linter tiếng việt",
    "gọt dịch thuật ngữ",
    "quy chuẩn báo chí",
    "agent skills tiếng việt",
  ],
  authors: [{ name: "Vietnamese Writing Skills Team" }],
  creator: "Vietnamese Writing Skills",
  publisher: "Vietnamese Writing Skills",
  formatDetection: {
    email: false,
    address: false,
    telephone: false,
  },
  alternates: {
    canonical: "/",
  },
  openGraph: {
    title: "Vietnamese Writing Skills - Công cụ Rà soát & Gọt giũa Văn phong Tiếng Việt",
    description:
      "Công cụ trực tuyến hỗ trợ người viết và biên tập viên rà soát lỗi sáo rỗng, gọt dịch thuật ngữ và viết lại tiếng Việt tự nhiên bằng AI.",
    url: siteUrl,
    siteName: "Vietnamese Writing Skills",
    locale: "vi_VN",
    type: "website",
    images: [
      {
        url: "/og-image.jpg",
        width: 1200,
        height: 675,
        alt: "Vietnamese Writing Skills banner",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Vietnamese Writing Skills - Công cụ Rà soát & Gọt giũa Văn phong Tiếng Việt",
    description:
      "Công cụ trực tuyến hỗ trợ người viết và biên tập viên rà soát lỗi sáo rỗng, gọt dịch thuật ngữ và viết lại tiếng Việt tự nhiên bằng AI.",
    images: ["/og-image.jpg"],
  },
  icons: {
    icon: "/favicon.png",
    shortcut: "/favicon.png",
    apple: "/apple-icon.png",
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
};

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "WebApplication",
  name: "Vietnamese Writing Skills",
  url: siteUrl,
  applicationCategory: "BusinessApplication",
  operatingSystem: "All",
  offers: {
    "@type": "Offer",
    price: "0",
    priceCurrency: "VND",
  },
  description:
    "Công cụ rà soát và gợi ý gọt giũa văn phong tiếng Việt cho người viết và biên tập viên dựa trên bộ Agent Skills.",
  inLanguage: "vi-VN",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="vi" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
      </head>
<body className="min-h-[100dvh] flex flex-col bg-page text-ink font-sans antialiased selection:bg-green-100 selection:text-green-900 dark:selection:bg-green-950 dark:selection:text-green-100">
        {/* Nền aurora trang trí — thuần CSS, không tương tác */}
        <div
          aria-hidden="true"
          className="pointer-events-none fixed inset-0 -z-10 overflow-hidden"
        >
          <div className="absolute -top-40 -left-32 h-[26rem] w-[26rem] rounded-full bg-green-400/20 dark:bg-green-500/10 blur-3xl animate-float" />
          <div className="absolute top-1/3 -right-40 h-[30rem] w-[30rem] rounded-full bg-emerald-400/15 dark:bg-emerald-500/10 blur-3xl animate-float-slow" />
          <div className="absolute -bottom-24 left-1/3 h-96 w-96 rounded-full bg-teal-400/10 dark:bg-teal-500/10 blur-3xl" />
        </div>
        <CapabilityProvider>
          {/* Frosted Glass Header */}
          <header className="sticky top-0 z-50 glass border-x-0 border-t-0 transition-all">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
              <Link href="/" className="flex items-center space-x-3 group">
                <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-green-600 via-emerald-500 to-teal-400 flex items-center justify-center text-white shadow-glow-sm group-hover:scale-105 group-active:scale-95 transition-transform">
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456z" />
                  </svg>
                </div>
                <div className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-2">
                  <span className="font-extrabold text-ink tracking-tight text-base sm:text-lg group-hover:text-green-700 dark:group-hover:text-green-400 transition-colors">
                    Vietnamese Writing Skills
                  </span>
                </div>
              </Link>

              <div className="flex items-center gap-2.5">
                <CapabilityNav />
                <ThemeToggle />
              </div>
            </div>
          </header>

          <main className="flex-grow max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
            {children}
          </main>

          {/* Footer */}
          <footer className="glass border-x-0 border-b-0 py-8 mt-16 text-center text-xs text-muted">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row items-center justify-between gap-4">
              <p className="text-muted max-w-2xl text-center md:text-right">
                Công cụ nhận diện tín hiệu văn phong cho người viết và biên tập viên. Không chấm điểm xác suất AI, không suy đoán tác giả.
              </p>
            </div>
          </footer>
        </CapabilityProvider>
        <Analytics />
      </body>
    </html>
  );
}
