"use client"

import { useState, useMemo } from "react"
import { motion } from "framer-motion"
import { clsx } from "clsx"
import { toast } from "sonner"
import { Card, CardHeader, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge, statusTone } from "@/components/ui/badge"
import { PageHeader, StatCard } from "@/components/ui/page-header"
import { Progress } from "@/components/ui/progress"
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select"
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer,
} from "recharts"
import {
  FlaskConical,
  CheckCircle2,
  XCircle,
  MoreHorizontal,
  Copy,
  Download,
  BarChart3,
  Activity,
  X,
  Search,
  Columns3,
} from "lucide-react"
import * as Dialog from "@radix-ui/react-dialog"

interface TrainingCurve {
  epoch: number
  loss: number
  accuracy: number
  valLoss: number
  valAccuracy: number
}

interface ConfusionMatrix {
  labels: string[]
  values: number[][]
}

interface ResourceUsage {
  time: string
  gpu: number
  cpu: number
  memory: number
}

interface Experiment {
  id: string
  name: string
  status: "running" | "completed" | "failed"
  algorithm: string
  dataset: string
  progress: number
  accuracy: number
  f1Score: number
  privacyScore: number
  trainingTime: number
  createdDate: string
  tags: string[]
  config: Record<string, string | number | boolean>
  trainingCurves: TrainingCurve[]
  confusionMatrix: ConfusionMatrix
  resourceUsage: ResourceUsage[]
}

const algorithms = ["SISA", "Influence", "Certified Removal", "Hybrid", "DeltaGrad"]
const datasetOptions = ["cifar-10", "imdb", "wikitext-103", "mnist", "flickr30k", "sst-2", "ag-news", "pubmed"]
const tagOptions = ["privacy", "utility", "benchmark", "production", "debug", "ablation", "baseline"]

function generateCurves(): TrainingCurve[] {
  return Array.from({ length: 10 }, (_, i) => {
    const base = 1.8 - i * 0.15 + Math.random() * 0.1
    return {
      epoch: i + 1,
      loss: Math.max(0.05, base + (Math.random() - 0.5) * 0.1),
      accuracy: Math.min(1, 0.4 + i * 0.05 + Math.random() * 0.04),
      valLoss: Math.max(0.1, base + 0.2 + (Math.random() - 0.5) * 0.12),
      valAccuracy: Math.min(0.95, 0.35 + i * 0.045 + Math.random() * 0.05),
    }
  })
}

function generateConfusionMatrix(): ConfusionMatrix {
  const labels = ["Class A", "Class B", "Class C", "Class D"]
  return {
    labels,
    values: labels.map(() => labels.map(() => Math.floor(Math.random() * 80 + 10))),
  }
}

function generateResourceUsage(): ResourceUsage[] {
  return Array.from({ length: 20 }, (_, i) => ({
    time: `${i * 30}s`,
    gpu: 40 + Math.random() * 50 + Math.sin(i * 0.5) * 15,
    cpu: 20 + Math.random() * 40,
    memory: 30 + Math.random() * 30,
  }))
}

function generateMockExperiments(count: number = 18): Experiment[] {
  return Array.from({ length: count }, (_, i) => {
    const statuses: Experiment["status"][] = ["running", "completed", "completed", "completed", "failed", "running"]
    const status = statuses[i % statuses.length]
    const progress = status === "completed" ? 100 : status === "failed" ? Math.floor(Math.random() * 60 + 10) : Math.floor(Math.random() * 70 + 20)
    const accuracy = status === "completed" ? 0.75 + Math.random() * 0.2 : status === "running" ? 0.4 + Math.random() * 0.3 : 0.2 + Math.random() * 0.3
    return {
      id: `exp_${(i + 1).toString().padStart(4, "0")}`,
      name: `${["LoRA Fine-tune", "Full Finetune", "Adapters Test", "Ablation Study", "Hyperparameter Search", "Cross-valid Run", "Privacy Audit", "Forget Quality"][i % 8]} v${Math.floor(i / 8) + 1}.${i % 4}`,
      status,
      algorithm: algorithms[i % algorithms.length],
      dataset: datasetOptions[i % datasetOptions.length],
      progress,
      accuracy,
      f1Score: accuracy * (0.85 + Math.random() * 0.15),
      privacyScore: status === "completed" ? 0.6 + Math.random() * 0.35 : 0.3 + Math.random() * 0.3,
      trainingTime: Math.floor(Math.random() * 3600 + 120),
      createdDate: new Date(Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000).toISOString(),
      tags: [
        tagOptions[i % tagOptions.length],
        tagOptions[(i + 2) % tagOptions.length],
      ].filter(Boolean) as string[],
      config: {
        learning_rate: [2e-5, 1e-4, 5e-5][i % 3],
        batch_size: [8, 16, 32][i % 3],
        epochs: [10, 20, 30][i % 3],
        lora_rank: [8, 16][i % 2],
        lora_alpha: [16, 32, 64][i % 3],
        warmup_steps: [100, 200, 500][i % 3],
        weight_decay: 0.01,
        optimizer: ["adamw", "sgd"][i % 2],
      },
      trainingCurves: generateCurves(),
      confusionMatrix: generateConfusionMatrix(),
      resourceUsage: generateResourceUsage(),
    }
  })
}

