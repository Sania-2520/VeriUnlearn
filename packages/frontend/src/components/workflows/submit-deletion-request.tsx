"use client"

import { useState, useMemo, useCallback, useEffect } from "react"
import { useRouter } from "next/navigation"
import { clsx } from "clsx"
import {
  Database,
  Search,
  Check,
  FlaskConical,
  Clock,
  DollarSign,
  Shield,
  BarChart3,
  Zap,
  Gauge,
  Info,
} from "lucide-react"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  WorkflowProvider,
  useWorkflow,
  type Step,
} from "./workflow-context"
import { WorkflowStepper } from "./workflow-stepper"
import { WorkflowStep } from "./workflow-step"
import { WorkflowActions } from "./workflow-actions"

/* ── Mock Data ──────────────────────────────────────────────────── */

const mockDatasets = [
  { id: "ds-cifar10", name: "CIFAR-10", type: "Image", size: "170 MB", records: 60000, classes: 10 },
  { id: "ds-imdb", name: "IMDB Reviews", type: "Text", size: "80 MB", records: 50000, classes: 2 },
  { id: "ds-credit", name: "Credit Card Fraud", type: "Tabular", size: "144 MB", records: 284807, classes: 2 },
  { id: "ds-chexpert", name: "CheXpert", type: "Medical Image", size: "1.2 GB", records: 224316, classes: 14 },
  { id: "ds-fmnist", name: "Fashion MNIST", type: "Image", size: "30 MB", records: 70000, classes: 10 },
]

const algorithms = [
  {
    id: "sisa",
    name: "SISA",
    description: "Sharded, Isolated, Sliced, Aggregated unlearning",
    accuracy: 94,
    speed: 88,
    privacy: 96,
    bestFor: "Large-scale image classifiers",
  },
  {
    id: "retraining",
    name: "Retraining",
    description: "Full model retraining from scratch",
    accuracy: 99,
    speed: 25,
    privacy: 99,
    bestFor: "Small models, maximum accuracy",
  },
  {
    id: "amnesiac",
    name: "AmnesiacML",
    description: "Gradient-based influence unlearning",
    accuracy: 92,
    speed: 82,
    privacy: 88,
    bestFor: "Neural networks, fast deletion",
  },
  {
    id: "fisher",
    name: "FisherForgetting",
    description: "Fisher information matrix approximation",
    accuracy: 91,
    speed: 75,
    privacy: 93,
    bestFor: "Privacy-critical applications",
  },
  {
    id: "deltagrad",
    name: "DeltaGrad",
    description: "Efficient gradient difference method",
    accuracy: 93,
    speed: 90,
    privacy: 85,
    bestFor: "Real-time unlearning pipelines",
  },
]

/* ── Steps ──────────────────────────────────────────────────────── */

const steps: Step[] = [
  { id: "select-data", title: "Select Data", description: "Choose dataset and data points to forget" },
  { id: "choose-algorithm", title: "Algorithm", description: "Select unlearning algorithm" },
  { id: "configure", title: "Configure", description: "Set hyperparameters" },
  { id: "review", title: "Review & Submit", description: "Confirm and submit" },
]

/* ── Inner Components ────────────────────────────────────────────── */

