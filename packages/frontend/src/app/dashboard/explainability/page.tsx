"use client"

import { useState } from "react"
import { useAuthStore } from "@/lib/store/auth-store"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import {
  Brain,
  BarChart3,
  GitCompare,
  Shield,
  Activity,
  ChevronDown,
  Loader2,
  AlertCircle,
  CheckCircle2,
} from "lucide-react"
import { clsx } from "clsx"

type ExplainMethod = "shap" | "lime" | "integrated_gradients" | "gradient" | "occlusion" | "perturbation"

interface ExplainResult {
  feature: string
  importance: number
  direction: string
}

interface ComparisonResult {
  feature: string
  pre: number
  post: number
  shift: number
}

const METHODS: { id: ExplainMethod; label: string; description: string }[] = [
  { id: "shap", label: "SHAP", description: "Game-theoretic feature importance" },
  { id: "lime", label: "LIME", description: "Local surrogate explanations" },
  { id: "integrated_gradients", label: "Integrated Gradients", description: "Path integral gradient attribution" },
  { id: "gradient", label: "Gradient", description: "Simple gradient attribution" },
  { id: "occlusion", label: "Occlusion", description: "Ablation-based attribution" },
  { id: "perturbation", label: "Perturbation", description: "Random perturbation importance" },
]

function ImportanceBar({ label, value, direction, maxVal }: { label: string; value: number; direction: string; maxVal: number }) {
  const pct = maxVal > 0 ? (value / maxVal) * 100 : 0
  const color = direction === "positive" ? "bg-emerald-500" : "bg-red-500"
  return (
    <div className="flex items-center gap-3 text-sm">
      <span className="w-24 text-right text-gray-400 truncate text-xs">{label}</span>
      <div className="flex-1 h-3 bg-[#171717] rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all duration-500`} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-16 text-right text-gray-300 text-xs font-mono">{value.toFixed(4)}</span>
    </div>
  )
}

