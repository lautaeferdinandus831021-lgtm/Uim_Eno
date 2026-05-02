"use client";
import { useRef, useEffect } from "react";
import { useBotStore } from "@/lib/store";

const levelColors: Record<string, string> = {
  info: "text-blu",
  success: "text-acc",
  warn: "text-yel",
  error: "text-red",
  trade: "text-pur",
  tf: "text-t3",
};

export function LogViewer() {
  const logs = useBotStore((s) => s.logs);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (ref.current) ref.current.scrollTop = ref.current.scrollHeight;
  }, [logs]);

  return (
    <div ref={ref} className="h-[300px] overflow-y-auto bg-bg border border-border rounded-lg p-3 font-mono text-[11px] leading-relaxed">
      {logs.length === 0 && (
        <div className="text-t3 text-center py-8">No logs yet. Start the bot to see activity.</div>
      )}
      {logs.map((log, i) => (
        <div key={i} className="flex gap-2 py-0.5">
          <span className="text-t3 tabular-nums shrink-0">{log.time}</span>
          <span className={`uppercase font-bold shrink-0 ${levelColors[log.level] || "text-t3"}`}>
            [{log.level}]
          </span>
          <span className="text-t2">{log.msg}</span>
        </div>
      ))}
    </div>
  );
}
