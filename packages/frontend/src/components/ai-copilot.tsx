"use client"

import { useState, useRef, useEffect, useCallback, type ReactNode } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { clsx } from "clsx"
import {
  Bot,
  X,
  Send,
  Sparkles,
  AlertCircle,
  RotateCcw,
  ArrowUpRight,
  FileText,
  BarChart3,
  Activity,
  Shield,
  CheckCircle2,
  TrendingDown,
  Scale,
  FileSearch,
  Cpu,
  Database,
  Clock,
  ExternalLink,
  ChevronRight,
} from "lucide-react"
import { useCopilot } from "@/hooks/use-copilot"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { TypingDots } from "@/components/ui/spinner"

const SUGGESTED_QUESTIONS = [
  "Why did trust score decrease?",
  "Compare SISA and Retraining",
  "Generate GDPR compliance report",
  "Recommend best algorithm for my data",
  "Explain verification certificate",
  "Find recent failed experiments",
  "Show latest audit events",
  "What changed in system health?",
]

type ResponseType =
  | "trust_score"
  | "compare_sisa"
  | "gdpr_report"
  | "recommend_algo"
  | "verify_cert"
  | "failed_experiments"
  | "audit_events"
  | "system_health"
  | "generic"

interface ChatMessage {
  id: string
  role: "user" | "assistant"
  text?: string
  responseType?: ResponseType
  timestamp: Date
}

type CopilotStatus = "idle" | "thinking" | "error"

let msgCounter = 0
function nextId() {
  msgCounter += 1
  return `msg-${msgCounter}-${Date.now()}`
}

function matchResponseType(question: string): ResponseType {
  const q = question.toLowerCase().trim()
  if (q.includes("trust score") || q.includes("why did")) return "trust_score"
  if (q.includes("compare") || (q.includes("sisa") && q.includes("retraining"))) return "compare_sisa"
  if (q.includes("gdpr") || q.includes("compliance") || q.includes("report")) return "gdpr_report"
  if (q.includes("recommend") || q.includes("algorithm") || q.includes("best")) return "recommend_algo"
  if (q.includes("verification") || q.includes("certificate") || q.includes("verify")) return "verify_cert"
  if (q.includes("failed") || q.includes("experiment")) return "failed_experiments"
  if (q.includes("audit") || q.includes("event")) return "audit_events"
  if (q.includes("system health") || q.includes("changed") || q.includes("health")) return "system_health"
  return "generic"
}

function classifyQuestion(question: string): ResponseType {
  return matchResponseType(question)
}

function renderUserMessage(text: string) {
  return <p className="text-sm text-[var(--text-on-brand)]">{text}</p>
}

function renderTrustScoreResponse(): ReactNode {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <TrendingDown className="h-4 w-4 text-[var(--danger)]" />
        <span className="text-sm font-semibold text-[var(--text-primary)]">Trust Score Analysis</span>
        <Badge tone="danger" dot>Critical</Badge>
      </div>
      <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-subtle)] p-3">
        <div className="mb-2 flex items-baseline justify-between">
          <span className="text-xs text-[var(--text-tertiary)]">Current Score</span>
          <span className="text-2xl font-bold text-[var(--danger)]">72.4%</span>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-[var(--text-secondary)]">
          <TrendingDown className="h-3 w-3 text-[var(--danger)]" />
          <span>Declined 8.3% over the past 7 days</span>
        </div>
      </div>
      <div className="space-y-1.5">
        <p className="text-xs font-semibold text-[var(--text-primary)]">Contributing Factors</p>
        <ul className="space-y-1 text-xs text-[var(--text-secondary)]">
          <li className="flex items-start gap-2">
            <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--danger)]" />
            Batch unlearning #AE-1024 increased MIA success rate to 0.51
          </li>
          <li className="flex items-start gap-2">
            <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--warning)]" />
            LoRA adapter v9 has 3.2% lower utility than v8
          </li>
          <li className="flex items-start gap-2">
            <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--warning)]" />
            2 verification certificates are pending re-validation
          </li>
        </ul>
      </div>
      <div className="flex gap-2">
        <Button variant="subtle" size="sm">
          <BarChart3 className="h-3.5 w-3.5" />
          View Details
        </Button>
        <Button variant="secondary" size="sm">
          <Activity className="h-3.5 w-3.5" />
          Monitor
        </Button>
      </div>
    </div>
  )
}

