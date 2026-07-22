"use client"

import { useEffect, useState, useCallback } from "react"
import { Button } from "@/components/ui/button"
import { startTraining, listCheckpoints } from "@/lib/api/client"
import {
  Play,
  RefreshCw,
  AlertCircle,
  CheckCircle,
  Clock,
  XCircle,
  Layers,
  Settings,
  BarChart3,
} from "lucide-react"

interface TrainingConfig {
  model_name: string
  dataset_path: string
  lora_rank: number
  lora_alpha: number
  epochs: number
  learning_rate: number
  batch_size: number
  max_seq_length: number
}

interface TrainingJob {
  id: string
  status: "queued" | "running" | "completed" | "failed"
  progress: number
  config: TrainingConfig
  metrics?: {
    loss?: number
    accuracy?: number
    learning_rate?: number
  }
  created_at: string
  started_at?: string
  completed_at?: string
  error_message?: string
}

interface Checkpoint {
  id: string
  job_id: string
  step: number
  epoch: number
  loss: number
  accuracy?: number
  file_path: string
  created_at: string
}

const defaultConfig: TrainingConfig = {
  model_name: "",
  dataset_path: "",
  lora_rank: 16,
  lora_alpha: 32,
  epochs: 3,
  learning_rate: 2e-4,
  batch_size: 8,
  max_seq_length: 512,
}

