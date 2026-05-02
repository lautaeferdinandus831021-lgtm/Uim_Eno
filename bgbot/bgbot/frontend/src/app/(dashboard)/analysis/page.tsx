"use client";
import { useState, useEffect, Component, ReactNode } from "react";
import { Card, CardHeader } from "@/components/ui/Card";
import { StatCard } from "@/components/ui/StatCard";
import { Badge } from "@/components/ui/Badge";
import { LiveCandleChart } from "@/components/charts/LiveCandleChart";
import { LiveMacdPanel } from "@/components/charts/LiveMacdPanel";
import { SignalDisplay } from "@/components/bot/SignalDisplay";
import { PositionTable } from "@/components/bot/PositionTable";
import { useBotStore } from "@/lib/store";
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
  const { m1, m5, aligned, balance, running, positions } = useBotStore();
  const [trades, setTrades] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);

  useEffect(() => {
    let ok = true;
    Promise.all([
      api.getTrades(50).then((t) => { if (ok) setTrades(t); }).catch(() => {}),
      api.getTradeStats().then((s) => { if (ok) setStats(s); }).catch(() => {}),
    ]);
    return () => { ok = false; };
  }, []);

  return (
    <div className="space-y-4 animate-in">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-t1">Live Analysis</h1>
        <div className="flex items-center gap-2">
          <div className={"w-2 h-2 rounded-full " + (running ? "bg-acc animate-pulse" : "bg-t3")} />
          <span className="text-t3 text-xs">{running ? "Live" : "Idle"}</span>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <StatCard label="Balance" value={"$" + balance.toFixed(2)} />
        <StatCard label="M1" value={m1.signal} color={m1.signal === "LONG" ? "text-acc" : m1.signal === "SHORT" ? "text-red" : "text-t3"} />
        <StatCard label="M5" value={m5.signal} color={m5.signal === "LONG" ? "text-acc" : m5.signal === "SHORT" ? "text-red" : "text-t3"} />
        <StatCard label="Aligned" value={aligned ? "YES" : "NO"} color={aligned ? "text-acc" : "text-t3"} />
        <StatCard label="PnL" value={"$" + (stats?.total_pnl || 0).toFixed(2)} color={(stats?.total_pnl || 0) >= 0 ? "text-acc" : "text-red"} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        <Card className="lg:col-span-3" padding="none">
          <div className="p-3 border-b border-border flex items-center justify-between">
            <h3 className="text-t1 text-sm font-semibold">M1 Chart</h3>
            <div className="flex items-center gap-2">
              <Badge value={m1.signal} />
              <span className="text-t2 text-xs font-mono">${m1.price?.toFixed(2) || "---"}</span>
            </div>
          </div>
          <div className="p-2"><LiveCandleChart timeframe="m1" height={280} /></div>
          <div className="p-2 border-t border-border"><LiveMacdPanel timeframe="m1" height={100} /></div>
        </Card>

        <Card>
          <CardHeader title="Signals" />
          <SignalDisplay label="M1 (1min)" signal={m1.signal} price={m1.price} />
          <SignalDisplay label="M5 (5min)" signal={m5.signal} price={m5.price} />
          <div className="mt-3 pt-3 border-t border-border space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-t3 text-xs">Alignment</span>
              <Badge value={aligned ? "ALIGNED" : "NONE"} />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-t3 text-xs">Bot</span>
              <Badge value={running ? "Running" : "Stopped"} />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-t3 text-xs">Positions</span>
              <span className="text-t2 text-xs font-bold">{positions.length}</span>
            </div>
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card padding="none">
          <div className="p-3 border-b border-border flex items-center justify-between">
            <h3 className="text-t1 text-sm font-semibold">M5 Chart</h3>
            <Badge value={m5.signal} />
          </div>
          <div className="p-2"><LiveCandleChart timeframe="m5" height={250} /></div>
          <div className="p-2 border-t border-border"><LiveMacdPanel timeframe="m5" height={100} /></div>
        </Card>
        <Card>
          <CardHeader title="Positions" subtitle={positions.length + " active"} />
          <PositionTable />
        </Card>
      </div>

      <Card>
        <CardHeader title="Recent Trades" subtitle={trades.length + " total"} />
        {trades.length === 0 ? (
          <div className="text-t3 text-sm text-center py-8">No trades yet</div>
        ) : (
          <div className="overflow-x-auto max-h-[300px]">
            <table className="w-full text-xs">
              <thead className="sticky top-0 bg-bg-2">
                <tr className="border-b border-border text-t3">
                  <th className="text-left py-2 px-2">Time</th>
                  <th className="text-left py-2 px-2">Mode</th>
                  <th className="text-left py-2 px-2">Side</th>
                  <th className="text-left py-2 px-2">Pair</th>
                  <th className="text-right py-2 px-2">Price</th>
                  <th className="text-right py-2 px-2">PnL</th>
                  <th className="text-left py-2 px-2">Status</th>
                </tr>
              </thead>
              <tbody>
                {trades.slice(0, 25).map((t: any, i: number) => (
                  <tr key={i} className="border-b border-border/30 hover:bg-bg-3/50">
                    <td className="py-1.5 px-2 text-t3 tabular-nums">{t.trade_time?.split("T")[1]?.slice(0, 8) || ""}</td>
                    <td className="py-1.5 px-2"><Badge value={t.mode} /></td>
                    <td className="py-1.5 px-2"><Badge value={t.side} /></td>
                    <td className="py-1.5 px-2 text-t2 font-medium">{t.pair}</td>
                    <td className="py-1.5 px-2 text-right text-t2 font-mono">${t.price?.toLocaleString()}</td>
                    <td className={"py-1.5 px-2 text-right font-mono font-bold " + (t.pnl >= 0 ? "text-acc" : "text-red")}>{t.pnl >= 0 ? "+" : ""}{t.pnl?.toFixed(2)}</td>
                    <td className="py-1.5 px-2"><Badge value={t.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}

export default function AnalysisPage() {
  return <PageBoundary><Content /></PageBoundary>;
}