function renderCompareSisaResponse(): ReactNode {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Scale className="h-4 w-4 text-[var(--accent)]" />
        <span className="text-sm font-semibold text-[var(--text-primary)]">SISA vs Full Retraining</span>
      </div>
      <div className="space-y-2">
        <div className="rounded-lg border border-[var(--border-subtle)]">
          <div className="flex items-center justify-between border-b border-[var(--border-subtle)] bg-[var(--brand-soft)] px-3 py-2">
            <span className="text-xs font-semibold text-[var(--brand-strong)]">SISA (Sharded Retraining)</span>
            <Badge tone="success" dot>Recommended</Badge>
          </div>
          <div className="space-y-1.5 p-3 text-xs text-[var(--text-secondary)]">
            <div className="flex items-center justify-between">
              <span>Runtime</span>
              <span className="font-medium text-[var(--text-primary)]">~2.4s</span>
            </div>
            <div className="flex items-center justify-between">
              <span>Utility retained</span>
              <span className="font-medium text-[var(--success)]">97.8%</span>
            </div>
            <div className="flex items-center justify-between">
              <span>Privacy improvement</span>
              <span className="font-medium text-[var(--success)]">+34.7%</span>
            </div>
            <div className="flex items-center justify-between">
              <span>Compute cost</span>
              <span className="font-medium text-[var(--text-primary)]">Low</span>
            </div>
            <div className="flex items-center justify-between">
              <span>Scaling</span>
              <span className="font-medium text-[var(--success)]">Excellent</span>
            </div>
          </div>
        </div>
        <div className="rounded-lg border border-[var(--border-subtle)]">
          <div className="border-b border-[var(--border-subtle)] bg-[var(--bg-subtle)] px-3 py-2">
            <span className="text-xs font-semibold text-[var(--text-primary)]">Full Retraining</span>
          </div>
          <div className="space-y-1.5 p-3 text-xs text-[var(--text-secondary)]">
            <div className="flex items-center justify-between">
              <span>Runtime</span>
              <span className="font-medium text-[var(--text-primary)]">~45s</span>
            </div>
            <div className="flex items-center justify-between">
              <span>Utility retained</span>
              <span className="font-medium text-[var(--success)]">99.1%</span>
            </div>
            <div className="flex items-center justify-between">
              <span>Privacy improvement</span>
              <span className="font-medium text-[var(--success)]">+31.2%</span>
            </div>
            <div className="flex items-center justify-between">
              <span>Compute cost</span>
              <span className="font-medium text-[var(--danger)]">High</span>
            </div>
            <div className="flex items-center justify-between">
              <span>Scaling</span>
              <span className="font-medium text-[var(--danger)]">Poor</span>
            </div>
          </div>
        </div>
      </div>
      <div className="flex gap-2">
        <Button variant="subtle" size="sm">
          <FileText className="h-3.5 w-3.5" />
          Full Comparison Report
        </Button>
        <Button variant="secondary" size="sm">
          <Cpu className="h-3.5 w-3.5" />
          Run Benchmark
        </Button>
      </div>
    </div>
  )
}

function renderGdprReportResponse(): ReactNode {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Shield className="h-4 w-4 text-[var(--purple)]" />
        <span className="text-sm font-semibold text-[var(--text-primary)]">GDPR Compliance Report</span>
        <Badge tone="purple" dot>Draft</Badge>
      </div>
      <div className="space-y-1.5">
        <div className="flex items-center justify-between rounded-lg border border-[var(--border-subtle)] px-3 py-2">
          <span className="text-xs text-[var(--text-secondary)]">Article 17 (Right to Erasure)</span>
          <CheckCircle2 className="h-4 w-4 text-[var(--success)]" />
        </div>
        <div className="flex items-center justify-between rounded-lg border border-[var(--border-subtle)] px-3 py-2">
          <span className="text-xs text-[var(--text-secondary)]">Article 32 (Security of Processing)</span>
          <CheckCircle2 className="h-4 w-4 text-[var(--success)]" />
        </div>
        <div className="flex items-center justify-between rounded-lg border border-[var(--border-subtle)] px-3 py-2">
          <span className="text-xs text-[var(--text-secondary)]">Article 5 (Lawful Processing)</span>
          <CheckCircle2 className="h-4 w-4 text-[var(--success)]" />
        </div>
        <div className="flex items-center justify-between rounded-lg border border-[var(--border-subtle)] px-3 py-2">
          <span className="text-xs text-[var(--text-secondary)]">Article 35 (DPIA)</span>
          <span className="text-xs font-medium text-[var(--warning)]">In Progress</span>
        </div>
        <div className="flex items-center justify-between rounded-lg border border-[var(--border-subtle)] px-3 py-2">
          <span className="text-xs text-[var(--text-secondary)]">Article 46 (Transfer Safeguards)</span>
          <span className="text-xs font-medium text-[var(--warning)]">Review Needed</span>
        </div>
      </div>
      <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-subtle)] p-3 text-xs">
        <div className="flex items-center justify-between">
          <span className="text-[var(--text-secondary)]">Overall compliance</span>
          <span className="font-semibold text-[var(--success)]">87%</span>
        </div>
        <div className="mt-1 h-2 overflow-hidden rounded-full bg-[var(--border-default)]">
          <div className="h-full w-[87%] rounded-full bg-[var(--success)] transition-all" />
        </div>
      </div>
      <div className="flex gap-2">
        <Button variant="primary" size="sm">
          <FileText className="h-3.5 w-3.5" />
          Generate Report
        </Button>
        <Button variant="secondary" size="sm">
          <ExternalLink className="h-3.5 w-3.5" />
          Export PDF
        </Button>
      </div>
    </div>
  )
}

