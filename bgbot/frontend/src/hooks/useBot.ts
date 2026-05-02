"use client";
import { useCallback } from "react";
import { useBotStore } from "@/lib/store";
import { api } from "@/lib/api";

export function useBot() {
  const { running, stats, balance, m1, m5, aligned } = useBotStore();
  const start = useCallback(() => api.startBot(), []);
  const stop = useCallback(() => api.stopBot(), []);
  return { running, stats, balance, m1, m5, aligned, start, stop };
}
