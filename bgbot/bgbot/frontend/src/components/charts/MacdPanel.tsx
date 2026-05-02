"use client";
import { useEffect, useRef } from "react";
import { createChart, IChartApi, Time } from "lightweight-charts";

interface OverlayPoint {
  time: number;
  value: number;
  color?: string;
}

interface Props {
  data?: {
    macd_line?: OverlayPoint[];
    macd_signal?: OverlayPoint[];
    macd_hist?: OverlayPoint[];
  };
  height?: number;
}

export function MacdPanel({ data, height = 150 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      height,
      layout: {
        background: { color: "#0c1018" },
        textColor: "#7a8ba8",
        fontSize: 10,
      },
      grid: {
        vertLines: { color: "#1a2536" },
        horzLines: { color: "#1a2536" },
      },
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
    if (!chartRef.current || !data) return;

    chartRef.current.removeSeries = chartRef.current.removeSeries;

    if (data.macd_line?.length) {
      const s = chartRef.current.addLineSeries({ color: "#3b82f6", lineWidth: 1, priceLineVisible: false, lastValueVisible: false });
      s.setData(data.macd_line.map((p) => ({ time: p.time as Time, value: p.value })));
    }
    if (data.macd_signal?.length) {
      const s = chartRef.current.addLineSeries({ color: "#f97316", lineWidth: 1, priceLineVisible: false, lastValueVisible: false });
      s.setData(data.macd_signal.map((p) => ({ time: p.time as Time, value: p.value })));
    }
    if (data.macd_hist?.length) {
      const s = chartRef.current.addHistogramSeries({ priceLineVisible: false, lastValueVisible: false });
      s.setData(data.macd_hist.map((p) => ({ time: p.time as Time, value: p.value, color: p.color || "#7a8ba8" })));
    }
    chartRef.current.timeScale().fitContent();
  }, [data]);

  return <div ref={containerRef} className="w-full rounded-lg overflow-hidden" />;
}
