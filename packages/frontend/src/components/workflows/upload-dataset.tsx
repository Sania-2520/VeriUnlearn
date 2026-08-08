"use client"

import { useState, useCallback, useEffect, useRef } from "react"
import { useRouter } from "next/navigation"
import { clsx } from "clsx"
import { useDropzone } from "react-dropzone"
import {
  Upload,
  Check,
  X,
  AlertTriangle,
  Shield,
  Eye,
  EyeOff,
  FileSpreadsheet,
  Database,
  Trash2,
  Plus,
} from "lucide-react"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input, Textarea } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select"
import {
  WorkflowProvider,
  useWorkflow,
  type Step,
} from "./workflow-context"
import { WorkflowStepper } from "./workflow-stepper"
import { WorkflowStep } from "./workflow-step"
import { WorkflowActions } from "./workflow-actions"

/* ── Types ──────────────────────────────────────────────────────── */

type ColumnType = "text" | "numeric" | "categorical" | "label"

interface ColumnInfo {
  name: string
  type: ColumnType
  detected: ColumnType
  sampleValues: string[]
}

interface PIIDetection {
  column: string
  type: string
  confidence: number
  severity: "high" | "medium" | "low"
}

/* ── Steps ──────────────────────────────────────────────────────── */

const steps: Step[] = [
  { id: "basic-info", title: "Basic Info", description: "Name, description, and metadata" },
  { id: "upload", title: "Upload", description: "Upload your dataset file" },
  { id: "schema", title: "Schema", description: "Map columns to types" },
  { id: "privacy", title: "Privacy", description: "Review PII and consent" },
  { id: "confirm", title: "Confirm", description: "Review and start upload" },
]

const ACCEPTED_TYPES = {
  "text/csv": [".csv"],
  "application/json": [".json"],
  "application/x-parquet": [".parquet"],
  "application/octet-stream": [".parquet"],
}

const MAX_FILE_SIZE = 500 * 1024 * 1024 // 500 MB

/* ── Mock preview data ──────────────────────────────────────────── */

const mockPreview: Record<string, string>[] = [
  { "id": "1", "name": "Alice", "age": "32", "email": "alice@example.com", "label": "0" },
  { "id": "2", "name": "Bob", "age": "45", "email": "bob@test.org", "label": "1" },
  { "id": "3", "name": "Charlie", "age": "28", "email": "charlie@mail.com", "label": "0" },
  { "id": "4", "name": "Diana", "age": "52", "email": "diana@email.com", "label": "1" },
  { "id": "5", "name": "Eve", "age": "37", "email": "eve@domain.com", "label": "0" },
]

const mockColumns: ColumnInfo[] = [
  { name: "id", type: "text", detected: "text", sampleValues: ["1", "2", "3"] },
  { name: "name", type: "text", detected: "text", sampleValues: ["Alice", "Bob", "Charlie"] },
  { name: "age", type: "numeric", detected: "numeric", sampleValues: ["32", "45", "28"] },
  { name: "email", type: "text", detected: "text", sampleValues: ["alice@...", "bob@..."] },
  { name: "label", type: "label", detected: "label", sampleValues: ["0", "1", "0"] },
]

const mockPII: PIIDetection[] = [
  { column: "email", type: "Email Address", confidence: 98, severity: "high" },
  { column: "name", type: "Person Name", confidence: 92, severity: "high" },
]

/* ── License options ────────────────────────────────────────────── */

const licenses = [
  { value: "mit", label: "MIT" },
  { value: "apache-2.0", label: "Apache 2.0" },
  { value: "cc-by-4.0", label: "CC BY 4.0" },
  { value: "odbl", label: "ODbL" },
  { value: "custom", label: "Custom License" },
]

/* ── Step Components ────────────────────────────────────────────── */

