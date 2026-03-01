export function localeFromLang(lang: string): string {
  return lang === "zh" ? "zh-CN" : "en-US";
}

export function formatDateTime(value: string | null | undefined, lang: string): string {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(localeFromLang(lang), {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false
  });
}
