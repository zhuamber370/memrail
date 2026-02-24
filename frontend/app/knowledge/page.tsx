/* eslint-disable react/jsx-no-bind */
"use client";

import { useEffect, useMemo, useState } from "react";

import { apiDelete, apiGet, apiPatch, apiPost } from "../../src/lib/api";
import { useI18n } from "../../src/i18n";

type NoteStatus = "active" | "archived";
type GroupKey = string | "__unclassified";

type SourceItem = { type: string; value: string };
type Note = {
  id: string;
  title: string;
  body: string;
  tags: string[];
  topic_id: string | null;
  status: NoteStatus;
  source_count: number;
  sources: SourceItem[];
  linked_task_ids: string[];
  linked_note_ids: string[];
  created_at?: string;
  updated_at?: string;
};
type NoteList = { items: Note[]; page: number; page_size: number; total: number };

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

type TopicSummaryItem = { topic_id: string | null; topic_name: string; count: number };
type TopicSummary = { items: TopicSummaryItem[] };

type NoteOut = { id: string };
type BatchClassifyOut = { updated: number; failed: number; failures: Array<{ note_id: string; reason: string }> };

export default function KnowledgePage() {
  const { t, lang } = useI18n();

  const [topics, setTopics] = useState<Topic[]>([]);
  const [summary, setSummary] = useState<TopicSummaryItem[]>([]);
  const [selectedGroup, setSelectedGroup] = useState<GroupKey>("__unclassified");
  const [statusFilter, setStatusFilter] = useState<NoteStatus>("active");

  const [searchQuery, setSearchQuery] = useState("");
  const [tagQuery, setTagQuery] = useState("");

  const [notes, setNotes] = useState<Note[]>([]);
  const [selectedNoteId, setSelectedNoteId] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  const [createTitle, setCreateTitle] = useState("");
  const [createBody, setCreateBody] = useState("");
  const [createSource, setCreateSource] = useState("ui://knowledge");
  const [createTags, setCreateTags] = useState("");
  const [createTopicId, setCreateTopicId] = useState<string>("");

  const [detailTopicId, setDetailTopicId] = useState<string>("");
  const [detailTags, setDetailTags] = useState("");

  const [bulkTopicId, setBulkTopicId] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [ready, setReady] = useState(false);

  const selectedNote = useMemo(
    () => notes.find((item) => item.id === selectedNoteId) ?? null,
    [notes, selectedNoteId]
  );
  const isUnclassifiedView = selectedGroup === "__unclassified";
  const isArchivedView = statusFilter === "archived";
  const allVisibleSelected = useMemo(
    () => notes.length > 0 && notes.every((item) => selectedIds.includes(item.id)),
    [notes, selectedIds]
  );

  useEffect(() => {
    void onInit();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!ready) return;
    void onRefreshNotes();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, selectedGroup, statusFilter, searchQuery, tagQuery]);

  useEffect(() => {
    if (!selectedNote) return;
    setDetailTopicId(selectedNote.topic_id ?? "");
    setDetailTags(selectedNote.tags.join(", "));
  }, [selectedNote]);

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

  function getGroupCount(group: GroupKey): number {
    if (group === "__unclassified") {
      return summary.find((item) => item.topic_id === null)?.count ?? 0;
    }
    return summary.find((item) => item.topic_id === group)?.count ?? 0;
  }

  async function onInit() {
    setError("");
    setLoading(true);
    try {
      const [topicRes, summaryRes] = await Promise.all([
        apiGet<TopicList>("/api/v1/topics"),
        apiGet<TopicSummary>("/api/v1/notes/topic-summary?status=active")
      ]);
      const activeTopics = topicRes.items.filter((item) => item.status === "active");
      setTopics(activeTopics);
      setSummary(summaryRes.items);
      setCreateTopicId(activeTopics[0]?.id ?? "");
      setBulkTopicId(activeTopics[0]?.id ?? "");

      const firstNonEmpty = activeTopics.find((topic) => {
        const found = summaryRes.items.find((item) => item.topic_id === topic.id);
        return (found?.count ?? 0) > 0;
      });
      if (firstNonEmpty) setSelectedGroup(firstNonEmpty.id);
      else if ((summaryRes.items.find((item) => item.topic_id === null)?.count ?? 0) > 0) setSelectedGroup("__unclassified");
      else setSelectedGroup(activeTopics[0]?.id ?? "__unclassified");

      setReady(true);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function onRefreshSummary() {
    const summaryRes = await apiGet<TopicSummary>(`/api/v1/notes/topic-summary?status=${statusFilter}`);
    setSummary(summaryRes.items);
  }

  async function onRefreshNotes() {
    setError("");
    setNotice("");
    setLoading(true);
    try {
      const params = new URLSearchParams({ page: "1", page_size: "100", status: statusFilter });
      if (selectedGroup === "__unclassified") params.set("unclassified", "true");
      else params.set("topic_id", selectedGroup);
      if (searchQuery.trim()) params.set("q", searchQuery.trim());
      if (tagQuery.trim()) params.set("tag", tagQuery.trim());

      const listed = await apiGet<NoteList>(`/api/v1/notes/search?${params.toString()}`);
      setNotes(listed.items);
      setSelectedIds((prev) => prev.filter((id) => listed.items.some((item) => item.id === id)));
      setSelectedNoteId((prev) => {
        if (prev && listed.items.some((item) => item.id === prev)) return prev;
        return listed.items[0]?.id ?? null;
      });
      await onRefreshSummary();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function onAppend() {
    if (!createTitle.trim() || !createBody.trim() || !createSource.trim()) {
      setError(t("knowledge.errValidation"));
      return;
    }
    setError("");
    setNotice("");
    setLoading(true);
    try {
      await apiPost<NoteOut>("/api/v1/notes/append", {
        title: createTitle.trim(),
        body: createBody.trim(),
        topic_id: createTopicId || null,
        sources: [{ type: "text", value: createSource.trim() }],
        tags: parseTags(createTags)
      });
      setCreateTitle("");
      setCreateBody("");
      setCreateTags("");
      setNotice(t("knowledge.noticeAppended"));
      await onRefreshNotes();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function onSaveDetail() {
    if (!selectedNote || isArchivedView) return;
    const nextTags = parseTags(detailTags);
    const tagsSame = JSON.stringify(nextTags) === JSON.stringify(selectedNote.tags);
    const nextTopic = detailTopicId || null;
    const topicSame = nextTopic === selectedNote.topic_id;
    if (tagsSame && topicSame) {
      setNotice(t("knowledge.noticeNoChange"));
      return;
    }
    setError("");
    setNotice("");
    setLoading(true);
    try {
      await apiPatch<Note>(`/api/v1/notes/${selectedNote.id}`, {
        topic_id: nextTopic,
        tags: nextTags
      });
      setNotice(t("knowledge.noticeUpdated"));
      await onRefreshNotes();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function onArchiveNote() {
    if (!selectedNote || isArchivedView) return;
    setError("");
    setNotice("");
    setLoading(true);
    try {
      await apiPatch<Note>(`/api/v1/notes/${selectedNote.id}`, { status: "archived" });
      setNotice(t("knowledge.noticeArchived"));
      await onRefreshNotes();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function onDeleteNote() {
    if (!selectedNote) return;
    if (!window.confirm(t("knowledge.confirmDelete"))) return;
    setError("");
    setNotice("");
    setLoading(true);
    try {
      await apiDelete(`/api/v1/notes/${selectedNote.id}`);
      setNotice(t("knowledge.noticeDeleted"));
      await onRefreshNotes();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function onBulkClassify() {
    if (!selectedIds.length || !bulkTopicId) return;
    setError("");
    setNotice("");
    setLoading(true);
    try {
      const result = await apiPost<BatchClassifyOut>("/api/v1/notes/batch-classify", {
        note_ids: selectedIds,
        topic_id: bulkTopicId
      });
      setNotice(`${t("knowledge.noticeClassified")}: ${result.updated}, failed: ${result.failed}`);
      await onRefreshNotes();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  function toggleSelected(noteId: string) {
    setSelectedIds((prev) => (prev.includes(noteId) ? prev.filter((id) => id !== noteId) : [...prev, noteId]));
  }

  function toggleSelectAllVisible() {
    if (allVisibleSelected) {
      setSelectedIds((prev) => prev.filter((id) => !notes.some((note) => note.id === id)));
      return;
    }
    setSelectedIds((prev) => {
      const merged = new Set(prev);
      notes.forEach((note) => merged.add(note.id));
      return Array.from(merged);
    });
  }

  function formatTime(value?: string): string {
    if (!value) return "-";
    try {
      return new Date(value).toLocaleString();
    } catch {
      return value;
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
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as NoteStatus)} className="taskInput">
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
        <select value={createTopicId} onChange={(e) => setCreateTopicId(e.target.value)} className="taskInput">
          <option value="">{t("knowledge.unclassified")}</option>
          {topics.map((topic) => (
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
          value={createSource}
          onChange={(e) => setCreateSource(e.target.value)}
          placeholder={t("knowledge.placeholderSource")}
          className="taskInput"
        />
        <textarea
          value={createBody}
          onChange={(e) => setCreateBody(e.target.value)}
          rows={3}
          placeholder={t("knowledge.placeholderBody")}
          className="taskInput taskTextArea knowledgeCreateBody"
        />
        <button className="badge" onClick={onAppend} disabled={loading || !createTitle.trim() || !createBody.trim() || !createSource.trim()}>
          {t("knowledge.append")}
        </button>
      </div>

      <div className="knowledgeLayout">
        <aside className="knowledgeTopics">
          <h2 className="changesSubTitle">{t("knowledge.topicGroups")}</h2>
          <button
            className={`knowledgeTopicBtn ${selectedGroup === "__unclassified" ? "knowledgeTopicBtnActive" : ""}`}
            onClick={() => setSelectedGroup("__unclassified")}
          >
            <span>{t("knowledge.unclassified")}</span>
            <strong>{getGroupCount("__unclassified")}</strong>
          </button>
          {topics.map((topic) => (
            <button
              key={topic.id}
              className={`knowledgeTopicBtn ${selectedGroup === topic.id ? "knowledgeTopicBtnActive" : ""}`}
              onClick={() => setSelectedGroup(topic.id)}
            >
              <span>{localizeTopicName(topic)}</span>
              <strong>{getGroupCount(topic.id)}</strong>
            </button>
          ))}
        </aside>

        <div className="knowledgeListPanel">
          {!isArchivedView ? (
            <div className="knowledgeBulkBar">
              {isUnclassifiedView ? (
                <>
                  <label className="meta" style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                    <input
                      type="checkbox"
                      checked={allVisibleSelected}
                      onChange={() => toggleSelectAllVisible()}
                      disabled={!notes.length || loading}
                    />
                    {t("knowledge.selectAll")}
                  </label>
                  <span className="meta">{t("knowledge.selected")}: {selectedIds.length}</span>
                  <select value={bulkTopicId} onChange={(e) => setBulkTopicId(e.target.value)} className="taskInput">
                    {topics.map((topic) => (
                      <option key={topic.id} value={topic.id}>
                        {localizeTopicName(topic)}
                      </option>
                    ))}
                  </select>
                  <button className="badge" onClick={onBulkClassify} disabled={loading || !selectedIds.length || !bulkTopicId}>
                    {t("knowledge.bulkClassify")}
                  </button>
                </>
              ) : (
                <span className="meta">{t("knowledge.selected")}: {selectedIds.length}</span>
              )}
            </div>
          ) : (
            <p className="meta">{t("knowledge.readOnlyHint")}</p>
          )}

          {error ? <p className="meta" style={{ color: "var(--danger)", marginTop: 8 }}>{error}</p> : null}
          {notice ? <p className="meta" style={{ color: "var(--success)", marginTop: 8 }}>{notice}</p> : null}

          <div className="knowledgeList">
            {notes.map((note) => (
              <div
                key={note.id}
                className={`knowledgeRow ${selectedNoteId === note.id ? "knowledgeRowActive" : ""}`}
                onClick={() => setSelectedNoteId(note.id)}
              >
                {!isArchivedView ? (
                  <input
                    type="checkbox"
                    checked={selectedIds.includes(note.id)}
                    onChange={(e) => {
                      e.stopPropagation();
                      toggleSelected(note.id);
                    }}
                    aria-label={`select ${note.title}`}
                  />
                ) : null}
                <div className="knowledgeRowMain">
                  <div className="knowledgeTitle">{note.title}</div>
                  <div className="knowledgeMeta">
                    <span>{t("knowledge.tags")}: {note.tags.length ? note.tags.join(", ") : "-"}</span>
                    <span>{t("knowledge.sourceCount")}: {note.source_count}</span>
                    <span>{t("knowledge.updated")}: {formatTime(note.updated_at)}</span>
                  </div>
                </div>
              </div>
            ))}
            {!notes.length ? <p className="meta">{t("knowledge.emptyList")}</p> : null}
          </div>
        </div>

        <aside className="knowledgeDetail">
          <h2 className="changesSubTitle">{t("knowledge.detail")}</h2>
          {selectedNote ? (
            <div className="knowledgeDetailContent">
              <div className="knowledgeDetailTitle">{selectedNote.title}</div>
              <div className="meta">{selectedNote.id}</div>
              <article className="knowledgeBody">{selectedNote.body}</article>

              <div className="taskDetailGrid">
                <div>
                  <div className="changesSummaryKey">{t("knowledge.updated")}</div>
                  <div className="changesLedgerText">{formatTime(selectedNote.updated_at)}</div>
                </div>
                <div>
                  <div className="changesSummaryKey">{t("knowledge.sourceCount")}</div>
                  <div className="changesLedgerText">{selectedNote.source_count}</div>
                </div>
              </div>

              {selectedNote.sources?.length ? (
                <div className="knowledgeSection">
                  <h3 className="changesGroupTitle">{t("knowledge.sources")}</h3>
                  {selectedNote.sources.map((src, idx) => (
                    <p key={`${src.type}:${src.value}:${idx}`} className="changesLedgerText">{src.type}: {src.value}</p>
                  ))}
                </div>
              ) : null}

              {selectedNote.linked_task_ids?.length ? (
                <div className="knowledgeSection">
                  <h3 className="changesGroupTitle">{t("knowledge.linkedTasks")}</h3>
                  {selectedNote.linked_task_ids.map((taskId) => (
                    <p key={taskId} className="changesLedgerText">{taskId}</p>
                  ))}
                </div>
              ) : null}

              {selectedNote.linked_note_ids?.length ? (
                <div className="knowledgeSection">
                  <h3 className="changesGroupTitle">{t("knowledge.linkedNotes")}</h3>
                  {selectedNote.linked_note_ids.map((noteId) => (
                    <p key={noteId} className="changesLedgerText">{noteId}</p>
                  ))}
                </div>
              ) : null}

              {!isArchivedView ? (
                <div className="knowledgeEdit">
                  <label className="taskField">
                    <span>{t("knowledge.topic")}</span>
                    <select value={detailTopicId} onChange={(e) => setDetailTopicId(e.target.value)} className="taskInput">
                      <option value="">{t("knowledge.unclassified")}</option>
                      {topics.map((topic) => (
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
                  <div className="taskDetailFormActions">
                    <button className="badge" onClick={onSaveDetail} disabled={loading}>{t("knowledge.save")}</button>
                    <button className="badge" onClick={onArchiveNote} disabled={loading}>{t("knowledge.archive")}</button>
                    <button className="badge" onClick={onDeleteNote} disabled={loading}>{t("knowledge.delete")}</button>
                  </div>
                </div>
              ) : (
                <>
                  <p className="meta">{t("knowledge.readOnlyHint")}</p>
                  <div className="taskDetailFormActions" style={{ marginTop: 10 }}>
                    <button className="badge" onClick={onDeleteNote} disabled={loading}>{t("knowledge.delete")}</button>
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
