"use client";
import { useBotStore } from "@/lib/store";

export default function BacktestPage() {
  const { running, m1, m5, aligned, balance, stats } = useBotStore();
  return (
    <div className="animate-in">
      <h1 className="text-xl font-bold text-t1 mb-4">Backtest</h1>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <div className="bg-bg-2 border border-border rounded-lg p-4"><div className="text-t3 text-xs mb-1">Balance</div><div className="text-t1 text-lg font-bold">${balance.toFixed(2)}</div></div>
        <div className="bg-bg-2 border border-border rounded-lg p-4"><div className="text-t3 text-xs mb-1">M1 Signal</div><div className="text-lg font-bold text-acc">{m1.signal}</div></div>
        <div className="bg-bg-2 border border-border rounded-lg p-4"><div className="text-t3 text-xs mb-1">M5 Signal</div><div className="text-lg font-bold text-blu">{m5.signal}</div></div>
        <div className="bg-bg-2 border border-border rounded-lg p-4"><div className="text-t3 text-xs mb-1">Status</div><div className="text-lg font-bold">{running ? <span className="text-acc">Running</span> : <span className="text-t3">Stopped</span>}</div></div>
      </div>
      <div className="bg-bg-2 border border-border rounded-lg p-6"><p className="text-t3 text-sm">Page content for backtest will be built here.</p></div>
    </div>
  );
}
