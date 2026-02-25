"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import { useI18n } from "../i18n";

const links = [
  { href: "/ideas", key: "nav.ideas" },
  { href: "/routes", key: "nav.routes" },
  { href: "/tasks", key: "nav.tasks" },
  { href: "/knowledge", key: "nav.knowledge" },
  { href: "/changes", key: "nav.changes" }
] as const;

export function AppShell({ children }: { children: ReactNode }) {
  const { lang, setLang, t } = useI18n();

  return (
    <div className="shell">
      <aside className="rail">
        <div className="brand">MEMRAIL / AGENT-FIRST</div>
        <div className="badges" style={{ marginTop: 6, marginBottom: 10 }}>
          <button
            className="badge"
            onClick={() => setLang("en")}
            aria-pressed={lang === "en"}
            style={{ borderColor: lang === "en" ? "var(--focus)" : undefined }}
          >
            {t("lang.en")}
          </button>
          <button
            className="badge"
            onClick={() => setLang("zh")}
            aria-pressed={lang === "zh"}
            style={{ borderColor: lang === "zh" ? "var(--focus)" : undefined }}
          >
            {t("lang.zh")}
          </button>
        </div>
        {links.map((link) => (
          <Link key={link.href} href={link.href} className="navLink">
            {t(link.key)}
          </Link>
        ))}
      </aside>
      <main className="main">{children}</main>
    </div>
  );
}
