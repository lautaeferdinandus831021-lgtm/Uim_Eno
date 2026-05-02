interface Props { value: string; size?: "sm" | "md"; }

const colorMap: Record<string, string> = {
  LONG: "bg-acc/15 text-acc border-acc/30",
  SHORT: "bg-red/15 text-red border-red/30",
  NEUTRAL: "bg-t3/10 text-t3 border-t3/20",
  buy: "bg-acc/15 text-acc border-acc/30",
  sell: "bg-red/15 text-red border-red/30",
  spot: "bg-blu/15 text-blu border-blu/30",
  perp: "bg-pur/15 text-pur border-pur/30",
  simulated: "bg-yel/15 text-yel border-yel/30",
  filled: "bg-acc/15 text-acc border-acc/30",
};

export function Badge({ value, size = "sm" }: Props) {
  const colors = colorMap[value] || "bg-bg-3 text-t3 border-border";
  const sz = size === "sm" ? "text-[10px] px-2 py-0.5" : "text-xs px-2.5 py-1";
  return (
    <span className={`inline-block font-semibold uppercase border rounded-md ${colors} ${sz}`}>
      {value}
    </span>
  );
}
