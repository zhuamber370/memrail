/* eslint-disable react/jsx-no-bind */
"use client";

import { useEffect, useState } from "react";

import { apiDelete, apiGet, apiPatch, apiPost } from "../../src/lib/api";
import { formatDateTime } from "../../src/lib/datetime";
import { useI18n } from "../../src/i18n";

type KnowledgeStatus = "active" | "archived";
type KnowledgeCategory = "ops_manual" | "mechanism_spec" | "decision_record";

type KnowledgeItem = {
  id: string;
  title: string;
  body: string;
  category: KnowledgeCategory;
  status: KnowledgeStatus;
  created_at?: string;
  updated_at?: string;
};

type KnowledgeList = {
  items: KnowledgeItem[];
  page: number;
  page_size: number;
  total: number;
};

export default function KnowledgePage() {
  const { t, lang } = useI18n();

  const [items, setItems] = useState<KnowledgeItem[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedDetail, setSelectedDetail] = useState<KnowledgeItem | null>(null);

  const [statusFilter, setStatusFilter] = useState<KnowledgeStatus>("active");
  const [categoryFilter, setCategoryFilter] = useState<KnowledgeCategory | "all">("all");
  const [searchQuery, setSearchQuery] = useState("");

  const [createTitle, setCreateTitle] = useState("");
  const [createBody, setCreateBody] = useState("");
  const [createCategory, setCreateCategory] = useState<KnowledgeCategory | "auto">("auto");

  const [detailTitle, setDetailTitle] = useState("");
  const [detailBody, setDetailBody] = useState("");
  const [detailCategory, setDetailCategory] = useState<KnowledgeCategory>("mechanism_spec");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    void onRefreshList();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter, categoryFilter, searchQuery]);

  function formatTime(value?: string): string {
    return formatDateTime(value, lang);
  }

  function previewBody(body: string): string {
    const text = body.trim().replace(/\s+/g, " ");
    if (text.length <= 120) return text;
    return `${text.slice(0, 117)}...`;
  }

  function categoryLabel(category: KnowledgeCategory): string {
    return t(`knowledge.category.${category}`);
  }

  function hydrateDetailForm(detail: KnowledgeItem) {
    setDetailTitle(detail.title);
    setDetailBody(detail.body);
    setDetailCategory(detail.category);
  }

  async function onLoadDetail(itemId: string) {
    const detail = await apiGet<KnowledgeItem>(`/api/v1/knowledge/${itemId}`);
    setSelectedDetail(detail);
    hydrateDetailForm(detail);
  }

  async function onRefreshList(preferredId?: string) {
    setError("");
    setNotice("");
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: "1",
        page_size: "100",
        status: statusFilter,
      });
      if (categoryFilter !== "all") params.set("category", categoryFilter);
      if (searchQuery.trim()) params.set("q", searchQuery.trim());

      const listed = await apiGet<KnowledgeList>(`/api/v1/knowledge?${params.toString()}`);
      setItems(listed.items);
      const nextId =
        preferredId && listed.items.some((item) => item.id === preferredId)
          ? preferredId
          : selectedId && listed.items.some((item) => item.id === selectedId)
            ? selectedId
            : listed.items[0]?.id ?? null;
      setSelectedId(nextId);
      if (nextId) {
        await onLoadDetail(nextId);
      } else {
        setSelectedDetail(null);
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function onCreateKnowledge() {
    if (!createTitle.trim() || !createBody.trim()) {
      setError(t("knowledge.errValidation"));
      return;
    }
    setError("");
    setNotice("");
    setLoading(true);
    try {
      const created = await apiPost<KnowledgeItem>("/api/v1/knowledge", {
        title: createTitle.trim(),
        body: createBody.trim(),
        ...(createCategory === "auto" ? {} : { category: createCategory }),
      });
      setCreateTitle("");
      setCreateBody("");
      setCreateCategory("auto");
      setNotice(t("knowledge.noticeCreated"));
      await onRefreshList(created.id);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function onSaveDetail() {
    if (!selectedDetail || selectedDetail.status === "archived") return;
    if (!detailTitle.trim() || !detailBody.trim()) {
      setError(t("knowledge.errValidation"));
      return;
    }
    setError("");
    setNotice("");
    setLoading(true);
    try {
      await apiPatch<KnowledgeItem>(`/api/v1/knowledge/${selectedDetail.id}`, {
        title: detailTitle.trim(),
        body: detailBody.trim(),
        category: detailCategory,
      });
      setNotice(t("knowledge.noticeUpdated"));
      await onRefreshList(selectedDetail.id);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function onArchiveSelected() {
    if (!selectedDetail || selectedDetail.status === "archived") return;
    setError("");
    setNotice("");
    setLoading(true);
    try {
      await apiPost<KnowledgeItem>(`/api/v1/knowledge/${selectedDetail.id}/archive`, {});
      setNotice(t("knowledge.noticeArchived"));
      await onRefreshList(selectedDetail.id);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function onDeleteSelected() {
    if (!selectedDetail) return;
    if (!window.confirm(t("knowledge.confirmDelete"))) return;
    setError("");
    setNotice("");
    setLoading(true);
    try {
      await apiDelete(`/api/v1/knowledge/${selectedDetail.id}`);
      setNotice(t("knowledge.noticeDeleted"));
      await onRefreshList();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="card knowledgeBoard">
      <div className="knowledgeHero">
        <div>
          <h1 className="h1">{t("knowledge.title")}</h1>
          <p className="meta">{t("knowledge.subtitle")}</p>
        </div>
        <div className="knowledgeHeroFilters">
          <input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={t("knowledge.placeholderSearch")}
            className="taskInput"
          />
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value as KnowledgeCategory | "all")}
            className="taskInput"
          >
            <option value="all">{t("knowledge.categoryAll")}</option>
            <option value="ops_manual">{t("knowledge.category.ops_manual")}</option>
            <option value="mechanism_spec">{t("knowledge.category.mechanism_spec")}</option>
            <option value="decision_record">{t("knowledge.category.decision_record")}</option>
          </select>
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as KnowledgeStatus)} className="taskInput">
            <option value="active">{t("knowledge.statusActive")}</option>
            <option value="archived">{t("knowledge.statusArchived")}</option>
          </select>
        </div>
      </div>

      <div className="knowledgeCreate">
        <input
          value={createTitle}
          onChange={(e) => setCreateTitle(e.target.value)}
          placeholder={t("knowledge.placeholderTitle")}
          className="taskInput"
        />
        <textarea
          value={createBody}
          onChange={(e) => setCreateBody(e.target.value)}
          rows={4}
          placeholder={t("knowledge.placeholderBody")}
          className="taskInput taskTextArea knowledgeCreateBody"
        />
        <select
          value={createCategory}
          onChange={(e) => setCreateCategory(e.target.value as KnowledgeCategory | "auto")}
          className="taskInput"
        >
          <option value="auto">{t("knowledge.categoryAuto")}</option>
          <option value="ops_manual">{t("knowledge.category.ops_manual")}</option>
          <option value="mechanism_spec">{t("knowledge.category.mechanism_spec")}</option>
          <option value="decision_record">{t("knowledge.category.decision_record")}</option>
        </select>
        <button className="badge" onClick={onCreateKnowledge} disabled={loading}>
          {t("knowledge.create")}
        </button>
      </div>

      <div className="knowledgeLayout" style={{ gridTemplateColumns: "1fr 1.3fr" }}>
        <div className="knowledgeListPanel">
          {error ? <p className="meta" style={{ color: "var(--danger)", marginTop: 8 }}>{error}</p> : null}
          {notice ? <p className="meta" style={{ color: "var(--success)", marginTop: 8 }}>{notice}</p> : null}
          <div className="knowledgeList">
            {items.map((item) => (
              <div
                key={item.id}
                className={`knowledgeRow ${selectedId === item.id ? "knowledgeRowActive" : ""}`}
                onClick={() => {
                  setSelectedId(item.id);
                  void onLoadDetail(item.id);
                }}
                >
                <div className="knowledgeRowMain">
                  <div className="knowledgeTitle">
                    <span className="badge" style={{ marginRight: 8 }}>{categoryLabel(item.category)}</span>
                    {item.title}
                  </div>
                  <div className="knowledgeMeta">
                    <span>{previewBody(item.body) || "-"}</span>
                    <span>{t("knowledge.updated")}: {formatTime(item.updated_at)}</span>
                  </div>
                </div>
              </div>
            ))}
            {!items.length ? <p className="meta">{t("knowledge.emptyList")}</p> : null}
          </div>
        </div>

        <aside className="knowledgeDetail">
          <h2 className="changesSubTitle">{t("knowledge.detail")}</h2>
          {selectedDetail ? (
            <div className="knowledgeDetailContent">
              <div className="knowledgeDetailTitle">{selectedDetail.title}</div>
              <div className="meta">{selectedDetail.id}</div>
              <div className="taskDetailGrid">
                <div>
                  <div className="changesSummaryKey">{t("knowledge.updated")}</div>
                  <div className="changesLedgerText">{formatTime(selectedDetail.updated_at)}</div>
                </div>
                <div>
                  <div className="changesSummaryKey">{t("knowledge.category")}</div>
                  <div className="changesLedgerText">{categoryLabel(selectedDetail.category)}</div>
                </div>
              </div>

              {selectedDetail.status === "archived" ? (
                <>
                  <p className="changesLedgerText" style={{ whiteSpace: "pre-wrap" }}>{selectedDetail.body}</p>
                  <p className="meta">{t("knowledge.readOnlyHint")}</p>
                  <div className="taskDetailFormActions" style={{ marginTop: 10 }}>
                    <button className="badge" onClick={onDeleteSelected} disabled={loading}>{t("knowledge.delete")}</button>
                  </div>
                </>
              ) : (
                <div className="knowledgeEdit">
                  <label className="taskField">
                    <span>{t("knowledge.titleField")}</span>
                    <input value={detailTitle} onChange={(e) => setDetailTitle(e.target.value)} className="taskInput" />
                  </label>
                  <label className="taskField">
                    <span>{t("knowledge.body")}</span>
                    <textarea
                      value={detailBody}
                      onChange={(e) => setDetailBody(e.target.value)}
                      className="taskInput taskTextArea"
                      rows={10}
                    />
                  </label>
                  <label className="taskField">
                    <span>{t("knowledge.category")}</span>
                    <select
                      value={detailCategory}
                      onChange={(e) => setDetailCategory(e.target.value as KnowledgeCategory)}
                      className="taskInput"
                    >
                      <option value="ops_manual">{t("knowledge.category.ops_manual")}</option>
                      <option value="mechanism_spec">{t("knowledge.category.mechanism_spec")}</option>
                      <option value="decision_record">{t("knowledge.category.decision_record")}</option>
                    </select>
                  </label>
                  <div className="taskDetailFormActions">
                    <button className="badge" onClick={onSaveDetail} disabled={loading}>{t("knowledge.save")}</button>
                    <button className="badge" onClick={onArchiveSelected} disabled={loading}>{t("knowledge.archive")}</button>
                    <button className="badge" onClick={onDeleteSelected} disabled={loading}>{t("knowledge.delete")}</button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <p className="meta">{t("knowledge.emptyDetail")}</p>
          )}
        </aside>
      </div>
    </section>
  );
}
