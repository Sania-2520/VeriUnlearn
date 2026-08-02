"use client"

import { useState, useMemo, useCallback, useRef, useEffect } from "react"
import { motion } from "framer-motion"
import {
  LineChart, Line, AreaChart, Area, BarChart, Bar, ScatterChart, Scatter,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  ResponsiveContainer, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ZAxis, Cell, ComposedChart,
} from "recharts"
import { toast } from "sonner"
import { clsx } from "clsx"
import { format, subDays, addDays } from "date-fns"
import { Card, CardHeader, CardContent } from "@/components/ui/card"
import { PageHeader } from "@/components/ui/page-header"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import {
  BarChart3, Download, Maximize2, Minimize2, FolderOpen,
  Clock, Activity, TrendingUp,
  Table2, Layers,
  ChevronDown, X,
  RefreshCw,
} from "lucide-react"

const ALGORITHMS = ["SISA", "Retraining", "AmnesiacML", "FisherForgetting", "DeltaGrad"] as const
type Algorithm = (typeof ALGORITHMS)[number]

const ALGO_COLORS: Record<Algorithm, string> = {
  SISA: "var(--chart-1)",
  Retraining: "var(--chart-2)",
  AmnesiacML: "var(--chart-3)",
  FisherForgetting: "var(--chart-4)",
  DeltaGrad: "var(--chart-5)",
}

const ALGO_COLORS_HEX: Record<Algorithm, string> = {
  SISA: "#10b981",
  Retraining: "#6366f1",
  AmnesiacML: "#f59e0b",
  FisherForgetting: "#ec4899",
  DeltaGrad: "#06b6d4",
}

const DATASETS = ["CIFAR-10", "CIFAR-100", "ImageNet", "MNIST", "Fashion-MNIST", "SVHN"]
const TIME_RANGES = ["Last 7 days", "Last 30 days", "Last 90 days", "All time"]

interface EpochData {
  epoch: number
  trainLoss: number
  valLoss: number
  trainAcc: number
  valAcc: number
  lr: number
}

interface AlgorithmRun {
  algorithm: Algorithm
  epochs: EpochData[]
}

interface RadarMetric {
  algorithm: string
  accuracy: number
  trainingSpeed: number
  privacyScore: number
  memoryEfficiency: number
  scalability: number
  robustness: number
}

interface ScatterPoint {
  algorithm: Algorithm
  privacyScore: number
  accuracy: number
  trainingTime: number
  color: string
}

interface ResourceData {
  algorithm: string
  gpuMemory: number
  cpuUsage: number
  trainingTime: number
  diskIO: number
}

interface ConfusionMatrix {
  algorithm: Algorithm
  matrix: number[][]
  labels: string[]
}

interface FeatureImportance {
  feature: string
  importance: number
}

interface EmbeddingPoint {
  x: number
  y: number
  label: string
  cluster: number
}

interface Experiment {
  id: string
  name: string
  start: Date
  end: Date
  status: "completed" | "running" | "failed" | "queued"
  algorithm: Algorithm
}

interface ResourceTimeline {
  time: string[]
  cpu: number[]
  memory: number[]
  events: { time: string; label: string; type: "checkpoint" | "eval" | "start" | "end" }[]
}

interface PipelineStage {
  id: string
  name: string
  status: "completed" | "running" | "pending" | "failed"
  duration: string
}

interface PipelineEdge {
  from: string
  to: string
}

function generateLossCurves(): AlgorithmRun[] {
  return ALGORITHMS.map((algo) => {
    const epochs: EpochData[] = []
    let trainLoss = 2.8 + Math.random() * 0.5
    let valLoss = trainLoss + 0.3 + Math.random() * 0.2
    const baseLR = algo === "SISA" ? 0.01 : algo === "Retraining" ? 0.008 : algo === "DeltaGrad" ? 0.05 : 0.02
    for (let e = 1; e <= 50; e++) {
      const decay = Math.exp(-e / 18) * (0.6 + Math.random() * 0.15)
      trainLoss = Math.max(0.12, trainLoss * (0.88 + Math.random() * 0.04) - 0.02 * Math.random())
      valLoss = Math.max(0.18, trainLoss + 0.05 + Math.random() * 0.12 * (1 + Math.sin(e / 5) * 0.3))
      const epochLR = baseLR * (algo === "AmnesiacML" ? (0.5 * (1 + Math.cos((e * Math.PI) / 50))) : algo === "FisherForgetting" ? Math.pow(0.95, e) : algo === "DeltaGrad" ? (0.1 + 0.9 * Math.exp(-e / 10)) : 0.5 ** Math.floor(e / 15))
      epochs.push({ epoch: e, trainLoss: +trainLoss.toFixed(4), valLoss: +valLoss.toFixed(4), trainAcc: 0, valAcc: 0, lr: +epochLR.toFixed(6) })
    }
    return { algorithm: algo, epochs }
  })
}

function addAccuracy(runs: AlgorithmRun[]): AlgorithmRun[] {
  return runs.map((run) => {
    const algoFactor = run.algorithm === "SISA" ? 0.96 : run.algorithm === "Retraining" ? 0.93 : run.algorithm === "AmnesiacML" ? 0.89 : run.algorithm === "FisherForgetting" ? 0.91 : 0.95
    return {
      ...run,
      epochs: run.epochs.map((e, i) => {
        const trainAcc = Math.min(algoFactor * 100, (algoFactor * 100 - 10) * (1 - Math.exp(-i / 8)) + 10 + (Math.random() - 0.5) * 1.5)
        const valAcc = Math.min(trainAcc * 0.96, trainAcc - 2 - Math.random() * 3 + Math.sin(i / 3) * 0.8)
        return { ...e, trainAcc: +trainAcc.toFixed(2), valAcc: +valAcc.toFixed(2) }
      }),
    }
  })
}

function generateRadarData(): RadarMetric[] {
  return ALGORITHMS.map((algo) => {
    const base: Record<string, number> = {
      SISA: { accuracy: 96, trainingSpeed: 72, privacyScore: 88, memoryEfficiency: 65, scalability: 78, robustness: 85 },
      Retraining: { accuracy: 91, trainingSpeed: 45, privacyScore: 82, memoryEfficiency: 40, scalability: 35, robustness: 90 },
      AmnesiacML: { accuracy: 88, trainingSpeed: 85, privacyScore: 74, memoryEfficiency: 82, scalability: 88, robustness: 70 },
      FisherForgetting: { accuracy: 93, trainingSpeed: 58, privacyScore: 92, memoryEfficiency: 55, scalability: 60, robustness: 82 },
      DeltaGrad: { accuracy: 85, trainingSpeed: 92, privacyScore: 70, memoryEfficiency: 90, scalability: 92, robustness: 65 },
    }[algo]!
    return { algorithm: algo, ...base } as RadarMetric
  })
}