interface CompareMetrics {
  name: string
  [key: string]: string | number
}

function ExperimentDetailModal({
  experiment,
  open,
  onClose,
}: {
  experiment: Experiment
  open: boolean
  onClose: () => void
}) {
  const curveData = experiment.trainingCurves.map((c) => ({
    epoch: c.epoch,
    Loss: Number(c.loss.toFixed(4)),
    Accuracy: Number((c.accuracy * 100).toFixed(1)),
    "Val Loss": Number(c.valLoss.toFixed(4)),
    "Val Accuracy": Number((c.valAccuracy * 100).toFixed(1)),
  }))

  const handleDownload = () => toast.success("Results downloaded")
  const handleClone = () => toast.success("Experiment cloned")

  return (
    <Dialog.Root open={open} onOpenChange={(v) => !v && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 max-h-[85vh] w-full max-w-4xl -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-xl border border-[var(--border-default)] bg-[var(--bg-surface)] shadow-[var(--shadow-lg)]">
          <div className="sticky top-0 z-10 flex items-center justify-between border-b border-[var(--border-subtle)] bg-[var(--bg-surface)] px-6 py-4">
            <div className="min-w-0">
              <Dialog.Title className="text-base font-semibold text-[var(--text-primary)]">{experiment.name}</Dialog.Title>
              <p className="mt-0.5 text-xs text-[var(--text-secondary)]">
                {experiment.algorithm} · {experiment.dataset}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Badge tone={statusTone(experiment.status)} dot>{experiment.status}</Badge>
              <Dialog.Close className="rounded-lg p-1.5 text-[var(--text-tertiary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]">
                <X className="h-4 w-4" />
              </Dialog.Close>
            </div>
          </div>

          <div className="space-y-6 p-6">
            <div className="grid grid-cols-4 gap-3">
              <div className="rounded-lg bg-[var(--bg-subtle)] p-3 text-center">
                <p className="text-xs text-[var(--text-tertiary)]">Accuracy</p>
                <p className="mt-1 text-lg font-semibold text-[var(--text-primary)]">{(experiment.accuracy * 100).toFixed(1)}%</p>
              </div>
              <div className="rounded-lg bg-[var(--bg-subtle)] p-3 text-center">
                <p className="text-xs text-[var(--text-tertiary)]">F1 Score</p>
                <p className="mt-1 text-lg font-semibold text-[var(--text-primary)]">{(experiment.f1Score * 100).toFixed(1)}%</p>
              </div>
              <div className="rounded-lg bg-[var(--bg-subtle)] p-3 text-center">
                <p className="text-xs text-[var(--text-tertiary)]">Privacy Score</p>
                <p className="mt-1 text-lg font-semibold text-[var(--text-primary)]">{(experiment.privacyScore * 100).toFixed(1)}%</p>
              </div>
              <div className="rounded-lg bg-[var(--bg-subtle)] p-3 text-center">
                <p className="text-xs text-[var(--text-tertiary)]">Training Time</p>
                <p className="mt-1 text-lg font-semibold text-[var(--text-primary)]">{Math.floor(experiment.trainingTime / 60)}m {experiment.trainingTime % 60}s</p>
              </div>
            </div>

            <div>
              <p className="mb-3 text-sm font-semibold text-[var(--text-primary)]">Training Curves</p>
              <div className="rounded-lg border border-[var(--border-subtle)] p-4">
                <ResponsiveContainer width="100%" height={280}>
                  <LineChart data={curveData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
                    <XAxis dataKey="epoch" stroke="var(--text-tertiary)" fontSize={11} tickMargin={8} label={{ value: "Epoch", position: "insideBottom", offset: -4, style: { fill: "var(--text-tertiary)", fontSize: 11 } }} />
                    <YAxis yAxisId="left" stroke="var(--text-tertiary)" fontSize={11} tickMargin={8} label={{ value: "Loss", angle: -90, position: "insideLeft", style: { fill: "var(--text-tertiary)", fontSize: 11 } }} />
                    <YAxis yAxisId="right" orientation="right" stroke="var(--text-tertiary)" fontSize={11} tickMargin={8} label={{ value: "Accuracy (%)", angle: 90, position: "insideRight", style: { fill: "var(--text-tertiary)", fontSize: 11 } }} domain={[0, 100]} />
                    <RechartsTooltip
                      contentStyle={{ background: "var(--bg-surface-elevated)", border: "1px solid var(--border-default)", borderRadius: 8, fontSize: 12 }}
                      labelStyle={{ color: "var(--text-primary)" }}
                    />
                    <Legend wrapperStyle={{ fontSize: 11, color: "var(--text-secondary)" }} />
                    <Line yAxisId="left" type="monotone" dataKey="Loss" stroke="var(--chart-1)" strokeWidth={2} dot={false} />
                    <Line yAxisId="left" type="monotone" dataKey="Val Loss" stroke="var(--chart-2)" strokeWidth={2} strokeDasharray="4 4" dot={false} />
                    <Line yAxisId="right" type="monotone" dataKey="Accuracy" stroke="var(--chart-3)" strokeWidth={2} dot={false} />
                    <Line yAxisId="right" type="monotone" dataKey="Val Accuracy" stroke="var(--chart-4)" strokeWidth={2} strokeDasharray="4 4" dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-6">
              <div>
                <p className="mb-3 text-sm font-semibold text-[var(--text-primary)]">Confusion Matrix</p>
                <div className="overflow-hidden rounded-lg border border-[var(--border-subtle)]">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="bg-[var(--bg-subtle)]">
                        <th className="p-2 text-left text-[var(--text-tertiary)] font-medium" />
                        {experiment.confusionMatrix.labels.map((l) => (
                          <th key={l} className="p-2 text-center text-[var(--text-tertiary)] font-medium">{l}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {experiment.confusionMatrix.values.map((row, i) => (
                        <tr key={i} className="border-t border-[var(--border-subtle)]">
                          <td className="p-2 font-medium text-[var(--text-secondary)]">{experiment.confusionMatrix.labels[i]}</td>
                          {row.map((val, j) => {
                            const maxVal = Math.max(...experiment.confusionMatrix.values.flat())
                            const intensity = (val / maxVal) * 0.8 + 0.2
                            return (
                              <td
                                key={j}
                                className="p-2 text-center font-mono tabular-nums"
                                style={{
                                  backgroundColor: i === j
                                    ? `color-mix(in srgb, var(--brand) ${intensity * 60}%, transparent)`
                                    : `color-mix(in srgb, var(--danger) ${intensity * 30}%, transparent)`,
                                  color: i === j ? "var(--text-on-brand)" : "var(--text-primary)",
                                }}
                              >
                                {val}
                              </td>
                            )
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div>
                <p className="mb-3 text-sm font-semibold text-[var(--text-primary)]">Privacy-Utility Tradeoff</p>
                <div className="flex h-full items-center justify-center rounded-lg border border-[var(--border-subtle)] p-4">
                  <ResponsiveContainer width="100%" height={220}>
                    <BarChart data={[{ name: "Privacy", value: experiment.privacyScore * 100, fill: "var(--chart-2)" }, { name: "Utility", value: experiment.accuracy * 100, fill: "var(--chart-1)" }]}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
                      <XAxis dataKey="name" stroke="var(--text-tertiary)" fontSize={11} />
                      <YAxis domain={[0, 100]} stroke="var(--text-tertiary)" fontSize={11} label={{ value: "Score (%)", angle: -90, position: "insideLeft", style: { fill: "var(--text-tertiary)", fontSize: 11 } }} />
                      <RechartsTooltip
                        contentStyle={{ background: "var(--bg-surface-elevated)", border: "1px solid var(--border-default)", borderRadius: 8, fontSize: 12 }}
                      />
                      <Bar dataKey="value" fill="var(--chart-1)" radius={[4, 4, 0, 0]} barSize={60} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>

            <div>
              <p className="mb-3 text-sm font-semibold text-[var(--text-primary)]">Resource Usage</p>
              <div className="rounded-lg border border-[var(--border-subtle)] p-4">
                <ResponsiveContainer width="100%" height={220}>
                  <LineChart data={experiment.resourceUsage}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
                    <XAxis dataKey="time" stroke="var(--text-tertiary)" fontSize={10} tickMargin={8} />
                    <YAxis domain={[0, 100]} stroke="var(--text-tertiary)" fontSize={10} tickMargin={8} label={{ value: "Usage %", angle: -90, position: "insideLeft", style: { fill: "var(--text-tertiary)", fontSize: 11 } }} />
                    <RechartsTooltip
                      contentStyle={{ background: "var(--bg-surface-elevated)", border: "1px solid var(--border-default)", borderRadius: 8, fontSize: 12 }}
                    />
                    <Legend wrapperStyle={{ fontSize: 11, color: "var(--text-secondary)" }} />
                    <Line type="monotone" dataKey="gpu" stroke="var(--chart-5)" strokeWidth={2} dot={false} name="GPU" />
                    <Line type="monotone" dataKey="cpu" stroke="var(--chart-3)" strokeWidth={2} dot={false} name="CPU" />
                    <Line type="monotone" dataKey="memory" stroke="var(--chart-4)" strokeWidth={2} dot={false} name="Memory" />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div>
              <p className="mb-3 text-sm font-semibold text-[var(--text-primary)]">Configuration</p>
              <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-app)] p-3">
                <pre className="max-h-40 overflow-y-auto font-mono text-[11px] text-[var(--text-secondary)] whitespace-pre-wrap">
                  {JSON.stringify(experiment.config, null, 2)}
                </pre>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Button variant="primary" size="sm" onClick={handleDownload}>
                <Download className="h-4 w-4" /> Download Results
              </Button>
              <Button variant="outline" size="sm" onClick={handleClone}>
                <Copy className="h-4 w-4" /> Clone Experiment
              </Button>
              <Button variant="secondary" size="sm" onClick={() => toast.success("Exporting as PDF...")}>
                <BarChart3 className="h-4 w-4" /> Export as PDF
              </Button>
            </div>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}

function ExperimentCard({
  experiment,
  compareMode,
  selectedForCompare,
  onToggleCompare,
  onClick,
}: {
  experiment: Experiment
  compareMode: boolean
  selectedForCompare: boolean
  onToggleCompare: (id: string) => void
  onClick: () => void
}) {
  const elapsed = Math.floor((Date.now() - new Date(experiment.createdDate).getTime()) / (1000 * 60 * 60 * 24))

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className={clsx(
        "surface rounded-xl overflow-hidden transition-all",
        selectedForCompare && "ring-2 ring-[var(--brand)]",
        compareMode && "cursor-pointer",
      )}
    >
      <div className="p-4" onClick={compareMode ? () => onToggleCompare(experiment.id) : onClick}>
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              {compareMode && (
                <div
                  className={clsx(
                    "h-4 w-4 rounded border-2 transition-colors shrink-0",
                    selectedForCompare
                      ? "border-[var(--brand)] bg-[var(--brand)]"
                      : "border-[var(--border-strong)]",
                  )}
                >
                  {selectedForCompare && (
                    <svg viewBox="0 0 16 16" className="h-full w-full text-[var(--text-on-brand)]">
                      <path d="M4 8l3 3 5-5" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  )}
                </div>
              )}
              <p className="truncate text-sm font-semibold text-[var(--text-primary)]">{experiment.name}</p>
            </div>
            <div className="mt-1.5 flex items-center gap-2">
              <Badge tone={statusTone(experiment.status)} dot>
                {experiment.status}
              </Badge>
              <span className="text-xs text-[var(--text-tertiary)]">{experiment.algorithm}</span>
            </div>
          </div>
          {!compareMode && (
            <div className="relative" onClick={(e) => e.stopPropagation()}>
              <button
                className="rounded-lg p-1.5 text-[var(--text-tertiary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
              >
                <MoreHorizontal className="h-4 w-4" />
              </button>
            </div>
          )}
        </div>

        <div className="mt-3 text-xs text-[var(--text-secondary)]">
          {experiment.dataset}
        </div>

        {experiment.status === "running" && (
          <div className="mt-3">
            <div className="flex items-center justify-between text-xs mb-1.5">
              <span className="text-[var(--text-tertiary)]">Progress</span>
              <span className="text-[var(--text-secondary)]">{experiment.progress}%</span>
            </div>
            <Progress value={experiment.progress} tone="info" size="sm" />
          </div>
        )}

        <div className="mt-3 grid grid-cols-2 gap-2">
          <div className="rounded-md bg-[var(--bg-subtle)] p-2 text-center">
            <p className="text-[10px] uppercase tracking-wider text-[var(--text-tertiary)]">Accuracy</p>
            <p className="mt-0.5 text-sm font-semibold tabular-nums text-[var(--text-primary)]">
              {(experiment.accuracy * 100).toFixed(1)}%
            </p>
          </div>
          <div className="rounded-md bg-[var(--bg-subtle)] p-2 text-center">
            <p className="text-[10px] uppercase tracking-wider text-[var(--text-tertiary)]">F1</p>
            <p className="mt-0.5 text-sm font-semibold tabular-nums text-[var(--text-primary)]">
              {(experiment.f1Score * 100).toFixed(1)}%
            </p>
          </div>
          <div className="rounded-md bg-[var(--bg-subtle)] p-2 text-center">
            <p className="text-[10px] uppercase tracking-wider text-[var(--text-tertiary)]">Privacy</p>
            <p className="mt-0.5 text-sm font-semibold tabular-nums text-[var(--text-primary)]">
              {(experiment.privacyScore * 100).toFixed(1)}%
            </p>
          </div>
          <div className="rounded-md bg-[var(--bg-subtle)] p-2 text-center">
            <p className="text-[10px] uppercase tracking-wider text-[var(--text-tertiary)]">Time</p>
            <p className="mt-0.5 text-sm font-semibold tabular-nums text-[var(--text-primary)]">
              {Math.floor(experiment.trainingTime / 60)}m
            </p>
          </div>
        </div>

        <div className="mt-3 flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            {experiment.tags.map((tag) => (
              <span
                key={tag}
                className="rounded-full bg-[var(--bg-subtle)] px-2 py-0.5 text-[10px] font-medium text-[var(--text-tertiary)]"
              >
                {tag}
              </span>
            ))}
          </div>
          <span className="text-[10px] text-[var(--text-tertiary)]">{elapsed}d ago</span>
        </div>
      </div>
    </motion.div>
  )
}

function CompareView({ experiments }: { experiments: Experiment[] }) {
  const compareMetrics: CompareMetrics[] = useMemo(() => {
    const keys = ["accuracy", "f1Score", "privacyScore", "trainingTime"] as const
    const labels: Record<string, string> = {
      accuracy: "Accuracy (%)",
      f1Score: "F1 Score (%)",
      privacyScore: "Privacy Score (%)",
      trainingTime: "Training Time (s)",
    }
    return keys.map((key) => ({
      name: labels[key],
      ...Object.fromEntries(
        experiments.map((e) => {
          const val = e[key]
          return [e.name, key === "trainingTime" ? val : Number((val * 100).toFixed(1))]
        }),
      ),
    }))
  }, [experiments])

  const radarData = useMemo(() => {
    return experiments.map((e) => ({
      name: e.name,
      Accuracy: Number((e.accuracy * 100).toFixed(1)),
      F1: Number((e.f1Score * 100).toFixed(1)),
      Privacy: Number((e.privacyScore * 100).toFixed(1)),
      Efficiency: Number(Math.max(0, 100 - e.trainingTime / 36).toFixed(1)),
    }))
  }, [experiments])

  const barData = useMemo(() => {
    return experiments.map((e) => ({
      name: e.name,
      Accuracy: Number((e.accuracy * 100).toFixed(1)),
      F1: Number((e.f1Score * 100).toFixed(1)),
    }))
  }, [experiments])

  const chartColors = ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)", "var(--chart-4)"]

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader title="Metric Comparison" description="Side-by-side experiment results" />
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--border-subtle)]">
                  <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">Metric</th>
                  {experiments.map((e) => (
                    <th key={e.id} className="px-4 py-2.5 text-left text-xs font-semibold text-[var(--text-primary)]">{e.name}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {compareMetrics.map((row, i) => (
                  <tr key={i} className="border-b border-[var(--border-subtle)] last:border-0">
                    <td className="px-4 py-2.5 text-[var(--text-secondary)]">{row.name}</td>
                    {experiments.map((e) => {
                      const val = row[e.name]
                      return (
                        <td key={e.id} className="px-4 py-2.5 font-mono tabular-nums text-[var(--text-primary)]">
                          {typeof val === "number" ? val : val}
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader title="Radar Comparison" />
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <RadarChart data={radarData.length > 0 ? (radarData[0] ? [{ ...radarData[0], ...Object.fromEntries(radarData.slice(1).flatMap((r) => Object.entries(r).map(([k, v]) => [`${r.name}_${k}`, v]))) }] : []) : []}>
                <PolarGrid stroke="var(--border-subtle)" />
                <PolarAngleAxis dataKey="name" tick={{ fill: "var(--text-tertiary)", fontSize: 10 }} />
                <PolarRadiusAxis tick={{ fill: "var(--text-tertiary)", fontSize: 10 }} domain={[0, 100]} />
                {experiments.map((e, i) => (
                  <Radar
                    key={e.id}
                    name={e.name}
                    dataKey="Accuracy"
                    stroke={chartColors[i]}
                    fill={chartColors[i]}
                    fillOpacity={0.1}
                  />
                ))}
              </RadarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader title="Accuracy & F1 Comparison" />
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={barData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
                <XAxis dataKey="name" tick={{ fill: "var(--text-tertiary)", fontSize: 10 }} />
                <YAxis domain={[0, 100]} tick={{ fill: "var(--text-tertiary)", fontSize: 10 }} />
                <RechartsTooltip
                  contentStyle={{ background: "var(--bg-surface-elevated)", border: "1px solid var(--border-default)", borderRadius: 8, fontSize: 12 }}
                />
                <Legend wrapperStyle={{ fontSize: 11, color: "var(--text-secondary)" }} />
                <Bar dataKey="Accuracy" fill="var(--chart-1)" radius={[4, 4, 0, 0]} />
                <Bar dataKey="F1" fill="var(--chart-2)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default function ExperimentsPage() {
  const [experiments] = useState<Experiment[]>(generateMockExperiments)
  const [search, setSearch] = useState("")
  const [algoFilter, setAlgoFilter] = useState<string>("")
  const [statusFilter, setStatusFilter] = useState<string>("")
  const [datasetFilter, setDatasetFilter] = useState<string>("")
  const [compareMode, setCompareMode] = useState(false)
  const [compareIds, setCompareIds] = useState<string[]>([])
  const [selectedExp, setSelectedExp] = useState<Experiment | null>(null)

  const filtered = useMemo(() => {
    return experiments.filter((e) => {
      if (search && !e.name.toLowerCase().includes(search.toLowerCase()) && !e.id.toLowerCase().includes(search.toLowerCase())) return false
      if (algoFilter && e.algorithm !== algoFilter) return false
      if (statusFilter && e.status !== statusFilter) return false
      if (datasetFilter && e.dataset !== datasetFilter) return false
      return true
    })
  }, [experiments, search, algoFilter, statusFilter, datasetFilter])

  const stats = useMemo(() => ({
    total: experiments.length,
    running: experiments.filter((e) => e.status === "running").length,
    completed: experiments.filter((e) => e.status === "completed").length,
    failed: experiments.filter((e) => e.status === "failed").length,
  }), [experiments])

  const handleNewExperiment = () => toast.success("New experiment creation wizard opened")

  const toggleCompare = (id: string) => {
    setCompareIds((prev) => {
      if (prev.includes(id)) return prev.filter((i) => i !== id)
      if (prev.length >= 4) {
        toast.error("You can compare up to 4 experiments")
        return prev
      }
      return [...prev, id]
    })
  }

  const comparedExperiments = experiments.filter((e) => compareIds.includes(e.id))

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="Experiments"
        description="Track, compare, and analyze unlearning experiments"
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant={compareMode ? "subtle" : "outline"}
              size="sm"
              onClick={() => { setCompareMode(!compareMode); if (compareMode) setCompareIds([]) }}
            >
              <Columns3 className="h-4 w-4" />
              {compareMode ? "Exit Compare" : "Compare"}
            </Button>
            <Button variant="primary" size="sm" onClick={handleNewExperiment}>
              <FlaskConical className="h-4 w-4" />
              New Experiment
            </Button>
          </div>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Total Experiments" value={stats.total} icon={BarChart3} tone="brand" />
        <StatCard label="Running" value={stats.running} icon={Activity} tone="info" hint={stats.running > 0 ? "In progress" : undefined} />
        <StatCard label="Completed" value={stats.completed} icon={CheckCircle2} tone="success" />
        <StatCard label="Failed" value={stats.failed} icon={XCircle} tone="danger" />
      </div>

      <Card>
        <CardContent className="pt-5">
          <div className="mb-5 flex flex-wrap items-center gap-3">
            <div className="relative flex-1 min-w-[200px] max-w-sm">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--text-tertiary)]" />
              <input
                type="text"
                placeholder="Search experiments..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] py-2 pl-9 pr-3 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
              />
            </div>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-32" aria-label="Filter by status">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All</SelectItem>
                <SelectItem value="running">Running</SelectItem>
                <SelectItem value="completed">Completed</SelectItem>
                <SelectItem value="failed">Failed</SelectItem>
              </SelectContent>
            </Select>
            <Select value={algoFilter} onValueChange={setAlgoFilter}>
              <SelectTrigger className="w-40" aria-label="Filter by algorithm">
                <SelectValue placeholder="Algorithm" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All</SelectItem>
                {algorithms.map((a) => (
                  <SelectItem key={a} value={a}>{a}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={datasetFilter} onValueChange={setDatasetFilter}>
              <SelectTrigger className="w-36" aria-label="Filter by dataset">
                <SelectValue placeholder="Dataset" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All</SelectItem>
                {datasetOptions.map((d) => (
                  <SelectItem key={d} value={d}>{d}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {compareMode && (
            <div className="mb-4 flex items-center gap-3 rounded-lg border border-[var(--info-border)] bg-[var(--info-soft)] px-4 py-2.5">
              <span className="text-sm text-[var(--info)]">
                Select 2–4 experiments to compare
              </span>
              {compareIds.length >= 2 && (
                <Button
                  variant="primary"
                  size="sm"
                  className="ml-auto"
                  onClick={() => setCompareMode(true)}
                >
                  Compare ({compareIds.length})
                </Button>
              )}
              {compareIds.length > 0 && (
                <button
                  onClick={() => setCompareIds([])}
                  className="text-xs text-[var(--text-tertiary)] hover:text-[var(--text-primary)]"
                >
                  Clear
                </button>
              )}
            </div>
          )}

          {compareMode && compareIds.length >= 2 ? (
            <CompareView experiments={comparedExperiments} />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {filtered.map((exp) => (
                <ExperimentCard
                  key={exp.id}
                  experiment={exp}
                  compareMode={compareMode}
                  selectedForCompare={compareIds.includes(exp.id)}
                  onToggleCompare={toggleCompare}
                  onClick={() => setSelectedExp(exp)}
                />
              ))}
              {filtered.length === 0 && (
                <div className="col-span-full py-16 text-center">
                  <FlaskConical className="mx-auto h-8 w-8 text-[var(--text-tertiary)] opacity-40" />
                  <p className="mt-3 text-sm font-medium text-[var(--text-secondary)]">No experiments found</p>
                  <p className="mt-1 text-xs text-[var(--text-tertiary)]">Try adjusting your search or filters</p>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {selectedExp && (
        <ExperimentDetailModal
          experiment={selectedExp}
          open={!!selectedExp}
          onClose={() => setSelectedExp(null)}
        />
      )}
    </div>
  )
}
