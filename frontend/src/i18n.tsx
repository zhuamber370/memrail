"use client";

import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

type Lang = "en" | "zh";

type Dictionary = Record<string, string>;

const dictionaries: Record<Lang, Dictionary> = {
  en: {
    "nav.tasks": "Tasks",
    "nav.knowledge": "Knowledge",
    "nav.changes": "Changes",
    "nav.audit": "Audit",
    "lang.en": "EN",
    "lang.zh": "中文",

    "tasks.title": "Tasks",
    "tasks.subtitle": "Ops board: view routing, bulk governance, detail review.",
    "tasks.create": "Create Task",
    "tasks.refresh": "Refresh",
    "tasks.selected": "Selected",
    "tasks.bulkPriority": "Bulk Priority",
    "tasks.bulkStatus": "Bulk Status",
    "tasks.start": "Start",
    "tasks.done": "Done",
    "tasks.reopen": "Reopen",
    "tasks.empty": "No tasks in this view.",
    "tasks.detail": "Task Detail",
    "tasks.status": "Status",
    "tasks.priority": "Priority",
    "tasks.project": "Project",
    "tasks.due": "Due",
    "tasks.cycle": "Cycle",
    "tasks.blockedBy": "Blocked By",
    "tasks.nextReview": "Next Review",
    "tasks.updated": "Updated",
    "tasks.source": "Source",
    "tasks.quickEdit": "Quick Edit",
    "tasks.saveDetail": "Save Detail",
    "tasks.pickOne": "Select a task to view details.",
    "tasks.placeholderTitle": "New task title",
    "tasks.placeholderProject": "project",
    "tasks.noticeCreated": "Task created.",
    "tasks.noticeUpdated": "Task updated",
    "tasks.noticeReopened": "Task reopened.",
    "tasks.noticeDetailSaved": "Details saved.",
    "tasks.noticeNoChange": "No changes to save.",
    "tasks.noticeBulk": "Bulk updated",
    "tasks.errTransition": "Status transition is not allowed. Reopen first.",
    "tasks.errNotFound": "Task not found. It may have been removed.",
    "tasks.errValidation": "Invalid input. Check project/due/status.",

    "tasks.view.today": "Today",
    "tasks.view.overdue": "Overdue",
    "tasks.view.this_week": "This Week",
    "tasks.view.backlog": "Backlog",
    "tasks.view.blocked": "Blocked",
    "tasks.view.done": "Done",

    "changes.title": "Changes",
    "changes.subtitle": "Batch writes must go through Dry-run -> Diff -> Commit.",
    "changes.actionsJson": "Actions JSON",
    "changes.dryRun": "Dry-run",
    "changes.commit": "Commit",
    "changes.undo": "Undo Last",
    "changes.pendingDry": "Dry-running...",
    "changes.pendingCommit": "Committing...",
    "changes.pendingUndo": "Undoing...",
    "changes.summary": "Dry-run Summary",
    "changes.entity": "Entity",
    "changes.fields": "Fields",
    "changes.diffLedger": "Diff Ledger",
    "changes.taskOnly": "Show task changes only",
    "changes.noTaskChanges": "No task changes in current result.",
    "changes.commitResult": "Commit Result",
    "changes.undoResult": "Undo Result",
    "changes.fieldChanges": "Field changes",

    "knowledge.title": "Knowledge",
    "knowledge.subtitle": "Capture methods and conclusions. Source is required.",
    "knowledge.append": "Append Note",
    "knowledge.search": "Search Notes",
    "knowledge.placeholderTitle": "Title",
    "knowledge.placeholderBody": "Body",
    "knowledge.placeholderSource": "source",

    "audit.title": "Audit",
    "audit.subtitle": "Track who/when/tool/action/target/source.",
    "audit.load": "Load Events"
  },
  zh: {
    "nav.tasks": "任务",
    "nav.knowledge": "知识",
    "nav.changes": "变更",
    "nav.audit": "审计",
    "lang.en": "EN",
    "lang.zh": "中文",

    "tasks.title": "任务",
    "tasks.subtitle": "运营台：视图切换、批量治理、详情审阅。",
    "tasks.create": "创建任务",
    "tasks.refresh": "刷新",
    "tasks.selected": "已选",
    "tasks.bulkPriority": "批量优先级",
    "tasks.bulkStatus": "批量状态",
    "tasks.start": "开始",
    "tasks.done": "完成",
    "tasks.reopen": "重开",
    "tasks.empty": "当前视图暂无任务。",
    "tasks.detail": "任务详情",
    "tasks.status": "状态",
    "tasks.priority": "优先级",
    "tasks.project": "项目",
    "tasks.due": "截止日期",
    "tasks.cycle": "周期",
    "tasks.blockedBy": "阻塞来源",
    "tasks.nextReview": "下次复盘",
    "tasks.updated": "更新时间",
    "tasks.source": "来源",
    "tasks.quickEdit": "快捷编辑",
    "tasks.saveDetail": "保存详情",
    "tasks.pickOne": "请选择一个任务查看详情。",
    "tasks.placeholderTitle": "新任务标题",
    "tasks.placeholderProject": "项目",
    "tasks.noticeCreated": "任务已创建。",
    "tasks.noticeUpdated": "任务已更新",
    "tasks.noticeReopened": "任务已重开。",
    "tasks.noticeDetailSaved": "详情已保存。",
    "tasks.noticeNoChange": "没有需要保存的变更。",
    "tasks.noticeBulk": "批量更新完成",
    "tasks.errTransition": "状态流不允许该变更，请先 Reopen 再推进状态。",
    "tasks.errNotFound": "任务不存在，可能已被删除或视图过期。",
    "tasks.errValidation": "输入字段不合法，请检查 project/due/status。",

    "tasks.view.today": "今天",
    "tasks.view.overdue": "已逾期",
    "tasks.view.this_week": "本周",
    "tasks.view.backlog": "待整理",
    "tasks.view.blocked": "被阻塞",
    "tasks.view.done": "已完成",

    "changes.title": "变更",
    "changes.subtitle": "批量写入必须经过 Dry-run -> Diff -> Commit。",
    "changes.actionsJson": "动作 JSON",
    "changes.dryRun": "预检",
    "changes.commit": "提交",
    "changes.undo": "回滚最近一次",
    "changes.pendingDry": "预检中...",
    "changes.pendingCommit": "提交中...",
    "changes.pendingUndo": "回滚中...",
    "changes.summary": "预检摘要",
    "changes.entity": "实体",
    "changes.fields": "字段",
    "changes.diffLedger": "差异台账",
    "changes.taskOnly": "仅看任务变更",
    "changes.noTaskChanges": "当前结果没有任务变更。",
    "changes.commitResult": "提交结果",
    "changes.undoResult": "回滚结果",
    "changes.fieldChanges": "字段变化",

    "knowledge.title": "知识",
    "knowledge.subtitle": "沉淀方法与结论；每条必须有 source。",
    "knowledge.append": "追加笔记",
    "knowledge.search": "搜索笔记",
    "knowledge.placeholderTitle": "标题",
    "knowledge.placeholderBody": "正文",
    "knowledge.placeholderSource": "来源",

    "audit.title": "审计",
    "audit.subtitle": "追踪 who/when/tool/action/target/source。",
    "audit.load": "加载事件"
  }
};

type I18nValue = {
  lang: Lang;
  setLang: (lang: Lang) => void;
  t: (key: string) => string;
};

const I18nContext = createContext<I18nValue | null>(null);

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Lang>("en");

  useEffect(() => {
    const saved = window.localStorage.getItem("afkms_lang");
    if (saved === "en" || saved === "zh") {
      setLang(saved);
    }
  }, []);

  useEffect(() => {
    window.localStorage.setItem("afkms_lang", lang);
    document.documentElement.lang = lang === "zh" ? "zh-CN" : "en";
  }, [lang]);

  const value = useMemo<I18nValue>(
    () => ({
      lang,
      setLang,
      t: (key: string) => dictionaries[lang][key] ?? key
    }),
    [lang]
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  const ctx = useContext(I18nContext);
  if (!ctx) {
    throw new Error("useI18n must be used within I18nProvider");
  }
  return ctx;
}
