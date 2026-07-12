const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    if (res.status === 401) {
      const refreshToken = localStorage.getItem("refresh_token");
      if (refreshToken) {
        try {
          const refreshRes = await fetch(`${API_BASE}/auth/refresh`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ refresh_token: refreshToken }),
          });

          if (refreshRes.ok) {
            const data = await refreshRes.json();
            localStorage.setItem("access_token", data.access_token);
            headers["Authorization"] = `Bearer ${data.access_token}`;

            const retryRes = await fetch(`${API_BASE}${endpoint}`, {
              ...options,
              headers,
            });
            if (retryRes.ok) return retryRes.json();
          }
        } catch {}
      }
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
    }
    throw new Error(`API Error: ${res.status}`);
  }

  return res.json();
}

export const api = {
  auth: {
    login: (username: string, password: string) =>
      request("/auth/login", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      }),
    register: (username: string, email: string, password: string) =>
      request("/auth/register", {
        method: "POST",
        body: JSON.stringify({ username, email, password }),
      }),
    me: () => request("/auth/me"),
  },
  chat: {
    conversations: () => request("/chat/conversations"),
    createConversation: (title: string) =>
      request("/chat/conversations", {
        method: "POST",
        body: JSON.stringify({ title }),
      }),
    getMessages: (convId: number) =>
      request(`/chat/conversations/${convId}/messages`),
    sendMessage: (convId: number, message: string) =>
      request(`/chat/conversations/${convId}/messages`, {
        method: "POST",
        body: JSON.stringify({ message, stream: false }),
      }),
  },
  training: {
    datasets: () => request("/training/datasets"),
    createDataset: (name: string, description?: string) =>
      request("/training/datasets", {
        method: "POST",
        body: JSON.stringify({ name, description }),
      }),
    versions: () => request("/training/versions"),
  },
  unlearning: {
    requests: () => request("/unlearning/requests"),
    createRequest: (sampleIds: number[], algorithm?: string) =>
      request("/unlearning/requests", {
        method: "POST",
        body: JSON.stringify({ sample_ids: sampleIds, algorithm }),
      }),
    getResult: (requestId: number) =>
      request(`/unlearning/results/${requestId}`),
  },
};
