"use client";
import { useState, useEffect, Component, ReactNode } from "react";
import { Card, CardHeader } from "@/components/ui/Card";
import { StatCard } from "@/components/ui/StatCard";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { api } from "@/lib/api";

class PageBoundary extends Component<{children: ReactNode}, {err: boolean}> {
  constructor(p: any) { super(p); this.state = { err: false }; }
  static getDerivedStateFromError() { return { err: true }; }
  render() {
    if (this.state.err) return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] gap-4">
        <p className="text-red text-sm">Something went wrong.</p>
        <button onClick={() => location.reload()} className="px-4 py-2 bg-bg-3 border border-border rounded-md text-t2 text-sm">Reload</button>
      </div>
    );
    return this.props.children;
  }
}

function Content() {
  const [trades, setTrades] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"all"|"spot"|"perp">("all");
  const [backtests, setBacktests] = useState<any[]>([]);

  const refresh = () => {
    setLoading(true);
    Promise.all([
      api.getTrades(500).then(setTrades).catch(() => setTrades([])),
      api.getTradeStats().then(setStats).catch(() => {}),
      api.getBacktestHistory().then(setBacktests).catch(() => {}),
    ]).finally(() => setLoading(false));
  };

  useEffect(() => { refresh(); }, []);

  const filtered = filter === "all" ? trades : trades.filter((t) => t.mode === filter);

  return (
    <div className="space-y-4 animate-in">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-t1">History</h1>
        <div className="flex items-center gap-2">
          <a href="/api/export-trades" target="_blank">
            <Button variant="secondary" size="sm">Export CSV</Button>
          </a>
          <Button variant="ghost" size="sm" onClick={refresh}>Refresh</Button>
        </div>
      </div>

      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
          <StatCard label="Total" value={stats.total} />
          <StatCard label="Wins" value={stats.wins} color="text-acc" />
          <StatCard label="Losses" value={stats.losses} color="text-red" />
          <StatCard label="Win Rate" value={stats.win_rate + "%"} />
          <StatCard label="PnL" value={"$" + stats.total_pnl.toFixed(2)} color={stats.total_pnl >= 0 ? "text-acc" : "text-red"} />
          <StatCard label="Spot/Perp" value={stats.spot + "/" + stats.perp} />
        </div>
      )}

      <Card>
        <CardHeader
          title="Trade History"
          subtitle={filtered.length + " trades"}
          action={
            <div className="flex gap-1 bg-bg-3 border border-border rounded-md overflow-hidden">
              {(["all","spot","perp"] as const).map((f) => (
                <button key={f} onClick={() => setFilter(f)} className={"px-3 py-1 text-xs font-semibold transition " + (filter === f ? "bg-acc/10 text-acc" : "text-t3 hover:text-t2")}>
                  {f.toUpperCase()}
                </button>
              ))}
            </div>
          }
        />
        {loading ? (
          <div className="text-t3 text-sm text-center py-8">Loading...</div>
        ) : filtered.length === 0 ? (
          <div className="text-t3 text-sm text-center py-8">No trades found</div>
        ) : (
          <div className="overflow-x-auto max-h-[500px] overflow-y-auto">
            <table className="w-full text-xs">
              <thead className="sticky top-0 bg-bg-2">
                <tr className="border-b border-border text-t3">
                  <th className="text-left py-2 px-2">#</th>
                  <th className="text-left py-2 px-2">Time</th>
                  <th className="text-left py-2 px-2">Mode</th>
                  <th className="text-left py-2 px-2">Side</th>
                  <th className="text-left py-2 px-2">Pair</th>
                  <th className="text-right py-2 px-2">Price</th>
                  <th className="text-right py-2 px-2">Size</th>
                  <th className="text-right py-2 px-2">PnL</th>
                  <th className="text-right py-2 px-2">PnL%</th>
                  <th className="text-right py-2 px-2">Fee</th>
                  <th className="text-left py-2 px-2">Status</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((t) => (
                  <tr key={t.id} className="border-b border-border/30 hover:bg-bg-3/50">
                    <td className="py-2 px-2 text-t3">{t.id}</td>
                    <td className="py-2 px-2 text-t3 tabular-nums whitespace-nowrap">
                      {t.trade_time?.replace("T"," ").slice(0,19) || ""}
                    </td>
                    <td className="py-2 px-2"><Badge value={t.mode} /></td>
                    <td className="py-2 px-2"><Badge value={t.side} /></td>
                    <td className="py-2 px-2 text-t2 font-medium">{t.pair}</td>
                    <td className="py-2 px-2 text-right text-t2 font-mono tabular-nums">
                      ${t.price?.toLocaleString(undefined,{minimumFractionDigits:2})}
                    </td>
                    <td className="py-2 px-2 text-right text-t2 font-mono tabular-nums">{t.size?.toFixed(4)}</td>
                    <td className={"py-2 px-2 text-right font-mono font-bold tabular-nums " + (t.pnl >= 0 ? "text-acc" : "text-red")}>
                      {t.pnl >= 0 ? "+" : ""}{t.pnl?.toFixed(2)}
                    </td>
                    <td className={"py-2 px-2 text-right font-mono tabular-nums " + (t.pnl_pct >= 0 ? "text-acc" : "text-red")}>
                      {t.pnl_pct?.toFixed(2)}%
                    </td>
                    <td className="py-2 px-2 text-right text-t3 font-mono tabular-nums">{t.fee?.toFixed(4)}</td>
                    <td className="py-2 px-2"><Badge value={t.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {backtests.length > 0 && (
        <Card>
          <CardHeader title="Backtest History" subtitle={backtests.length + " runs"} />
          <div className="space-y-2">
            {backtests.map((bt) => (
              <div key={bt.id} className="flex items-center justify-between py-2 px-3 bg-bg-3/50 border border-border/50 rounded-md">
                <div className="flex items-center gap-3 text-xs">
                  <span className="text-t3 tabular-nums">{bt.created_at?.replace("T"," ").slice(0,19)}</span>
                  <span className="text-t2 font-medium">{bt.config?.symbol || "BTCUSDT"}</span>
                </div>
                <div className="flex items-center gap-4 text-xs">
                  <span className={"font-mono font-bold " + ((bt.metrics?.total_return||0) >= 0 ? "text-acc" : "text-red")}>
                    {bt.metrics?.total_return >= 0 ? "+" : ""}${bt.metrics?.total_return}
                  </span>
                  <span className="text-t3">WR: {bt.metrics?.win_rate}%</span>
                  <span className="text-t3">{bt.metrics?.total_trades} trades</span>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

export default function HistoryPage() {
  return <PageBoundary><Content /></PageBoundary>;
}
