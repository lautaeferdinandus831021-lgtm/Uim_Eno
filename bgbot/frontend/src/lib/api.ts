const API = process.env.NEXT_PUBLIC_API_URL || "";
class ApiClient {
  private token: string | null = null;
  setToken(t: string | null) { this.token = t; if (t) localStorage.setItem("token", t); else localStorage.removeItem("token"); }
  getToken(): string | null { if (!this.token) this.token = localStorage.getItem("token"); return this.token; }
  private async req<T>(path: string, opts: RequestInit = {}): Promise<T> {
    const token = this.getToken();
    const headers: Record<string, string> = {"Content-Type": "application/json", ...(opts.headers as Record<string, string>)};
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const res = await fetch(`${API}${path}`, {...opts, headers});
    if (res.status === 401) { this.setToken(null); window.location.href = "/login"; throw new Error("Unauthorized"); }
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Request failed");
    return data as T;
  }
  async login(email: string, password: string, otp?: string) { const d = await this.req<any>("/auth/login", {method: "POST", body: JSON.stringify({email, password, otp})}); if (d.access_token) this.setToken(d.access_token); return d; }
  async register(email: string, password: string, confirm: string) { return this.req<any>("/auth/register", {method: "POST", body: JSON.stringify({email, password, confirm})}); }
  async forgot(email: string) { return this.req<any>("/auth/forgot", {method: "POST", body: JSON.stringify({email})}); }
  async reset(token: string, password: string, confirm: string) { return this.req<any>("/auth/reset", {method: "POST", body: JSON.stringify({token, password, confirm})}); }
  async me() { return this.req<any>("/auth/me"); }
  logout() { this.setToken(null); window.location.href = "/login"; }
  async getConfig() { return this.req<any>("/api/get-config"); }
  async saveConfig(cfg: any) { return this.req<any>("/api/save-config", {method: "POST", body: JSON.stringify(cfg)}); }
  async saveApi(cfg: any) { return this.req<any>("/api/save-api", {method: "POST", body: JSON.stringify(cfg)}); }
  async testApi() { return this.req<any>("/api/test-api"); }
  async getTrades(limit = 100) { return this.req<any[]>(`/api/trades?limit=${limit}`); }
  async getTradeStats() { return this.req<any>("/api/trade-stats"); }
  async getPositions() { return this.req<any[]>("/api/positions"); }
  async startBot() { return this.req<any>("/api/bot/start", {method: "POST"}); }
  async stopBot() { return this.req<any>("/api/bot/stop", {method: "POST"}); }
  async runBacktest(cfg: any) { return this.req<any>("/api/run-backtest", {method: "POST", body: JSON.stringify(cfg)}); }
  async getBacktestHistory() { return this.req<any>("/api/backtest-history"); }
}
export const api = new ApiClient();
