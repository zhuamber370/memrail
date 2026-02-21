/* eslint-disable react/jsx-no-bind */
"use client";

import { useState } from "react";

import { apiGet, apiPost } from "../../src/lib/api";
import { useI18n } from "../../src/i18n";

type Note = { id: string; title: string; created_at?: string; updated_at?: string };
type NoteList = { items: Array<Record<string, unknown>>; page: number; page_size: number; total: number };

export default function KnowledgePage() {
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [source, setSource] = useState("ui://knowledge");
  const [notes, setNotes] = useState<Array<Record<string, unknown>>>([]);
  const [error, setError] = useState("");
  const { t } = useI18n();

  async function onAppend() {
    setError("");
    try {
      await apiPost<Note>("/api/v1/notes/append", {
        title,
        body,
        sources: [{ type: "text", value: source }],
        tags: []
      });
      setTitle("");
      setBody("");
      await onSearch();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function onSearch() {
    setError("");
    try {
      const listed = await apiGet<NoteList>("/api/v1/notes/search?page=1&page_size=20");
      setNotes(listed.items);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <section className="card">
      <h1 className="h1">{t("knowledge.title")}</h1>
      <p className="meta">{t("knowledge.subtitle")}</p>
      <input
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder={t("knowledge.placeholderTitle")}
        style={{ width: "100%", marginTop: 10, border: "2px solid var(--line)", borderRadius: 10, padding: 10 }}
      />
      <textarea
        value={body}
        onChange={(e) => setBody(e.target.value)}
        rows={5}
        placeholder={t("knowledge.placeholderBody")}
        style={{ width: "100%", marginTop: 10, border: "2px solid var(--line)", borderRadius: 10, padding: 10 }}
      />
      <input
        value={source}
        onChange={(e) => setSource(e.target.value)}
        placeholder={t("knowledge.placeholderSource")}
        style={{ width: "100%", marginTop: 10, border: "2px solid var(--line)", borderRadius: 10, padding: 10 }}
      />
      <div className="badges">
        <button className="badge" onClick={onAppend} disabled={!title.trim() || !body.trim()}>
          {t("knowledge.append")}
        </button>
        <button className="badge" onClick={onSearch}>{t("knowledge.search")}</button>
      </div>
      {error ? <p className="meta" style={{ color: "var(--danger)" }}>{error}</p> : null}
      <pre style={{ marginTop: 12, background: "#fff", border: "2px solid var(--line)", borderRadius: 10, padding: 10, overflowX: "auto" }}>
{JSON.stringify(notes, null, 2)}
      </pre>
    </section>
  );
}