function BasicInfoStep() {
  const { formData, updateFormData, setStepValidation } = useWorkflow()
  const [name, setName] = useState((formData.datasetName as string) ?? "")
  const [description, setDescription] = useState((formData.datasetDescription as string) ?? "")
  const [tagsInput, setTagsInput] = useState("")
  const [tags, setTags] = useState<string[]>((formData.datasetTags as string[]) ?? [])
  const [license, setLicense] = useState((formData.datasetLicense as string) ?? "")

  useEffect(() => {
    const valid = name.trim().length > 0 && license !== ""
    setStepValidation(0, {
      isValid: valid,
      message: valid ? undefined : "Dataset name and license are required",
    })
  }, [name, license, setStepValidation])

  const addTag = () => {
    const t = tagsInput.trim().toLowerCase()
    if (t && !tags.includes(t)) {
      const next = [...tags, t]
      setTags(next)
      updateFormData({ datasetTags: next })
    }
    setTagsInput("")
  }

  const removeTag = (tag: string) => {
    const next = tags.filter((t) => t !== tag)
    setTags(next)
    updateFormData({ datasetTags: next })
  }

  return (
    <WorkflowStep title="Basic Information" description="Provide the name and metadata for your dataset.">
      <div className="max-w-lg space-y-5">
        <Input
          label="Dataset Name *"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g., Customer Feedback Q3"
          leftIcon={<Database className="h-4 w-4" />}
        />

        <Textarea
          label="Description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="A brief description of the dataset..."
          rows={3}
        />

        <div>
          <label className="block text-sm font-medium text-[var(--text-secondary)]">Tags</label>
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            {tags.map((tag) => (
              <Badge key={tag} tone="brand">
                {tag}
                <button type="button" onClick={() => removeTag(tag)} className="ml-1 hover:text-[var(--danger)]">
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            ))}
          </div>
          <div className="mt-2 flex gap-2">
            <Input
              value={tagsInput}
              onChange={(e) => setTagsInput(e.target.value)}
              placeholder="Add a tag..."
              onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addTag() } }}
            />
            <Button type="button" variant="secondary" size="sm" onClick={addTag} disabled={!tagsInput.trim()}>
              <Plus className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-[var(--text-secondary)]">License *</label>
          <Select value={license} onValueChange={setLicense}>
            <SelectTrigger className="mt-1.5 w-full">
              <SelectValue placeholder="Select a license" />
            </SelectTrigger>
            <SelectContent>
              {licenses.map((l) => (
                <SelectItem key={l.value} value={l.value}>{l.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>
    </WorkflowStep>
  )
}

function UploadDataStep() {
  const { formData, setStepValidation } = useWorkflow()
  const [file, setFile] = useState<File | null>((formData.datasetFile as File) ?? null)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploading, setUploading] = useState(false)
  const simulating = useRef(false)

  const onDrop = useCallback((accepted: File[]) => {
    const f = accepted[0]
    if (!f) return
    setFile(f)
    setUploadProgress(0)
    setUploading(true)
    simulating.current = true
    let p = 0
    const interval = setInterval(() => {
      p += Math.random() * 15
      if (p >= 100) {
        p = 100
        clearInterval(interval)
        setUploading(false)
        simulating.current = false
      }
      setUploadProgress(Math.min(100, p))
    }, 200)
  }, [])

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop,
    accept: ACCEPTED_TYPES,
    maxSize: MAX_FILE_SIZE,
    multiple: false,
  })

  useEffect(() => {
    setStepValidation(1, {
      isValid: !!file && !uploading,
      message: !file ? "Upload a dataset file" : uploading ? "Upload in progress..." : undefined,
    })
  }, [file, uploading, setStepValidation])

  const formatSize = (bytes: number) => {
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  return (
    <WorkflowStep title="Upload Data" description="Drag and drop your dataset file or click to browse.">
      <div className="space-y-5">
        <div
          {...getRootProps()}
          className={clsx(
            "flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-10 transition-all",
            isDragActive && !isDragReject
              ? "border-[var(--brand)] bg-[var(--brand-soft)]"
              : isDragReject
                ? "border-[var(--danger)] bg-[var(--danger-soft)]"
                : "border-[var(--border-default)] bg-[var(--bg-surface)] hover:border-[var(--brand)] hover:bg-[var(--bg-hover)]",
          )}
        >
          <input {...getInputProps()} />
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-[var(--bg-subtle)] text-[var(--text-tertiary)]">
            <Upload className="h-6 w-6" />
          </div>
          <p className="mt-3 text-sm font-medium text-[var(--text-primary)]">
            {isDragActive
              ? isDragReject
                ? "File type not supported"
                : "Drop your file here"
              : "Drag & drop or click to browse"}
          </p>
          <p className="mt-1 text-xs text-[var(--text-tertiary)]">
            CSV, JSON, or Parquet &middot; up to {formatSize(MAX_FILE_SIZE)}
          </p>
        </div>

        {file && (
          <div className="animate-fade-up rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
            <div className="flex items-center gap-3">
              <FileSpreadsheet className="h-8 w-8 text-[var(--brand)] shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-[var(--text-primary)] truncate">{file.name}</p>
                <p className="text-xs text-[var(--text-tertiary)]">{formatSize(file.size)}</p>
              </div>
              {!uploading && (
                <button type="button" onClick={() => setFile(null)} className="text-[var(--text-tertiary)] hover:text-[var(--danger)]">
                  <Trash2 className="h-4 w-4" />
                </button>
              )}
            </div>
            {uploading && (
              <div className="mt-3">
                <Progress value={uploadProgress} showLabel />
              </div>
            )}
            {!uploading && uploadProgress === 100 && (
              <div className="mt-2 flex items-center gap-1.5 text-xs text-[var(--success)]">
                <Check className="h-3.5 w-3.5" />
                Upload complete
              </div>
            )}
          </div>
        )}
      </div>
    </WorkflowStep>
  )
}

