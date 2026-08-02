"use client"

import { useState, useMemo } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { clsx } from "clsx"
import { toast } from "sonner"
import { Card, CardHeader, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge, statusTone } from "@/components/ui/badge"
import { PageHeader, StatCard } from "@/components/ui/page-header"
import { DataTable, type Column } from "@/components/ui/data-table"
import { Progress } from "@/components/ui/progress"
import { Input } from "@/components/ui/input"
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select"
import { HelpTip, Tooltip, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip"
import { EmptyState } from "@/components/ui/empty-state"
import {
  ShieldCheck,
  Download,
  Search,
  Filter,
  Copy,
  CheckCheck,
  Eye,
  FileDown,
  Share2,
  X,
  RotateCcw,
  Ban,
  ChevronDown,
  MoreHorizontal,
  ArrowUpDown,
  Shield,
  AlertTriangle,
  Clock,
  ExternalLink,
  FileJson,
  FileText,
  QrCode,
} from "lucide-react"
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
} from "recharts"

interface MerkleNode {
  hash: string
  left?: MerkleNode
  right?: MerkleNode
}

interface Certificate {
  id: string
  modelName: string
  algorithm: string
  createdAt: string
  expiryDate: string
  status: "active" | "revoked" | "expired" | "pending"
  trustScore: number
  modelDetails: {
    name: string
    version: string
    framework: string
    parameters: string
  }
  datasetDetails: {
    name: string
    size: number
    split: string
  }
  algoConfig: Record<string, string | number | boolean>
  merkleProof: MerkleNode
}

const algorithms = ["SISA", "Influence", "Certified Removal", "Hybrid", "DeltaGrad"]
const models = [
  "gpt-2-unlearn-v3",
  "bert-base-uncased",
  "llama-3.2-3b-unlearn",
  "resnet-50-scrubbed",
  "vit-large-ipc",
  "roberta-base-unlearn",
  "t5-small-forget",
  "clip-vit-scrubbed",
]
const datasets = ["cifar-10", "imdb", "wikitext-103", "mnist", "flickr30k", "sst-2", "ag-news", "pubmed"]

function randomHex(len: number): string {
  return Array.from({ length: len }, () => Math.floor(Math.random() * 16).toString(16)).join("")
}

function randomDate(startDays: number, endDays: number): string {
  const d = new Date()
  d.setDate(d.getDate() + startDays + Math.floor(Math.random() * (endDays - startDays)))
  return d.toISOString()
}

function generateMerkleTree(depth: number = 3): MerkleNode {
  if (depth === 0) return { hash: randomHex(64) }
  return {
    hash: randomHex(64),
    left: generateMerkleTree(depth - 1),
    right: generateMerkleTree(depth - 1),
  }
}

function generateMockCertificates(count: number = 35): Certificate[] {
  return Array.from({ length: count }, (_, i) => {
    const statuses: Certificate["status"][] = ["active", "active", "active", "revoked", "expired", "pending"]
    const status = statuses[i % statuses.length]
    return {
      id: `0x${randomHex(64)}`,
      modelName: models[i % models.length],
      algorithm: algorithms[i % algorithms.length],
      createdAt: randomDate(-90, -1),
      expiryDate: status === "expired" ? randomDate(-30, -1) : randomDate(30, 365),
      status,
      trustScore: status === "active" ? 70 + Math.floor(Math.random() * 30) : status === "revoked" ? Math.floor(Math.random() * 30) : status === "expired" ? Math.floor(Math.random() * 50) : Math.floor(Math.random() * 60),
      modelDetails: {
        name: models[i % models.length],
        version: `${Math.floor(Math.random() * 5)}.${Math.floor(Math.random() * 10)}.${Math.floor(Math.random() * 20)}`,
        framework: ["PyTorch", "TensorFlow", "JAX"][i % 3],
        parameters: `${[125, 350, 700, 85, 300, 110, 60, 150][i % 8]}M`,
      },
      datasetDetails: {
        name: datasets[i % datasets.length],
        size: [50000, 25000, 100000, 70000, 31000, 95000, 120000, 20000][i % 8],
        split: ["80/10/10", "70/15/15", "90/5/5"][i % 3],
      },
      algoConfig: {
        learning_rate: [2e-5, 1e-4, 5e-5, 3e-5][i % 4],
        batch_size: [8, 16, 32, 64][i % 4],
        epochs: [3, 5, 10][i % 3],
        lora_rank: [8, 16, 32][i % 3],
        delta_threshold: 0.01,
        certification: status === "active",
      },
      merkleProof: generateMerkleTree(),
    }
  })
}

