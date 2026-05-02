export interface User { id: number; email: string; name: string; picture: string; provider: string; totp_enabled: boolean; }
export interface Trade { id: number; trade_time: string; mode: "spot" | "perp"; side: "buy" | "sell"; pair: string; price: number; order_type: string; size: number; pnl: number; pnl_pct: number; fee: number; status: string; order_id: string; }
export interface TradeStats { total: number; wins: number; losses: number; total_pnl: number; spot: number; perp: number; win_rate: number; }
export interface Position { id: number; symbol: string; side: string; size: number; entry_price: number; current_price: number; pnl: number; pnl_pct: number; hold_side: string; leverage: number; }
export interface BotConfig { market_mode: string; symbol: string; order_size: number; tp_percent: number; sl_percent: number; leverage: number; macd_fast: number; macd_slow: number; macd_signal: number; [key: string]: any; }
