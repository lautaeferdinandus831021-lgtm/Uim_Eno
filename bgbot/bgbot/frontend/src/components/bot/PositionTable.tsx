"use client";
import { useBotStore } from "@/lib/store";

export function PositionTable() {
  const positions = useBotStore((s) => s.positions);

  if (!positions.length) {
    return <div className="text-t3 text-sm text-center py-6">No open positions</div>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-border text-t3">
            <th className="text-left py-2 px-2 font-medium">Symbol</th>
            <th className="text-left py-2 px-2 font-medium">Side</th>
            <th className="text-right py-2 px-2 font-medium">Size</th>
            <th className="text-right py-2 px-2 font-medium">Entry</th>
            <th className="text-right py-2 px-2 font-medium">Current</th>
            <th className="text-right py-2 px-2 font-medium">PnL</th>
            <th className="text-right py-2 px-2 font-medium">PnL %</th>
          </tr>
        </thead>
        <tbody>
          {positions.map((p: any, i: number) => {
            const pnlColor = p.pnl >= 0 ? "text-acc" : "text-red";
            return (
              <tr key={i} className="border-b border-border/30 hover:bg-bg-3/50">
                <td className="py-2 px-2 text-t1 font-medium">{p.symbol}</td>
                <td className="py-2 px-2"><span className={p.side === "long" ? "text-acc" : "text-red"}>{p.side}</span></td>
                <td className="py-2 px-2 text-right text-t2 tabular-nums">{p.size}</td>
                <td className="py-2 px-2 text-right text-t2 font-mono tabular-nums">${p.entry_price?.toLocaleString()}</td>
                <td className="py-2 px-2 text-right text-t2 font-mono tabular-nums">${p.current_price?.toLocaleString()}</td>
                <td className={`py-2 px-2 text-right font-mono font-bold tabular-nums ${pnlColor}`}>{p.pnl >= 0 ? "+" : ""}{p.pnl?.toFixed(2)}</td>
                <td className={`py-2 px-2 text-right font-mono tabular-nums ${pnlColor}`}>{p.pnl_pct?.toFixed(2)}%</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