function SelectDataStep() {
  const { formData, setStepValidation } = useWorkflow()
  const [search, setSearch] = useState("")
  const [selectedDataset, setSelectedDataset] = useState<string | null>(
    (formData.selectedDataset as string) ?? null,
  )
  const [selectedPoints, setSelectedPoints] = useState<number>(
    (formData.selectedPoints as number) ?? 50,
  )

  const filtered = useMemo(
    () =>
      mockDatasets.filter(
        (d) =>
          d.name.toLowerCase().includes(search.toLowerCase()) ||
          d.type.toLowerCase().includes(search.toLowerCase()),
      ),
    [search],
  )

  useEffect(() => {
    const valid = !!selectedDataset && selectedPoints > 0
    setStepValidation(0, {
      isValid: valid,
      message: valid ? undefined : "Select a dataset and specify data points to forget",
    })
  }, [selectedDataset, selectedPoints, setStepValidation])

  return (
    <WorkflowStep title="Select Data" description="Choose the dataset and specify how many records to forget.">
      <div className="space-y-5">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--text-tertiary)]" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search datasets..."
            className="w-full rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] pl-9 pr-3 py-2 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
          />
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          {filtered.map((ds) => {
            const selected = selectedDataset === ds.id
            return (
              <button
                key={ds.id}
                type="button"
                onClick={() => setSelectedDataset(ds.id)}
                className={clsx(
                  "flex items-start gap-3 rounded-lg border p-3 text-left transition-all",
                  selected
                    ? "border-[var(--brand)] bg-[var(--brand-soft)] ring-1 ring-[var(--brand-border)]"
                    : "border-[var(--border-default)] bg-[var(--bg-surface)] hover:border-[var(--border-strong)] hover:bg-[var(--bg-hover)]",
                )}
              >
                <span
                  className={clsx(
                    "flex h-9 w-9 shrink-0 items-center justify-center rounded-lg",
                    selected
                      ? "bg-[var(--brand)] text-[var(--text-on-brand)]"
                      : "bg-[var(--bg-subtle)] text-[var(--text-tertiary)]",
                  )}
                >
                  <Database className="h-4 w-4" />
                </span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-[var(--text-primary)]">{ds.name}</span>
                    <Badge tone="neutral">{ds.type}</Badge>
                  </div>
                  <p className="mt-0.5 text-xs text-[var(--text-tertiary)]">
                    {ds.records.toLocaleString()} records &middot; {ds.size}
                  </p>
                </div>
                {selected && <Check className="mt-1 h-4 w-4 text-[var(--brand)] shrink-0" />}
              </button>
            )
          })}
        </div>

        {selectedDataset && (
          <div className="animate-fade-up rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-subtle)] p-4">
            <label className="text-sm font-medium text-[var(--text-secondary)]">
              Number of records to forget
            </label>
            <div className="mt-2 flex items-center gap-4">
              <input
                type="range"
                min={1}
                max={1000}
                value={selectedPoints}
                onChange={(e) => setSelectedPoints(Number(e.target.value))}
                className="flex-1 accent-[var(--brand)]"
              />
              <span className="w-16 text-right text-sm font-semibold tabular-nums text-[var(--text-primary)]">
                {selectedPoints}
              </span>
            </div>
            <p className="mt-1 text-xs text-[var(--text-tertiary)]">
              {selectedPoints <= 10
                ? "Small request — should complete quickly."
                : selectedPoints <= 100
                  ? "Moderate request — typical processing time."
                  : "Large request — may take several minutes."}
            </p>
          </div>
        )}

        {!selectedDataset && (
          <p className="text-xs text-[var(--text-tertiary)]">Select a dataset to continue.</p>
        )}
      </div>
    </WorkflowStep>
  )
}

