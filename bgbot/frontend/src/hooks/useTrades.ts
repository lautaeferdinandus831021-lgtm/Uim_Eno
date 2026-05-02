"use client";
import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import { Trade, TradeStats } from "@/lib/types";

export function useTrades() {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [stats, setStats] = useState<TradeStats | null>(null);
  const [loading, setLoading] = useState(true);
  const refresh = useCallback(async () => {
    setLoading(true);
    try { const [t, s] = await Promise.all([api.getTrades(200), api.getTradeStats()]); setTrades(t); setStats(s); }
    catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { refresh(); }, [refresh]);
  return { trades, stats, loading, refresh };
}
