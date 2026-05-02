"use client";
import { Badge } from "@/components/ui/Badge";

interface Props {
  trade: {
    time?: string;
    trade_time?: string;
    mode: string;
    side: string;
    pair: string;
    price: number;
    pnl: number;
    status: string;
  };
}

export function TradeRow({ trade }: Props) {
  const pnlColor = trade.pnl >= 0 ? "text-acc" : "text-red";
  const time = trade.time || trade.trade_time || "";

  return (
    <div className="flex items-center justify-between py-2 px-3 border-b border-border/30 hover:bg-bg-3/50 transition text-xs">
      <div className="flex items-center gap-2 min-w-[120px]">
        <span className="text-t3 tabular-nums">{time.split(" ")[1] || time}</span>
      </div>
      <Badge value={trade.mode} />
      <Badge value={trade.side} />
      <span className="text-t2 font-medium min-w-[80px]">{trade.pair}</span>
      <span className="text-t2 font-mono tabular-nums min-w-[80px]">
        ${trade.price.toLocaleString(undefined, { minimumFractionDigits: 2 })}
      </span>
      <span className={`font-mono font-bold tabular-nums ${pnlColor}`}>
        {trade.pnl >= 0 ? "+" : ""}{trade.pnl.toFixed(2)}
      </span>
      <Badge value={trade.status} />
    </div>
  );
}
