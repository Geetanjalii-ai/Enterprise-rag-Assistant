let inMemoryToken: string | null = null;

export const getAccessToken = (): string | null => inMemoryToken;
export const setAccessToken = (token: string | null) => {
  inMemoryToken = token;
};

const getBaseUrl = (): string => {
  const envUrl = import.meta.env.VITE_API_BASE_URL;
  if (envUrl !== undefined && envUrl !== null) {
    if (typeof window !== "undefined" && window.location.hostname === "127.0.0.1") {
      return envUrl.replace("localhost", "127.0.0.1");
    }
    return envUrl;
  }
  const host = typeof window !== "undefined" ? window.location.hostname : "localhost";
  return `http://${host}:8000`;
};

const API_PREFIX = "/api/v1";

let isRefreshing = false;
let refreshSubscribers: ((token: string) => void)[] = [];

const onRefreshed = (token: string) => {
  refreshSubscribers.forEach((cb) => cb(token));
  refreshSubscribers = [];
};

export async function apiFetch<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const cleanEndpoint = endpoint.startsWith(API_PREFIX)
    ? endpoint
    : `${API_PREFIX}${endpoint.startsWith("/") ? endpoint : "/" + endpoint}`;
  const url = `${getBaseUrl()}${cleanEndpoint}`;
  const headers = new Headers(options.headers || {});

  if (inMemoryToken && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${inMemoryToken}`);
  }

  // Ensure JSON Content-Type unless multipart
  if (options.body instanceof FormData) {
    headers.delete("Content-Type");
  } else if (!headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(url, {
    ...options,
    headers,
    credentials: "include", // send httpOnly refresh cookie
  });

  if (response.status === 401 && !cleanEndpoint.includes("/auth/refresh") && !cleanEndpoint.includes("/auth/login") && !cleanEndpoint.includes("/auth/register")) {
    // Attempt one-time automatic refresh
    if (!isRefreshing) {
      isRefreshing = true;
      try {
        const refreshResp = await fetch(`${getBaseUrl()}${API_PREFIX}/auth/refresh`, {
          method: "POST",
          credentials: "include",
        });
        if (refreshResp.ok) {
          const data = await refreshResp.json();
          setAccessToken(data.access_token);
          isRefreshing = false;
          onRefreshed(data.access_token);
        } else {
          setAccessToken(null);
          isRefreshing = false;
        }
      } catch {
        setAccessToken(null);
        isRefreshing = false;
      }
    }

    // Retry with new token if refreshed
    return new Promise((resolve, reject) => {
      refreshSubscribers.push(async (newToken: string) => {
        try {
          headers.set("Authorization", `Bearer ${newToken}`);
          const retryResp = await fetch(url, {
            ...options,
            headers,
            credentials: "include",
          });
          if (!retryResp.ok) {
            const err = await retryResp.json().catch(() => ({}));
            reject(Object.assign(new Error(err.detail || "API Error"), { response: retryResp }));
          } else {
            resolve((await retryResp.json()) as T);
          }
        } catch (err) {
          reject(err);
        }
      });
    });
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const err = new Error(errorData.detail || `Request failed with status ${response.status}`);
    (err as any).response = { status: response.status, data: errorData };
    throw err;
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

export const api = {
  get: <T = any>(endpoint: string, config?: { params?: Record<string, any> }) => {
    let url = endpoint;
    if (config?.params) {
      const searchParams = new URLSearchParams();
      Object.entries(config.params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== "") {
          searchParams.append(k, String(v));
        }
      });
      const qs = searchParams.toString();
      if (qs) url += `?${qs}`;
    }
    return apiFetch<T>(url, { method: "GET" }).then((data) => ({ data }));
  },
  post: <T = any>(endpoint: string, body?: any, config?: { headers?: Record<string, string> }) => {
    const isFormData = body instanceof FormData;
    return apiFetch<T>(endpoint, {
      method: "POST",
      headers: config?.headers,
      body: isFormData ? body : JSON.stringify(body),
    }).then((data) => ({ data }));
  },
  patch: <T = any>(endpoint: string, body?: any) => {
    return apiFetch<T>(endpoint, {
      method: "PATCH",
      body: JSON.stringify(body),
    }).then((data) => ({ data }));
  },
  delete: <T = any>(endpoint: string) => {
    return apiFetch<T>(endpoint, { method: "DELETE" }).then((data) => ({ data }));
  },
  put: <T = any>(endpoint: string, body?: any) => {
    return apiFetch<T>(endpoint, {
      method: "PUT",
      body: JSON.stringify(body),
    }).then((data) => ({ data }));
  },
};