function renderRecommendAlgoResponse(): ReactNode {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Sparkles className="h-4 w-4 text-[var(--accent)]" />
        <span className="text-sm font-semibold text-[var(--text-primary)]">Algorithm Recommendation</span>
      </div>
      <div className="rounded-lg border border-[var(--brand-border)] bg-[var(--brand-soft)] p-3">
        <div className="flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 text-[var(--brand)]" />
          <span className="text-sm font-medium text-[var(--brand-strong)]">Hybrid Engine (SISA + Influence)</span>
        </div>
        <p className="mt-1 text-xs text-[var(--text-secondary)]">
          Best suited for your data profile: 1,247 training samples, 768-dim embeddings, batch deletion requests
        </p>
      </div>
      <div className="space-y-1.5 text-xs">
        <p className="font-semibold text-[var(--text-primary)]">Why this recommendation</p>
        <ul className="space-y-1 text-[var(--text-secondary)]">
          <li className="flex items-start gap-2">
            <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--brand)]" />
            Data volume (1.2K samples) benefits from SISA sharding
          </li>
          <li className="flex items-start gap-2">
            <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--brand)]" />
            High-dimensional embeddings handled by influence functions
          </li>
          <li className="flex items-start gap-2">
            <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--brand)]" />
            Batch operations achieve 94.2% utility retention
          </li>
          <li className="flex items-start gap-2">
            <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--brand)]" />
            Cryptographically verifiable certificates supported natively
          </li>
        </ul>
      </div>
      <div className="flex gap-2">
        <Button variant="subtle" size="sm">
          <Cpu className="h-3.5 w-3.5" />
          Configure Engine
        </Button>
        <Button variant="secondary" size="sm">
          <BarChart3 className="h-3.5 w-3.5" />
          Compare All
        </Button>
      </div>
    </div>
  )
}

function renderVerifyCertResponse(): ReactNode {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Shield className="h-4 w-4 text-[var(--brand)]" />
        <span className="text-sm font-semibold text-[var(--text-primary)]">Verification Certificate</span>
        <Badge tone="success" dot>Verified</Badge>
      </div>
      <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-subtle)] p-3 space-y-2">
        <div className="flex items-center justify-between text-xs">
          <span className="text-[var(--text-tertiary)]">Certificate ID</span>
          <span className="font-mono text-[var(--text-primary)]">CERT-2026-0714-001</span>
        </div>
        <div className="flex items-center justify-between text-xs">
          <span className="text-[var(--text-tertiary)]">Algorithm</span>
          <span className="text-[var(--text-primary)]">Ed25519 + SHA256 Merkle Tree</span>
        </div>
        <div className="flex items-center justify-between text-xs">
          <span className="text-[var(--text-tertiary)]">Merkle Root</span>
          <span className="font-mono text-[var(--text-primary)]">7b4e2f...a8c3</span>
        </div>
        <div className="flex items-center justify-between text-xs">
          <span className="text-[var(--text-tertiary)]">Issued</span>
          <span className="text-[var(--text-primary)]">2026-07-14 10:02 UTC</span>
        </div>
        <div className="flex items-center justify-between text-xs">
          <span className="text-[var(--text-tertiary)]">Status</span>
          <Badge tone="success">Verified</Badge>
        </div>
      </div>
      <div className="space-y-1 text-xs text-[var(--text-secondary)]">
        <p className="font-semibold text-[var(--text-primary)]">Verification Steps</p>
        <ul className="space-y-1">
          <li className="flex items-center gap-2">
            <CheckCircle2 className="h-3.5 w-3.5 text-[var(--success)]" />
            SHA256 hash verification successful
          </li>
          <li className="flex items-center gap-2">
            <CheckCircle2 className="h-3.5 w-3.5 text-[var(--success)]" />
            Merkle proof validated
          </li>
          <li className="flex items-center gap-2">
            <CheckCircle2 className="h-3.5 w-3.5 text-[var(--success)]" />
            Ed25519 signature authentic
          </li>
          <li className="flex items-center gap-2">
            <CheckCircle2 className="h-3.5 w-3.5 text-[var(--success)]" />
            Certificate anchored to public ledger
          </li>
        </ul>
      </div>
      <div className="flex gap-2">
        <Button variant="subtle" size="sm">
          <FileText className="h-3.5 w-3.5" />
          View Certificate
        </Button>
        <Button variant="secondary" size="sm">
          <ExternalLink className="h-3.5 w-3.5" />
          Verify On-Chain
        </Button>
      </div>
    </div>
  )
}

