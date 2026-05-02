import { io, Socket } from "socket.io-client";
const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";
class WsClient {
  private socket: Socket | null = null;
  private listeners: Map<string, Set<Function>> = new Map();
  connect(token: string) {
    if (this.socket?.connected) return;
    this.socket = io(WS_URL, {auth: {token}, transports: ["websocket"], reconnection: true, reconnectionDelay: 2000});
    this.socket.on("connect", () => this.emit("__connected"));
    this.socket.on("disconnect", () => this.emit("__disconnected"));
    ["state_update", "trade", "log", "chart_m1", "chart_m5"].forEach((e) => this.socket?.on(e, (d: any) => this.emit(e, d)));
  }
  disconnect() { this.socket?.disconnect(); this.socket = null; }
  send(event: string, data?: any) { this.socket?.emit(event, data); }
  on(event: string, cb: Function) { if (!this.listeners.has(event)) this.listeners.set(event, new Set()); this.listeners.get(event)!.add(cb); return () => this.listeners.get(event)?.delete(cb); }
  private emit(event: string, data?: any) { this.listeners.get(event)?.forEach((cb) => cb(data)); }
}
export const ws = new WsClient();
