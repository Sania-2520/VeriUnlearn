import type { TourStep } from "./tour-step"

export const defaultTourSteps: TourStep[] = [
  {
    targetSelector: "",
    title: "Welcome to VeriUnlearn",
    content:
      "Your enterprise machine unlearning platform for AI governance and compliance.",
    placement: "center",
    icon: "Sparkles",
    action: { label: "Let's Go!" },
    showSkip: false,
    showDots: true,
  },
  {
    targetSelector: '[data-tour="dashboard"]',
    title: "Dashboard Overview",
    content:
      "Monitor your system at a glance: active models, running jobs, compliance scores, and recent activity all in one place.",
    placement: "right",
    icon: "LayoutDashboard",
    showSkip: true,
    showDots: true,
  },
  {
    targetSelector: '[data-tour="unlearning"]',
    title: "Machine Unlearning",
    content:
      "Submit deletion requests, choose algorithms, and track the unlearning process. VeriUnlearn supports 5 state-of-the-art algorithms.",
    placement: "right",
    icon: "ListTodo",
    showSkip: true,
    showDots: true,
  },
  {
    targetSelector: '[data-tour="experiments"]',
    title: "Experiments",
    content:
      "Run benchmarks, compare algorithm performance, and analyze results with interactive visualizations.",
    placement: "right",
    icon: "BarChart3",
    showSkip: true,
    showDots: true,
  },
  {
    targetSelector: '[data-tour="certificates"]',
    title: "Verification Certificates",
    content:
      "Each unlearning operation generates a cryptographically verifiable certificate with a Merkle proof of deletion.",
    placement: "right",
    icon: "ShieldCheck",
    showSkip: true,
    showDots: true,
  },
  {
    targetSelector: '[data-tour="operations"]',
    title: "Operations Center",
    content:
      "Monitor system health, view real-time logs, manage alerts, and ensure your infrastructure is running smoothly.",
    placement: "right",
    icon: "Gauge",
    showSkip: true,
    showDots: true,
  },
  {
    targetSelector: '[data-tour="copilot"]',
    title: "AI Copilot",
    content:
      "Use our intelligent assistant to answer questions, generate reports, and get recommendations. Press \u2318K anytime.",
    placement: "bottom",
    icon: "Bot",
    showSkip: true,
    showDots: true,
  },
  {
    targetSelector: "",
    title: "Ready to begin?",
    content:
      "Explore the platform, submit your first unlearning request, or run a benchmark. We're here to help.",
    placement: "center",
    icon: "Rocket",
    action: { label: "Start Using VeriUnlearn" },
    showSkip: false,
    showDots: true,
  },
]