function generateScatterData(): ScatterPoint[] {
  const points: ScatterPoint[] = []
  ALGORITHMS.forEach((algo) => {
    for (let i = 0; i < 6; i++) {
      const base = { SISA: [85, 92], Retraining: [78, 88], AmnesiacML: [70, 86], FisherForgetting: [82, 90], DeltaGrad: [65, 82] }[algo]!
      points.push({
        algorithm: algo,
        privacyScore: Math.max(30, Math.min(100, base[0] + (Math.random() - 0.5) * 24)),
        accuracy: Math.max(40, Math.min(100, base[1] + (Math.random() - 0.5) * 16)),
        trainingTime: Math.round(100 + Math.random() * 400),
        color: ALGO_COLORS_HEX[algo],
      })
    }
  })
  return points
}

function generateResourceData(): ResourceData[] {
  return ALGORITHMS.map((algo) => {
    const base = { SISA: [4.2, 68, 145, 320], Retraining: [8.6, 92, 380, 580], AmnesiacML: [2.8, 55, 98, 210], FisherForgetting: [6.4, 78, 260, 450], DeltaGrad: [3.2, 62, 112, 280] }[algo]!
    return { algorithm: algo, gpuMemory: base[0], cpuUsage: base[1], trainingTime: base[2], diskIO: base[3] }
  })
}

function generateConfusionMatrices(): ConfusionMatrix[] {
  return ALGORITHMS.map((algo) => {
    const labels = ["Cat", "Dog", "Bird", "Fish", "Frog"]
    const accuracy = { SISA: 0.94, Retraining: 0.89, AmnesiacML: 0.85, FisherForgetting: 0.91, DeltaGrad: 0.83 }[algo]!
    const matrix = labels.map((_, i) =>
      labels.map((_, j) => {
        if (i === j) return Math.round(accuracy * 80 + Math.random() * 10 + 5)
        return Math.round(Math.random() * 5 * (1 - accuracy) + 1)
      })
    )
    return { algorithm: algo, matrix, labels }
  })
}

function generateFeatureImportance(): FeatureImportance[] {
  const features = [
    "Pixel Intensity Mean", "Edge Density", "Color Histogram Var", "Texture Contrast",
    "Gabor Filter Response", "SIFT Keypoints", "HOG Gradient Mag", "LBP Pattern",
    "Deep Embedding L2", "Attention Weight Avg", "ResNet Block-3 Activ", "ViT Patch Mean",
    "Token CLS Embedding", "LayerNorm Scale", "FFN Hidden State", "Conv-1x1 Weight Sparsity",
    "BatchNorm Running Mean", "Dropout Mask Ratio", "Grad Cam Activation", "Saliency Map Peak",
  ]
  return features.map((f) => ({ feature: f, importance: +(Math.random() * 0.95 + 0.05).toFixed(4) }))
    .sort((a, b) => b.importance - a.importance)
}

function generateEmbeddings(): EmbeddingPoint[] {
  const points: EmbeddingPoint[] = []
  const cls = ["Cat", "Dog", "Bird", "Fish", "Frog"]
  for (let i = 0; i < 200; i++) {
    const ci = i % cls.length
    const angle = (ci / cls.length) * Math.PI * 2 + (Math.random() - 0.5) * 0.6
    const radius = 2 + Math.random() * 3
    points.push({
      x: Math.cos(angle) * radius + (Math.random() - 0.5) * 0.8,
      y: Math.sin(angle) * radius + (Math.random() - 0.5) * 0.8,
      label: cls[ci],
      cluster: ci,
    })
  }
  return points
}

function generateExperiments(): Experiment[] {
  const startBase = subDays(new Date(), 14)
  const algos = [...ALGORITHMS]
  const statuses: Experiment["status"][] = ["completed", "running", "failed", "queued"]
  return Array.from({ length: 12 }, (_, i) => {
    const algo = algos[i % algos.length]
    const dur = 30 + Math.floor(Math.random() * 240)
    const start = addDays(startBase, Math.floor(i * 1.2))
    const status = i === 0 ? "running" : i < 9 ? "completed" : i < 11 ? "failed" : "queued"
    return {
      id: `exp-${i + 1}`,
      name: `Exp #${i + 1} - ${algo} on ${["CIFAR-10", "CIFAR-100", "ImageNet"][i % 3]}`,
      start,
      end: addDays(start, dur / 24),
      status: status as Experiment["status"],
      algorithm: algo,
    }
  })
}

function generateResourceTimeline(): ResourceTimeline {
  const points: ResourceTimeline["events"] = []
  for (let h = 0; h < 24; h++) {
    if (h % 4 === 0) points.push({ time: `${h}:00`, label: h % 8 === 0 ? "Checkpoint" : "Eval", type: h % 8 === 0 ? "checkpoint" : "eval" })
  }
  return {
    time: Array.from({ length: 24 }, (_, i) => `${i}:00`),
    cpu: Array.from({ length: 24 }, () => Math.round(30 + Math.random() * 55 + Math.sin(Math.random() * 6) * 10)),
    memory: Array.from({ length: 24 }, () => +(4 + Math.random() * 8 + Math.sin(Math.random() * 4) * 2).toFixed(1)),
    events: points,
  }
}

function generatePipelineData(): { stages: PipelineStage[]; edges: PipelineEdge[] } {
  const stages: PipelineStage[] = [
    { id: "load", name: "Data Loading", status: "completed", duration: "2.3s" },
    { id: "preprocess", name: "Preprocessing", status: "completed", duration: "8.1s" },
    { id: "augment", name: "Augmentation", status: "completed", duration: "4.7s" },
    { id: "train", name: "Training", status: "running", duration: "--" },
    { id: "unlearn", name: "Unlearn Step", status: "pending", duration: "--" },
    { id: "verify", name: "Verification", status: "pending", duration: "--" },
  ]
  const edges: PipelineEdge[] = [
    { from: "load", to: "preprocess" },
    { from: "preprocess", to: "augment" },
    { from: "augment", to: "train" },
    { from: "train", to: "unlearn" },
    { from: "unlearn", to: "verify" },
  ]
  return { stages, edges }
}

const container = { hidden: {}, show: { transition: { staggerChildren: 0.05 } } }
const item = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.16, 1, 0.3, 1] } },
}

function StatusBadge({ status }: { status: Experiment["status"] }) {
  const tones: Record<string, "success" | "warning" | "danger" | "info"> = {
    completed: "success",
    running: "warning",
    failed: "danger",
    queued: "info",
  }
  return <Badge tone={tones[status]} dot>{status}</Badge>
}

function ChartTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  return (
    <div className="surface-elevated rounded-lg px-3 py-2 text-xs shadow-[var(--shadow-md)] z-50">
      <p className="mb-1 font-medium text-[var(--text-primary)]">{label}</p>
      {payload.map((p: any, i: number) => (
        <p key={i} style={{ color: p.color ?? p.stroke }} className="tabular-nums">
          {p.name ?? p.dataKey}: {typeof p.value === "number" ? p.value.toLocaleString() : p.value}
          {p.payload?.unit ? ` ${p.payload.unit}` : ""}
        </p>
      ))}
    </div>
  )
}

function FullscreenButton({ isFull, onClick }: { isFull: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="flex h-7 w-7 items-center justify-center rounded-md text-[var(--text-tertiary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
      title={isFull ? "Exit fullscreen" : "Fullscreen"}
    >
      {isFull ? <Minimize2 className="h-3.5 w-3.5" /> : <Maximize2 className="h-3.5 w-3.5" />}
    </button>
  )
}

function ExportPngButton({ chartId }: { chartId: string }) {
  const handleExport = useCallback(() => {
    const el = document.getElementById(chartId)
    if (!el) return
    import("recharts").then(() => {
      const svg = el.querySelector("svg.recharts-surface")
      if (!svg) { toast.error("No chart rendered"); return }
      const svgData = new XMLSerializer().serializeToString(svg)
      const canvas = document.createElement("canvas")
      const rect = svg.getBoundingClientRect()
      canvas.width = rect.width * 2
      canvas.height = rect.height * 2
      const ctx = canvas.getContext("2d")
      if (!ctx) return
      ctx.scale(2, 2)
      const img = new Image()
      const blob = new Blob([svgData], { type: "image/svg+xml;charset=utf-8" })
      const url = URL.createObjectURL(blob)
      img.onload = () => {
        ctx.fillStyle = "#ffffff"
        ctx.fillRect(0, 0, rect.width, rect.height)
        ctx.drawImage(img, 0, 0, rect.width, rect.height)
        URL.revokeObjectURL(url)
        const a = document.createElement("a")
        a.href = canvas.toDataURL("image/png")
        a.download = `${chartId}.png`
        a.click()
        toast.success("Chart exported as PNG")
      }
      img.src = url
    })
  }, [chartId])
  return (
    <button
      onClick={handleExport}
      className="flex h-7 w-7 items-center justify-center rounded-md text-[var(--text-tertiary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
      title="Export as PNG"
    >
      <Download className="h-3.5 w-3.5" />
    </button>
  )
}

function CardActions({ chartId, isFull, onToggleFull }: { chartId: string; isFull: boolean; onToggleFull: () => void }) {
  return (
    <div className="flex items-center gap-1">
      <ExportPngButton chartId={chartId} />
      <FullscreenButton isFull={isFull} onClick={onToggleFull} />
    </div>
  )
}

interface ChartCardProps {
  id: string
  title: string
  description?: string
  badge?: string
  isFull: boolean
  onToggleFull: () => void
  children: React.ReactNode
}

function ChartCard({ id, title, description, badge, isFull, onToggleFull, children }: ChartCardProps) {
  return (
    <div
      id={id}
      className={clsx(
        "surface rounded-xl shadow-[var(--shadow-sm)] transition-all duration-300",
        isFull && "fixed inset-4 z-50 overflow-auto",
      )}
    >
      <div className="flex items-start justify-between gap-3 border-b border-[var(--border-subtle)] px-4 py-3">
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-[var(--text-primary)]">{title}</h3>
          {description && <p className="mt-0.5 text-xs text-[var(--text-secondary)]">{description}</p>}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {badge && <Badge tone="info" dot>{badge}</Badge>}
          <CardActions chartId={id} isFull={isFull} onToggleFull={onToggleFull} />
        </div>
      </div>
      <div className={clsx("p-4", isFull ? "h-[calc(100%-60px)]" : "h-[300px]")}>{children}</div>
    </div>
  )
}