function renderFailedExperimentsResponse(): ReactNode {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <AlertCircle className="h-4 w-4 text-[var(--danger)]" />
        <span className="text-sm font-semibold text-[var(--text-primary)]">Recent Failed Experiments</span>
        <Badge tone="danger" dot>3 Failed</Badge>
      </div>
      <div className="space-y-2">
        <div className="rounded-lg border border-[var(--danger-border)] bg-[var(--danger-soft)] p-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-[var(--text-primary)]">Batch Unlearn #AE-1024</span>
            <Badge tone="danger">Failed</Badge>
          </div>
          <p className="mt-1 text-xs text-[var(--text-secondary)]">MIA accuracy threshold exceeded (0.51 &gt; 0.50)</p>
          <p className="text-xs text-[var(--text-tertiary)]">2026-07-14 09:32 UTC</p>
        </div>
        <div className="rounded-lg border border-[var(--danger-border)] bg-[var(--danger-soft)] p-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-[var(--text-primary)]">Adapter v8 → v9 Retrain</span>
            <Badge tone="danger">Failed</Badge>
          </div>
          <p className="mt-1 text-xs text-[var(--text-secondary)]">GPU OOM during LoRA fine-tuning on sample batch</p>
          <p className="text-xs text-[var(--text-tertiary)]">2026-07-13 18:15 UTC</p>
        </div>
        <div className="rounded-lg border border-[var(--danger-border)] bg-[var(--danger-soft)] p-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-[var(--text-primary)]">Influence Calc #512</span>
            <Badge tone="danger">Failed</Badge>
          </div>
          <p className="mt-1 text-xs text-[var(--text-secondary)]">Embedding dimension mismatch: expected 768, got 512</p>
          <p className="text-xs text-[var(--text-tertiary)]">2026-07-12 22:45 UTC</p>
        </div>
      </div>
      <div className="flex gap-2">
        <Button variant="danger" size="sm">
          <RotateCcw className="h-3.5 w-3.5" />
          Retry All
        </Button>
        <Button variant="secondary" size="sm">
          <FileSearch className="h-3.5 w-3.5" />
          Investigate
        </Button>
      </div>
    </div>
  )
}

function renderAuditEventsResponse(): ReactNode {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Activity className="h-4 w-4 text-[var(--info)]" />
        <span className="text-sm font-semibold text-[var(--text-primary)]">Latest Audit Events</span>
        <Badge tone="info" dot>Live</Badge>
      </div>
      <div className="space-y-1">
        {[
          { time: "10:02:14", action: "Certificate Generated", id: "CERT-2026-0714-001", tone: "success" as const },
          { time: "10:01:55", action: "Knowledge Graph Refreshed", id: "KG-Update-84", tone: "info" as const },
          { time: "10:01:30", action: "Privacy Evaluation Passed", id: "PE-512", tone: "success" as const },
          { time: "09:58:12", action: "Batch Unlearn Initiated", id: "AE-1024", tone: "warning" as const },
          { time: "09:45:00", action: "User Authentication", id: "user@example.com", tone: "neutral" as const },
          { time: "09:30:22", action: "API Key Rotated", id: "key-prod-3", tone: "warning" as const },
        ].map((ev) => (
          <div
            key={ev.id}
            className="flex items-center gap-3 rounded-lg px-3 py-2 transition-colors hover:bg-[var(--bg-hover)]"
          >
            <span className="w-14 shrink-0 text-xs text-[var(--text-tertiary)] font-mono">{ev.time}</span>
            <Badge tone={ev.tone} dot={false} className="shrink-0">
              {ev.action}
            </Badge>
            <span className="truncate text-xs text-[var(--text-tertiary)] font-mono">{ev.id}</span>
          </div>
        ))}
      </div>
      <div className="flex gap-2">
        <Button variant="subtle" size="sm">
          <FileText className="h-3.5 w-3.5" />
          Full Audit Log
        </Button>
        <Button variant="secondary" size="sm">
          <ExternalLink className="h-3.5 w-3.5" />
          Navigate to Audit
        </Button>
      </div>
    </div>
  )
}