function MerkleTreeVisualizer({ node, depth = 0 }: { node: MerkleNode; depth?: number }) {
  const indent = depth * 24
  return (
    <div className="font-mono text-[11px] leading-relaxed">
      <div className="flex items-start gap-2" style={{ paddingLeft: indent }}>
        <span className="mt-0.5 text-[var(--text-tertiary)]">
          {depth > 0 ? "└─" : "●"}
        </span>
        <span className="text-[var(--text-secondary)] break-all">{node.hash.slice(0, 16)}…{node.hash.slice(-8)}</span>
      </div>
      {node.left && <MerkleTreeVisualizer node={node.left} depth={depth + 1} />}
      {node.right && <MerkleTreeVisualizer node={node.right} depth={depth + 1} />}
    </div>
  )
}

function DetailPanel({ certificate, onClose }: { certificate: Certificate; onClose: () => void }) {
  const [copied, setCopied] = useState(false)

  const copyId = async () => {
    await navigator.clipboard.writeText(certificate.id)
    setCopied(true)
    toast.success("Certificate ID copied")
    setTimeout(() => setCopied(false), 2000)
  }

  const handleDownload = (format: string) => {
    toast.success(`Certificate downloaded as ${format}`)
  }

  const handleShare = () => {
    navigator.clipboard.writeText(`${window.location.origin}/verify/${certificate.id}`)
    toast.success("Verification link copied to clipboard")
  }

  const trustTone = certificate.trustScore >= 80 ? "success" as const : certificate.trustScore >= 50 ? "warning" as const : "danger" as const

  return (
    <motion.div
      initial={{ x: "100%" }}
      animate={{ x: 0 }}
      exit={{ x: "100%" }}
      transition={{ type: "spring", damping: 28, stiffness: 300 }}
      className="fixed inset-y-0 right-0 z-50 w-full max-w-lg border-l border-[var(--border-default)] bg-[var(--bg-surface)] shadow-[var(--shadow-lg)] overflow-y-auto"
    >
      <div className="sticky top-0 z-10 flex items-center justify-between border-b border-[var(--border-subtle)] bg-[var(--bg-surface)] px-5 py-4">
        <h2 className="text-sm font-semibold text-[var(--text-primary)]">Certificate Details</h2>
        <button
          onClick={onClose}
          className="rounded-lg p-1.5 text-[var(--text-tertiary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="space-y-5 p-5">
        <div>
          <p className="mb-1.5 text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">Certificate ID</p>
          <div className="flex items-center gap-2 rounded-lg bg-[var(--bg-subtle)] p-2.5">
            <code className="flex-1 break-all font-mono text-xs text-[var(--text-secondary)]">{certificate.id}</code>
            <button
              onClick={copyId}
              className="shrink-0 rounded-md p-1.5 text-[var(--text-tertiary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--brand)]"
            >
              {copied ? <CheckCheck className="h-3.5 w-3.5 text-[var(--success)]" /> : <Copy className="h-3.5 w-3.5" />}
            </button>
          </div>
        </div>

        <div>
          <p className="mb-2 text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">Merkle Proof</p>
          <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-app)] p-3">
            <MerkleTreeVisualizer node={certificate.merkleProof} />
          </div>
        </div>

        <div>
          <p className="mb-2 text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">Verification</p>
          <div className="space-y-2 rounded-lg border border-[var(--border-subtle)] p-3">
            <div className="flex items-center justify-between text-xs">
              <span className="text-[var(--text-tertiary)]">Status</span>
              <Badge tone={statusTone(certificate.status)} dot>{certificate.status}</Badge>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-[var(--text-tertiary)]">Trust Score</span>
              <span className="flex items-center gap-2">
                <Progress value={certificate.trustScore} tone={trustTone} size="sm" className="w-24" />
                <span className="tabular-nums text-[var(--text-secondary)]">{certificate.trustScore}%</span>
              </span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-[var(--text-tertiary)]">Verified At</span>
              <span className="text-[var(--text-secondary)]">{new Date(certificate.createdAt).toLocaleString()}</span>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-lg border border-[var(--border-subtle)] p-3">
            <p className="mb-1.5 text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">Model</p>
            <p className="text-sm font-medium text-[var(--text-primary)]">{certificate.modelDetails.name}</p>
            <p className="text-xs text-[var(--text-tertiary)]">v{certificate.modelDetails.version}</p>
            <p className="mt-1 text-xs text-[var(--text-secondary)]">{certificate.modelDetails.framework} · {certificate.modelDetails.parameters}</p>
          </div>
          <div className="rounded-lg border border-[var(--border-subtle)] p-3">
            <p className="mb-1.5 text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">Dataset</p>
            <p className="text-sm font-medium text-[var(--text-primary)]">{certificate.datasetDetails.name}</p>
            <p className="text-xs text-[var(--text-tertiary)]">{certificate.datasetDetails.size.toLocaleString()} samples</p>
            <p className="mt-1 text-xs text-[var(--text-secondary)]">Split: {certificate.datasetDetails.split}</p>
          </div>
        </div>

        <div>
          <p className="mb-2 text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">Algorithm Configuration</p>
          <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-app)] p-3">
            <pre className="font-mono text-[11px] text-[var(--text-secondary)] whitespace-pre-wrap">
              {JSON.stringify(certificate.algoConfig, null, 2)}
            </pre>
          </div>
        </div>

        <div className="space-y-2">
          <p className="mb-1.5 text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">Downloads</p>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" onClick={() => handleDownload("pdf")}>
              <FileText className="h-3.5 w-3.5" /> PDF
            </Button>
            <Button variant="outline" size="sm" onClick={() => handleDownload("json")}>
              <FileJson className="h-3.5 w-3.5" /> JSON
            </Button>
            <Button variant="outline" size="sm" onClick={() => handleDownload("proof")}>
              <Shield className="h-3.5 w-3.5" /> Raw Proof
            </Button>
          </div>
        </div>

        <Button variant="secondary" className="w-full" onClick={handleShare}>
          <Share2 className="h-4 w-4" />
          Share Verification Link
        </Button>
      </div>
    </motion.div>
  )
}