function SchemaMappingStep() {
  const { formData, setStepValidation } = useWorkflow()
  const [columns, setColumns] = useState<ColumnInfo[]>(
    (formData.schemaColumns as ColumnInfo[]) ?? mockColumns,
  )

  useEffect(() => {
    const hasLabel = columns.some((c) => c.type === "label")
    setStepValidation(2, {
      isValid: hasLabel,
      message: hasLabel ? undefined : "At least one column must be marked as 'label'",
    })
  }, [columns, setStepValidation])

  const setColumnType = (index: number, type: ColumnType) => {
    setColumns((prev) => prev.map((c, i) => (i === index ? { ...c, type } : c)))
  }

  return (
    <WorkflowStep title="Schema Mapping" description="Verify and adjust column types for your dataset.">
      <div className="space-y-4">
        <div className="overflow-x-auto rounded-lg border border-[var(--border-default)]">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-[var(--border-subtle)] bg-[var(--bg-subtle)]">
                <th className="px-3 py-2 text-xs font-medium text-[var(--text-tertiary)]">Column</th>
                <th className="px-3 py-2 text-xs font-medium text-[var(--text-tertiary)]">Type</th>
                <th className="px-3 py-2 text-xs font-medium text-[var(--text-tertiary)]">Sample Values</th>
              </tr>
            </thead>
            <tbody>
              {columns.map((col, i) => (
                <tr key={col.name} className="border-b border-[var(--border-subtle)] last:border-0">
                  <td className="px-3 py-2.5">
                    <span className="font-medium text-[var(--text-primary)]">{col.name}</span>
                  </td>
                  <td className="px-3 py-2.5">
                    <select
                      value={col.type}
                      onChange={(e) => setColumnType(i, e.target.value as ColumnType)}
                      className="rounded-md border border-[var(--border-default)] bg-[var(--bg-surface)] px-2 py-1 text-xs text-[var(--text-primary)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
                    >
                      <option value="text">Text</option>
                      <option value="numeric">Numeric</option>
                      <option value="categorical">Categorical</option>
                      <option value="label">Label</option>
                    </select>
                  </td>
                  <td className="px-3 py-2.5">
                    <div className="flex gap-1.5">
                      {col.sampleValues.map((v, j) => (
                        <code key={j} className="rounded bg-[var(--bg-subtle)] px-1.5 py-0.5 text-xs text-[var(--text-secondary)]">
                          {v}
                        </code>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="rounded-lg border border-[var(--border-subtle)]">
          <div className="border-b border-[var(--border-subtle)] bg-[var(--bg-subtle)] px-4 py-2">
            <span className="text-xs font-medium text-[var(--text-tertiary)]">Preview (first 5 rows)</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-[var(--border-subtle)]">
                  {columns.map((col) => (
                    <th key={col.name} className="px-3 py-2 font-medium text-[var(--text-secondary)]">
                      {col.name}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {mockPreview.map((row, i) => (
                  <tr key={i} className="border-b border-[var(--border-subtle)] last:border-0">
                    {columns.map((col) => (
                      <td key={col.name} className="px-3 py-2 text-[var(--text-primary)]">
                        {row[col.name] ?? "—"}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </WorkflowStep>
  )
}

function PrivacyReviewStep() {
  const { formData, setStepValidation } = useWorkflow()
  const [anonymize, setAnonymize] = useState<Record<string, boolean>>(
    (formData.privacyAnonymize as Record<string, boolean>) ?? { email: true, name: true },
  )
  const [consent, setConsent] = useState((formData.privacyConsent as boolean) ?? false)

  useEffect(() => {
    setStepValidation(3, {
      isValid: consent,
      message: consent ? undefined : "You must agree to the data usage terms",
    })
  }, [consent, setStepValidation])

  const toggleAnonymize = (col: string) => {
    setAnonymize((prev) => ({ ...prev, [col]: !prev[col] }))
  }

  return (
    <WorkflowStep title="Privacy Review" description="Review detected PII and configure anonymization.">
      <div className="space-y-5">
        {mockPII.length > 0 && (
          <div className="rounded-lg border border-[var(--warning-border)] bg-[var(--warning-soft)] p-4">
            <div className="flex items-start gap-2">
              <AlertTriangle className="mt-0.5 h-4 w-4 text-[var(--warning)] shrink-0" />
              <div>
                <p className="text-sm font-medium text-[var(--text-primary)]">
                  {mockPII.length} potential PII {mockPII.length === 1 ? "field" : "fields"} detected
                </p>
                <p className="mt-0.5 text-xs text-[var(--text-secondary)]">
                  Review and anonymize sensitive columns before uploading.
                </p>
              </div>
            </div>
          </div>
        )}

        <div className="space-y-2">
          {mockPII.map((pii) => (
            <div
              key={pii.column}
              className="flex items-center justify-between rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] p-3"
            >
              <div className="flex items-center gap-3">
                <Shield className="h-4 w-4 text-[var(--danger)]" />
                <div>
                  <p className="text-sm font-medium text-[var(--text-primary)]">{pii.column}</p>
                  <p className="text-xs text-[var(--text-tertiary)]">
                    {pii.type} &middot; {pii.confidence}% confidence
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => toggleAnonymize(pii.column)}
                className={clsx(
                  "flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-all",
                  anonymize[pii.column]
                    ? "bg-[var(--brand-soft)] text-[var(--brand-strong)]"
                    : "bg-[var(--bg-subtle)] text-[var(--text-tertiary)]",
                )}
              >
                {anonymize[pii.column] ? (
                  <>
                    <EyeOff className="h-3.5 w-3.5" /> Anonymized
                  </>
                ) : (
                  <>
                    <Eye className="h-3.5 w-3.5" /> Visible
                  </>
                )}
              </button>
            </div>
          ))}
        </div>

        <label className="flex items-start gap-3 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] p-3 cursor-pointer hover:bg-[var(--bg-hover)]">
          <input
            type="checkbox"
            checked={consent}
            onChange={(e) => setConsent(e.target.checked)}
            className="mt-0.5 h-4 w-4 rounded border-[var(--border-default)] text-[var(--brand)] accent-[var(--brand)]"
          />
          <div>
            <p className="text-sm font-medium text-[var(--text-primary)]">
              I confirm that I have the right to upload and use this data
            </p>
            <p className="mt-0.5 text-xs text-[var(--text-tertiary)]">
              This data will be processed in accordance with the VeriUnlearn privacy policy and data processing agreement.
            </p>
          </div>
        </label>
      </div>
    </WorkflowStep>
  )
}

function ConfirmStep() {
  const { formData } = useWorkflow()
  const file = formData.datasetFile as File | null
  const columns = (formData.schemaColumns as ColumnInfo[]) ?? mockColumns
  const anonymize = (formData.privacyAnonymize as Record<string, boolean>) ?? {}

  return (
    <WorkflowStep title="Confirm & Upload" description="Review your dataset details before uploading.">
      <div className="space-y-4">
        <Card>
          <CardHeader title="Dataset Details" />
          <CardContent className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-[var(--text-secondary)]">Name</span>
              <span className="font-medium text-[var(--text-primary)]">{formData.datasetName as string}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-[var(--text-secondary)]">License</span>
              <span className="font-medium text-[var(--text-primary)]">
                {licenses.find((l) => l.value === formData.datasetLicense)?.label ?? formData.datasetLicense as string}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-[var(--text-secondary)]">File</span>
              <span className="font-medium text-[var(--text-primary)]">{file?.name ?? "—"}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-[var(--text-secondary)]">Size</span>
              <span className="font-medium text-[var(--text-primary)]">
                {file ? `${(file.size / (1024 * 1024)).toFixed(1)} MB` : "—"}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-[var(--text-secondary)]">Columns</span>
              <span className="font-medium text-[var(--text-primary)]">{columns.length}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-[var(--text-secondary)]">Tags</span>
              <span className="font-medium text-[var(--text-primary)]">
                {(formData.datasetTags as string[])?.join(", ") ?? "—"}
              </span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader title="Column Types" />
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {columns.map((col) => (
                <Badge key={col.name} tone={col.type === "label" ? "brand" : "neutral"}>
                  {col.name}: {col.type}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader title="Privacy Actions" />
          <CardContent>
            <div className="flex items-center justify-between text-sm">
              <span className="text-[var(--text-secondary)]">Anonymized columns</span>
              <span className="font-medium text-[var(--text-primary)]">
                {Object.values(anonymize).filter(Boolean).length} of {Object.keys(anonymize).length}
              </span>
            </div>
            <Progress
              value={(Object.values(anonymize).filter(Boolean).length / Math.max(Object.keys(anonymize).length, 1)) * 100}
              className="mt-2"
              tone="success"
            />
          </CardContent>
        </Card>
      </div>
    </WorkflowStep>
  )
}

/* ── Main Wizard ────────────────────────────────────────────────── */

export function UploadDataset() {
  const router = useRouter()

  return (
    <WorkflowProvider steps={steps}>
      <UploadDatasetInner onCancel={() => router.push("/dashboard/datasets")} />
    </WorkflowProvider>
  )
}

function UploadDatasetInner({ onCancel }: { onCancel: () => void }) {
  const { formData, setIsSubmitting } = useWorkflow()
  const router = useRouter()
  const [error, setError] = useState<string | null>(null)

  const handleComplete = async () => {
    setIsSubmitting(true)
    setError(null)
    try {
      console.log("Uploading dataset:", formData)
      await new Promise((resolve) => setTimeout(resolve, 3000))
      router.push("/dashboard/datasets")
    } catch {
      setError("Upload failed. Please try again.")
      setIsSubmitting(false)
    }
  }

  return (
    <div className="mx-auto max-w-3xl">
      <WorkflowStepper className="mb-8" />

      <div className="min-h-[400px]">
        <BasicInfoStep />
        <UploadDataStep />
        <SchemaMappingStep />
        <PrivacyReviewStep />
        <ConfirmStep />
      </div>

      {error && (
        <div className="mt-4 rounded-lg border border-[var(--danger-border)] bg-[var(--danger-soft)] p-3 text-sm text-[var(--danger)]">
          {error}
        </div>
      )}

      <WorkflowActions
        onCancel={onCancel}
        onComplete={handleComplete}
        completeLabel="Upload Dataset"
        className="mt-8 border-t border-[var(--border-subtle)] pt-6"
      />
    </div>
  )
}