function renderSystemHealthResponse(): ReactNode {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Activity className="h-4 w-4 text-[var(--success)]" />
        <span className="text-sm font-semibold text-[var(--text-primary)]">System Health Overview</span>
      </div>
      <div className="space-y-2">
        <div className="flex items-center justify-between rounded-lg border border-[var(--border-subtle)] px-3 py-2">
          <div className="flex items-center gap-2">
            <Cpu className="h-3.5 w-3.5 text-[var(--success)]" />
            <span className="text-xs text-[var(--text-secondary)]">Unlearning Engine</span>
          </div>
          <Badge tone="success" dot>Healthy</Badge>
        </div>
        <div className="flex items-center justify-between rounded-lg border border-[var(--border-subtle)] px-3 py-2">
          <div className="flex items-center gap-2">
            <Database className="h-3.5 w-3.5 text-[var(--success)]" />
            <span className="text-xs text-[var(--text-secondary)]">Vector Database</span>
          </div>
          <Badge tone="success" dot>Healthy</Badge>
        </div>
        <div className="flex items-center justify-between rounded-lg border border-[var(--border-subtle)] px-3 py-2">
          <div className="flex items-center gap-2">
            <Database className="h-3.5 w-3.5 text-[var(--warning)]" />
            <span className="text-xs text-[var(--text-secondary)]">Message Store</span>
          </div>
          <Badge tone="warning" dot>Degraded</Badge>
        </div>
        <div className="flex items-center justify-between rounded-lg border border-[var(--border-subtle)] px-3 py-2">
          <div className="flex items-center gap-2">
            <Shield className="h-3.5 w-3.5 text-[var(--success)]" />
            <span className="text-xs text-[var(--text-secondary)]">Verification Service</span>
          </div>
          <Badge tone="success" dot>Healthy</Badge>
        </div>
        <div className="flex items-center justify-between rounded-lg border border-[var(--border-subtle)] px-3 py-2">
          <div className="flex items-center gap-2">
            <Clock className="h-3.5 w-3.5 text-[var(--warning)]" />
            <span className="text-xs text-[var(--text-secondary)]">LoRA Adapter Sync</span>
          </div>
          <Badge tone="warning" dot>Lagging</Badge>
        </div>
      </div>
      <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-subtle)] p-3 text-xs">
        <div className="flex items-center gap-2 text-[var(--warning)]">
          <AlertCircle className="h-3.5 w-3.5" />
          <span className="font-medium">Recent Changes</span>
        </div>
        <ul className="mt-1.5 space-y-1 text-[var(--text-secondary)]">
          <li className="flex items-start gap-2">
            <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--warning)]" />
            Message store replication lag increased to 2.4s
          </li>
          <li className="flex items-start gap-2">
            <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--info)]" />
            Verification service was upgraded to v2.1.0
          </li>
          <li className="flex items-start gap-2">
            <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--info)]" />
            3 new adapters deployed to staging
          </li>
        </ul>
      </div>
      <div className="flex gap-2">
        <Button variant="subtle" size="sm">
          <Activity className="h-3.5 w-3.5" />
          Dashboard
        </Button>
        <Button variant="secondary" size="sm">
          <BarChart3 className="h-3.5 w-3.5" />
          Metrics
        </Button>
      </div>
    </div>
  )
}

