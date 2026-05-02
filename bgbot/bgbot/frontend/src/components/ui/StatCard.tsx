interface Props { label: string; value: string | number; sub?: string; color?: string; }

export function StatCard({ label, value, sub, color = "text-t1" }: Props) {
  return (
    <div className="bg-bg-2 border border-border rounded-lg p-4">
      <div className="text-t3 text-[11px] font-medium uppercase tracking-wider mb-1">{label}</div>
      <div className={`${color} text-xl font-bold tabular-nums`}>{value}</div>
      {sub && <div className="text-t3 text-xs mt-1">{sub}</div>}
    </div>
  );
}
