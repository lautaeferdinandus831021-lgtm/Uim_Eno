import numpy as np


class BacktestMetrics:
    @staticmethod
    def calculate(initial_balance, final_balance, trades, max_drawdown, max_drawdown_pct):
        wins = [t for t in trades if t["pnl"] > 0]
        losses = [t for t in trades if t["pnl"] <= 0]
        gp = sum(t["pnl"] for t in wins) if wins else 0
        gl = abs(sum(t["pnl"] for t in losses)) if losses else 0
        aw = float(np.mean([t["pnl"] for t in wins])) if wins else 0
        al = float(np.mean([abs(t["pnl"]) for t in losses])) if losses else 0
        rets = [t["pnl_pct"] for t in trades]
        std = float(np.std(rets)) if len(rets) > 1 else 0
        sharpe = (float(np.mean(rets)) / std) * np.sqrt(252) if std > 0 else 0
        return {"initial_balance": initial_balance, "final_balance": round(final_balance, 2), "total_return": round(final_balance - initial_balance, 2), "total_return_pct": round(((final_balance - initial_balance) / initial_balance) * 100, 2), "total_trades": len(trades), "wins": len(wins), "losses": len(losses), "win_rate": round(len(wins) / len(trades) * 100, 1) if trades else 0, "gross_profit": round(gp, 2), "gross_loss": round(gl, 2), "profit_factor": round(gp / gl, 2) if gl > 0 else 0, "total_fees": round(sum(t["fee"] for t in trades), 2), "max_drawdown": round(max_drawdown, 2), "max_drawdown_pct": round(max_drawdown_pct, 2), "avg_win": round(aw, 2), "avg_loss": round(al, 2), "reward_risk": round(aw / al, 2) if al > 0 else 0, "sharpe_ratio": round(sharpe, 2)}
