"use client";
interface Props { label: string; signal: string; price: number; }

const signalColors: Record<string, string> = {
  LONG: "text-acc", SHORT: "text-red", NEUTRAL: "text-t3",
};

export function SignalDisplay({ label, signal, price }: Props) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-border/50 last:border-0">
      <span className="text-t3 text-xs font-medium">{label}</span>
      <div className="flex items-center gap-3">
        <span className="text-t2 text-xs font-mono tabular-nums">
          ${price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </span>
        <span className={`text-xs font-bold ${signalColors[signal] || "text-t3"}`}>
          {signal}
        </span>
      </div>
    </div>
  );
}
