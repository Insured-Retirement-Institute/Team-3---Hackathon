/**
 * Backend API client. Set VITE_API_BASE_URL (default http://localhost:8000) when running frontend.
 * Mandatory auth: set VITE_AUTH_TOKEN (default matches backend AUTH_TOKEN).
 */
const API_BASE = (import.meta.env.VITE_API_BASE_URL as string) || "http://localhost:8000";

/** Bearer token required by backend for all /api/* requests. Must match backend AUTH_TOKEN. */
const AUTH_TOKEN =
  (import.meta.env.VITE_AUTH_TOKEN as string) ||
  "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJJUi1EZW1vIiwiZXhwIjoxOTk5OTk5OTk5fQ.dummy";

function authHeaders(extra: Record<string, string> = {}): Record<string, string> {
  return {
    Authorization: `Bearer ${AUTH_TOKEN}`,
    ...extra,
  };
}

async function request<T>(
  path: string,
  options: RequestInit & { params?: Record<string, string> } = {}
): Promise<T> {
  const { params, ...init } = options;
  const url = new URL(path.startsWith("http") ? path : `${API_BASE}${path}`);
  if (params) {
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
  }
  const headers: Record<string, string> = authHeaders(init.headers as Record<string, string>);
  if (init.body && typeof init.body === "string") headers["Content-Type"] = "application/json";

  const res = await fetch(url.toString(), { ...init, headers });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  const contentType = res.headers.get("content-type");
  if (contentType?.includes("application/json")) {
    return res.json() as Promise<T>;
  }
  return res.text() as Promise<T>;
}

export const api = {
  get: <T>(path: string, params?: Record<string, string>) =>
    request<T>(path, { method: "GET", params }),

  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),

  postForm: async <T>(path: string, formData: FormData): Promise<T> => {
    const url = path.startsWith("http") ? path : `${API_BASE}${path}`;
    const res = await fetch(url, { method: "POST", headers: authHeaders(), body: formData });
    if (!res.ok) throw new Error(await res.text() || `HTTP ${res.status}`);
    const ct = res.headers.get("content-type");
    return (ct?.includes("application/json") ? res.json() : res.text()) as Promise<T>;
  },
};

// Types matching backend responses
export interface AdvisorListItem {
  id: string;
  npn?: string;
  name?: string;
  status?: string;
  created_at?: string;
}

export interface AdvisorDetail {
  id: string;
  npn?: string;
  first_name?: string;
  last_name?: string;
  email?: string;
  phone?: string;
  broker_dealer?: string;
  license_states?: string[];
  status?: string;
  transfer_date?: string;
}

export interface CarrierSubmissionItem {
  id: string;
  advisor_id: string;
  carrier_id: string;
  status?: string;
  agent_code?: string | null;
  accepted_states?: string[] | null;
  rejected_states?: string[] | null;
  request_data?: { submitted_states?: string[] } | null;
  created_at?: string;
  error_message?: string | null;
}

export interface ListAdvisorsResponse {
  success: boolean;
  data: AdvisorListItem[];
}

export interface ListCarrierSubmissionsResponse {
  success: boolean;
  data: CarrierSubmissionItem[];
}

export interface SeedResponse {
  success: boolean;
  created: number;
  advisors: { id: string; npn: string; name: string }[];
}

export interface CarrierFormatIdsResponse {
  success: boolean;
  carrier_ids: string[];
  carriers?: {
    carrier_id: string;
    name: string;
    template_used?: string;
    default_template?: string;
  }[];
}

export interface CarriersListResponse {
  success: boolean;
  data: {
    id: string;
    name: string;
    default_template?: string;
    has_custom_yaml?: boolean;
  }[];
}

export interface SampleFormatResponse {
  success: boolean;
  yaml: string;
  description?: string;
  template_name?: string;
}

export interface TestTransformResponse {
  success: boolean;
  payload: Record<string, unknown>;
  format_used: string;
  carrier_id: string;
  custom_yaml_uploaded?: boolean;
  bedrock_used?: boolean;
  message?: string | null;
}

export interface CreateAdvisorRequest {
  npn: string;
  first_name?: string;
  last_name?: string;
  email?: string;
  phone?: string;
  broker_dealer?: string;
  license_states?: string[];
  status?: string;
}

export interface CreateAdvisorResponse {
  success: boolean;
  advisor_id: string;
}

export interface CreateAndTransferRequest {
  agent: CreateAdvisorRequest;
  carriers: string[];
  states: string[];
}

export interface CreateAndTransferResponse {
  success: boolean;
  advisor_id: string;
  submission_ids: string[];
  status: string;
}