export default function ExplainabilityPage() {
  const { user } = useAuthStore()
  const [selectedMethod, setSelectedMethod] = useState<ExplainMethod>("shap")
  const [methodDropdown, setMethodDropdown] = useState(false)
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<"samples" | "features" | "compare" | "heatmap" | "drift">("samples")
  const [sampleResults, setSampleResults] = useState<ExplainResult[]>([])
  const [comparisonResults, setComparisonResults] = useState<ComparisonResult[]>([])
  const [driftSummary, setDriftSummary] = useState<Record<string, unknown> | null>(null)
  const [error, setError] = useState<string | null>(null)

  if (!user) return null

  const runSampleExplanation = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch("/api/v1/explain/samples", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${localStorage.getItem("access_token")}` },
        body: JSON.stringify({
          samples: [[1.0, 0.5, 0.2, 0.8, 0.3]],
          method: selectedMethod,
        }),
      })
      const data = await res.json()
      if (data.results?.[0]?.feature_importances) {
        setSampleResults(data.results[0].feature_importances)
      }
    } catch {
      setError("Failed to explain samples. Check ML Engine connection.")
    } finally {
      setLoading(false)
    }
  }

  const runFeatureAnalysis = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch("/api/v1/explain/features", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${localStorage.getItem("access_token")}` },
        body: JSON.stringify({
          dataset: [[1.0, 0.5, 0.2], [0.8, 0.3, 0.9], [0.1, 0.7, 0.4]],
          method: selectedMethod,
        }),
      })
      const data = await res.json()
      if (data.global_importance) {
        setSampleResults(
          Object.entries(data.global_importance).map(([feature, importance]) => ({
            feature,
            importance: importance as number,
            direction: (importance as number) >= 0 ? "positive" : "negative",
          }))
        )
      }
    } catch {
      setError("Failed to analyze features.")
    } finally {
      setLoading(false)
    }
  }

  const runComparison = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch("/api/v1/explain/compare", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${localStorage.getItem("access_token")}` },
        body: JSON.stringify({
          pre_unlearn_samples: [[1.0, 0.5, 0.2]],
          post_unlearn_samples: [[0.9, 0.6, 0.1]],
          method: selectedMethod,
        }),
      })
      const data = await res.json()
      if (data.comparisons?.[0]?.shifts) {
        setComparisonResults(data.comparisons[0].shifts)
      }
    } catch {
      setError("Failed to compare explanations.")
    } finally {
      setLoading(false)
    }
  }

  const runDriftAnalysis = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch("/api/v1/explain/drift", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${localStorage.getItem("access_token")}` },
        body: JSON.stringify({
          pre_confidences: [0.85, 0.82, 0.88, 0.84, 0.86],
          post_confidences: [0.79, 0.75, 0.81, 0.77, 0.80],
          pre_importances: [{ f0: 0.5, f1: 0.3, f2: 0.2 }],
          post_importances: [{ f0: 0.4, f1: 0.35, f2: 0.25 }],
        }),
      })
      setDriftSummary(data)
    } catch {
      setError("Failed to analyze drift.")
    } finally {
      setLoading(false)
    }
  }

  const runAction = () => {
    switch (activeTab) {
      case "samples":
        runSampleExplanation()
        break
      case "features":
        runFeatureAnalysis()
        break
      case "compare":
        runComparison()
        break
      case "drift":
        runDriftAnalysis()
        break
    }
  }

  const maxImportance = Math.max(...sampleResults.map((r) => r.importance), 0.001)

  const tabs = [
    { id: "samples" as const, label: "Explain Samples", icon: Brain },
    { id: "features" as const, label: "Feature Analysis", icon: BarChart3 },
    { id: "compare" as const, label: "Before/After Compare", icon: GitCompare },
    { id: "heatmap" as const, label: "Privacy Heatmap", icon: Shield },
    { id: "drift" as const, label: "Model Drift", icon: Activity },
  ]

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto w-full">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-100">Explainability</h1>
          <p className="text-sm text-gray-500 mt-1">
            Model interpretability with SHAP, LIME, Integrated Gradients, and feature attribution
          </p>
        </div>
      </div>

      <div className="flex items-center justify-between">
        <div className="flex flex-wrap gap-1.5">
          {tabs.map((tab) => {
            const TabIcon = tab.icon
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={clsx(
                  "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer",
                  activeTab === tab.id
                    ? "bg-emerald-600/20 text-emerald-400 border border-emerald-600/30"
                    : "text-gray-400 hover:bg-[#2f2f2f] border border-transparent"
                )}
              >
                <TabIcon className="h-3.5 w-3.5" />
                {tab.label}
              </button>
            )
          })}
        </div>

        <div className="flex items-center gap-3">
          <div className="relative">
            <button
              onClick={() => setMethodDropdown(!methodDropdown)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#171717] border border-[#2f2f2f] text-xs text-gray-300 hover:text-white transition-colors cursor-pointer"
            >
              {METHODS.find((m) => m.id === selectedMethod)?.label}
              <ChevronDown className="h-3 w-3" />
            </button>
            {methodDropdown && (
              <div className="absolute top-10 right-0 w-52 bg-[#171717] border border-[#2f2f2f] rounded-xl shadow-2xl py-1.5 z-40 text-xs">
                {METHODS.map((m) => (
                  <button
                    key={m.id}
                    onClick={() => {
                      setSelectedMethod(m.id)
                      setMethodDropdown(false)
                    }}
                    className={clsx(
                      "w-full text-left px-4 py-2 hover:bg-[#2f2f2f] transition-colors cursor-pointer",
                      selectedMethod === m.id ? "text-emerald-400 font-medium" : "text-gray-300"
                    )}
                  >
                    <span className="font-medium">{m.label}</span>
                    <p className="text-gray-500 text-[10px] mt-0.5">{m.description}</p>
                  </button>
                ))}
              </div>
            )}
          </div>

          <button
            onClick={runAction}
            disabled={loading}
            className="flex items-center gap-1.5 px-4 py-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:bg-emerald-600/50 rounded-lg text-xs font-medium text-white transition-colors cursor-pointer"
          >
            {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Brain className="h-3.5 w-3.5" />}
            {loading ? "Computing..." : "Run"}
          </button>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 px-4 py-3 bg-red-900/20 border border-red-800/30 rounded-xl text-sm text-red-400">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {error}
        </div>
      )}

      <Card className="bg-[#171717] border-[#2f2f2f]/50">
        <CardHeader className="border-b border-[#2f2f2f]/30 pb-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-gray-200">
              {activeTab === "samples" && "Sample Explanations"}
              {activeTab === "features" && "Global Feature Importance"}
              {activeTab === "compare" && "Before / After Unlearning Comparison"}
              {activeTab === "heatmap" && "Privacy Risk Heatmap"}
              {activeTab === "drift" && "Model Drift Analysis"}
            </h2>
            {sampleResults.length > 0 && (
              <div className="flex items-center gap-1 text-xs text-emerald-400">
                <CheckCircle2 className="h-3 w-3" />
                {sampleResults.length} features
              </div>
            )}
          </div>
        </CardHeader>
        <CardContent className="pt-4">
          {activeTab === "samples" && (
            <div className="space-y-2">
              {sampleResults.length === 0 && !loading && (
                <p className="text-sm text-gray-500 text-center py-8">Click &quot;Run&quot; to explain a sample input with {METHODS.find((m) => m.id === selectedMethod)?.label}.</p>
              )}
              {sampleResults.map((r, i) => (
                <ImportanceBar key={i} label={r.feature} value={r.importance} direction={r.direction} maxVal={maxImportance} />
              ))}
            </div>
          )}

          {activeTab === "features" && (
            <div className="space-y-2">
              {sampleResults.length === 0 && !loading && (
                <p className="text-sm text-gray-500 text-center py-8">Run feature analysis to see global importance scores.</p>
              )}
              {sampleResults.map((r, i) => (
                <ImportanceBar key={i} label={r.feature} value={r.importance} direction={r.direction} maxVal={maxImportance} />
              ))}
            </div>
          )}

          {activeTab === "compare" && (
            <div className="space-y-3">
              {comparisonResults.length === 0 && !loading && (
                <p className="text-sm text-gray-500 text-center py-8">Run a comparison to see how feature importance shifts after unlearning.</p>
              )}
              {comparisonResults.map((r, i) => (
                <div key={i} className="flex items-center gap-3 text-sm">
                  <span className="w-24 text-right text-gray-400 truncate text-xs">{r.feature}</span>
                  <div className="flex-1 flex items-center gap-1">
                    <div className="flex-1 h-2 bg-[#212121] rounded-full overflow-hidden">
                      <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${Math.abs(r.pre) * 100}%` }} />
                    </div>
                    <span className="text-xs text-gray-500 w-8 text-center">vs</span>
                    <div className="flex-1 h-2 bg-[#212121] rounded-full overflow-hidden">
                      <div className={clsx("h-full rounded-full", r.shift >= 0 ? "bg-emerald-500" : "bg-red-500")} style={{ width: `${Math.abs(r.post) * 100}%` }} />
                    </div>
                  </div>
                  <span className={clsx("w-12 text-right text-xs font-mono", r.shift >= 0 ? "text-emerald-400" : "text-red-400")}>
                    {r.shift >= 0 ? "+" : ""}{r.shift.toFixed(3)}
                  </span>
                </div>
              ))}
            </div>
          )}

          {activeTab === "heatmap" && (
            <div className="text-center py-8">
              <Shield className="h-8 w-8 text-gray-600 mx-auto mb-3" />
              <p className="text-sm text-gray-500">Privacy risk heatmap visualization integrates with security assessments.</p>
              <p className="text-xs text-gray-600 mt-1">Use the Security module to generate privacy scores, then visualize them here.</p>
            </div>
          )}

          {activeTab === "drift" && (
            <div className="space-y-4">
              {!driftSummary && !loading && (
                <p className="text-sm text-gray-500 text-center py-8">Run drift analysis to detect model behavior changes after unlearning.</p>
              )}
              {driftSummary && (
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-[#212121] rounded-xl p-4 border border-[#2f2f2f]/30">
                    <p className="text-xs text-gray-500 mb-1">Confidence Drift</p>
                    <p className={clsx("text-lg font-semibold", (driftSummary.confidence_drift as number) < -0.01 ? "text-red-400" : "text-emerald-400")}>
                      {(driftSummary.confidence_drift as number).toFixed(4)}
                    </p>
                  </div>
                  <div className="bg-[#212121] rounded-xl p-4 border border-[#2f2f2f]/30">
                    <p className="text-xs text-gray-500 mb-1">Importance Drift</p>
                    <p className={clsx("text-lg font-semibold", (driftSummary.importance_drift as number) > 0.1 ? "text-red-400" : "text-emerald-400")}>
                      {(driftSummary.importance_drift as number).toFixed(4)}
                    </p>
                  </div>
                  <div className="bg-[#212121] rounded-xl p-4 border border-[#2f2f2f]/30">
                    <p className="text-xs text-gray-500 mb-1">Pre-Volatility</p>
                    <p className="text-lg font-semibold text-gray-200">{(driftSummary.volatility_pre as number).toFixed(4)}</p>
                  </div>
                  <div className="bg-[#212121] rounded-xl p-4 border border-[#2f2f2f]/30">
                    <p className="text-xs text-gray-500 mb-1">Post-Volatility</p>
                    <p className="text-lg font-semibold text-gray-200">{(driftSummary.volatility_post as number).toFixed(4)}</p>
                  </div>
                  <div className="col-span-2 bg-[#212121] rounded-xl p-4 border border-[#2f2f2f]/30">
                    <p className="text-xs text-gray-500 mb-1">Status</p>
                    <div className="flex items-center gap-2">
                      <div className={clsx("h-2 w-2 rounded-full", driftSummary.drift_detected ? "bg-red-500" : "bg-emerald-500")} />
                      <p className="text-sm font-medium text-gray-200">
                        {driftSummary.drift_detected ? "Drift Detected" : "No Significant Drift"}
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="bg-[#171717] border-[#2f2f2f]/50">
        <CardHeader className="border-b border-[#2f2f2f]/30 pb-3">
          <h2 className="text-sm font-semibold text-gray-200">Available Methods</h2>
        </CardHeader>
        <CardContent className="pt-4">
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {METHODS.map((m) => (
              <div key={m.id} className="bg-[#212121] rounded-xl p-3 border border-[#2f2f2f]/30">
                <p className="text-sm font-medium text-gray-200">{m.label}</p>
                <p className="text-xs text-gray-500 mt-1">{m.description}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
