"use client";
import { useEffect, useRef } from "react";
import { createChart, IChartApi, Time } from "lightweight-charts";
import { useBotStore } from "@/lib/store";

interface Props { timeframe: "m1" | "m5"; height?: number; }

export function LiveMacdPanel({ timeframe, height = 120 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const chartData = useBotStore((s) => timeframe === "m1" ? s.chartM1 : s.chartM5);

  useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, {
      height,
      layout: { background: { color: "#0c1018" }, textColor: "#7a8ba8", fontSize: 10 },
      grid: { vertLines: { color: "#1a2536" }, horzLines: { color: "#1a2536" } },
      rightPriceScale: { borderColor: "#1a2536" },
      timeScale: { borderColor: "#1a2536", visible: false },
    });
    chartRef.current = chart;
    const ro = new ResizeObserver(() => {
      if (containerRef.current) chart.applyOptions({ width: containerRef.current.clientWidth });
    });
    ro.observe(containerRef.current);
    return () => { ro.disconnect(); chart.remove(); };
  }, [height]);

  useEffect(() => {
    if (!chartRef.current || !chartData?.overlays) return;
    const { overlays } = chartData;
    if (overlays.macd_line?.length) {
      const s = chartRef.current.addLineSeries({ color: "#3b82f6", lineWidth: 1, priceLineVisible: false, lastValueVisible: false });
      s.setData(overlays.macd_line.map((p: any) => ({ time: p.time as Time, value: p.value })));
    }
    if (overlays.macd_signal?.length) {
      const s = chartRef.current.addLineSeries({ color: "#f97316", lineWidth: 1, priceLineVisible: false, lastValueVisible: false });
      s.setData(overlays.macd_signal.map((p: any) => ({ time: p.time as Time, value: p.value })));
    }
    if (overlays.macd_hist?.length) {
      const s = chartRef.current.addHistogramSeries({ priceLineVisible: false, lastValueVisible: false });
      s.setData(overlays.macd_hist.map((p: any) => ({ time: p.time as Time, value: p.value, color: p.color || "#7a8ba8" })));
    }
    chartRef.current.timeScale().fitContent();
  }, [chartData]);

  return <div ref={containerRef} className="w-full rounded-lg overflow-hidden" />;
}