export default function TrainingPage() {
  const [config, setConfig] = useState<TrainingConfig>(defaultConfig)
  const [isStarting, setIsStarting] = useState(false)
  const [activeJob, setActiveJob] = useState<TrainingJob | null>(null)
  const [checkpoints, setCheckpoints] = useState<Checkpoint[]>([])
  const [isLoadingCheckpoints, setIsLoadingCheckpoints] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const fetchCheckpoints = useCallback(async () => {
    setIsLoadingCheckpoints(true)
    try {
      const res = await listCheckpoints()
      setCheckpoints(res.data || res.checkpoints || [])
    } catch (err) {
      console.error("Failed to fetch checkpoints:", err)
    } finally {
      setIsLoadingCheckpoints(false)
    }
  }, [])

  useEffect(() => {
    fetchCheckpoints()
  }, [fetchCheckpoints])

  const handleStartTraining = async () => {
    if (!config.model_name.trim()) {
      setError("Model name is required")
      return
    }
    if (!config.dataset_path.trim()) {
      setError("Dataset path is required")
      return
    }
    setIsStarting(true)
    setError(null)
    setSuccess(null)
    try {
      const res = await startTraining(config)
      setActiveJob(res)
      setSuccess("Training job started successfully")
      setTimeout(() => setSuccess(null), 5000)
    } catch (err) {
      console.error("Failed to start training job:", err)
      setError("Failed to start training job")
    } finally {
      setIsStarting(false)
    }
  }

  const updateConfig = (key: keyof TrainingConfig, value: string | number) => {
    setConfig((prev) => ({ ...prev, [key]: value }))
  }

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">LoRA Training</h1>
          <p className="text-sm text-[var(--text-tertiary)] mt-1">Configure and run LoRA fine-tuning jobs</p>
        </div>
        <button
          onClick={fetchCheckpoints}
          className="flex items-center gap-2 px-3 py-2 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] bg-[var(--bg-hover)] hover:bg-[var(--bg-active)] border border-[var(--bg-hover)] hover:border-[var(--border-strong)] rounded-lg transition-colors cursor-pointer"
        >
          <RefreshCw className="h-4 w-4" />
        </button>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-3 bg-[var(--danger-soft)] border border-[var(--danger-border)] rounded-lg text-sm text-[var(--danger)]">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {error}
          <button onClick={() => setError(null)} className="ml-auto text-[var(--danger)] hover:text-[var(--danger-border)] cursor-pointer">
            ×
          </button>
        </div>
      )}

      {success && (
        <div className="flex items-center gap-2 p-3 bg-[var(--brand-soft)] border border-[var(--brand-border)] rounded-lg text-sm text-[var(--brand)]">
          <CheckCircle className="h-4 w-4 shrink-0" />
          {success}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Training Configuration */}
        <div className="lg:col-span-2 bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-xl p-5">
          <div className="flex items-center gap-2 mb-5">
            <Settings className="h-4 w-4 text-[var(--brand)]" />
            <h2 className="text-sm font-semibold text-[var(--text-primary)]">Training Configuration</h2>
          </div>

          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs text-[var(--text-tertiary)] font-medium">Model Name *</label>
                <input
                  type="text"
                  value={config.model_name}
                  onChange={(e) => updateConfig("model_name", e.target.value)}
                  placeholder="e.g. llama-3.2-3b"
                  className="w-full px-3 py-2 bg-[var(--bg-app)] border border-[var(--border-default)] focus:border-[var(--border-strong)] rounded-lg text-sm text-[var(--text-primary)] placeholder-[var(--text-tertiary)] focus:outline-none transition-colors"
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-xs text-[var(--text-tertiary)] font-medium">Dataset Path *</label>
                <input
                  type="text"
                  value={config.dataset_path}
                  onChange={(e) => updateConfig("dataset_path", e.target.value)}
                  placeholder="e.g. /data/training_data.jsonl"
                  className="w-full px-3 py-2 bg-[var(--bg-app)] border border-[var(--border-default)] focus:border-[var(--border-strong)] rounded-lg text-sm text-[var(--text-primary)] placeholder-[var(--text-tertiary)] focus:outline-none transition-colors"
                />
              </div>
            </div>

            <div className="border-t border-[var(--border-default)] pt-4">
              <p className="text-xs text-[var(--text-tertiary)] uppercase tracking-wider font-semibold mb-3">LoRA Parameters</p>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs text-[var(--text-tertiary)] font-medium">Rank</label>
                  <input
                    type="number"
                    value={config.lora_rank}
                    onChange={(e) => updateConfig("lora_rank", parseInt(e.target.value) || 16)}
                    className="w-full px-3 py-2 bg-[var(--bg-app)] border border-[var(--border-default)] focus:border-[var(--border-strong)] rounded-lg text-sm text-[var(--text-primary)] focus:outline-none transition-colors"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs text-[var(--text-tertiary)] font-medium">Alpha</label>
                  <input
                    type="number"
                    value={config.lora_alpha}
                    onChange={(e) => updateConfig("lora_alpha", parseInt(e.target.value) || 32)}
                    className="w-full px-3 py-2 bg-[var(--bg-app)] border border-[var(--border-default)] focus:border-[var(--border-strong)] rounded-lg text-sm text-[var(--text-primary)] focus:outline-none transition-colors"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs text-[var(--text-tertiary)] font-medium">Learning Rate</label>
                  <input
                    type="text"
                    value={config.learning_rate}
                    onChange={(e) => updateConfig("learning_rate", parseFloat(e.target.value) || 2e-4)}
                    className="w-full px-3 py-2 bg-[var(--bg-app)] border border-[var(--border-default)] focus:border-[var(--border-strong)] rounded-lg text-sm text-[var(--text-primary)] focus:outline-none transition-colors"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs text-[var(--text-tertiary)] font-medium">Max Seq Length</label>
                  <input
                    type="number"
                    value={config.max_seq_length}
                    onChange={(e) => updateConfig("max_seq_length", parseInt(e.target.value) || 512)}
                    className="w-full px-3 py-2 bg-[var(--bg-app)] border border-[var(--border-default)] focus:border-[var(--border-strong)] rounded-lg text-sm text-[var(--text-primary)] focus:outline-none transition-colors"
                  />
                </div>
              </div>
            </div>

            <div className="border-t border-[var(--border-default)] pt-4">
              <p className="text-xs text-[var(--text-tertiary)] uppercase tracking-wider font-semibold mb-3">Training Parameters</p>
              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs text-[var(--text-tertiary)] font-medium">Epochs</label>
                  <input
                    type="number"
                    value={config.epochs}
                    onChange={(e) => updateConfig("epochs", parseInt(e.target.value) || 3)}
                    min={1}
                    className="w-full px-3 py-2 bg-[var(--bg-app)] border border-[var(--border-default)] focus:border-[var(--border-strong)] rounded-lg text-sm text-[var(--text-primary)] focus:outline-none transition-colors"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs text-[var(--text-tertiary)] font-medium">Batch Size</label>
                  <input
                    type="number"
                    value={config.batch_size}
                    onChange={(e) => updateConfig("batch_size", parseInt(e.target.value) || 8)}
                    min={1}
                    className="w-full px-3 py-2 bg-[var(--bg-app)] border border-[var(--border-default)] focus:border-[var(--border-strong)] rounded-lg text-sm text-[var(--text-primary)] focus:outline-none transition-colors"
                  />
                </div>
              </div>
            </div>

            <div className="pt-2">
              <Button onClick={handleStartTraining} loading={isStarting} variant="primary" size="md">
                <Play className="h-4 w-4 mr-2" />
                Start Training
              </Button>
            </div>
          </div>
        </div>

        {/* Training Progress Sidebar */}
        <div className="space-y-4">
          {/* Active Job */}
          <div className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-xl p-5">
            <div className="flex items-center gap-2 mb-4">
              <BarChart3 className="h-4 w-4 text-[var(--brand)]" />
              <h2 className="text-sm font-semibold text-[var(--text-primary)]">Training Progress</h2>
            </div>

            {activeJob ? (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-[var(--text-tertiary)]">Status</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full border ${
                    activeJob.status === "running"
                      ? "bg-[var(--brand-soft)] text-[var(--brand)] border-[var(--brand-border)]"
                      : activeJob.status === "completed"
                        ? "bg-[var(--brand-soft)] text-[var(--brand)] border-[var(--brand-border)]"
                        : activeJob.status === "failed"
                          ? "bg-[var(--danger-soft)] text-[var(--danger)] border-[var(--danger-border)]"
                          : "bg-[var(--warning-soft)] text-[var(--warning)] border-[var(--warning-border)]"
                  }`}>
                    {activeJob.status}
                  </span>
                </div>

                <div>
                  <div className="flex justify-between text-xs text-[var(--text-tertiary)] mb-1.5">
                    <span>Progress</span>
                    <span>{activeJob.progress}%</span>
                  </div>
                  <div className="w-full h-2 bg-[var(--bg-hover)] rounded-full overflow-hidden">
                    <div
                      className="h-full bg-[var(--brand)] rounded-full transition-all duration-500"
                      style={{ width: `${activeJob.progress}%` }}
                    />
                  </div>
                </div>

                {activeJob.metrics && (
                  <div className="space-y-2">
                    {activeJob.metrics.loss !== undefined && (
                      <div className="flex justify-between text-xs">
                        <span className="text-[var(--text-tertiary)]">Loss</span>
                        <span className="text-[var(--text-secondary)] font-mono">{activeJob.metrics.loss.toFixed(4)}</span>
                      </div>
                    )}
                    {activeJob.metrics.accuracy !== undefined && (
                      <div className="flex justify-between text-xs">
                        <span className="text-[var(--text-tertiary)]">Accuracy</span>
                        <span className="text-[var(--text-secondary)] font-mono">{(activeJob.metrics.accuracy * 100).toFixed(2)}%</span>
                      </div>
                    )}
                    {activeJob.metrics.learning_rate !== undefined && (
                      <div className="flex justify-between text-xs">
                        <span className="text-[var(--text-tertiary)]">Learning Rate</span>
                        <span className="text-[var(--text-secondary)] font-mono">{activeJob.metrics.learning_rate.toExponential(2)}</span>
                      </div>
                    )}
                  </div>
                )}

                <div className="space-y-1 text-xs text-[var(--text-tertiary)]">
                  {activeJob.started_at && (
                    <div className="flex items-center gap-1.5">
                      <Clock className="h-3 w-3" />
                      Started: {new Date(activeJob.started_at).toLocaleTimeString()}
                    </div>
                  )}
                  {activeJob.completed_at && (
                    <div className="flex items-center gap-1.5">
                      <CheckCircle className="h-3 w-3" />
                      Completed: {new Date(activeJob.completed_at).toLocaleTimeString()}
                    </div>
                  )}
                  {activeJob.error_message && (
                    <div className="flex items-start gap-1.5 text-[var(--danger)]">
                      <XCircle className="h-3 w-3 mt-0.5 shrink-0" />
                      {activeJob.error_message}
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="text-center py-6 text-[var(--text-tertiary)]">
                <Play className="h-6 w-6 mx-auto mb-2 opacity-40" />
                <p className="text-xs">No active training job</p>
              </div>
            )}
          </div>

          {/* Checkpoints */}
          <div className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-xl p-5">
            <div className="flex items-center gap-2 mb-4">
              <Layers className="h-4 w-4 text-[var(--brand)]" />
              <h2 className="text-sm font-semibold text-[var(--text-primary)]">Checkpoints</h2>
              <span className="text-xs text-[var(--text-tertiary)] ml-auto">{checkpoints.length}</span>
            </div>

            {isLoadingCheckpoints ? (
              <div className="flex items-center justify-center py-6">
                <div className="animate-spin h-5 w-5 border-2 border-[var(--brand)] border-t-transparent rounded-full" />
              </div>
            ) : checkpoints.length === 0 ? (
              <div className="text-center py-6 text-[var(--text-tertiary)]">
                <Layers className="h-6 w-6 mx-auto mb-2 opacity-40" />
                <p className="text-xs">No checkpoints yet</p>
              </div>
            ) : (
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {checkpoints.map((cp) => (
                  <div key={cp.id} className="p-2.5 bg-[var(--bg-app)] border border-[var(--border-default)] rounded-lg">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-medium text-[var(--text-secondary)]">
                        Step {cp.step} · Epoch {cp.epoch}
                      </span>
                      <span className="text-xs text-[var(--text-tertiary)]">
                        {new Date(cp.created_at).toLocaleTimeString()}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 text-xs text-[var(--text-tertiary)]">
                      <span>Loss: <span className="text-[var(--text-secondary)] font-mono">{cp.loss.toFixed(4)}</span></span>
                      {cp.accuracy !== undefined && (
                        <span>Acc: <span className="text-[var(--text-secondary)] font-mono">{(cp.accuracy * 100).toFixed(1)}%</span></span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
