/* eslint-disable react/jsx-no-bind */
"use client";

import { useEffect, useMemo, useState } from "react";

import { apiDelete, apiGet, apiPatch, apiPost } from "../../src/lib/api";
import { useI18n } from "../../src/i18n";

type KnowledgeType = "playbook" | "decision" | "brief";
type KnowledgeStatus = "active" | "archived";

type Topic = {
  id: string;
  name: string;
  name_en: string;
  name_zh: string;
  kind: string;
  status: string;
  summary: string;
};
type TopicList = { items: Topic[] };

type KnowledgeListItem = {
  id: string;
  type: KnowledgeType;
  title: string;
  topic_id: string | null;
  tags: string[];
  status: KnowledgeStatus;
  evidence_count: number;
  created_at?: string;
  updated_at?: string;
};
type KnowledgeList = { items: KnowledgeListItem[]; page: number; page_size: number; total: number };

type KnowledgeEvidence = {
  id: string;
  item_id: string;
  source_ref: string;
  excerpt: string;
  created_at?: string;
};

type KnowledgeDetail = KnowledgeListItem & {
  content: Record<string, unknown>;
  evidences: KnowledgeEvidence[];
};

export default function KnowledgePage() {
  const { t, lang } = useI18n();

  const [topics, setTopics] = useState<Topic[]>([]);
  const [items, setItems] = useState<KnowledgeListItem[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedDetail, setSelectedDetail] = useState<KnowledgeDetail | null>(null);

  const [statusFilter, setStatusFilter] = useState<KnowledgeStatus>("active");
  const [typeFilter, setTypeFilter] = useState<KnowledgeType | "all">("all");
  const [topicFilter, setTopicFilter] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [tagQuery, setTagQuery] = useState("");

  const [createType, setCreateType] = useState<KnowledgeType>("playbook");
  const [createTitle, setCreateTitle] = useState("");
  const [createTopicId, setCreateTopicId] = useState("");
  const [createTags, setCreateTags] = useState("");
  const [createSourceRef, setCreateSourceRef] = useState("ui://knowledge");
  const [createExcerpt, setCreateExcerpt] = useState("");
  const [createGoal, setCreateGoal] = useState("");
  const [createSteps, setCreateSteps] = useState("");
  const [createDecision, setCreateDecision] = useState("");
  const [createRationale, setCreateRationale] = useState("");
  const [createSummary, setCreateSummary] = useState("");
  const [createHighlights, setCreateHighlights] = useState("");

  const [detailTitle, setDetailTitle] = useState("");
  const [detailTopicId, setDetailTopicId] = useState("");
  const [detailTags, setDetailTags] = useState("");
  const [detailGoal, setDetailGoal] = useState("");
  const [detailSteps, setDetailSteps] = useState("");
  const [detailDecision, setDetailDecision] = useState("");
  const [detailRationale, setDetailRationale] = useState("");
  const [detailSummary, setDetailSummary] = useState("");
  const [detailHighlights, setDetailHighlights] = useState("");
  const [detailSourceRef, setDetailSourceRef] = useState("ui://knowledge");
  const [detailExcerpt, setDetailExcerpt] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const activeTopics = useMemo(() => topics.filter((topic) => topic.status === "active"), [topics]);

  useEffect(() => {
    void onInit();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    void onRefreshList();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter, typeFilter, topicFilter, searchQuery, tagQuery]);

  function localizeTopicName(topic?: Topic): string {
    if (!topic) return t("knowledge.unclassified");
    const target = lang === "zh" ? topic.name_zh : topic.name_en;
    return target?.trim() || topic.name;
  }

  function parseTags(input: string): string[] {
    return input
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
  }

  function parseLines(input: string): string[] {
    return input
      .split("\n")
      .map((item) => item.trim())
      .filter(Boolean);
  }

  function formatTime(value?: string): string {
    if (!value) return "-";
    try {
      return new Date(value).toLocaleString();
    } catch {
      return value;
    }
  }

  function typeLabel(type: KnowledgeType): string {
    return t(`knowledge.type.${type}`);
  }

  function buildCreateContent(): Record<string, unknown> | null {
    if (createType === "playbook") {
      const steps = parseLines(createSteps);
      if (!createGoal.trim() || !steps.length) return null;
      return { goal: createGoal.trim(), steps };
    }
    if (createType === "decision") {
      if (!createDecision.trim() || !createRationale.trim()) return null;
      return { decision: createDecision.trim(), rationale: createRationale.trim() };
    }
    const highlights = parseLines(createHighlights);
    if (!createSummary.trim() || !highlights.length) return null;
    return { summary: createSummary.trim(), highlights };
  }

  function buildDetailContent(type: KnowledgeType): Record<string, unknown> | null {
    if (type === "playbook") {
      const steps = parseLines(detailSteps);
      if (!detailGoal.trim() || !steps.length) return null;
      return { goal: detailGoal.trim(), steps };
    }
    if (type === "decision") {
      if (!detailDecision.trim() || !detailRationale.trim()) return null;
      return { decision: detailDecision.trim(), rationale: detailRationale.trim() };
    }
    const highlights = parseLines(detailHighlights);
    if (!detailSummary.trim() || !highlights.length) return null;
    return { summary: detailSummary.trim(), highlights };
  }

  function hydrateDetailForm(detail: KnowledgeDetail) {
    setDetailTitle(detail.title);
    setDetailTopicId(detail.topic_id ?? "");
    setDetailTags(detail.tags.join(", "));
    setDetailSourceRef("ui://knowledge");
    setDetailExcerpt("");

    const content = detail.content ?? {};
    if (detail.type === "playbook") {
      setDetailGoal(String(content.goal ?? ""));
      setDetailSteps(Array.isArray(content.steps) ? (content.steps as string[]).join("\n") : "");
      setDetailDecision("");
      setDetailRationale("");
      setDetailSummary("");
      setDetailHighlights("");
      return;
    }
    if (detail.type === "decision") {
      setDetailDecision(String(content.decision ?? ""));
      setDetailRationale(String(content.rationale ?? ""));
      setDetailGoal("");
      setDetailSteps("");
      setDetailSummary("");
      setDetailHighlights("");
      return;
    }
    setDetailSummary(String(content.summary ?? ""));
    setDetailHighlights(Array.isArray(content.highlights) ? (content.highlights as string[]).join("\n") : "");
    setDetailGoal("");
    setDetailSteps("");
    setDetailDecision("");
    setDetailRationale("");
  }

  function renderContentReadonly(detail: KnowledgeDetail) {
    const content = detail.content ?? {};
    if (detail.type === "playbook") {
      const steps = Array.isArray(content.steps) ? (content.steps as string[]) : [];
      return (
        <div className="knowledgeSection">
          <h3 className="changesGroupTitle">{t("knowledge.goal")}</h3>
          <p className="changesLedgerText">{String(content.goal ?? "-")}</p>
          <h3 className="changesGroupTitle" style={{ marginTop: 12 }}>{t("knowledge.steps")}</h3>
          {steps.length ? (
            steps.map((step, idx) => <p key={`${idx}:${step}`} className="changesLedgerText">{idx + 1}. {step}</p>)
          ) : (
            <p className="changesLedgerText">-</p>
          )}
        </div>
      );
    }
    if (detail.type === "decision") {
      return (
        <div className="knowledgeSection">
          <h3 className="changesGroupTitle">{t("knowledge.decision")}</h3>
          <p className="changesLedgerText">{String(content.decision ?? "-")}</p>
          <h3 className="changesGroupTitle" style={{ marginTop: 12 }}>{t("knowledge.rationale")}</h3>
          <p className="changesLedgerText">{String(content.rationale ?? "-")}</p>
        </div>
      );
    }
    const highlights = Array.isArray(content.highlights) ? (content.highlights as string[]) : [];
    return (
      <div className="knowledgeSection">
        <h3 className="changesGroupTitle">{t("knowledge.summary")}</h3>
        <p className="changesLedgerText">{String(content.summary ?? "-")}</p>
        <h3 className="changesGroupTitle" style={{ marginTop: 12 }}>{t("knowledge.highlights")}</h3>
        {highlights.length ? (
          highlights.map((line, idx) => <p key={`${idx}:${line}`} className="changesLedgerText">{idx + 1}. {line}</p>)
        ) : (
          <p className="changesLedgerText">-</p>
        )}
      </div>
    );
  }

  async function onInit() {
    setError("");
    setLoading(true);
    try {
      const topicRes = await apiGet<TopicList>("/api/v1/topics");
      const topicsActive = topicRes.items.filter((item) => item.status === "active");
      setTopics(topicRes.items);
      setCreateTopicId(topicsActive[0]?.id ?? "");
      await onRefreshList();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function onLoadDetail(itemId: string) {
    const detail = await apiGet<KnowledgeDetail>(`/api/v1/knowledge/${itemId}`);
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
      if (typeFilter !== "all") params.set("type", typeFilter);
      if (topicFilter) params.set("topic_id", topicFilter);
      if (searchQuery.trim()) params.set("q", searchQuery.trim());
      if (tagQuery.trim()) params.set("tag", tagQuery.trim());

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
    const content = buildCreateContent();
    if (!createTitle.trim() || !createSourceRef.trim() || !createExcerpt.trim() || !content) {
      setError(t("knowledge.errValidation"));
      return;
    }
    setError("");
    setNotice("");
    setLoading(true);
    try {
      const created = await apiPost<KnowledgeDetail>("/api/v1/knowledge", {
        type: createType,
        title: createTitle.trim(),
        topic_id: createTopicId || null,
        tags: parseTags(createTags),
        content,
        evidences: [{ source_ref: createSourceRef.trim(), excerpt: createExcerpt.trim() }],
      });
      setCreateTitle("");
      setCreateTags("");
      setCreateExcerpt("");
      setCreateGoal("");
      setCreateSteps("");
      setCreateDecision("");
      setCreateRationale("");
      setCreateSummary("");
      setCreateHighlights("");
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
    const content = buildDetailContent(selectedDetail.type);
    if (!detailTitle.trim() || !content) {
      setError(t("knowledge.errValidation"));
      return;
    }
    setError("");
    setNotice("");
    setLoading(true);
    try {
      await apiPatch<KnowledgeDetail>(`/api/v1/knowledge/${selectedDetail.id}`, {
        title: detailTitle.trim(),
        topic_id: detailTopicId || null,
        tags: parseTags(detailTags),
        content,
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
      await apiPost<KnowledgeDetail>(`/api/v1/knowledge/${selectedDetail.id}/archive`, {});
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

  async function onAppendEvidence() {
    if (!selectedDetail || selectedDetail.status === "archived") return;
    if (!detailSourceRef.trim() || !detailExcerpt.trim()) {
      setError(t("knowledge.errValidation"));
      return;
    }
    setError("");
    setNotice("");
    setLoading(true);
    try {
      await apiPost<KnowledgeEvidence>(`/api/v1/knowledge/${selectedDetail.id}/evidences`, {
        source_ref: detailSourceRef.trim(),
        excerpt: detailExcerpt.trim(),
      });
      setDetailExcerpt("");
      setNotice(t("knowledge.noticeEvidenceAdded"));
      await onRefreshList(selectedDetail.id);
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
          <input
            value={tagQuery}
            onChange={(e) => setTagQuery(e.target.value)}
            placeholder={t("knowledge.placeholderTag")}
            className="taskInput"
          />
          <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value as KnowledgeType | "all")} className="taskInput">
            <option value="all">{t("knowledge.typeAll")}</option>
            <option value="playbook">{t("knowledge.type.playbook")}</option>
            <option value="decision">{t("knowledge.type.decision")}</option>
            <option value="brief">{t("knowledge.type.brief")}</option>
          </select>
          <select value={topicFilter} onChange={(e) => setTopicFilter(e.target.value)} className="taskInput">
            <option value="">{t("knowledge.topicAll")}</option>
            {activeTopics.map((topic) => (
              <option key={topic.id} value={topic.id}>
                {localizeTopicName(topic)}
              </option>
            ))}
          </select>
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as KnowledgeStatus)} className="taskInput">
            <option value="active">{t("knowledge.statusActive")}</option>
            <option value="archived">{t("knowledge.statusArchived")}</option>
          </select>
        </div>
      </div>

      <div className="knowledgeCreate">
        <select value={createType} onChange={(e) => setCreateType(e.target.value as KnowledgeType)} className="taskInput">
          <option value="playbook">{t("knowledge.type.playbook")}</option>
          <option value="decision">{t("knowledge.type.decision")}</option>
          <option value="brief">{t("knowledge.type.brief")}</option>
        </select>
        <input
          value={createTitle}
          onChange={(e) => setCreateTitle(e.target.value)}
          placeholder={t("knowledge.placeholderTitle")}
          className="taskInput"
        />
        <select value={createTopicId} onChange={(e) => setCreateTopicId(e.target.value)} className="taskInput">
          <option value="">{t("knowledge.unclassified")}</option>
          {activeTopics.map((topic) => (
            <option key={topic.id} value={topic.id}>
              {localizeTopicName(topic)}
            </option>
          ))}
        </select>
        <input
          value={createTags}
          onChange={(e) => setCreateTags(e.target.value)}
          placeholder={t("knowledge.placeholderTags")}
          className="taskInput"
        />
        <input
          value={createSourceRef}
          onChange={(e) => setCreateSourceRef(e.target.value)}
          placeholder={t("knowledge.placeholderSourceRef")}
          className="taskInput"
        />
        <textarea
          value={createExcerpt}
          onChange={(e) => setCreateExcerpt(e.target.value)}
          rows={2}
          placeholder={t("knowledge.placeholderExcerpt")}
          className="taskInput taskTextArea knowledgeCreateBody"
        />
        {createType === "playbook" ? (
          <>
            <textarea
              value={createGoal}
              onChange={(e) => setCreateGoal(e.target.value)}
              rows={2}
              placeholder={t("knowledge.placeholderGoal")}
              className="taskInput taskTextArea knowledgeCreateBody"
            />
            <textarea
              value={createSteps}
              onChange={(e) => setCreateSteps(e.target.value)}
              rows={3}
              placeholder={t("knowledge.placeholderSteps")}
              className="taskInput taskTextArea knowledgeCreateBody"
            />
          </>
        ) : null}
        {createType === "decision" ? (
          <>
            <textarea
              value={createDecision}
              onChange={(e) => setCreateDecision(e.target.value)}
              rows={2}
              placeholder={t("knowledge.placeholderDecision")}
              className="taskInput taskTextArea knowledgeCreateBody"
            />
            <textarea
              value={createRationale}
              onChange={(e) => setCreateRationale(e.target.value)}
              rows={3}
              placeholder={t("knowledge.placeholderRationale")}
              className="taskInput taskTextArea knowledgeCreateBody"
            />
          </>
        ) : null}
        {createType === "brief" ? (
          <>
            <textarea
              value={createSummary}
              onChange={(e) => setCreateSummary(e.target.value)}
              rows={2}
              placeholder={t("knowledge.placeholderSummary")}
              className="taskInput taskTextArea knowledgeCreateBody"
            />
            <textarea
              value={createHighlights}
              onChange={(e) => setCreateHighlights(e.target.value)}
              rows={3}
              placeholder={t("knowledge.placeholderHighlights")}
              className="taskInput taskTextArea knowledgeCreateBody"
            />
          </>
        ) : null}
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
                    <span className="badge" style={{ marginRight: 8 }}>{typeLabel(item.type)}</span>
                    {item.title}
                  </div>
                  <div className="knowledgeMeta">
                    <span>{t("knowledge.tags")}: {item.tags.length ? item.tags.join(", ") : "-"}</span>
                    <span>{t("knowledge.sourceCount")}: {item.evidence_count}</span>
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
                  <div className="changesSummaryKey">{t("knowledge.type")}</div>
                  <div className="changesLedgerText">{typeLabel(selectedDetail.type)}</div>
                </div>
                <div>
                  <div className="changesSummaryKey">{t("knowledge.updated")}</div>
                  <div className="changesLedgerText">{formatTime(selectedDetail.updated_at)}</div>
                </div>
                <div>
                  <div className="changesSummaryKey">{t("knowledge.sourceCount")}</div>
                  <div className="changesLedgerText">{selectedDetail.evidence_count}</div>
                </div>
              </div>

              {renderContentReadonly(selectedDetail)}

              <div className="knowledgeSection">
                <h3 className="changesGroupTitle">{t("knowledge.sources")}</h3>
                {selectedDetail.evidences.length ? (
                  selectedDetail.evidences.map((ev) => (
                    <div key={ev.id} style={{ marginBottom: 8 }}>
                      <p className="changesLedgerText">{ev.source_ref}</p>
                      <p className="changesLedgerText">{ev.excerpt}</p>
                    </div>
                  ))
                ) : (
                  <p className="changesLedgerText">-</p>
                )}
              </div>

              {selectedDetail.status === "archived" ? (
                <>
                  <p className="meta">{t("knowledge.readOnlyHint")}</p>
                  <div className="taskDetailFormActions" style={{ marginTop: 10 }}>
                    <button className="badge" onClick={onDeleteSelected} disabled={loading}>{t("knowledge.delete")}</button>
                  </div>
                </>
              ) : (
                <>
                  <div className="knowledgeEdit">
                    <label className="taskField">
                      <span>{t("knowledge.titleField")}</span>
                      <input value={detailTitle} onChange={(e) => setDetailTitle(e.target.value)} className="taskInput" />
                    </label>
                    <label className="taskField">
                      <span>{t("knowledge.topic")}</span>
                      <select value={detailTopicId} onChange={(e) => setDetailTopicId(e.target.value)} className="taskInput">
                        <option value="">{t("knowledge.unclassified")}</option>
                        {activeTopics.map((topic) => (
                          <option key={topic.id} value={topic.id}>
                            {localizeTopicName(topic)}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="taskField">
                      <span>{t("knowledge.tags")}</span>
                      <input value={detailTags} onChange={(e) => setDetailTags(e.target.value)} className="taskInput" />
                    </label>
                    {selectedDetail.type === "playbook" ? (
                      <>
                        <label className="taskField">
                          <span>{t("knowledge.goal")}</span>
                          <textarea value={detailGoal} onChange={(e) => setDetailGoal(e.target.value)} className="taskInput taskTextArea" rows={2} />
                        </label>
                        <label className="taskField">
                          <span>{t("knowledge.steps")}</span>
                          <textarea value={detailSteps} onChange={(e) => setDetailSteps(e.target.value)} className="taskInput taskTextArea" rows={3} />
                        </label>
                      </>
                    ) : null}
                    {selectedDetail.type === "decision" ? (
                      <>
                        <label className="taskField">
                          <span>{t("knowledge.decision")}</span>
                          <textarea value={detailDecision} onChange={(e) => setDetailDecision(e.target.value)} className="taskInput taskTextArea" rows={2} />
                        </label>
                        <label className="taskField">
                          <span>{t("knowledge.rationale")}</span>
                          <textarea value={detailRationale} onChange={(e) => setDetailRationale(e.target.value)} className="taskInput taskTextArea" rows={3} />
                        </label>
                      </>
                    ) : null}
                    {selectedDetail.type === "brief" ? (
                      <>
                        <label className="taskField">
                          <span>{t("knowledge.summary")}</span>
                          <textarea value={detailSummary} onChange={(e) => setDetailSummary(e.target.value)} className="taskInput taskTextArea" rows={2} />
                        </label>
                        <label className="taskField">
                          <span>{t("knowledge.highlights")}</span>
                          <textarea value={detailHighlights} onChange={(e) => setDetailHighlights(e.target.value)} className="taskInput taskTextArea" rows={3} />
                        </label>
                      </>
                    ) : null}
                    <div className="taskDetailFormActions">
                      <button className="badge" onClick={onSaveDetail} disabled={loading}>{t("knowledge.save")}</button>
                      <button className="badge" onClick={onArchiveSelected} disabled={loading}>{t("knowledge.archive")}</button>
                      <button className="badge" onClick={onDeleteSelected} disabled={loading}>{t("knowledge.delete")}</button>
                    </div>
                  </div>

                  <div className="knowledgeSection">
                    <h3 className="changesGroupTitle">{t("knowledge.addEvidence")}</h3>
                    <input
                      value={detailSourceRef}
                      onChange={(e) => setDetailSourceRef(e.target.value)}
                      placeholder={t("knowledge.placeholderSourceRef")}
                      className="taskInput"
                    />
                    <textarea
                      value={detailExcerpt}
                      onChange={(e) => setDetailExcerpt(e.target.value)}
                      placeholder={t("knowledge.placeholderExcerpt")}
                      rows={3}
                      className="taskInput taskTextArea"
                    />
                    <div className="taskDetailFormActions">
                      <button className="badge" onClick={onAppendEvidence} disabled={loading}>{t("knowledge.addEvidence")}</button>
                    </div>
                  </div>
                </>
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