export default function CertificatesPage() {
  const [certificates] = useState<Certificate[]>(generateMockCertificates)
  const [search, setSearch] = useState("")
  const [statusFilter, setStatusFilter] = useState<string>("")
  const [algoFilter, setAlgoFilter] = useState<string>("")
  const [selectedIds, setSelectedIds] = useState<Set<string | number>>(new Set())
  const [detailCert, setDetailCert] = useState<Certificate | null>(null)
  const [loading, setLoading] = useState(false)

  const filtered = useMemo(() => {
    return certificates.filter((c) => {
      if (search && !c.modelName.toLowerCase().includes(search.toLowerCase()) && !c.id.toLowerCase().includes(search.toLowerCase())) return false
      if (statusFilter && c.status !== statusFilter) return false
      if (algoFilter && c.algorithm !== algoFilter) return false
      return true
    })
  }, [certificates, search, statusFilter, algoFilter])

  const stats = useMemo(() => ({
    total: certificates.length,
    active: certificates.filter((c) => c.status === "active").length,
    revoked: certificates.filter((c) => c.status === "revoked").length,
    pending: certificates.filter((c) => c.status === "pending").length,
  }), [certificates])

  const handleExportAll = () => {
    toast.success("Exporting all certificates...")
  }

  const handleGenerate = () => {
    toast.success("New certificate generation started")
  }

  const handleVerify = () => {
    toast.success("Verification process initiated")
  }

  const handleBulkAction = (action: string) => {
    toast.success(`Bulk ${action} for ${selectedIds.size} certificates`)
    setSelectedIds(new Set())
  }

  const columns: Column<Certificate>[] = [
    {
      key: "id",
      label: "Certificate ID",
      sortable: true,
      width: "200px",
      render: (cert) => (
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs text-[var(--text-secondary)]">
            {cert.id.slice(0, 10)}…{cert.id.slice(-6)}
          </span>
          <button
            onClick={async (e) => {
              e.stopPropagation()
              await navigator.clipboard.writeText(cert.id)
              toast.success("Certificate ID copied")
            }}
            className="rounded p-0.5 text-[var(--text-tertiary)] transition-colors hover:text-[var(--brand)]"
          >
            <Copy className="h-3 w-3" />
          </button>
        </div>
      ),
    },
    {
      key: "modelName",
      label: "Model Name",
      sortable: true,
      className: "font-medium",
      render: (cert) => (
        <span className="text-sm text-[var(--text-primary)]">{cert.modelName}</span>
      ),
    },
    {
      key: "algorithm",
      label: "Algorithm",
      sortable: true,
      hideOnMobile: true,
      render: (cert) => (
        <Badge tone="accent">{cert.algorithm}</Badge>
      ),
    },
    {
      key: "createdAt",
      label: "Created",
      sortable: true,
      hideOnMobile: true,
      render: (cert) => (
        <span className="text-xs text-[var(--text-secondary)]">{new Date(cert.createdAt).toLocaleDateString()}</span>
      ),
    },
    {
      key: "expiryDate",
      label: "Expiry",
      sortable: true,
      hideOnMobile: true,
      render: (cert) => (
        <span className={clsx("text-xs", new Date(cert.expiryDate) < new Date() ? "text-[var(--danger)]" : "text-[var(--text-secondary)]")}>
          {new Date(cert.expiryDate).toLocaleDateString()}
        </span>
      ),
    },
    {
      key: "status",
      label: "Status",
      sortable: true,
      width: "110px",
      render: (cert) => (
        <Badge tone={statusTone(cert.status)} dot>{cert.status}</Badge>
      ),
    },
    {
      key: "trustScore",
      label: "Trust Score",
      sortable: true,
      width: "160px",
      render: (cert) => {
        const tone = cert.trustScore >= 80 ? "success" as const : cert.trustScore >= 50 ? "warning" as const : "danger" as const
        return (
          <div className="flex items-center gap-2">
            <Progress value={cert.trustScore} tone={tone} size="sm" className="flex-1" />
            <span className="w-8 text-right text-xs tabular-nums text-[var(--text-secondary)]">{cert.trustScore}</span>
          </div>
        )
      },
    },
    {
      key: "actions",
      label: "",
      width: "60px",
      render: (cert) => (
        <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                onClick={() => setDetailCert(cert)}
                className="rounded-lg p-1.5 text-[var(--text-tertiary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
              >
                <Eye className="h-3.5 w-3.5" />
              </button>
            </TooltipTrigger>
            <TooltipContent>View details</TooltipContent>
          </Tooltip>
          <div className="relative">
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  className="rounded-lg p-1.5 text-[var(--text-tertiary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
                >
                  <MoreHorizontal className="h-3.5 w-3.5" />
                </button>
              </TooltipTrigger>
              <TooltipContent>More actions</TooltipContent>
            </Tooltip>
          </div>
        </div>
      ),
    },
  ]

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="Verification Certificates"
        description="Cryptographically signed proofs of unlearning for model accountability"
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="primary" size="sm" onClick={handleGenerate}>
              <ShieldCheck className="h-4 w-4" />
              Generate Certificate
            </Button>
            <Button variant="outline" size="sm" onClick={handleVerify}>
              <CheckCheck className="h-4 w-4" />
              Verify Certificate
            </Button>
            <Button variant="secondary" size="sm" onClick={handleExportAll}>
              <Download className="h-4 w-4" />
              Export All
            </Button>
          </div>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Total Certificates" value={stats.total} icon={Shield} tone="brand" hint="All time" />
        <StatCard label="Active" value={stats.active} icon={CheckCheck} tone="success" hint="Valid proofs" />
        <StatCard label="Revoked" value={stats.revoked} icon={Ban} tone="danger" hint="Invalidated" />
        <StatCard label="Pending Verification" value={stats.pending} icon={Clock} tone="warning" hint="Awaiting confirmation" />
      </div>

      <Card>
        <CardContent className="pt-5">
          <div className="mb-4 flex flex-wrap items-center gap-3">
            <div className="relative flex-1 min-w-[200px] max-w-sm">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--text-tertiary)]" />
              <input
                type="text"
                placeholder="Search certificates..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] py-2 pl-9 pr-3 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
              />
            </div>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-36" aria-label="Filter by status">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="revoked">Revoked</SelectItem>
                <SelectItem value="expired">Expired</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
              </SelectContent>
            </Select>
            <Select value={algoFilter} onValueChange={setAlgoFilter}>
              <SelectTrigger className="w-40" aria-label="Filter by algorithm">
                <SelectValue placeholder="Algorithm" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Algorithms</SelectItem>
                {algorithms.map((a) => (
                  <SelectItem key={a} value={a}>{a}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {selectedIds.size > 0 && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-4 flex items-center gap-3 rounded-lg border border-[var(--brand-border)] bg-[var(--brand-soft)] px-4 py-2.5"
            >
              <span className="text-sm font-medium text-[var(--brand-strong)]">
                {selectedIds.size} selected
              </span>
              <div className="flex items-center gap-1.5 ml-auto">
                <Button variant="subtle" size="sm" onClick={() => handleBulkAction("Verify")}>
                  <CheckCheck className="h-3.5 w-3.5" /> Verify
                </Button>
                <Button variant="subtle" size="sm" onClick={() => handleBulkAction("Export")}>
                  <Download className="h-3.5 w-3.5" /> Export
                </Button>
                <Button variant="subtle" size="sm" onClick={() => handleBulkAction("Revoke")}>
                  <Ban className="h-3.5 w-3.5" /> Revoke
                </Button>
                <button
                  onClick={() => setSelectedIds(new Set())}
                  className="rounded-lg p-1.5 text-[var(--text-tertiary)] transition-colors hover:bg-[var(--bg-hover)]"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </motion.div>
          )}

          <DataTable<Certificate>
            columns={columns}
            data={filtered}
            loading={loading}
            pageSize={10}
            selectedIds={selectedIds}
            onSelectionChange={setSelectedIds}
            onRowClick={(cert) => setDetailCert(cert)}
            emptyState={
              <EmptyState
                icon={Shield}
                title="No certificates found"
                description={search || statusFilter || algoFilter ? "Try adjusting your filters." : "Generate your first verification certificate to get started."}
              />
            }
          />
        </CardContent>
      </Card>

      <AnimatePresence>
        {detailCert && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm"
              onClick={() => setDetailCert(null)}
            />
            <DetailPanel certificate={detailCert} onClose={() => setDetailCert(null)} />
          </>
        )}
      </AnimatePresence>
    </div>
  )
}
