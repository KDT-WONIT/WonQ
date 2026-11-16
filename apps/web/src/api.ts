export type JobKind = "chatbot" | "report" | "inspection" | "monitoring";
export type JobStatus = "queued" | "running" | "completed" | "failed";

export type Asset = {
  id: string;
  code: string;
  name: string;
  location: string;
  department: string;
  item_code: string | null;
  serial: string | null;
  qr_token: string;
  status: string;
};

export type DashboardSummary = {
  total_assets: number;
  active_assets: number;
  categories: Record<string, number>;
  weekly_changes: number | null;
  audit_checked: number | null;
  audit_matched: number | null;
  audit_issues: number | null;
};

export type Job = {
  id: string;
  kind: JobKind;
  status: JobStatus;
  result: Record<string, unknown> | null;
};

export async function request<T>(
  path: string,
  token?: string,
  body?: Record<string, unknown>,
): Promise<T> {
  const headers = new Headers();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (body) headers.set("Content-Type", "application/json");

  const response = await fetch(`/api${path}`, {
    method: body ? "POST" : "GET",
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = data?.detail;
    const validation = Array.isArray(detail) ? detail.find((item) => typeof item?.msg === "string") : null;
    throw new Error(typeof detail === "string" ? detail : validation?.msg ?? `요청 실패 (${response.status})`);
  }
  return data as T;
}
