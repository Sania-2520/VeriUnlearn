"use client"

import { useState, useMemo } from "react"
import { clsx } from "clsx"
import { ChevronUp, ChevronDown, ChevronsUpDown } from "lucide-react"

export type SortDirection = "asc" | "desc" | null

export interface Column<T> {
  key: string
  label: string
  sortable?: boolean
  render?: (item: T) => React.ReactNode
  className?: string
  hideOnMobile?: boolean
  width?: string
}

interface DataTableProps<T extends { id: string | number }> {
  columns: Column<T>[]
  data: T[]
  loading?: boolean
  emptyState?: React.ReactNode
  onRowClick?: (item: T) => void
  selectedIds?: Set<string | number>
  onSelectionChange?: (ids: Set<string | number>) => void
  pageSize?: number
  className?: string
  stickyHeader?: boolean
}

export function DataTable<T extends { id: string | number }>({
  columns,
  data,
  loading,
  emptyState,
  onRowClick,
  selectedIds,
  onSelectionChange,
  pageSize = 10,
  className,
  stickyHeader = true,
}: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null)
  const [sortDir, setSortDir] = useState<SortDirection>(null)
  const [page, setPage] = useState(1)

  const handleSort = (key: string) => {
    if (sortKey === key) {
      if (sortDir === "asc") { setSortDir("desc"); return }
      if (sortDir === "desc") { setSortDir(null); setSortKey(null); return }
    }
    setSortKey(key)
    setSortDir("asc")
  }

  const sorted = useMemo(() => {
    if (!sortKey || !sortDir) return data
    return [...data].sort((a, b) => {
      const aVal = (a as Record<string, unknown>)[sortKey]
      const bVal = (b as Record<string, unknown>)[sortKey]
      if (aVal == null) return 1
      if (bVal == null) return -1
      const cmp = typeof aVal === "string" ? (aVal as string).localeCompare(bVal as string) : (aVal as number) - (bVal as number)
      return sortDir === "asc" ? cmp : -cmp
    })
  }, [data, sortKey, sortDir])

  const totalPages = Math.max(1, Math.ceil(sorted.length / pageSize))
  const paginated = sorted.slice((page - 1) * pageSize, page * pageSize)

  const allSelected = selectedIds && paginated.length > 0 && paginated.every((item) => selectedIds.has(item.id))
  const someSelected = selectedIds && paginated.some((item) => selectedIds.has(item.id))

  const toggleAll = () => {
    if (!onSelectionChange) return
    if (allSelected) {
      const next = new Set(selectedIds)
      paginated.forEach((item) => next.delete(item.id))
      onSelectionChange(next)
    } else {
      const next = new Set(selectedIds ?? [])
      paginated.forEach((item) => next.add(item.id))
      onSelectionChange(next)
    }
  }

  const toggleItem = (id: string | number) => {
    if (!onSelectionChange) return
    const next = new Set(selectedIds ?? [])
    if (next.has(id)) next.delete(id)
    else next.add(id)
    onSelectionChange(next)
  }

  const SkeletonRow = () => (
    <tr className="border-b border-[var(--border-subtle)]">
      {onSelectionChange && <td className="px-4 py-3"><div className="h-4 w-4 skeleton-shimmer rounded bg-[var(--bg-subtle)]" /></td>}
      {columns.map((col) => (
        <td key={col.key} className={clsx("px-4 py-3", col.hideOnMobile && "hidden md:table-cell")}>
          <div className="h-3.5 w-3/4 skeleton-shimmer rounded bg-[var(--bg-subtle)]" />
        </td>
      ))}
    </tr>
  )

  return (
    <div className={clsx("surface rounded-xl overflow-hidden", className)}>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-sm">
          <thead className={clsx(stickyHeader && "sticky top-0 z-10", "bg-[var(--bg-subtle)]")}>
            <tr>
              {onSelectionChange && (
                <th className="w-10 px-4 py-3 text-left">
                  <input
                    type="checkbox"
                    checked={allSelected}
                    ref={(el) => { if (el) el.indeterminate = Boolean(someSelected && !allSelected) }}
                    onChange={toggleAll}
                    className="h-4 w-4 rounded border-[var(--border-strong)] text-[var(--brand)] focus:ring-[var(--brand)]"
                  />
                </th>
              )}
              {columns.map((col) => (
                <th
                  key={col.key}
                  className={clsx(
                    "px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--text-tertiary)]",
                    col.sortable && "cursor-pointer select-none hover:text-[var(--text-secondary)]",
                    col.hideOnMobile && "hidden md:table-cell",
                  )}
                  style={col.width ? { width: col.width } : undefined}
                  onClick={() => col.sortable && handleSort(col.key)}
                >
                  <div className="flex items-center gap-1">
                    {col.label}
                    {col.sortable && (
                      <span className="inline-flex flex-col">
                        {sortKey === col.key ? (
                          sortDir === "asc" ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />
                        ) : (
                          <ChevronsUpDown className="h-3 w-3 opacity-40" />
                        )}
                      </span>
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              Array.from({ length: 5 }).map((_, i) => <SkeletonRow key={i} />)
            ) : paginated.length === 0 ? (
              <tr>
                <td colSpan={columns.length + (onSelectionChange ? 1 : 0)} className="px-4 py-12">
                  {emptyState ?? (
                    <div className="text-center text-sm text-[var(--text-tertiary)]">No data</div>
                  )}
                </td>
              </tr>
            ) : (
              paginated.map((item) => (
                <tr
                  key={item.id}
                  className={clsx(
                    "border-b border-[var(--border-subtle)] transition-colors last:border-0",
                    onRowClick && "cursor-pointer hover:bg-[var(--bg-hover)]",
                    selectedIds?.has(item.id) && "bg-[var(--brand-soft)]",
                  )}
                  onClick={() => onRowClick?.(item)}
                >
                  {onSelectionChange && (
                    <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={selectedIds?.has(item.id) ?? false}
                        onChange={() => toggleItem(item.id)}
                        className="h-4 w-4 rounded border-[var(--border-strong)] text-[var(--brand)] focus:ring-[var(--brand)]"
                      />
                    </td>
                  )}
                  {columns.map((col) => (
                    <td
                      key={col.key}
                      className={clsx("px-4 py-3 align-middle", col.hideOnMobile && "hidden md:table-cell")}
                    >
                      {col.render ? col.render(item) : (String((item as Record<string, unknown>)[col.key] ?? "—"))}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {!loading && totalPages > 1 && (
        <div className="flex items-center justify-between border-t border-[var(--border-subtle)] px-4 py-3">
          <span className="text-xs text-[var(--text-tertiary)]">
            {sorted.length} total
          </span>
          <div className="flex items-center gap-1.5">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="rounded-lg px-3 py-1.5 text-xs font-medium text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)] disabled:opacity-40"
            >
              Previous
            </button>
            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
              const start = Math.max(1, page - 2)
              const pageNum = start + i
              if (pageNum > totalPages) return null
              return (
                <button
                  key={pageNum}
                  onClick={() => setPage(pageNum)}
                  className={clsx(
                    "h-7 w-7 rounded-lg text-xs font-medium transition-colors",
                    pageNum === page
                      ? "bg-[var(--brand)] text-[var(--text-on-brand)]"
                      : "text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]",
                  )}
                >
                  {pageNum}
                </button>
              )
            })}
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="rounded-lg px-3 py-1.5 text-xs font-medium text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)] disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
