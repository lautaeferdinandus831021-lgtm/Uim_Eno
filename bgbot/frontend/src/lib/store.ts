import { create } from "zustand";
interface BotState {
  running: boolean; connected: boolean; balance: number; mode: string; symbol: string;
  m1: { signal: string; price: number }; m5: { signal: string; price: number }; aligned: boolean;
  positions: any[]; trades: any[]; logs: any[];
  stats: { total: number; wins: number; losses: number; total_pnl: number; spot: number; perp: number };
  risk_status: any;
  update: (s: Partial<BotState>) => void; addTrade: (t: any) => void; addLog: (l: any) => void; clearLogs: () => void;
}
export const useBotStore = create<BotState>((set) => ({
  running: false, connected: false, balance: 0, mode: "spot", symbol: "BTCUSDT",
  m1: {signal: "NEUTRAL", price: 0}, m5: {signal: "NEUTRAL", price: 0}, aligned: false,
  positions: [], trades: [], logs: [],
  stats: {total: 0, wins: 0, losses: 0, total_pnl: 0, spot: 0, perp: 0}, risk_status: {},
  update: (s) => set((p) => ({...p, ...s})),
  addTrade: (t) => set((p) => ({trades: [t, ...p.trades].slice(0, 100)})),
  addLog: (l) => set((p) => ({logs: [...p.logs, l].slice(-500)})),
  clearLogs: () => set({logs: []}),
}));
