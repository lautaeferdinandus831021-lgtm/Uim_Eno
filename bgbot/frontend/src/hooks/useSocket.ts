"use client";
import { useEffect } from "react";
import { ws } from "@/lib/socket";
import { api } from "@/lib/api";
import { useBotStore } from "@/lib/store";

export function useSocket() {
  const store = useBotStore();
  useEffect(() => {
    const token = api.getToken();
    if (!token) return;
    ws.connect(token);
    const unsubs = [
      ws.on("__connected", () => store.update({connected: true})),
      ws.on("__disconnected", () => store.update({connected: false})),
      ws.on("state_update", (d: any) => store.update(d)),
      ws.on("trade", (d: any) => store.addTrade(d)),
      ws.on("log", (d: any) => store.addLog(d)),
    ];
    return () => { unsubs.forEach((u) => u()); ws.disconnect(); };
  }, []);
  return ws;
}