function ChooseAlgorithmStep() {
  const { formData, setStepValidation } = useWorkflow()
  const [selected, setSelected] = useState<string | null>(
    (formData.selectedAlgorithm as string) ?? null,
  )
  const [hovered, setHovered] = useState<string | null>(null)

  useEffect(() => {
    setStepValidation(1, {
      isValid: !!selected,
      message: selected ? undefined : "Select an unlearning algorithm",
    })
  }, [selected, setStepValidation])

  const activeId = hovered ?? selected
  const activeAlgo = algorithms.find((a) => a.id === activeId)

  return (
    <WorkflowStep title="Choose Algorithm" description="Select the unlearning algorithm that best fits your use case.">
      <div className="grid gap-4 lg:grid-cols-5">
        <div className="space-y-3 lg:col-span-3">
          {algorithms.map((algo) => {
            const isSelected = selected === algo.id
            const isHovered = hovered === algo.id
            return (
              <button
                key={algo.id}
                type="button"
                onClick={() => setSelected(algo.id)}
                onMouseEnter={() => setHovered(algo.id)}
                onMouseLeave={() => setHovered(null)}
                className={clsx(
                  "w-full rounded-lg border p-3 text-left transition-all",
                  isSelected
                    ? "border-[var(--brand)] bg-[var(--brand-soft)] ring-1 ring-[var(--brand-border)]"
                    : isHovered
                      ? "border-[var(--border-strong)] bg-[var(--bg-hover)]"
                      : "border-[var(--border-default)] bg-[var(--bg-surface)] hover:border-[var(--border-strong)] hover:bg-[var(--bg-hover)]",
                )}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-[var(--text-primary)]">{algo.name}</span>
                      <Badge tone="purple">{algo.id === "sisa" ? "Popular" : algo.id === "deltagrad" ? "Fastest" : algo.id === "fisher" ? "High Privacy" : ""}</Badge>
                    </div>
                    <p className="mt-0.5 text-xs text-[var(--text-secondary)]">{algo.description}</p>
                  </div>
                  {isSelected && <Check className="mt-0.5 h-4 w-4 shrink-0 text-[var(--brand)]" />}
                </div>
              </button>
            )
          })}
        </div>

        <div className="lg:col-span-2">
          {activeAlgo ? (
            <div className="animate-fade-up sticky top-4 rounded-xl border border-[var(--border-default)] bg-[var(--bg-surface-elevated)] p-4">
              <h4 className="text-sm font-semibold text-[var(--text-primary)]">{activeAlgo.name}</h4>
              <p className="mt-1 text-xs text-[var(--text-secondary)]">{activeAlgo.description}</p>

              <div className="mt-4 space-y-3">
                <MetricBar label="Accuracy" value={activeAlgo.accuracy} icon={Gauge} />
                <MetricBar label="Speed" value={activeAlgo.speed} icon={Zap} />
                <MetricBar label="Privacy" value={activeAlgo.privacy} icon={Shield} />
              </div>

              <div className="mt-4 rounded-lg bg-[var(--bg-subtle)] p-2.5">
                <p className="text-xs text-[var(--text-tertiary)]">
                  <span className="font-medium text-[var(--text-secondary)]">Best for:</span> {activeAlgo.bestFor}
                </p>
              </div>
            </div>
          ) : (
            <div className="flex h-full items-center justify-center rounded-xl border border-dashed border-[var(--border-default)] p-6">
              <div className="text-center">
                <FlaskConical className="mx-auto h-8 w-8 text-[var(--text-tertiary)]" />
                <p className="mt-2 text-xs text-[var(--text-tertiary)]">Select an algorithm to see metrics</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </WorkflowStep>
  )
}

function MetricBar({
  label,
  value,
  icon: Icon,
}: {
  label: string
  value: number
  icon: React.ComponentType<{ className?: string }>
}) {
  const color =
    value >= 90 ? "var(--success)" : value >= 70 ? "var(--warning)" : "var(--danger)"
  return (
    <div>
      <div className="flex items-center justify-between text-xs">
        <span className="flex items-center gap-1 text-[var(--text-secondary)]">
          <Icon className="h-3 w-3" /> {label}
        </span>
        <span className="font-medium tabular-nums text-[var(--text-primary)]">{value}%</span>
      </div>
      <div className="mt-1 h-1.5 rounded-full bg-[var(--bg-subtle)]">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${value}%`, backgroundColor: color }}
        />
      </div>
    </div>
  )
}

function ConfigureStep() {
  const { formData, setStepValidation } = useWorkflow()
  const [lr, setLr] = useState((formData.learningRate as number) ?? 0.001)
  const [batchSize, setBatchSize] = useState((formData.batchSize as number) ?? 32)
  const [epochs, setEpochs] = useState((formData.epochs as number) ?? 5)
  const [forgetRatio, setForgetRatio] = useState((formData.forgetRatio as number) ?? 0.1)

  useEffect(() => {
    const valid = lr > 0 && batchSize > 0 && epochs > 0 && forgetRatio > 0 && forgetRatio <= 1
    setStepValidation(2, { isValid: valid })
  }, [lr, batchSize, epochs, forgetRatio, setStepValidation])

  return (
    <WorkflowStep title="Configure Parameters" description="Fine-tune the unlearning process hyperparameters.">
      <div className="grid gap-6 sm:grid-cols-2">
        <div>
          <label className="text-sm font-medium text-[var(--text-secondary)]">Learning Rate</label>
          <input
            type="number"
            step={0.0001}
            value={lr}
            onChange={(e) => setLr(Number(e.target.value))}
            className="mt-1.5 w-full rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
          />
        </div>
        <div>
          <label className="text-sm font-medium text-[var(--text-secondary)]">Batch Size</label>
          <input
            type="number"
            step={1}
            value={batchSize}
            onChange={(e) => setBatchSize(Number(e.target.value))}
            className="mt-1.5 w-full rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
          />
        </div>
        <div>
          <label className="text-sm font-medium text-[var(--text-secondary)]">Epochs</label>
          <input
            type="number"
            step={1}
            value={epochs}
            onChange={(e) => setEpochs(Number(e.target.value))}
            className="mt-1.5 w-full rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
          />
        </div>
        <div>
          <label className="text-sm font-medium text-[var(--text-secondary)]">Forget Ratio</label>
          <div className="mt-1.5 flex items-center gap-3">
            <input
              type="range"
              min={0.01}
              max={1}
              step={0.01}
              value={forgetRatio}
              onChange={(e) => setForgetRatio(Number(e.target.value))}
              className="flex-1 accent-[var(--brand)]"
            />
            <span className="w-12 text-right text-sm font-semibold tabular-nums text-[var(--text-primary)]">
              {Math.round(forgetRatio * 100)}%
            </span>
          </div>
        </div>
      </div>

      <div className="mt-6 animate-fade-up rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-subtle)] p-4">
        <div className="flex items-start gap-3">
          <Info className="mt-0.5 h-4 w-4 text-[var(--info)] shrink-0" />
          <div className="text-xs text-[var(--text-secondary)]">
            <p className="font-medium text-[var(--text-primary)]">Impact Estimate</p>
            <ul className="mt-1 list-inside list-disc space-y-0.5">
              <li>Estimated runtime: ~{Math.round(epochs * batchSize * (1 + forgetRatio * 10) / 10)} min</li>
              <li>
                {forgetRatio < 0.15
                  ? "Low forget ratio — minimal model impact expected."
                  : forgetRatio < 0.35
                    ? "Moderate forget ratio — some retraining required."
                    : "High forget ratio — significant retraining needed."}
              </li>
            </ul>
          </div>
        </div>
      </div>
    </WorkflowStep>
  )
}

function ReviewStep() {
  const { formData } = useWorkflow()

  const dataset = mockDatasets.find((d) => d.id === formData.selectedDataset)
  const algo = algorithms.find((a) => a.id === formData.selectedAlgorithm)

  return (
    <WorkflowStep title="Review & Submit" description="Verify your selections before submitting the deletion request.">
      <div className="space-y-4">
        <Card>
          <CardHeader title="Dataset" />
          <CardContent>
            <div className="flex items-center gap-3">
              <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-[var(--brand-soft)] text-[var(--brand)]">
                <Database className="h-5 w-5" />
              </span>
              <div>
                <p className="text-sm font-medium text-[var(--text-primary)]">{dataset?.name ?? "—"}</p>
                <p className="text-xs text-[var(--text-secondary)]">
                  {dataset?.type} &middot; {dataset?.records?.toLocaleString()} records
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader title="Algorithm" />
          <CardContent>
            <div className="flex items-center gap-3">
              <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-[var(--purple-soft)] text-[var(--purple)]">
                <FlaskConical className="h-5 w-5" />
              </span>
              <div>
                <p className="text-sm font-medium text-[var(--text-primary)]">{algo?.name ?? "—"}</p>
                <p className="text-xs text-[var(--text-secondary)]">{algo?.description}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader title="Parameters" />
          <CardContent>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <div>
                <p className="text-xs text-[var(--text-tertiary)]">Learning Rate</p>
                <p className="text-sm font-semibold text-[var(--text-primary)]">{formData.learningRate as number}</p>
              </div>
              <div>
                <p className="text-xs text-[var(--text-tertiary)]">Batch Size</p>
                <p className="text-sm font-semibold text-[var(--text-primary)]">{formData.batchSize as number}</p>
              </div>
              <div>
                <p className="text-xs text-[var(--text-tertiary)]">Epochs</p>
                <p className="text-sm font-semibold text-[var(--text-primary)]">{formData.epochs as number}</p>
              </div>
              <div>
                <p className="text-xs text-[var(--text-tertiary)]">Forget Ratio</p>
                <p className="text-sm font-semibold text-[var(--text-primary)]">
                  {Math.round((formData.forgetRatio as number) * 100)}%
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader title="Estimate" />
          <CardContent>
            <div className="grid gap-4 sm:grid-cols-3">
              <div className="flex items-center gap-3 rounded-lg bg-[var(--bg-subtle)] p-3">
                <Clock className="h-5 w-5 text-[var(--text-tertiary)]" />
                <div>
                  <p className="text-xs text-[var(--text-tertiary)]">Est. Time</p>
                  <p className="text-sm font-semibold text-[var(--text-primary)]">
                    ~{Math.round((formData.epochs as number) * (formData.batchSize as number) * (1 + (formData.forgetRatio as number) * 10) / 10)} min
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3 rounded-lg bg-[var(--bg-subtle)] p-3">
                <DollarSign className="h-5 w-5 text-[var(--text-tertiary)]" />
                <div>
                  <p className="text-xs text-[var(--text-tertiary)]">Est. Cost</p>
                  <p className="text-sm font-semibold text-[var(--text-primary)]">$0.42</p>
                </div>
              </div>
              <div className="flex items-center gap-3 rounded-lg bg-[var(--bg-subtle)] p-3">
                <BarChart3 className="h-5 w-5 text-[var(--text-tertiary)]" />
                <div>
                  <p className="text-xs text-[var(--text-tertiary)]">Confidence</p>
                  <p className="text-sm font-semibold text-[var(--success)]">High</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </WorkflowStep>
  )
}

/* ── Main Wizard ──────────────────────────────────────────────────── */

export function SubmitDeletionRequest() {
  const router = useRouter()
  const [error, setError] = useState<string | null>(null)

  const handleComplete = useCallback(
    async (data: Record<string, unknown>) => {
      try {
        console.log("Submitting deletion request:", data)
        await new Promise((resolve) => setTimeout(resolve, 1500))
        router.push("/dashboard/unlearning")
      } catch {
        setError("Failed to submit request. Please try again.")
      }
    },
    [router],
  )

  return (
    <WorkflowProvider steps={steps} onComplete={handleComplete}>
      <WorkflowInner onCancel={() => router.push("/dashboard/unlearning")} error={error} />
    </WorkflowProvider>
  )
}

function WorkflowInner({ onCancel, error }: { onCancel: () => void; error: string | null }) {
  const { formData, setIsSubmitting } = useWorkflow()
  const router = useRouter()
  const [submitError, setSubmitError] = useState<string | null>(error)

  useEffect(() => setSubmitError(error), [error])

  const handleComplete = async () => {
    setIsSubmitting(true)
    setSubmitError(null)
    try {
      console.log("Submitting deletion request:", formData)
      await new Promise((resolve) => setTimeout(resolve, 2000))
      router.push("/dashboard/unlearning")
    } catch {
      setSubmitError("Failed to submit request. Please try again.")
      setIsSubmitting(false)
    }
  }

  return (
    <div className="mx-auto max-w-3xl">
      <WorkflowStepper className="mb-8" />

      <div className="min-h-[400px]">
        <SelectDataStep />
        <ChooseAlgorithmStep />
        <ConfigureStep />
        <ReviewStep />
      </div>

      {submitError && (
        <div className="mt-4 rounded-lg border border-[var(--danger-border)] bg-[var(--danger-soft)] p-3 text-sm text-[var(--danger)]">
          {submitError}
        </div>
      )}

      <WorkflowActions
        onCancel={onCancel}
        onComplete={handleComplete}
        className="mt-8 border-t border-[var(--border-subtle)] pt-6"
      />
    </div>
  )
}
