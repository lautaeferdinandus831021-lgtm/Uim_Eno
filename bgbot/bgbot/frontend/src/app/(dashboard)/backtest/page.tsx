"use client";
import { useState, Component, ReactNode } from "react";
import { Card, CardHeader } from "@/components/ui/Card";
import { StatCard } from "@/components/ui/StatCard";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { EquityCurve } from "@/components/charts/EquityCurve";
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
  const [form, setForm] = useState({
    symbol: "BTCUSDT", granularity: "5m", days: 7, initial_balance: 10000,
    macd_fast: 4, macd_slow: 5, macd_signal: 1, tp_percent: 2.5, sl_percent: 1.5, order_size: 50,
  });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState("");

  const handleRun = async () => {
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const r = await api.runBacktest({
        symbol: form.symbol,
        granularity: form.granularity,
        days: form.days,
        initial_balance: form.initial_balance,
        config: {
          macd_fast: form.macd_fast, macd_slow: form.macd_slow, macd_signal: form.macd_signal,
          tp_percent: form.tp_percent, sl_percent: form.sl_percent, order_size: form.order_size,
        },
      });
      setResult(r);
    } catch (e: any) {
      setError(e.message);
    }
    setLoading(false);
  };

  const m = result?.metrics;

  return (
    <div className="space-y-4 animate-in">
      <h1 className="text-xl font-bold text-t1">Backtest</h1>

      <Card>
        <CardHeader title="Configuration" subtitle="Set parameters and run backtest" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <label className="text-t2 text-xs font-medium block mb-1">Symbol</label>
            <select value={form.symbol} onChange={(e) => setForm({...form, symbol: e.target.value})} className="w-full px-3 py-2 bg-bg-3 border border-border rounded-md text-t1 text-sm focus:outline-none focus:border-acc">
              <option value="BTCUSDT">BTC/USDT</option>
              <option value="ETHUSDT">ETH/USDT</option>
              <option value="SOLUSDT">SOL/USDT</option>
            </select>
          </div>
          <div>
            <label className="text-t2 text-xs font-medium block mb-1">Timeframe</label>
            <select value={form.granularity} onChange={(e) => setForm({...form, granularity: e.target.value})} className="w-full px-3 py-2 bg-bg-3 border border-border rounded-md text-t1 text-sm focus:outline-none focus:border-acc">
              <option value="1m">1 Min</option>
              <option value="5m">5 Min</option>
              <option value="15m">15 Min</option>
              <option value="1h">1 Hour</option>
            </select>
          </div>
          <Input label="Days" type="number" value={form.days} onChange={(e) => setForm({...form, days: +e.target.value})} />
          <Input label="Balance ($)" type="number" value={form.initial_balance} onChange={(e) => setForm({...form, initial_balance: +e.target.value})} />
        </div>
        <div className="grid grid-cols-2 md:grid-cols-6 gap-4 mt-4">
          <Input label="MACD Fast" type="number" value={form.macd_fast} onChange={(e) => setForm({...form, macd_fast: +e.target.value})} />
          <Input label="MACD Slow" type="number" value={form.macd_slow} onChange={(e) => setForm({...form, macd_slow: +e.target.value})} />
          <Input label="MACD Signal" type="number" value={form.macd_signal} onChange={(e) => setForm({...form, macd_signal: +e.target.value})} />
          <Input label="TP %" type="number" step="0.1" value={form.tp_percent} onChange={(e) => setForm({...form, tp_percent: +e.target.value})} />
          <Input label="SL %" type="number" step="0.1" value={form.sl_percent} onChange={(e) => setForm({...form, sl_percent: +e.target.value})} />
          <Input label="Size ($)" type="number" value={form.order_size} onChange={(e) => setForm({...form, order_size: +e.target.value})} />
        </div>
        <div className="mt-4">
          <Button onClick={handleRun} loading={loading} size="lg">
            {loading ? "Running..." : "Run Backtest"}
          </Button>
        </div>
        {error && (
          <div className="mt-3 text-xs text-red bg-red/10 border border-red/30 rounded-md px-3 py-2">{error}</div>
        )}
      </Card>

      {m && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <StatCard label="Return" value={"$" + m.total_return} sub={m.total_return_pct + "%"} color={m.total_return >= 0 ? "text-acc" : "text-red"} />
            <StatCard label="Win Rate" value={m.win_rate + "%"} sub={m.wins + "W / " + m.losses + "L"} />
            <StatCard label="Profit Factor" value={m.profit_factor} />
            <StatCard label="Max DD" value={m.max_drawdown_pct + "%"} color="text-red" />
            <StatCard label="Sharpe" value={m.sharpe_ratio} />
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatCard label="Trades" value={m.total_trades} />
            <StatCard label="Avg Win" value={"$" + m.avg_win} color="text-acc" />
            <StatCard label="Avg Loss" value={"$" + m.avg_loss} color="text-red" />
            <StatCard label="R:R" value={m.reward_risk} />
          </div>

          {result.equity?.length > 0 && (
            <Card padding="none">
              <div className="p-3 border-b border-border">
                <h3 className="text-t1 text-sm font-semibold">Equity Curve</h3>
              </div>
              <div className="p-2">
                <EquityCurve data={result.equity} height={250} />
              </div>
            </Card>
          )}

          {result.trades?.length > 0 && (
            <Card>
              <CardHeader title="Trades" subtitle={result.trades.length + " trades"} />
              <div className="overflow-x-auto max-h-[400px] overflow-y-auto">
                <table className="w-full text-xs">
                  <thead className="sticky top-0 bg-bg-2">
                    <tr className="border-b border-border text-t3">
                      <th className="text-left py-2 px-2">#</th>
                      <th className="text-left py-2 px-2">Side</th>
                      <th className="text-right py-2 px-2">Entry</th>
                      <th className="text-right py-2 px-2">Exit</th>
                      <th className="text-right py-2 px-2">PnL</th>
                      <th className="text-right py-2 px-2">PnL%</th>
                      <th className="text-left py-2 px-2">Exit</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.trades.map((t: any, i: number) => (
                      <tr key={i} className="border-b border-border/30 hover:bg-bg-3/50">
                        <td className="py-1.5 px-2 text-t3">{i + 1}</td>
                        <td className="py-1.5 px-2">
                          <span className={t.side === "LONG" ? "text-acc" : "text-red"}>{t.side}</span>
                        </td>
                        <td className="py-1.5 px-2 text-right font-mono text-t2">${t.entry?.toLocaleString()}</td>
                        <td className="py-1.5 px-2 text-right font-mono text-t2">${t.exit?.toLocaleString()}</td>
                        <td className={"py-1.5 px-2 text-right font-mono font-bold " + (t.pnl >= 0 ? "text-acc" : "text-red")}>
                          {t.pnl >= 0 ? "+" : ""}{t.pnl}
                        </td>
                        <td className={"py-1.5 px-2 text-right font-mono " + (t.pnl_pct >= 0 ? "text-acc" : "text-red")}>
                          {t.pnl_pct}%
                        </td>
                        <td className="py-1.5 px-2 text-t3">{t.exit_type}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  );
}

export default function BacktestPage() {
  return <PageBoundary><Content /></PageBoundary>;
}
