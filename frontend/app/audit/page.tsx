/* eslint-disable react/jsx-no-bind */
"use client";

import { useState } from "react";

import { apiGet } from "../../src/lib/api";
import { useI18n } from "../../src/i18n";

type AuditList = {
  items: Array<Record<string, unknown>>;
  page: number;
  page_size: number;
  total: number;
};

export default function AuditPage() {
  const [events, setEvents] = useState<Array<Record<string, unknown>>>([]);
  const [error, setError] = useState("");
  const { t } = useI18n();

  async function onLoad() {
    setError("");
    try {
      const data = await apiGet<AuditList>("/api/v1/audit/events?page=1&page_size=20");
      setEvents(data.items);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <section className="card">
      <h1 className="h1">{t("audit.title")}</h1>
      <p className="meta">{t("audit.subtitle")}</p>
      <div className="badges">
        <button className="badge" onClick={onLoad}>{t("audit.load")}</button>
      </div>
      {error ? <p className="meta" style={{ color: "var(--danger)" }}>{error}</p> : null}
      <pre style={{ marginTop: 12, background: "#fff", border: "2px solid var(--line)", borderRadius: 10, padding: 10, overflowX: "auto" }}>
{JSON.stringify(events, null, 2)}
      </pre>
    </section>
  );
}
