"use client";
import { useEffect, useRef } from "react";
import { createChart, IChartApi, ISeriesApi, CandlestickData, HistogramData, Time } from "lightweight-charts";

interface Candle {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
}

interface OverlayPoint {
  time: number;
  value: number;
  color?: string;
}

interface Overlays {
  macd_line?: OverlayPoint[];
  macd_signal?: OverlayPoint[];
  macd_hist?: OverlayPoint[];
  ema_fast?: OverlayPoint[];
  ema_slow?: OverlayPoint[];
}

interface Props {
  candles: Candle[];
  overlays?: Overlays;
  signal?: string;
  price?: number;
  height?: number;
}

export function CandleChart({ candles, overlays, signal, price, height = 400 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleRef = useRef<ISeriesApi<"Candlestick"> | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      height,
      layout: {
        background: { color: "#0c1018" },
        textColor: "#7a8ba8",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: "#1a2536" },
        horzLines: { color: "#1a2536" },
      },
      crosshair: {
        mode: 0,
        vertLine: { color: "#00d4aa33", labelBackgroundColor: "#00d4aa" },
        horzLine: { color: "#00d4aa33", labelBackgroundColor: "#00d4aa" },
      },
      rightPriceScale: {
        borderColor: "#1a2536",
        scaleMargins: { top: 0.1, bottom: 0.1 },
      },
      timeScale: {
        borderColor: "#1a2536",
        timeVisible: true,
        secondsVisible: false,
      },
    });

    const candleSeries = chart.addCandlestickSeries({
      upColor: "#00d4aa",
      downColor: "#ff4757",
      borderUpColor: "#00d4aa",
      borderDownColor: "#ff4757",
      wickUpColor: "#00d4aa",
      wickDownColor: "#ff4757",
    });

    chartRef.current = chart;
    candleRef.current = candleSeries;

    const ro = new ResizeObserver(() => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    });
    ro.observe(containerRef.current);

    return () => {
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
      candleRef.current = null;
    };
  }, [height]);

  useEffect(() => {
    if (!candleRef.current || !candles.length) return;

    const data: CandlestickData[] = candles.map((c) => ({
      time: c.time as Time,
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close,
    }));

    candleRef.current.setData(data);

    if (overlays?.ema_fast?.length && chartRef.current) {
      const emaSeries = chartRef.current.addLineSeries({
        color: "#3b82f6",
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      emaSeries.setData(
        overlays.ema_fast.map((p) => ({
          time: p.time as Time,
          value: p.value,
        }))
      );
    }

    if (overlays?.ema_slow?.length && chartRef.current) {
      const emaSeries = chartRef.current.addLineSeries({
        color: "#f97316",
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      emaSeries.setData(
        overlays.ema_slow.map((p) => ({
          time: p.time as Time,
          value: p.value,
        }))
      );
    }

    chartRef.current?.timeScale().fitContent();
  }, [candles, overlays]);

  return (
    <div className="relative">
      <div ref={containerRef} className="w-full rounded-lg overflow-hidden" />
      {signal && signal !== "NEUTRAL" && (
        <div className={`absolute top-3 right-3 px-3 py-1 rounded-md text-xs font-bold ${signal === "LONG" ? "bg-acc/20 text-acc border border-acc/30" : "bg-red/20 text-red border border-red/30"}`}>
          {signal}
        </div>
      )}
      {price !== undefined && (
        <div className="absolute top-3 left-3 text-t1 text-sm font-mono font-bold">
          ${price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </div>
      )}
    </div>
  );
}