function renderGenericResponse(question: string): ReactNode {
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <Bot className="h-4 w-4 text-[var(--accent)]" />
        <span className="text-sm font-semibold text-[var(--text-primary)]">AI Assistant</span>
      </div>
      <p className="text-sm text-[var(--text-secondary)]">
        I understand you&apos;re asking about &ldquo;{question}&rdquo;. While I don&apos;t have specific data on this topic, I can help you with:
      </p>
      <ul className="space-y-1 text-xs text-[var(--text-secondary)]">
        <li className="flex items-center gap-2">
          <ChevronRight className="h-3 w-3 text-[var(--brand)]" />
          Explaining verification certificates and cryptographic proofs
        </li>
        <li className="flex items-center gap-2">
          <ChevronRight className="h-3 w-3 text-[var(--brand)]" />
          Comparing unlearning algorithms for your specific use case
        </li>
        <li className="flex items-center gap-2">
          <ChevronRight className="h-3 w-3 text-[var(--brand)]" />
          Generating compliance reports and audit summaries
        </li>
        <li className="flex items-center gap-2">
          <ChevronRight className="h-3 w-3 text-[var(--brand)]" />
          Analyzing trust scores and system health metrics
        </li>
      </ul>
      <p className="text-xs text-[var(--text-tertiary)]">Could you rephrase or choose one of these topics?</p>
    </div>
  )
}

const RESPONSE_RENDERERS: Record<ResponseType, () => ReactNode> = {
  trust_score: renderTrustScoreResponse,
  compare_sisa: renderCompareSisaResponse,
  gdpr_report: renderGdprReportResponse,
  recommend_algo: renderRecommendAlgoResponse,
  verify_cert: renderVerifyCertResponse,
  failed_experiments: renderFailedExperimentsResponse,
  audit_events: renderAuditEventsResponse,
  system_health: renderSystemHealthResponse,
  generic: () => renderGenericResponse(""),
}

function getFollowUpSuggestions(type: ResponseType): string[] {
  const map: Record<ResponseType, string[]> = {
    trust_score: ["How can I improve trust score?", "Compare weekly trends", "Show impacted models"],
    compare_sisa: ["When should I use full retraining?", "Show SISA sharding config", "Benchmark on my data"],
    gdpr_report: ["Download full report", "Schedule compliance audit", "View Article 17 details"],
    recommend_algo: ["Explain SISA algorithm", "Compare with Certified Removal", "Estimate compute cost"],
    verify_cert: ["View all certificates", "Run verification now", "Export certificate chain"],
    failed_experiments: ["View failure logs", "Retry with debug mode", "Notify engineering team"],
    audit_events: ["Filter by event type", "Export audit trail", "Set up alert rules"],
    system_health: ["View incident history", "Configure health alerts", "View resource usage"],
    generic: ["Compare SISA and Retraining", "Show latest audit events", "What changed in system health?"],
  }
  return map[type] ?? map.generic
}

