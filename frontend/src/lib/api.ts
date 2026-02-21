const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY ?? "";

export function apiHeaders(): HeadersInit {
  const headers: Record<string, string> = {
    "Content-Type": "application/json"
  };
  if (API_KEY) {
    headers.Authorization = `Bearer ${API_KEY}`;
  }
  return headers;
}

export async function apiPost<T>(path: string, payload: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: apiHeaders(),
    body: JSON.stringify(payload),
    cache: "no-store"
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`POST ${path} failed: ${res.status} ${text}`);
  }
  return res.json() as Promise<T>;
}

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "GET",
    headers: apiHeaders(),
    cache: "no-store"
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`GET ${path} failed: ${res.status} ${text}`);
  }
  return res.json() as Promise<T>;
}

export async function apiPatch<T>(path: string, payload: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "PATCH",
    headers: apiHeaders(),
    body: JSON.stringify(payload),
    cache: "no-store"
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`PATCH ${path} failed: ${res.status} ${text}`);
  }
  return res.json() as Promise<T>;
}


export async function apiDelete(path: string): Promise<void> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "DELETE",
    headers: apiHeaders(),
    cache: "no-store"
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`DELETE ${path} failed: ${res.status} ${text}`);
  }
}