function MultiSelect({
  options,
  selected,
  onChange,
  label,
}: {
  options: readonly string[]
  selected: string[]
  onChange: (v: string[]) => void
  label: string
}) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener("mousedown", handleClick)
    return () => document.removeEventListener("mousedown", handleClick)
  }, [])
  const toggle = (v: string) => {
    onChange(selected.includes(v) ? selected.filter((s) => s !== v) : [...selected, v])
  }
  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="inline-flex h-9 items-center gap-2 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] px-3 py-1.5 text-sm text-[var(--text-secondary)] transition-colors hover:border-[var(--brand)] whitespace-nowrap"
      >
        <Layers className="h-4 w-4" />
        <span className="hidden sm:inline">{label}</span>
        <span className="rounded bg-[var(--brand-soft)] px-1.5 py-0.5 text-xs font-medium text-[var(--brand-strong)]">{selected.length}</span>
        <ChevronDown className={clsx("h-3.5 w-3.5 transition-transform", open && "rotate-180")} />
      </button>
      {open && (
        <div className="absolute right-0 top-full z-50 mt-1 w-52 animate-scale-in rounded-xl border border-[var(--border-default)] bg-[var(--bg-surface-elevated)] py-1.5 shadow-[var(--shadow-lg)]">
          {options.map((opt) => (
            <button
              key={opt}
              onClick={() => toggle(opt)}
              className="flex w-full items-center gap-2.5 px-4 py-2 text-left text-sm text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)]"
            >
              <span className={clsx(
                "flex h-4 w-4 items-center justify-center rounded border text-[10px] font-medium transition-colors",
                selected.includes(opt)
                  ? "border-[var(--brand)] bg-[var(--brand)] text-[var(--text-on-brand)]"
                  : "border-[var(--border-strong)] text-transparent",
              )}>
                {selected.includes(opt) ? "✓" : ""}
              </span>
              {opt}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function SelectBox({
  options,
  value,
  onChange,
  label,
  icon: Icon,
}: {
  options: readonly string[]
  value: string
  onChange: (v: string) => void
  label: string
  icon?: typeof Clock
}) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener("mousedown", handleClick)
    return () => document.removeEventListener("mousedown", handleClick)
  }, [])
  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="inline-flex h-9 items-center gap-2 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] px-3 py-1.5 text-sm text-[var(--text-secondary)] transition-colors hover:border-[var(--brand)] whitespace-nowrap"
      >
        {Icon && <Icon className="h-4 w-4" />}
        <span>{value || label}</span>
        <ChevronDown className={clsx("h-3.5 w-3.5 transition-transform", open && "rotate-180")} />
      </button>
      {open && (
        <div className="absolute right-0 top-full z-50 mt-1 w-48 animate-scale-in rounded-xl border border-[var(--border-default)] bg-[var(--bg-surface-elevated)] py-1.5 shadow-[var(--shadow-lg)]">
          {options.map((opt) => (
            <button
              key={opt}
              onClick={() => { onChange(opt); setOpen(false) }}
              className={clsx(
                "flex w-full items-center px-4 py-2 text-left text-sm transition-colors hover:bg-[var(--bg-hover)]",
                opt === value ? "font-medium text-[var(--brand-strong)]" : "text-[var(--text-secondary)]",
              )}
            >
              {opt === value && <span className="mr-2 text-[var(--brand)]">✓</span>}
              {opt}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function GanttBar({ exp, dayWidth }: { exp: Experiment; dayWidth: number }) {
  const startX = 0
  const durHours = (exp.end.getTime() - exp.start.getTime()) / 3600000
  const width = Math.max(dayWidth, durHours * dayWidth)
  const colorMap: Record<string, string> = {
    completed: "var(--success)",
    running: "var(--warning)",
    failed: "var(--danger)",
    queued: "var(--text-tertiary)",
  }
  return (
    <div className="relative flex items-center h-7 group">
      <div
        className="h-5 rounded-full transition-all group-hover:shadow-[var(--shadow-md)]"
        style={{
          width: `${Math.min(width, 400)}px`,
          backgroundColor: colorMap[exp.status],
          opacity: exp.status === "queued" ? 0.5 : 0.85,
          minWidth: "8px",
        }}
      />
    </div>
  )
}

export default function VisualizationsPage() {
  const [timeRange, setTimeRange] = useState("Last 30 days")
  const [dataset, setDataset] = useState("CIFAR-10")
  const [selectedAlgos, setSelectedAlgos] = useState<string[]>([...ALGORITHMS])
  const [cmAlgo, setCmAlgo] = useState<Algorithm>("SISA")
  const [fullscreenId, setFullscreenId] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [pipelineStage, setPipelineStage] = useState<string | null>(null)
  const [syncedEpoch, setSyncedEpoch] = useState<number | null>(null)

  const lossData = useMemo(() => addAccuracy(generateLossCurves()), [])
  const radarData = useMemo(() => generateRadarData(), [])
  const scatterData = useMemo(() => generateScatterData(), [])
  const resourceData = useMemo(() => generateResourceData(), [])
  const confusionMatrices = useMemo(() => generateConfusionMatrices(), [])
  const featureImportance = useMemo(() => generateFeatureImportance(), [])
  const embeddings = useMemo(() => generateEmbeddings(), [])
  const experiments = useMemo(() => generateExperiments(), [])
  const resourceTimeline = useMemo(() => generateResourceTimeline(), [])
  const pipeline = useMemo(() => generatePipelineData(), [])

  const filteredLossData = useMemo(
    () => lossData.filter((r) => selectedAlgos.includes(r.algorithm)),
    [lossData, selectedAlgos],
  )

  const toggleFullscreen = useCallback((id: string) => {
    setFullscreenId((prev) => (prev === id ? null : id))
  }, [])

  const handleRefresh = useCallback(() => {
    setLoading(true)
    setTimeout(() => {
      setLoading(false)
      toast.success("Visualizations refreshed")
    }, 800)
  }, [])

  const handleExportDashboard = useCallback(() => {
    toast.success("Dashboard export started", { description: "Your export will be ready shortly" })
  }, [])

  const epochsForLoss = useMemo(() => {
    if (filteredLossData.length === 0) return []
    return filteredLossData[0].epochs.map((_, i) => ({
      epoch: i + 1,
      ...Object.fromEntries(filteredLossData.flatMap((r) => [
        [`${r.algorithm}_trainLoss`, r.epochs[i].trainLoss],
        [`${r.algorithm}_valLoss`, r.epochs[i].valLoss],
        [`${r.algorithm}_trainAcc`, r.epochs[i].trainAcc],
        [`${r.algorithm}_valAcc`, r.epochs[i].valAcc],
      ])),
    }))
  }, [filteredLossData])

  const epochsForLR = useMemo(() => {
    if (filteredLossData.length === 0) return []
    return filteredLossData[0].epochs.map((_, i) => ({
      epoch: i + 1,
      ...Object.fromEntries(filteredLossData.flatMap((r) => [
        [`${r.algorithm}_lr`, r.epochs[i].lr],
      ])),
    }))
  }, [filteredLossData])

  const cmData = useMemo(() => confusionMatrices.find((c) => c.algorithm === cmAlgo)!, [confusionMatrices, cmAlgo])

  const confusionChartData = useMemo(() => {
    return cmData.labels.map((label, i) => ({
      name: label,
      ...Object.fromEntries(cmData.labels.map((l, j) => [l, cmData.matrix[i][j]])),
    }))
  }, [cmData])

  const activeAlgorithms = useMemo(
    () => ALGORITHMS.filter((a) => selectedAlgos.includes(a)),
    [selectedAlgos],
  )

  if (loading) {
    return (
      <div className="p-5 md:p-6 space-y-6 max-w-[1600px] mx-auto">
        <div className="flex items-center justify-between">
          <div className="space-y-2">
            <Skeleton className="h-6 w-48" />
            <Skeleton className="h-4 w-72" />
          </div>
          <Skeleton className="h-9 w-28 rounded-lg" />
        </div>
        {[0, 1, 2, 3].map((row) => (
          <div key={row} className="grid gap-4 md:grid-cols-3">
            {[0, 1, 2].map((i) => (
              <div key={i} className="surface rounded-xl p-5">
                <Skeleton className="h-4 w-32" />
                <Skeleton className="mt-4 h-48 w-full rounded-lg" />
              </div>
            ))}
          </div>
        ))}
      </div>
    )
  }

  return (
    <motion.div
      variants={container}
      initial="hidden"
      animate="show"
      className={clsx("p-5 md:p-6 space-y-6 max-w-[1600px] mx-auto", fullscreenId && "overflow-hidden")}
    >
      <motion.div variants={item}>
        <PageHeader
          title="Visualizations"
          description="Interactive experiment analytics and model visualization hub"
          actions={
            <div className="flex flex-wrap items-center gap-2">
              <SelectBox options={TIME_RANGES} value={timeRange} onChange={setTimeRange} label="Time range" icon={Clock} />
              <SelectBox options={DATASETS} value={dataset} onChange={setDataset} label="Dataset" icon={FolderOpen} />
              <MultiSelect options={ALGORITHMS} selected={selectedAlgos} onChange={setSelectedAlgos} label="Algorithms" />
              <button
                onClick={handleRefresh}
                className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] text-[var(--text-secondary)] transition-colors hover:border-[var(--brand)] hover:text-[var(--brand-strong)]"
              >
                <RefreshCw className="h-4 w-4" />
              </button>
              <button
                onClick={handleExportDashboard}
                className="inline-flex h-9 items-center gap-2 rounded-lg border border-[var(--border-default)] bg-[var(--brand)] px-3.5 py-1.5 text-sm font-medium text-[var(--text-on-brand)] transition-all hover:bg-[var(--brand-strong)]"
              >
                <Download className="h-4 w-4" />
                <span className="hidden sm:inline">Export</span>
              </button>
            </div>
          }
        />
      </motion.div>

      <div className={clsx("space-y-6", fullscreenId && "hidden")}>
        <motion.div variants={item}>
          <div className="mb-3 flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-[var(--text-tertiary)]" />
            <h2 className="text-sm font-semibold text-[var(--text-primary)]">Training Dynamics</h2>
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            <ChartCard
              id="loss-curves"
              title="Loss Curves"
              description="Training & validation loss over epochs"
              badge="Live"
              isFull={fullscreenId === "loss-curves"}
              onToggleFull={() => toggleFullscreen("loss-curves")}
            >
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={epochsForLoss} margin={{ top: 8, right: 8, bottom: 8, left: 0 }}>
                  <CartesianGrid stroke="var(--border-subtle)" strokeDasharray="3 3" />
                  <XAxis dataKey="epoch" tick={{ fontSize: 10, fill: "var(--text-tertiary)" }} axisLine={false} tickLine={false} label={{ value: "Epoch", position: "insideBottom", offset: -4, style: { fontSize: 10, fill: "var(--text-tertiary)" } }} />
                  <YAxis tick={{ fontSize: 10, fill: "var(--text-tertiary)" }} axisLine={false} tickLine={false} width={36} />
                  <Tooltip content={<ChartTooltip />} />
                  <Legend wrapperStyle={{ fontSize: 10, color: "var(--text-secondary)" }} onClick={(e) => {}} />
                  {activeAlgorithms.map((algo) => (
                    <Line key={`${algo}_tl`} type="monotone" dataKey={`${algo}_trainLoss`} stroke={ALGO_COLORS_HEX[algo]} strokeWidth={2} dot={false} name={`${algo} (Train)`} activeDot={{ r: 3 }} />
                  ))}
                  {activeAlgorithms.map((algo) => (
                    <Line key={`${algo}_vl`} type="monotone" dataKey={`${algo}_valLoss`} stroke={ALGO_COLORS_HEX[algo]} strokeWidth={2} strokeDasharray="5 4" dot={false} name={`${algo} (Val)`} activeDot={{ r: 3 }} />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </ChartCard>

            <ChartCard
              id="accuracy-curves"
              title="Accuracy Curves"
              description="Training & validation accuracy over epochs"
              badge="Live"
              isFull={fullscreenId === "accuracy-curves"}
              onToggleFull={() => toggleFullscreen("accuracy-curves")}
            >
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={epochsForLoss} margin={{ top: 8, right: 8, bottom: 8, left: 0 }}>
                  <CartesianGrid stroke="var(--border-subtle)" strokeDasharray="3 3" />
                  <XAxis dataKey="epoch" tick={{ fontSize: 10, fill: "var(--text-tertiary)" }} axisLine={false} tickLine={false} label={{ value: "Epoch", position: "insideBottom", offset: -4, style: { fontSize: 10, fill: "var(--text-tertiary)" } }} />
                  <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: "var(--text-tertiary)" }} axisLine={false} tickLine={false} width={36} unit="%" />
                  <Tooltip content={<ChartTooltip />} />
                  <Legend wrapperStyle={{ fontSize: 10, color: "var(--text-secondary)" }} />
                  {activeAlgorithms.map((algo) => (
                    <Line key={`${algo}_ta`} type="monotone" dataKey={`${algo}_trainAcc`} stroke={ALGO_COLORS_HEX[algo]} strokeWidth={2} dot={false} name={`${algo} (Train)`} activeDot={{ r: 3 }} />
                  ))}
                  {activeAlgorithms.map((algo) => (
                    <Line key={`${algo}_va`} type="monotone" dataKey={`${algo}_valAcc`} stroke={ALGO_COLORS_HEX[algo]} strokeWidth={2} strokeDasharray="5 4" dot={false} name={`${algo} (Val)`} activeDot={{ r: 3 }} />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </ChartCard>

            <ChartCard
              id="lr-schedule"
              title="Learning Rate Schedule"
              description="LR decay strategies over steps"
              badge="Schedules"
              isFull={fullscreenId === "lr-schedule"}
              onToggleFull={() => toggleFullscreen("lr-schedule")}
            >
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={epochsForLR} margin={{ top: 8, right: 8, bottom: 8, left: 0 }}>
                  <CartesianGrid stroke="var(--border-subtle)" strokeDasharray="3 3" />
                  <XAxis dataKey="epoch" tick={{ fontSize: 10, fill: "var(--text-tertiary)" }} axisLine={false} tickLine={false} label={{ value: "Step", position: "insideBottom", offset: -4, style: { fontSize: 10, fill: "var(--text-tertiary)" } }} />
                  <YAxis tick={{ fontSize: 10, fill: "var(--text-tertiary)" }} axisLine={false} tickLine={false} width={44} />
                  <Tooltip content={<ChartTooltip />} />
                  <Legend wrapperStyle={{ fontSize: 10, color: "var(--text-secondary)" }} />
                  {activeAlgorithms.map((algo) => (
                    <Line key={`${algo}_lr`} type="monotone" dataKey={`${algo}_lr`} stroke={ALGO_COLORS_HEX[algo]} strokeWidth={2} dot={false} name={`${algo}`} activeDot={{ r: 3 }} />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </ChartCard>
          </div>
        </motion.div>

        <motion.div variants={item}>
          <div className="mb-3 flex items-center gap-2">
            <BarChart3 className="h-4 w-4 text-[var(--text-tertiary)]" />
            <h2 className="text-sm font-semibold text-[var(--text-primary)]">Comparative Analysis</h2>
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            <ChartCard
              id="algorithm-radar"
              title="Algorithm Radar"
              description="Multi-metric algorithm comparison"
              badge="Radar"
              isFull={fullscreenId === "algorithm-radar"}
              onToggleFull={() => toggleFullscreen("algorithm-radar")}
            >
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={radarData} margin={{ top: 8, right: 24, bottom: 8, left: 24 }}>
                  <PolarGrid stroke="var(--border-subtle)" />
                  <PolarAngleAxis dataKey="algorithm" tick={{ fontSize: 9, fill: "var(--text-secondary)" }} />
                  <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fontSize: 9, fill: "var(--text-tertiary)" }} axisLine={false} />
                  <Tooltip content={<ChartTooltip />} />
                  <Legend wrapperStyle={{ fontSize: 10, color: "var(--text-secondary)" }} />
                  <Radar name="Accuracy" dataKey="accuracy" stroke="var(--chart-1)" fill="var(--chart-1)" fillOpacity={0.15} strokeWidth={1.5} />
                  <Radar name="Training Speed" dataKey="trainingSpeed" stroke="var(--chart-2)" fill="var(--chart-2)" fillOpacity={0.15} strokeWidth={1.5} />
                  <Radar name="Privacy Score" dataKey="privacyScore" stroke="var(--chart-3)" fill="var(--chart-3)" fillOpacity={0.15} strokeWidth={1.5} />
                  <Radar name="Memory Eff." dataKey="memoryEfficiency" stroke="var(--chart-4)" fill="var(--chart-4)" fillOpacity={0.15} strokeWidth={1.5} />
                  <Radar name="Scalability" dataKey="scalability" stroke="var(--chart-5)" fill="var(--chart-5)" fillOpacity={0.15} strokeWidth={1.5} />
                  <Radar name="Robustness" dataKey="robustness" stroke="var(--chart-6)" fill="var(--chart-6)" fillOpacity={0.15} strokeWidth={1.5} />
                </RadarChart>
              </ResponsiveContainer>
            </ChartCard>

            <ChartCard
              id="privacy-utility"
              title="Privacy-Utility Tradeoff"
              description="Scatter: privacy vs accuracy"
              badge="Scatter"
              isFull={fullscreenId === "privacy-utility"}
              onToggleFull={() => toggleFullscreen("privacy-utility")}
            >
              <ResponsiveContainer width="100%" height="100%">
                <ScatterChart margin={{ top: 8, right: 8, bottom: 8, left: 0 }}>
                  <CartesianGrid stroke="var(--border-subtle)" strokeDasharray="3 3" />
                  <XAxis dataKey="privacyScore" domain={[40, 100]} tick={{ fontSize: 10, fill: "var(--text-tertiary)" }} axisLine={false} tickLine={false} label={{ value: "Privacy Score", position: "insideBottom", offset: -4, style: { fontSize: 10, fill: "var(--text-tertiary)" } }} />
                  <YAxis dataKey="accuracy" domain={[40, 100]} tick={{ fontSize: 10, fill: "var(--text-tertiary)" }} axisLine={false} tickLine={false} width={36} label={{ value: "Accuracy (%)", angle: -90, position: "insideLeft", style: { fontSize: 10, fill: "var(--text-tertiary)" } }} />
                  <ZAxis dataKey="trainingTime" range={[40, 200]} />
                  <Tooltip content={<ChartTooltip />} />
                  <Legend wrapperStyle={{ fontSize: 10, color: "var(--text-secondary)" }} />
                  {activeAlgorithms.map((algo) => (
                    <Scatter key={algo} name={algo} data={scatterData.filter((p) => p.algorithm === algo)} fill={ALGO_COLORS_HEX[algo]} strokeWidth={0} />
                  ))}
                </ScatterChart>
              </ResponsiveContainer>
            </ChartCard>

            <ChartCard
              id="resource-usage"
              title="Resource Usage"
              description="GPU / CPU / Time / I/O by algorithm"
              badge="Resources"
              isFull={fullscreenId === "resource-usage"}
              onToggleFull={() => toggleFullscreen("resource-usage")}
            >
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={resourceData.filter((r) => selectedAlgos.includes(r.algorithm))} margin={{ top: 8, right: 8, bottom: 8, left: 0 }} barGap={2} barCategoryGap="15%">
                  <CartesianGrid stroke="var(--border-subtle)" strokeDasharray="3 3" />
                  <XAxis dataKey="algorithm" tick={{ fontSize: 10, fill: "var(--text-tertiary)" }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 10, fill: "var(--text-tertiary)" }} axisLine={false} tickLine={false} width={36} />
                  <Tooltip content={<ChartTooltip />} />
                  <Legend wrapperStyle={{ fontSize: 10, color: "var(--text-secondary)" }} />
                  <Bar dataKey="gpuMemory" name="GPU Memory (GB)" fill="var(--chart-1)" radius={[2, 2, 0, 0]} maxBarSize={20} />
                  <Bar dataKey="cpuUsage" name="CPU Usage (%)" fill="var(--chart-2)" radius={[2, 2, 0, 0]} maxBarSize={20} />
                  <Bar dataKey="trainingTime" name="Training Time (min)" fill="var(--chart-3)" radius={[2, 2, 0, 0]} maxBarSize={20} />
                  <Bar dataKey="diskIO" name="Disk I/O (MB/s)" fill="var(--chart-4)" radius={[2, 2, 0, 0]} maxBarSize={20} />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
          </div>
        </motion.div>

        <motion.div variants={item}>
          <div className="mb-3 flex items-center gap-2">
            <Table2 className="h-4 w-4 text-[var(--text-tertiary)]" />
            <h2 className="text-sm font-semibold text-[var(--text-primary)]">Distribution Analysis</h2>
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            <ChartCard
              id="confusion-matrix"
              title="Confusion Matrix"
              description={`True vs Predicted — ${cmAlgo}`}
              badge="Heatmap"
              isFull={fullscreenId === "confusion-matrix"}
              onToggleFull={() => toggleFullscreen("confusion-matrix")}
            >
              <div className="flex flex-col h-full">
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-xs text-[var(--text-tertiary)]">Algorithm:</span>
                  <div className="flex flex-wrap gap-1">
                    {ALGORITHMS.map((a) => (
                      <button
                        key={a}
                        onClick={() => setCmAlgo(a)}
                        className={clsx(
                          "rounded-md px-2 py-0.5 text-xs font-medium transition-colors",
                          cmAlgo === a
                            ? "bg-[var(--brand)] text-[var(--text-on-brand)]"
                            : "bg-[var(--bg-subtle)] text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]",
                        )}
                      >
                        {a}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="flex-1 min-h-0">
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={confusionChartData} margin={{ top: 4, right: 4, bottom: 4, left: 4 }}>
                      <XAxis dataKey="name" tick={{ fontSize: 9, fill: "var(--text-tertiary)" }} axisLine={false} tickLine={false} />
                      <YAxis type="category" dataKey="name" tick={{ fontSize: 9, fill: "var(--text-tertiary)" }} axisLine={false} tickLine={false} width={40} />
                      <Tooltip content={<ChartTooltip />} />
                      {cmData.labels.map((l) => (
                        <Bar key={l} dataKey={l} stackId="a" fill="var(--chart-1)" fillOpacity={0.7} stroke="none" name={l} />
                      ))}
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </ChartCard>

            <ChartCard
              id="feature-importance"
              title="Feature Importance"
              description="Top 20 features by importance score"
              badge="Top 20"
              isFull={fullscreenId === "feature-importance"}
              onToggleFull={() => toggleFullscreen("feature-importance")}
            >
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={featureImportance.slice(0, 20)} layout="vertical" margin={{ top: 4, right: 8, bottom: 4, left: 8 }} barCategoryGap="20%">
                  <CartesianGrid stroke="var(--border-subtle)" strokeDasharray="3 3" horizontal={false} />
                  <XAxis type="number" domain={[0, 1]} tick={{ fontSize: 9, fill: "var(--text-tertiary)" }} axisLine={false} tickLine={false} />
                  <YAxis type="category" dataKey="feature" tick={{ fontSize: 8, fill: "var(--text-secondary)" }} axisLine={false} tickLine={false} width={100} />
                  <Tooltip content={<ChartTooltip />} />
                  <Bar dataKey="importance" radius={[0, 3, 3, 0]} maxBarSize={14}>
                    {featureImportance.slice(0, 20).map((entry, index) => (
                      <Cell key={entry.feature} fill={`var(--chart-${(index % 6) + 1})`} fillOpacity={0.85 - index * 0.025} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>

            <ChartCard
              id="embedding-viz"
              title="Embedding Visualization"
              description="t-SNE / UMAP projection of feature space"
              badge="2D"
              isFull={fullscreenId === "embedding-viz"}
              onToggleFull={() => toggleFullscreen("embedding-viz")}
            >
              <ResponsiveContainer width="100%" height="100%">
                <ScatterChart margin={{ top: 8, right: 8, bottom: 8, left: 0 }}>
                  <CartesianGrid stroke="var(--border-subtle)" strokeDasharray="3 3" />
                  <XAxis dataKey="x" tick={{ fontSize: 9, fill: "var(--text-tertiary)" }} axisLine={false} tickLine={false} domain={["auto", "auto"]} />
                  <YAxis dataKey="y" tick={{ fontSize: 9, fill: "var(--text-tertiary)" }} axisLine={false} tickLine={false} width={36} domain={["auto", "auto"]} />
                  <Tooltip content={<ChartTooltip />} />
                  <Legend wrapperStyle={{ fontSize: 10, color: "var(--text-secondary)" }} />
                  {["Cat", "Dog", "Bird", "Fish", "Frog"].map((cls, ci) => (
                    <Scatter
                      key={cls}
                      name={cls}
                      data={embeddings.filter((p) => p.label === cls)}
                      fill={`var(--chart-${ci + 1})`}
                      stroke="none"
                    />
                  ))}
                </ScatterChart>
              </ResponsiveContainer>
            </ChartCard>
          </div>
        </motion.div>

        <motion.div variants={item}>
          <div className="mb-3 flex items-center gap-2">
            <Activity className="h-4 w-4 text-[var(--text-tertiary)]" />
            <h2 className="text-sm font-semibold text-[var(--text-primary)]">System & Experiment Analytics</h2>
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            <ChartCard
              id="experiment-timeline"
              title="Experiment Timeline"
              description="Gantt view of experiment runs"
              badge="Gantt"
              isFull={fullscreenId === "experiment-timeline"}
              onToggleFull={() => toggleFullscreen("experiment-timeline")}
            >
              <div className="h-full overflow-auto">
                <div className="min-w-[500px]">
                  <div className="grid grid-cols-[160px_1fr] gap-2 text-xs text-[var(--text-tertiary)] mb-2">
                    <span>Experiment</span>
                    <span className="text-right">Timeline (14 days)</span>
                  </div>
                  <div className="space-y-1.5">
                    {experiments.map((exp) => (
                      <div key={exp.id} className="grid grid-cols-[160px_1fr] gap-2 items-center">
                        <div className="truncate text-xs text-[var(--text-secondary)]">
                          <span className="font-medium text-[var(--text-primary)]">{exp.name}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <GanttBar exp={exp} dayWidth={20} />
                          <StatusBadge status={exp.status} />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </ChartCard>

            <ChartCard
              id="resource-timeline"
              title="CPU / Memory Timeline"
              description="System resource usage over 24h"
              badge="Dual Axis"
              isFull={fullscreenId === "resource-timeline"}
              onToggleFull={() => toggleFullscreen("resource-timeline")}
            >
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={resourceTimeline.time.map((t, i) => ({ time: t, cpu: resourceTimeline.cpu[i], memory: resourceTimeline.memory[i] }))} margin={{ top: 8, right: 8, bottom: 8, left: 0 }}>
                  <CartesianGrid stroke="var(--border-subtle)" strokeDasharray="3 3" />
                  <XAxis dataKey="time" tick={{ fontSize: 9, fill: "var(--text-tertiary)" }} axisLine={false} tickLine={false} interval={2} />
                  <YAxis yAxisId="left" tick={{ fontSize: 9, fill: "var(--text-tertiary)" }} axisLine={false} tickLine={false} width={36} unit="%" label={{ value: "CPU %", angle: -90, position: "insideLeft", style: { fontSize: 10, fill: "var(--text-tertiary)" } }} />
                  <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 9, fill: "var(--text-tertiary)" }} axisLine={false} tickLine={false} width={36} unit=" GB" label={{ value: "Memory", angle: 90, position: "insideRight", style: { fontSize: 10, fill: "var(--text-tertiary)" } }} />
                  <Tooltip content={<ChartTooltip />} />
                  <Legend wrapperStyle={{ fontSize: 10, color: "var(--text-secondary)" }} />
                  <Area yAxisId="left" type="monotone" dataKey="cpu" stroke="var(--chart-1)" fill="var(--chart-1)" fillOpacity={0.12} strokeWidth={2} name="CPU Usage" dot={false} />
                  <Line yAxisId="right" type="monotone" dataKey="memory" stroke="var(--chart-2)" strokeWidth={2} name="Memory Usage" dot={false} activeDot={{ r: 4 }} />
                  {resourceTimeline.events.filter((e) => e.type === "checkpoint").map((ev, i) => {
                    const idx = resourceTimeline.time.indexOf(ev.time)
                    return idx >= 0 ? (
                      <Line key={i} yAxisId="left" data={[{ time: ev.time, cpu: 0 }]} dataKey="cpu" stroke="var(--warning)" strokeDasharray="3 3" strokeWidth={1} name={ev.label} dot={false} activeDot={false} />
                    ) : null
                  })}
                </ComposedChart>
              </ResponsiveContainer>
            </ChartCard>

            <ChartCard
              id="pipeline-dag"
              title="Pipeline DAG"
              description="Visual pipeline stage graph"
              badge="Pipeline"
              isFull={fullscreenId === "pipeline-dag"}
              onToggleFull={() => toggleFullscreen("pipeline-dag")}
            >
              <div className="flex flex-col items-center justify-center h-full gap-4">
                <svg viewBox="0 0 400 200" className="w-full max-w-[400px] h-auto">
                  {pipeline.edges.map((edge, i) => {
                    const fromIdx = pipeline.stages.findIndex((s) => s.id === edge.from)
                    const toIdx = pipeline.stages.findIndex((s) => s.id === edge.to)
                    const x1 = 40 + fromIdx * 64
                    const y1 = 90
                    const x2 = 40 + toIdx * 64
                    const y2 = 90
                    return (
                      <line key={i} x1={x1 + 28} y1={y1} x2={x2} y2={y2}
                        stroke="var(--border-strong)" strokeWidth={2} strokeDasharray={i < 3 ? "none" : "5 3"}
                      />
                    )
                  })}
                  {pipeline.stages.map((stage, i) => {
                    const cx = 40 + i * 64
                    const cy = 90
                    const colorMap: Record<string, string> = {
                      completed: "var(--success)",
                      running: "var(--warning)",
                      pending: "var(--text-tertiary)",
                      failed: "var(--danger)",
                    }
                    const isActive = pipelineStage === stage.id
                    return (
                      <g key={stage.id} onClick={() => setPipelineStage(stage.id)} style={{ cursor: "pointer" }}>
                        <rect x={cx} y={cy - 20} width={56} height={40} rx={8}
                          fill={colorMap[stage.status]}
                          fillOpacity={isActive ? 1 : 0.2}
                          stroke={colorMap[stage.status]}
                          strokeWidth={isActive ? 2.5 : 1.5}
                        />
                        <text x={cx + 28} y={cy + 4} textAnchor="middle"
                          fill={isActive ? "white" : "var(--text-secondary)"}
                          fontSize={9} fontWeight={600}
                        >
                          {stage.name}
                        </text>
                      </g>
                    )
                  })}
                </svg>
                {pipelineStage && (
                  <div className="animate-fade-up rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] px-4 py-2 text-xs text-[var(--text-secondary)]">
                    <span className="font-medium text-[var(--text-primary)]">
                      {pipeline.stages.find((s) => s.id === pipelineStage)?.name}
                    </span>
                    {" — "}Status: {pipeline.stages.find((s) => s.id === pipelineStage)?.status}
                    {" · "}Duration: {pipeline.stages.find((s) => s.id === pipelineStage)?.duration}
                  </div>
                )}
              </div>
            </ChartCard>
          </div>
        </motion.div>
      </div>

      {fullscreenId && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 backdrop-blur-sm"
          onClick={() => setFullscreenId(null)}
        >
          <div
            className="w-[90vw] h-[85vh] surface rounded-2xl shadow-[var(--shadow-lg)] overflow-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="sticky top-0 z-10 flex items-center justify-between border-b border-[var(--border-subtle)] bg-[var(--bg-surface)] px-5 py-3">
              <span className="text-sm font-semibold text-[var(--text-primary)]">{fullscreenId.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}</span>
              <div className="flex items-center gap-2">
                <ExportPngButton chartId={fullscreenId} />
                <button
                  onClick={() => setFullscreenId(null)}
                  className="flex h-8 w-8 items-center justify-center rounded-lg text-[var(--text-tertiary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>
            <div className="p-5" style={{ height: "calc(85vh - 60px)" }}>
              {fullscreenId === "loss-curves" && (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={epochsForLoss} margin={{ top: 16, right: 16, bottom: 16, left: 16 }}>
                    <CartesianGrid stroke="var(--border-subtle)" strokeDasharray="3 3" />
                    <XAxis dataKey="epoch" tick={{ fontSize: 11, fill: "var(--text-tertiary)" }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fontSize: 11, fill: "var(--text-tertiary)" }} axisLine={false} tickLine={false} width={48} />
                    <Tooltip content={<ChartTooltip />} />
                    <Legend wrapperStyle={{ fontSize: 11, color: "var(--text-secondary)" }} />
                    {activeAlgorithms.map((algo) => (
                      <Line key={`${algo}_tl`} type="monotone" dataKey={`${algo}_trainLoss`} stroke={ALGO_COLORS_HEX[algo]} strokeWidth={2.5} dot={false} name={`${algo} (Train)`} activeDot={{ r: 4 }} />
                    ))}
                    {activeAlgorithms.map((algo) => (
                      <Line key={`${algo}_vl`} type="monotone" dataKey={`${algo}_valLoss`} stroke={ALGO_COLORS_HEX[algo]} strokeWidth={2.5} strokeDasharray="5 4" dot={false} name={`${algo} (Val)`} activeDot={{ r: 4 }} />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              )}
              {fullscreenId === "accuracy-curves" && (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={epochsForLoss} margin={{ top: 16, right: 16, bottom: 16, left: 16 }}>
                    <CartesianGrid stroke="var(--border-subtle)" strokeDasharray="3 3" />
                    <XAxis dataKey="epoch" tick={{ fontSize: 11, fill: "var(--text-tertiary)" }} axisLine={false} tickLine={false} />
                    <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: "var(--text-tertiary)" }} axisLine={false} tickLine={false} width={48} />
                    <Tooltip content={<ChartTooltip />} />
                    <Legend wrapperStyle={{ fontSize: 11, color: "var(--text-secondary)" }} />
                    {activeAlgorithms.map((algo) => (
                      <Line key={`${algo}_ta`} type="monotone" dataKey={`${algo}_trainAcc`} stroke={ALGO_COLORS_HEX[algo]} strokeWidth={2.5} dot={false} name={`${algo} (Train)`} activeDot={{ r: 4 }} />
                    ))}
                    {activeAlgorithms.map((algo) => (
                      <Line key={`${algo}_va`} type="monotone" dataKey={`${algo}_valAcc`} stroke={ALGO_COLORS_HEX[algo]} strokeWidth={2.5} strokeDasharray="5 4" dot={false} name={`${algo} (Val)`} activeDot={{ r: 4 }} />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>
        </motion.div>
      )}

      <motion.div variants={item} className="flex items-center justify-between border-t border-[var(--border-subtle)] pt-4 text-[11px] text-[var(--text-tertiary)]">
        <span>Last updated: {format(new Date(), "MMM dd, yyyy HH:mm:ss")}</span>
        <span>VeriUnlearn v1.0 &middot; Visualizations Hub</span>
      </motion.div>
    </motion.div>
  )
}
