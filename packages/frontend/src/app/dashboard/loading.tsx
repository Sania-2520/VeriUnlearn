export default function DashboardLoading() {
  return (
    <div className="p-6 space-y-6">
      <div className="h-8 w-48 bg-[var(--bg-hover)] rounded animate-pulse" />
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-32 bg-[var(--bg-hover)] rounded-lg animate-pulse" />
        ))}
      </div>
      <div className="h-64 bg-[var(--bg-hover)] rounded-lg animate-pulse" />
    </div>
  );
}