export function AiCopilot() {
  const { isOpen, toggle } = useCopilot()
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState("")
  const [status, setStatus] = useState<CopilotStatus>("idle")
  const [followUps, setFollowUps] = useState<string[]>(SUGGESTED_QUESTIONS)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const panelRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [])

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 300)
    }
  }, [isOpen])

  useEffect(() => {
    scrollToBottom()
  }, [messages, status, scrollToBottom])

  useEffect(() => {
    if (!isOpen || !panelRef.current) return
    const panel = panelRef.current
    const focusable = panel.querySelectorAll<HTMLElement>(
      'button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])'
    )
    if (focusable.length > 0) focusable[0].focus()
    function handleTab(e: KeyboardEvent) {
      if (e.key !== "Tab") return
      const elements = panel.querySelectorAll<HTMLElement>(
        'button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])'
      )
      if (elements.length === 0) return
      const first = elements[0]
      const last = elements[elements.length - 1]
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault()
        last.focus()
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault()
        first.focus()
      }
    }
    panel.addEventListener("keydown", handleTab)
    return () => panel.removeEventListener("keydown", handleTab)
  }, [isOpen])

  const addUserMessage = useCallback((text: string) => {
    const msg: ChatMessage = { id: nextId(), role: "user", text, timestamp: new Date() }
    setMessages((prev) => [...prev, msg])
  }, [])

  const addAssistantMessage = useCallback((responseType: ResponseType) => {
    const msg: ChatMessage = { id: nextId(), role: "assistant", responseType, timestamp: new Date() }
    setMessages((prev) => [...prev, msg])
    setFollowUps(getFollowUpSuggestions(responseType))
    setStatus("idle")
    setErrorMessage(null)
  }, [])

  const simulateResponse = useCallback(
    (question: string) => {
      const type = classifyQuestion(question)
      addUserMessage(question)
      setStatus("thinking")
      setFollowUps([])
      const delay = 800 + Math.random() * 1200
      setTimeout(() => {
        const shouldError = Math.random() < 0.05
        if (shouldError) {
          setStatus("error")
          setErrorMessage("Failed to generate response. The AI service encountered an issue.")
        } else {
          addAssistantMessage(type)
        }
      }, delay)
    },
    [addUserMessage, addAssistantMessage]
  )

  const handleSend = useCallback(() => {
    const trimmed = input.trim()
    if (!trimmed || status === "thinking") return
    setInput("")
    simulateResponse(trimmed)
  }, [input, status, simulateResponse])

  const handleSuggested = useCallback(
    (question: string) => {
      simulateResponse(question)
    },
    [simulateResponse]
  )

  const handleRetry = useCallback(() => {
    const lastUserMsg = [...messages].reverse().find((m) => m.role === "user")
    if (lastUserMsg?.text) {
      setMessages((prev) => prev.filter((m) => m.role !== "assistant"))
      setStatus("thinking")
      setErrorMessage(null)
      const type = classifyQuestion(lastUserMsg.text)
      const delay = 800 + Math.random() * 1200
      setTimeout(() => {
        addAssistantMessage(type)
      }, delay)
    }
  }, [messages, addAssistantMessage])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault()
        handleSend()
      }
    },
    [handleSend]
  )

  const renderMessage = (msg: ChatMessage) => {
    if (msg.role === "user") {
      return (
        <div key={msg.id} className="flex justify-end animate-fade-up">
          <div className="max-w-[85%] rounded-2xl rounded-br-sm bg-[var(--brand)] px-4 py-2.5">
            {renderUserMessage(msg.text ?? "")}
          </div>
        </div>
      )
    }
    return (
      <div key={msg.id} className="flex justify-start animate-fade-up">
        <div className="max-w-[85%] rounded-2xl rounded-bl-sm border border-[var(--border-subtle)] bg-[var(--bg-surface-elevated)] p-4 shadow-[var(--shadow-sm)]">
          {msg.responseType && RESPONSE_RENDERERS[msg.responseType]?.()}
        </div>
      </div>
    )
  }

  const isMac =
    typeof navigator !== "undefined" ? navigator.platform.toLowerCase().includes("mac") : false
  const modifierKey = isMac ? "\u2318" : "Ctrl+"

  return (
    <>
      <AnimatePresence>
        {!isOpen && (
          <motion.button
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0, opacity: 0 }}
            transition={{ type: "spring", stiffness: 400, damping: 25 }}
            onClick={toggle}
            className="fixed bottom-6 right-6 z-40 flex h-12 w-12 items-center justify-center rounded-full bg-[var(--brand)] text-white shadow-[var(--shadow-lg)] transition-shadow hover:shadow-[var(--shadow-lg)] hover:brightness-110 active:scale-95 cursor-pointer"
            aria-label="Open AI Copilot"
            title={`AI Copilot (${modifierKey}K)`}
          >
            <Bot className="h-5 w-5" />
          </motion.button>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {isOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="fixed inset-0 z-40 bg-black/20 backdrop-blur-[2px]"
              onClick={toggle}
              aria-hidden="true"
            />
            <motion.div
              ref={panelRef}
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              transition={{ type: "spring", stiffness: 300, damping: 30 }}
              className="fixed inset-y-0 right-0 z-50 flex w-full max-w-[440px] flex-col border-l border-[var(--border-default)] bg-[var(--bg-surface)] shadow-[var(--shadow-lg)]"
              role="dialog"
              aria-modal="true"
              aria-label="AI Copilot"
            >
              <div className="flex shrink-0 items-center justify-between border-b border-[var(--border-subtle)] px-5 py-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--brand-soft)]">
                    <Bot className="h-4 w-4 text-[var(--brand)]" />
                  </div>
                  <div>
                    <h2 className="text-sm font-semibold text-[var(--text-primary)]">AI Copilot</h2>
                    <div className="flex items-center gap-1.5">
                      <span
                        className={clsx(
                          "h-1.5 w-1.5 rounded-full",
                          status === "thinking"
                            ? "bg-[var(--warning)] animate-pulse"
                            : status === "error"
                              ? "bg-[var(--danger)]"
                              : "bg-[var(--success)]"
                        )}
                      />
                      <span className="text-[11px] text-[var(--text-tertiary)]">
                        {status === "thinking" ? "Thinking..." : status === "error" ? "Error" : "Online"}
                      </span>
                    </div>
                  </div>
                </div>
                <button
                  onClick={toggle}
                  className="flex h-8 w-8 items-center justify-center rounded-lg text-[var(--text-tertiary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)] cursor-pointer"
                  aria-label="Close AI Copilot"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
                {messages.length === 0 && status === "idle" && (
                  <div className="flex flex-col items-center justify-center py-8 text-center">
                    <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-[var(--brand-soft)]">
                      <Sparkles className="h-6 w-6 text-[var(--brand)]" />
                    </div>
                    <h3 className="mt-4 text-sm font-semibold text-[var(--text-primary)]">
                      How can I help you?
                    </h3>
                    <p className="mt-1 text-xs text-[var(--text-tertiary)]">
                      Ask me anything about your unlearning pipeline
                    </p>
                    <div className="mt-6 flex w-full flex-wrap gap-2">
                      {SUGGESTED_QUESTIONS.map((q) => (
                        <button
                          key={q}
                          onClick={() => handleSuggested(q)}
                          className="rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] px-3 py-2 text-xs text-[var(--text-secondary)] transition-all hover:border-[var(--brand-border)] hover:bg-[var(--brand-soft)] hover:text-[var(--brand-strong)] cursor-pointer"
                        >
                          {q}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {messages.map(renderMessage)}

                {status === "thinking" && (
                  <div className="flex justify-start animate-fade-up">
                    <div className="rounded-2xl rounded-bl-sm border border-[var(--border-subtle)] bg-[var(--bg-surface-elevated)] px-4 py-3 shadow-[var(--shadow-sm)]">
                      <div className="flex items-center gap-2 text-sm text-[var(--text-tertiary)]">
                        <Bot className="h-4 w-4" />
                        <TypingDots />
                      </div>
                    </div>
                  </div>
                )}

                {status === "error" && (
                  <div className="flex justify-start animate-fade-up">
                    <div className="max-w-[85%] rounded-2xl rounded-bl-sm border border-[var(--danger-border)] bg-[var(--danger-soft)] p-4">
                      <div className="flex items-center gap-2">
                        <AlertCircle className="h-4 w-4 text-[var(--danger)]" />
                        <span className="text-sm font-medium text-[var(--danger)]">Error</span>
                      </div>
                      <p className="mt-1 text-xs text-[var(--text-secondary)]">
                        {errorMessage ?? "Something went wrong. Please try again."}
                      </p>
                      <Button
                        variant="danger"
                        size="sm"
                        className="mt-2"
                        onClick={handleRetry}
                      >
                        <RotateCcw className="h-3.5 w-3.5" />
                        Retry
                      </Button>
                    </div>
                  </div>
                )}

                {status === "idle" && followUps.length > 0 && messages.length > 0 && (
                  <div className="space-y-2 animate-fade-up">
                    <p className="text-xs font-medium text-[var(--text-tertiary)]">Follow up</p>
                    <div className="flex flex-wrap gap-2">
                      {followUps.map((q) => (
                        <button
                          key={q}
                          onClick={() => handleSuggested(q)}
                          className="flex items-center gap-1 rounded-full border border-[var(--border-default)] bg-[var(--bg-surface)] px-3 py-1.5 text-xs text-[var(--text-secondary)] transition-all hover:border-[var(--brand-border)] hover:bg-[var(--brand-soft)] hover:text-[var(--brand-strong)] cursor-pointer"
                        >
                          {q}
                          <ArrowUpRight className="h-3 w-3" />
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>

              <div className="shrink-0 border-t border-[var(--border-subtle)] px-5 py-4">
                <div className="flex items-center gap-2">
                  <div className="relative flex-1">
                    <input
                      ref={inputRef}
                      type="text"
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      onKeyDown={handleKeyDown}
                      placeholder="Ask a question..."
                      disabled={status === "thinking"}
                      className="w-full rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] px-4 py-2.5 pr-10 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] transition-colors focus:border-[var(--brand)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)] disabled:opacity-50"
                    />
                  </div>
                  <button
                    onClick={handleSend}
                    disabled={!input.trim() || status === "thinking"}
                    className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[var(--brand)] text-white transition-all hover:bg-[var(--brand-strong)] disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
                    aria-label="Send message"
                  >
                    <Send className="h-4 w-4" />
                  </button>
                </div>
                <p className="mt-2 text-[11px] text-[var(--text-tertiary)] text-center">
                  {modifierKey}K to toggle &middot; Esc to close
                </p>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  )
}
