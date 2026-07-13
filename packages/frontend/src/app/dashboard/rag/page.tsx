"use client"

import { useEffect, useState, useCallback } from "react"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import * as ragApi from "@/lib/api/client"
import {
  Upload,
  Search,
  Trash2,
  FileText,
  Database,
  RefreshCw,
  AlertCircle,
  CheckCircle,
  File,
  X,
} from "lucide-react"

interface RagDocument {
  id: string
  filename: string
  chunk_count: number
  status: "indexed" | "processing" | "failed"
  created_at: string
  metadata?: Record<string, unknown>
}

interface SearchResult {
  document_id: string
  filename: string
  chunk_index: number
  content: string
  score: number
}

export default function RagPage() {
  const [documents, setDocuments] = useState<RagDocument[]>([])
  const [isLoadingDocs, setIsLoadingDocs] = useState(true)
  const [uploadingFiles, setUploadingFiles] = useState<File[]>([])
  const [isUploading, setIsUploading] = useState(false)
  const [searchQuery, setSearchQuery] = useState("")
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isDragOver, setIsDragOver] = useState(false)

  const fetchDocuments = useCallback(async () => {
    setIsLoadingDocs(true)
    setError(null)
    try {
      const res = await ragApi.listDocuments()
      setDocuments(res.data || res.documents || [])
    } catch {
      setError("Failed to load documents")
    } finally {
      setIsLoadingDocs(false)
    }
  }, [])

  useEffect(() => {
    fetchDocuments()
  }, [fetchDocuments])

  const handleFiles = (files: FileList | File[]) => {
    const fileArray = Array.from(files)
    setUploadingFiles((prev) => [...prev, ...fileArray])
  }

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
    if (e.dataTransfer.files.length > 0) {
      handleFiles(e.dataTransfer.files)
    }
  }, [])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(true)
  }, [])

  const handleDragLeave = useCallback(() => {
    setIsDragOver(false)
  }, [])

  const removeFile = (index: number) => {
    setUploadingFiles((prev) => prev.filter((_, i) => i !== index))
  }

  const handleUpload = async () => {
    if (uploadingFiles.length === 0) return
    setIsUploading(true)
    setError(null)
    try {
      for (const file of uploadingFiles) {
        await ragApi.uploadDocument(file)
      }
      setUploadingFiles([])
      await fetchDocuments()
    } catch {
      setError("Failed to upload one or more documents")
    } finally {
      setIsUploading(false)
    }
  }

  const handleSearch = async () => {
    if (!searchQuery.trim()) return
    setIsSearching(true)
    setError(null)
    try {
      const res = await ragApi.searchDocuments(searchQuery.trim())
      setSearchResults(res.results || [])
    } catch {
      setError("Search failed")
    } finally {
      setIsSearching(false)
    }
  }

  const handleDelete = async (docId: string) => {
    try {
      await ragApi.deleteDocument(docId)
      setDocuments((prev) => prev.filter((d) => d.id !== docId))
    } catch {
      setError("Failed to delete document")
    }
  }

  const totalChunks = documents.reduce((acc, d) => acc + (d.chunk_count || 0), 0)
  const indexedCount = documents.filter((d) => d.status === "indexed").length

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">RAG Documents</h1>
          <p className="text-sm text-gray-400 mt-1">Manage documents indexed for retrieval-augmented generation</p>
        </div>
        <button
          onClick={fetchDocuments}
          className="flex items-center gap-2 px-3 py-2 text-sm text-gray-300 hover:text-white bg-[#2f2f2f] hover:bg-[#3a3a3a] border border-[#2f2f2f] hover:border-gray-500 rounded-lg transition-colors cursor-pointer"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </button>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-3 bg-red-950/30 border border-red-900/40 rounded-lg text-sm text-red-400">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {error}
          <button onClick={() => setError(null)} className="ml-auto text-red-400 hover:text-red-300 cursor-pointer">
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      <div className="grid grid-cols-3 gap-4">
        <div className="bg-[#171717] border border-[#2f2f2f]/60 rounded-xl p-4">
          <div className="flex items-center gap-2 text-xs text-gray-500 uppercase tracking-wider font-semibold mb-2">
            <FileText className="h-3.5 w-3.5" />
            Documents
          </div>
          <p className="text-2xl font-bold text-white">{documents.length}</p>
        </div>
        <div className="bg-[#171717] border border-[#2f2f2f]/60 rounded-xl p-4">
          <div className="flex items-center gap-2 text-xs text-gray-500 uppercase tracking-wider font-semibold mb-2">
            <Database className="h-3.5 w-3.5" />
            Total Chunks
          </div>
          <p className="text-2xl font-bold text-white">{totalChunks}</p>
        </div>
        <div className="bg-[#171717] border border-[#2f2f2f]/60 rounded-xl p-4">
          <div className="flex items-center gap-2 text-xs text-gray-500 uppercase tracking-wider font-semibold mb-2">
            <CheckCircle className="h-3.5 w-3.5" />
            Indexed
          </div>
          <p className="text-2xl font-bold text-emerald-500">{indexedCount}</p>
        </div>
      </div>

      <div className="bg-[#171717] border border-[#2f2f2f]/60 rounded-xl p-5">
        <h2 className="text-sm font-semibold text-gray-200 mb-4">Upload Documents</h2>
        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
            isDragOver
              ? "border-emerald-500 bg-emerald-950/10"
              : "border-[#2f2f2f] hover:border-gray-500"
          }`}
        >
          <Upload className="h-8 w-8 text-gray-500 mx-auto mb-3" />
          <p className="text-sm text-gray-300">Drag and drop files here, or click to browse</p>
          <p className="text-xs text-gray-500 mt-1">Supports PDF, TXT, MD, DOCX up to 10MB</p>
          <input
            type="file"
            multiple
            onChange={(e) => {
              if (e.target.files) handleFiles(e.target.files)
            }}
            className="hidden"
            id="file-upload"
          />
          <label
            htmlFor="file-upload"
            className="inline-flex items-center gap-2 mt-4 px-4 py-2 text-sm text-gray-300 bg-[#2f2f2f] hover:bg-[#3a3a3a] border border-[#2f2f2f] hover:border-gray-500 rounded-lg transition-colors cursor-pointer"
          >
            <File className="h-4 w-4" />
            Browse Files
          </label>
        </div>

        {uploadingFiles.length > 0 && (
          <div className="mt-4 space-y-2">
            {uploadingFiles.map((file, idx) => (
              <div key={idx} className="flex items-center justify-between p-2.5 bg-[#212121] border border-[#2f2f2f] rounded-lg">
                <div className="flex items-center gap-2 text-sm text-gray-300">
                  <File className="h-4 w-4 text-gray-400" />
                  <span>{file.name}</span>
                  <span className="text-xs text-gray-500">({(file.size / 1024).toFixed(1)} KB)</span>
                </div>
                <button
                  onClick={() => removeFile(idx)}
                  className="p-1 text-gray-400 hover:text-red-400 transition-colors cursor-pointer"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            ))}
            <Button onClick={handleUpload} loading={isUploading} variant="primary" size="sm">
              Upload {uploadingFiles.length} file{uploadingFiles.length > 1 ? "s" : ""}
            </Button>
          </div>
        )}
      </div>

      <div className="bg-[#171717] border border-[#2f2f2f]/60 rounded-xl p-5">
        <h2 className="text-sm font-semibold text-gray-200 mb-4">Search Documents</h2>
        <div className="flex gap-2">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleSearch()
              }}
              placeholder="Search indexed document content..."
              className="w-full pl-10 pr-4 py-2.5 bg-[#212121] border border-[#2f2f2f] focus:border-gray-500 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none transition-colors"
            />
          </div>
          <Button onClick={handleSearch} loading={isSearching} variant="secondary" size="md">
            Search
          </Button>
        </div>

        {searchResults.length > 0 && (
          <div className="mt-4 space-y-3">
            <p className="text-xs text-gray-500 font-medium">{searchResults.length} results found</p>
            {searchResults.map((result, idx) => (
              <div key={idx} className="p-4 bg-[#212121] border border-[#2f2f2f] rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2 text-xs text-gray-400">
                    <FileText className="h-3.5 w-3.5" />
                    <span className="font-medium text-gray-300">{result.filename}</span>
                    <span>chunk {result.chunk_index}</span>
                  </div>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-950/40 text-emerald-400 border border-emerald-900/40">
                    {(result.score * 100).toFixed(1)}%
                  </span>
                </div>
                <p className="text-sm text-gray-300 leading-relaxed whitespace-pre-wrap">{result.content}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="bg-[#171717] border border-[#2f2f2f]/60 rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-gray-200">Indexed Documents</h2>
          <span className="text-xs text-gray-500">{documents.length} documents</span>
        </div>

        {isLoadingDocs ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin h-6 w-6 border-2 border-emerald-500 border-t-transparent rounded-full" />
          </div>
        ) : documents.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <FileText className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">No documents indexed yet</p>
          </div>
        ) : (
          <div className="space-y-2">
            {documents.map((doc) => (
              <div key={doc.id} className="flex items-center justify-between p-3 bg-[#212121] border border-[#2f2f2f] rounded-lg hover:border-gray-500/50 transition-colors">
                <div className="flex items-center gap-3 min-w-0">
                  <FileText className="h-4 w-4 text-gray-400 shrink-0" />
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-200 truncate">{doc.filename}</p>
                    <p className="text-xs text-gray-500">
                      {doc.chunk_count} chunks
                      <span className="mx-1.5">·</span>
                      {new Date(doc.created_at).toLocaleDateString()}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full border ${
                      doc.status === "indexed"
                        ? "bg-emerald-950/30 text-emerald-400 border-emerald-900/40"
                        : doc.status === "processing"
                          ? "bg-yellow-950/30 text-yellow-400 border-yellow-900/40"
                          : "bg-red-950/30 text-red-400 border-red-900/40"
                    }`}
                  >
                    {doc.status}
                  </span>
                  <button
                    onClick={() => handleDelete(doc.id)}
                    className="p-1.5 text-gray-500 hover:text-red-400 hover:bg-red-950/20 rounded-lg transition-colors cursor-pointer"
                    title="Delete document"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
