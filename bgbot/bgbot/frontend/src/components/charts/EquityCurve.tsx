"use client";
import { useEffect, useRef } from "react";
import { createChart, IChartApi, Time } from "lightweight-charts";

interface Point { time: number; value: number; }

interface Props { data: Point[]; height?: number; }

export function EquityCurve({ data, height = 200 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current || !data.length) return;
    const chart = createChart(containerRef.current, {
      height,
      layout: { background: { color: "#0c1018" }, textColor: "#7a8ba8", fontSize: 10 },
      grid: { vertLines: { color: "#1a2536" }, horzLines: { color: "#1a2536" } },
      rightPriceScale: { borderColor: "#1a2536" },
      timeScale: { borderColor: "#1a2536", timeVisible: true },
    });

    const series = chart.addAreaSeries({
      topColor: "rgba(0, 212, 170, 0.3)",
      bottomColor: "rgba(0, 212, 170, 0.02)",
      lineColor: "#00d4aa",
      lineWidth: 2,
      priceLineVisible: false,
    });
    series.setData(data.map((p) => ({ time: p.time as Time, value: p.value })));
    chart.timeScale().fitContent();

    const ro = new ResizeObserver(() => {
      if (containerRef.current) chart.applyOptions({ width: containerRef.current.clientWidth });
    });
    ro.observe(containerRef.current);

    return () => { ro.disconnect(); chart.remove(); };
  }, [data, height]);

  return <div ref={containerRef} className="w-full rounded-lg overflow-hidden" />;
}
