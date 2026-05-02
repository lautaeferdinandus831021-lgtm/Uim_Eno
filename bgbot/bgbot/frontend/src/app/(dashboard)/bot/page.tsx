"use client";
import { useState, useEffect, Component, ReactNode } from "react";
import { Card, CardHeader } from "@/components/ui/Card";
import { StatCard } from "@/components/ui/StatCard";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { SignalDisplay } from "@/components/bot/SignalDisplay";
import { LogViewer } from "@/components/bot/LogViewer";
import { PositionTable } from "@/components/bot/PositionTable";
import { useBotStore } from "@/lib/store";
import { useBot } from "@/hooks/useBot";
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
  const { running, m1, m5, aligned, balance, start, stop } = useBot();
  const { positions, risk_status } = useBotStore();
  const [stats, setStats] = useState<any>(null);

  useEffect(() => {
    let ok = true;
    api.getTradeStats().then((s) => { if (ok) setStats(s); }).catch(() => {});
    const iv = setInterval(() => {
      api.getTradeStats().then((s) => { if (ok) setStats(s); }).catch(() => {});
    }, 30000);
    return () => { ok = false; clearInterval(iv); };
  }, []);

  return (
    <div className="space-y-4 animate-in">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-t1">Bot Control</h1>
        <div className="flex items-center gap-3">
          <div className={"flex items-center gap-2 text-xs font-medium " + (running ? "text-acc" : "text-t3")}>
            <div className={"w-2.5 h-2.5 rounded-full " + (running ? "bg-acc animate-pulse" : "bg-t3")} />
            {running ? "Running" : "Stopped"}
          </div>
          {running ? (
            <Button onClick={stop} variant="danger" size="sm">Stop Bot</Button>
          ) : (
            <Button onClick={start} size="sm">Start Bot</Button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
        <StatCard label="Balance" value={"$" + balance.toFixed(2)} />
        <StatCard label="M1" value={m1.signal} color={m1.signal === "LONG" ? "text-acc" : m1.signal === "SHORT" ? "text-red" : "text-t3"} />
        <StatCard label="M5" value={m5.signal} color={m5.signal === "LONG" ? "text-acc" : m5.signal === "SHORT" ? "text-red" : "text-t3"} />
        <StatCard label="Aligned" value={aligned ? "YES" : "NO"} color={aligned ? "text-acc" : "text-t3"} />
        <StatCard label="Trades" value={stats?.total || 0} />
        <StatCard label="PnL" value={"$" + (stats?.total_pnl || 0).toFixed(2)} color={(stats?.total_pnl || 0) >= 0 ? "text-acc" : "text-red"} />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard label="Wins" value={stats?.wins || 0} color="text-acc" />
        <StatCard label="Losses" value={stats?.losses || 0} color="text-red" />
        <StatCard label="Win Rate" value={(stats?.win_rate || 0) + "%"} />
        <StatCard label="Trades/Hr" value={risk_status?.trades_this_hour || 0} sub={"max " + (risk_status?.max_trades_per_hour || 10)} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2">
          <CardHeader title="Live Logs" subtitle="Real-time bot activity" />
          <LogViewer />
        </Card>
        <div className="space-y-4">
          <Card>
            <CardHeader title="Signals" />
            <SignalDisplay label="M1 (1min)" signal={m1.signal} price={m1.price} />
            <SignalDisplay label="M5 (5min)" signal={m5.signal} price={m5.price} />
          </Card>
          <Card>
            <CardHeader title="Risk" />
            <div className="space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-t3">Daily Loss</span>
                <span className="text-t2">${risk_status?.daily_loss?.toFixed(2) || "0.00"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-t3">Loss %</span>
                <span className="text-t2">{risk_status?.daily_loss_pct?.toFixed(2) || "0.00"}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-t3">Can Trade</span>
                <Badge value={risk_status?.can_trade ? "YES" : "BLOCKED"} />
              </div>
            </div>
          </Card>
        </div>
      </div>

      <Card>
        <CardHeader title="Positions" subtitle={positions.length + " open"} />
        <PositionTable />
      </Card>
    </div>
  );
}

export default function BotPage() {
  return <PageBoundary><Content /></PageBoundary>;
}
