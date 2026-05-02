"use client";
import { useState, useEffect } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { api } from "@/lib/api";

interface BotCfg {
  market_mode: string; symbol: string; order_size: number;
  tp_percent: number; sl_percent: number; leverage: number;
  macd_fast: number; macd_slow: number; macd_signal: number;
  [key: string]: any;
}

const DEFAULT: BotCfg = {
  market_mode: "spot", symbol: "BTCUSDT", order_size: 50,
  tp_percent: 2.5, sl_percent: 1.5, leverage: 3,
  macd_fast: 4, macd_slow: 5, macd_signal: 1,
};

interface Props { onSaved?: () => void; }

export function BotConfigForm({ onSaved }: Props) {
  const [cfg, setCfg] = useState<BotCfg>(DEFAULT);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    api.getConfig().then((c: any) => { if (c && c.macd_fast !== undefined) setCfg(c); }).catch(() => {});
  }, []);

  const set = <K extends keyof BotCfg>(key: K, val: BotCfg[K]) => setCfg((p) => ({ ...p, [key]: val }));

  const handleSave = async () => {
    setLoading(true);
    try { await api.saveConfig(cfg); setMsg("Config saved!"); onSaved?.(); }
    catch(e:any) { setMsg(e.message); }
    setLoading(false);
  };

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="text-t2 text-xs font-medium block mb-1">Market Mode</label>
          <select value={cfg.market_mode} onChange={(e) => set("market_mode", e.target.value)} className="w-full px-3 py-2 bg-bg-3 border border-border rounded-md text-t1 text-sm focus:outline-none focus:border-acc">
            <option value="spot">Spot</option>
            <option value="perp">Perpetual</option>
          </select>
        </div>
        <div>
          <label className="text-t2 text-xs font-medium block mb-1">Symbol</label>
          <select value={cfg.symbol} onChange={(e) => set("symbol", e.target.value)} className="w-full px-3 py-2 bg-bg-3 border border-border rounded-md text-t1 text-sm focus:outline-none focus:border-acc">
            <option value="BTCUSDT">BTC/USDT</option>
            <option value="ETHUSDT">ETH/USDT</option>
            <option value="SOLUSDT">SOL/USDT</option>
            <option value="BNBUSDT">BNB/USDT</option>
          </select>
        </div>
      </div>
      <div className="grid grid-cols-3 gap-4">
        <Input label="Order Size ($)" type="number" value={cfg.order_size} onChange={(e) => set("order_size", +e.target.value)} />
        <Input label="TP %" type="number" step="0.1" value={cfg.tp_percent} onChange={(e) => set("tp_percent", +e.target.value)} />
        <Input label="SL %" type="number" step="0.1" value={cfg.sl_percent} onChange={(e) => set("sl_percent", +e.target.value)} />
      </div>
      {cfg.market_mode === "perp" && (
        <Input label="Leverage" type="number" value={cfg.leverage} onChange={(e) => set("leverage", +e.target.value)} />
      )}
      <div className="border-t border-border pt-4">
        <h4 className="text-t2 text-xs font-semibold mb-3 uppercase tracking-wider">MACD Settings</h4>
        <div className="grid grid-cols-3 gap-4">
          <Input label="Fast" type="number" value={cfg.macd_fast} onChange={(e) => set("macd_fast", +e.target.value)} />
          <Input label="Slow" type="number" value={cfg.macd_slow} onChange={(e) => set("macd_slow", +e.target.value)} />
          <Input label="Signal" type="number" value={cfg.macd_signal} onChange={(e) => set("macd_signal", +e.target.value)} />
        </div>
      </div>
      {msg && <div className="text-xs text-acc bg-acc/10 border border-acc/30 rounded-md px-3 py-2">{msg}</div>}
      <Button onClick={handleSave} loading={loading} size="sm">Save Config</Button>
    </div>
  );
}
