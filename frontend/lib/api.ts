const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

async function request<T = any>(
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
        } catch (e) { console.error("Token refresh failed:", e); }
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
    deleteConversation: (convId: number) =>
      request(`/chat/conversations/${convId}`, { method: "DELETE" }),
  },
  datasets: {
    list: (params?: { page?: number; page_size?: number; search?: string; status?: string; dataset_type?: string }) => {
      const searchParams = new URLSearchParams();
      if (params?.page) searchParams.set("page", String(params.page));
      if (params?.page_size) searchParams.set("page_size", String(params.page_size));
      if (params?.search) searchParams.set("search", params.search);
      if (params?.status) searchParams.set("status", params.status);
      if (params?.dataset_type) searchParams.set("dataset_type", params.dataset_type);
      const qs = searchParams.toString();
      return request(`/datasets/${qs ? `?${qs}` : ""}`);
    },
    get: (id: number) => request(`/datasets/${id}`),
    upload: (name: string, file: File, description?: string) => {
      const formData = new FormData();
      formData.append("file", file);
      const params = new URLSearchParams({ name });
      if (description) params.set("description", description);
      const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
      return fetch(`${API_BASE}/datasets/upload?${params}`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      }).then((r) => r.json());
    },
    update: (id: number, data: { name?: string; description?: string }) =>
      request(`/datasets/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    delete: (id: number) =>
      request(`/datasets/${id}`, { method: "DELETE" }).then(() => true),
    preview: (id: number) => request(`/datasets/${id}/preview`),
    versions: (id: number) => request(`/datasets/${id}/versions`),
    validate: (id: number) => request(`/datasets/${id}/validate`),
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
  trainingJobs: {
    list: (params?: { page?: number; page_size?: number; status?: string }) => {
      const searchParams = new URLSearchParams();
      if (params?.page) searchParams.set("page", String(params.page));
      if (params?.page_size) searchParams.set("page_size", String(params.page_size));
      if (params?.status) searchParams.set("status", params.status);
      const qs = searchParams.toString();
      return request(`/training-jobs/${qs ? `?${qs}` : ""}`);
    },
    get: (id: number) => request(`/training-jobs/${id}`),
    create: (data: { name?: string; dataset_id: number; config?: Record<string, unknown> }) =>
      request("/training-jobs/", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    start: (id: number) =>
      request(`/training-jobs/${id}/start`, { method: "POST" }),
    logs: (id: number) => request(`/training-jobs/${id}/logs`),
    cancel: (id: number) =>
      request(`/training-jobs/${id}/cancel`, { method: "POST" }),
    delete: (id: number) =>
      request(`/training-jobs/${id}`, { method: "DELETE" }).then(() => true),
    stats: () => request("/training-jobs/stats"),
  },
  registry: {
    versions: (params?: { status?: string; page?: number; page_size?: number }) => {
      const searchParams = new URLSearchParams();
      if (params?.status) searchParams.set("status", params.status);
      if (params?.page) searchParams.set("page", String(params.page));
      if (params?.page_size) searchParams.set("page_size", String(params.page_size));
      const qs = searchParams.toString();
      return request(`/registry/versions${qs ? `?${qs}` : ""}`);
    },
    get: (id: number) => request(`/registry/versions/${id}`),
    activate: (id: number) =>
      request(`/registry/versions/${id}/activate`, { method: "POST" }),
    deploy: (id: number) =>
      request(`/registry/versions/${id}/deploy`, { method: "POST" }),
    archive: (id: number) =>
      request(`/registry/versions/${id}/archive`, { method: "POST" }),
    delete: (id: number) =>
      request(`/registry/versions/${id}`, { method: "DELETE" }).then(() => true),
    compare: (v1: number, v2: number) =>
      request(`/registry/compare/${v1}/${v2}`),
    lineage: (id: number) => request(`/registry/versions/${id}/lineage`),
    stats: () => request("/registry/stats"),
  },
  inference: {
    generate: (data: {
      prompt: string;
      model_version_id?: number;
      conversation_id?: number;
      temperature?: number;
      max_tokens?: number;
    }) =>
      request("/inference/generate", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    logs: (params?: { page?: number; page_size?: number }) => {
      const searchParams = new URLSearchParams();
      if (params?.page) searchParams.set("page", String(params.page));
      if (params?.page_size) searchParams.set("page_size", String(params.page_size));
      const qs = searchParams.toString();
      return request(`/inference/logs${qs ? `?${qs}` : ""}`);
    },
    stats: () => request("/inference/stats"),
    models: () => request("/inference/models"),
  },
  dashboard: {
    stats: () => request("/dashboard/stats"),
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
  verification: {
    jobs: (params?: { page?: number; page_size?: number; status?: string }) => {
      const sp = new URLSearchParams();
      if (params?.page) sp.set("page", String(params.page));
      if (params?.page_size) sp.set("page_size", String(params.page_size));
      if (params?.status) sp.set("status", params.status);
      const qs = sp.toString();
      return request(`/verification/jobs${qs ? `?${qs}` : ""}`);
    },
    getJob: (id: number) => request(`/verification/jobs/${id}`),
    createJob: (requestId: number, jobId?: number) =>
      request("/verification/jobs", {
        method: "POST",
        body: JSON.stringify({ request_id: requestId, job_id: jobId }),
      }),
    runJob: (id: number) =>
      request(`/verification/jobs/${id}/run`, { method: "POST" }),
    jobResults: (id: number) => request(`/verification/jobs/${id}/results`),
    jobTrust: (id: number) => request(`/verification/jobs/${id}/trust`),
    jobReport: (id: number) => request(`/verification/jobs/${id}/report`),
    jobStats: () => request("/verification/jobs/stats"),
    certificates: (params?: { page?: number; page_size?: number }) => {
      const sp = new URLSearchParams();
      if (params?.page) sp.set("page", String(params.page));
      if (params?.page_size) sp.set("page_size", String(params.page_size));
      const qs = sp.toString();
      return request(`/verification/certificates${qs ? `?${qs}` : ""}`);
    },
    getCertificate: (certId: string) => request(`/verification/certificates/${certId}`),
    validateCertificate: (certId: string) =>
      request(`/verification/certificates/${certId}/validate`),
    compare: (beforeId: number, afterId: number) =>
      request(`/verification/compare/${beforeId}/${afterId}`),
    trustScore: (jobId: number) =>
      request(`/verification/trust-scores/${jobId}`),
    reports: (params?: { page?: number; page_size?: number }) => {
      const sp = new URLSearchParams();
      if (params?.page) sp.set("page", String(params.page));
      if (params?.page_size) sp.set("page_size", String(params.page_size));
      const qs = sp.toString();
      return request(`/verification/reports${qs ? `?${qs}` : ""}`);
    },
  },
  mlops: {
    health: () => request("/v2/mlops/health"),
    readiness: () => request("/v2/mlops/readiness"),
    liveness: () => request("/v2/mlops/liveness"),
    operations: () => request("/v2/mlops/operations"),
    systemMetrics: () => request("/v2/mlops/metrics/system"),
    workers: () => request("/v2/mlops/metrics/workers"),
    logs: (params?: { query?: string; level?: string; limit?: number }) => {
      const sp = new URLSearchParams();
      if (params?.query) sp.set("query", params.query);
      if (params?.level) sp.set("level", params.level);
      if (params?.limit) sp.set("limit", String(params.limit));
      const qs = sp.toString();
      return request(`/v2/mlops/logs${qs ? `?${qs}` : ""}`);
    },
    experiments: (params?: { status?: string; limit?: number }) => {
      const sp = new URLSearchParams();
      if (params?.status) sp.set("status", params.status);
      if (params?.limit) sp.set("limit", String(params.limit));
      const qs = sp.toString();
      return request(`/v2/mlops/experiments${qs ? `?${qs}` : ""}`);
    },
    createExperiment: (data: { name: string; description?: string }) =>
      request("/v2/mlops/experiments", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    experimentRuns: (expId: number) =>
      request(`/v2/mlops/experiments/${expId}/runs`),
    pipelines: (params?: { status?: string; limit?: number }) => {
      const sp = new URLSearchParams();
      if (params?.status) sp.set("status", params.status);
      if (params?.limit) sp.set("limit", String(params.limit));
      const qs = sp.toString();
      return request(`/v2/mlops/pipelines${qs ? `?${qs}` : ""}`);
    },
    pipelineRuns: () => request("/v2/mlops/pipelines/runs"),
    modelStats: () => request("/v2/mlops/models/stats"),
    config: () => request("/v2/mlops/config"),
  },
  research: {
    // Algorithms
    algorithms: (params?: { enabled_only?: boolean; model_type?: string }) => {
      const sp = new URLSearchParams();
      if (params?.enabled_only) sp.set("enabled_only", "true");
      if (params?.model_type) sp.set("model_type", params.model_type);
      const qs = sp.toString();
      return request(`/v2/research/algorithms${qs ? `?${qs}` : ""}`);
    },
    getAlgorithm: (name: string) => request(`/v2/research/algorithms/${name}`),
    registerAlgorithm: (data: {
      name: string;
      version?: string;
      description?: string;
      complexity?: string;
      supported_models?: string[];
      supported_datasets?: string[];
      paper_title?: string;
      implementation_class?: string;
    }) =>
      request("/v2/research/algorithms", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    toggleAlgorithm: (name: string, enabled: boolean) =>
      request(`/v2/research/algorithms/${name}/toggle?enabled=${enabled}`, { method: "POST" }),
    algorithmMetrics: () => request("/v2/research/algorithms/types/available"),

    // Benchmarks
    benchmarks: (params?: { status?: string; limit?: number }) => {
      const sp = new URLSearchParams();
      if (params?.status) sp.set("status_filter", params.status);
      if (params?.limit) sp.set("limit", String(params.limit));
      const qs = sp.toString();
      return request(`/v2/research/benchmarks${qs ? `?${qs}` : ""}`);
    },
    getBenchmark: (id: number) => request(`/v2/research/benchmarks/${id}`),
    createBenchmark: (data: {
      name: string;
      description?: string;
      algorithms?: string[];
      num_runs?: number;
      seed?: number;
    }) =>
      request("/v2/research/benchmarks", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    deleteBenchmark: (id: number) =>
      request(`/v2/research/benchmarks/${id}`, { method: "DELETE" }).then(() => true),
    runBenchmark: (benchmarkId: number, data: { algorithm_name: string; seed?: number }) =>
      request(`/v2/research/benchmarks/${benchmarkId}/run`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    benchmarkRuns: (benchmarkId: number) =>
      request(`/v2/research/benchmarks/${benchmarkId}/runs`),

    // Metrics
    recordMetric: (runId: number, data: { metric_name: string; metric_value: number; metric_unit?: string }) =>
      request(`/v2/research/runs/${runId}/metrics`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    runMetrics: (runId: number) => request(`/v2/research/runs/${runId}/metrics`),
    metricDefinitions: () => request("/v2/research/metrics/definitions"),

    // Leaderboards
    leaderboards: () => request("/v2/research/leaderboards"),
    getLeaderboard: (id: number) => request(`/v2/research/leaderboards/${id}`),
    createLeaderboard: (data: { name: string; ranking_metric?: string }) =>
      request("/v2/research/leaderboards", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    leaderboardEntries: (id: number) => request(`/v2/research/leaderboards/${id}/entries`),
    addLeaderboardEntry: (id: number, data: { algorithm_name: string; score: number; scores_json?: Record<string, number> }) =>
      request(`/v2/research/leaderboards/${id}/entries`, {
        method: "POST",
        body: JSON.stringify(data),
      }),

    // Attacks
    attackTypes: () => request("/v2/research/attacks/types"),
    runAttack: (data: { attack_type: string; benchmark_run_id?: number }) =>
      request("/v2/research/attacks/run", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    attackResults: (params?: { benchmark_run_id?: number }) => {
      const sp = new URLSearchParams();
      if (params?.benchmark_run_id) sp.set("benchmark_run_id", String(params.benchmark_run_id));
      const qs = sp.toString();
      return request(`/v2/research/attacks/results${qs ? `?${qs}` : ""}`);
    },

    // Comparisons
    comparisons: (params?: { limit?: number }) => {
      const sp = new URLSearchParams();
      if (params?.limit) sp.set("limit", String(params.limit));
      const qs = sp.toString();
      return request(`/v2/research/comparisons${qs ? `?${qs}` : ""}`);
    },
    createComparison: (data: {
      name: string;
      comparison_type: string;
      items: Array<{ name: string }>;
    }) =>
      request("/v2/research/comparisons", {
        method: "POST",
        body: JSON.stringify(data),
      }),

    // Reports
    reports: () => request("/v2/research/reports"),
    generateReport: (data: { benchmark_id: number; title: string; report_format?: string }) =>
      request("/v2/research/reports/generate", {
        method: "POST",
        body: JSON.stringify(data),
      }),

    // Reproducibility
    captureSnapshot: (data: { random_seed?: number; python_version?: string; git_commit?: string }) =>
      request("/v2/research/reproducibility/snapshot", {
        method: "POST",
        body: JSON.stringify(data),
      }),

    // Plugins
    plugins: (params?: { plugin_type?: string }) => {
      const sp = new URLSearchParams();
      if (params?.plugin_type) sp.set("plugin_type", params.plugin_type);
      const qs = sp.toString();
      return request(`/v2/research/plugins${qs ? `?${qs}` : ""}`);
    },
    registerPlugin: (data: { name: string; plugin_type: string; entry_point: string; description?: string }) =>
      request("/v2/research/plugins", {
        method: "POST",
        body: JSON.stringify(data),
      }),

    // Explainability
    explainability: (data: { model_version_id: number; method: string; num_samples?: number }) =>
      request("/v2/research/explainability", {
        method: "POST",
        body: JSON.stringify(data),
      }),

    // Export
    exportBenchmark: (id: number, format?: string) =>
      request(`/v2/research/export/benchmark/${id}?format=${format || "json"}`, { method: "POST" }),
    exportLeaderboard: (id: number, format?: string) =>
      request(`/v2/research/export/leaderboard/${id}?format=${format || "json"}`, { method: "POST" }),
  },
  governance: {
    dashboard: () => request("/governance/dashboard"),
    policies: (params?: { page?: number; page_size?: number; status?: string }) => {
      const sp = new URLSearchParams();
      if (params?.page) sp.set("page", String(params.page));
      if (params?.page_size) sp.set("page_size", String(params.page_size));
      if (params?.status) sp.set("status", params.status);
      const qs = sp.toString();
      return request(`/governance/policies${qs ? `?${qs}` : ""}`);
    },
    createPolicy: (data: {
      name: string;
      description: string;
      policy_type: string;
      regulation: string;
    }) =>
      request("/governance/policies", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    consents: (params?: { page?: number; page_size?: number; status?: string }) => {
      const sp = new URLSearchParams();
      if (params?.page) sp.set("page", String(params.page));
      if (params?.page_size) sp.set("page_size", String(params.page_size));
      if (params?.status) sp.set("status", params.status);
      const qs = sp.toString();
      return request(`/governance/consents${qs ? `?${qs}` : ""}`);
    },
    grantConsent: (data: {
      subject: string;
      purpose: string;
      dataset_id: number;
      regulation: string;
      expires_days?: number;
    }) =>
      request("/governance/consents", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    pendingApprovals: () => request("/governance/approvals/pending"),
    approveApproval: (id: number) =>
      request(`/governance/approvals/${id}/approve`, { method: "POST" }),
    rejectApproval: (id: number) =>
      request(`/governance/approvals/${id}/reject`, { method: "POST" }),
    workflows: (params?: { page?: number; page_size?: number }) => {
      const sp = new URLSearchParams();
      if (params?.page) sp.set("page", String(params.page));
      if (params?.page_size) sp.set("page_size", String(params.page_size));
      const qs = sp.toString();
      return request(`/governance/workflows${qs ? `?${qs}` : ""}`);
    },
    reports: (params?: { page?: number; page_size?: number }) => {
      const sp = new URLSearchParams();
      if (params?.page) sp.set("page", String(params.page));
      if (params?.page_size) sp.set("page_size", String(params.page_size));
      const qs = sp.toString();
      return request(`/governance/reports${qs ? `?${qs}` : ""}`);
    },
  },
};
