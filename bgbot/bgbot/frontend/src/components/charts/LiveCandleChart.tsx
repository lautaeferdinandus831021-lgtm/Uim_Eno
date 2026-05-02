"use client";
import { useEffect, useRef } from "react";
import { createChart, IChartApi, ISeriesApi, Time } from "lightweight-charts";
import { useBotStore } from "@/lib/store";

interface Props { timeframe: "m1" | "m5"; height?: number; }

export function LiveCandleChart({ timeframe, height = 350 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const emaFastRef = useRef<ISeriesApi<"Line"> | null>(null);
  const emaSlowRef = useRef<ISeriesApi<"Line"> | null>(null);
  const chartData = useBotStore((s) => timeframe === "m1" ? s.chartM1 : s.chartM5);
  const signal = useBotStore((s) => timeframe === "m1" ? s.m1.signal : s.m5.signal);
  const price = useBotStore((s) => timeframe === "m1" ? s.m1.price : s.m5.price);

  useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, {
      height,
      layout: { background: { color: "#0c1018" }, textColor: "#7a8ba8", fontSize: 11 },
      grid: { vertLines: { color: "#1a2536" }, horzLines: { color: "#1a2536" } },
      crosshair: { mode: 0 },
      rightPriceScale: { borderColor: "#1a2536", scaleMargins: { top: 0.05, bottom: 0.25 } },
      timeScale: { borderColor: "#1a2536", timeVisible: true },
    });
    const cs = chart.addCandlestickSeries({
      upColor: "#00d4aa", downColor: "#ff4757",
      borderUpColor: "#00d4aa", borderDownColor: "#ff4757",
      wickUpColor: "#00d4aa80", wickDownColor: "#ff475780",
    });
    const ef = chart.addLineSeries({ color: "#3b82f6", lineWidth: 1, priceLineVisible: false, lastValueVisible: false });
    const es = chart.addLineSeries({ color: "#f97316", lineWidth: 1, priceLineVisible: false, lastValueVisible: false });
    chartRef.current = chart;
    candleRef.current = cs;
    emaFastRef.current = ef;
    emaSlowRef.current = es;
    const ro = new ResizeObserver(() => {
      if (containerRef.current) chart.applyOptions({ width: containerRef.current.clientWidth });
    });
    ro.observe(containerRef.current);
    return () => { ro.disconnect(); chart.remove(); };
  }, [height]);

  useEffect(() => {
    if (!chartData || !candleRef.current) return;
    const { candles, overlays } = chartData;
    if (candles?.length) {
      candleRef.current.setData(candles.map((c) => ({ time: c.time as Time, open: c.open, high: c.high, low: c.low, close: c.close })));
    }
    if (overlays?.ema_fast?.length && emaFastRef.current) {
      emaFastRef.current.setData(overlays.ema_fast.map((p: any) => ({ time: p.time as Time, value: p.value })));
    }
    if (overlays?.ema_slow?.length && emaSlowRef.current) {
      emaSlowRef.current.setData(overlays.ema_slow.map((p: any) => ({ time: p.time as Time, value: p.value })));
    }
    chartRef.current?.timeScale().fitContent();
  }, [chartData]);

  const signalColor = signal === "LONG" ? "text-acc" : signal === "SHORT" ? "text-red" : "text-t3";

  return (
    <div className="relative">
      <div ref={containerRef} className="w-full rounded-lg overflow-hidden" />
      <div className="absolute top-3 left-3 flex items-center gap-3">
        <span className="text-t1 text-sm font-mono font-bold">
          ${price?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) || "—"}
        </span>
        <span className={`text-xs font-bold uppercase ${signalColor}`}>{signal}</span>
      </div>
      <div className="absolute top-3 right-3 text-t3 text-[10px] font-mono uppercase">
        {timeframe === "m1" ? "1 Minute" : "5 Minutes"}
      </div>
    </div>
  );
}
