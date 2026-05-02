"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { useSocket } from "@/hooks/useSocket";
import { useBotStore } from "@/lib/store";
import { api } from "@/lib/api";

const NAV = [
  { href: "/setup", label: "Setup" },
  { href: "/analysis", label: "Analysis" },
  { href: "/bot", label: "Bot" },
  { href: "/backtest", label: "Backtest" },
  { href: "/history", label: "History" },
];

export default function DashLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, loading } = useAuth();
  useSocket();
  const connected = useBotStore((s) => s.connected);
  if (loading) return <div className="min-h-screen flex items-center justify-center"><div className="text-t3 text-sm">Loading...</div></div>;
  if (!user) { if (typeof window !== "undefined") router.replace("/login"); return null; }
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-50 bg-bg/95 backdrop-blur border-b border-border h-[52px] flex items-center justify-between px-6">
        <div className="flex items-center gap-4">
          <span className="font-bold text-acc text-base">BG-BOT<span className="text-t3 text-xs font-light"> v5</span></span>
          <nav className="flex gap-0.5 bg-bg-3 border border-border rounded-md overflow-hidden">
            {NAV.map((n) => (<Link key={n.href} href={n.href} className={`px-3.5 py-1.5 text-xs font-semibold transition ${pathname === n.href ? "bg-acc/10 text-acc" : "text-t3 hover:text-t2"}`}>{n.label}</Link>))}
          </nav>
        </div>
        <div className="flex items-center gap-3">
          <div className={`w-2 h-2 rounded-full ${connected ? "bg-acc" : "bg-t3"}`} />
          <span className="text-t2 text-xs">{user.email}</span>
          <button onClick={() => api.logout()} className="px-3 py-1 text-xs text-t3 border border-border rounded-md hover:text-red hover:border-red transition">Logout</button>
        </div>
      </header>
      <main className="p-4 md:p-6 max-w-[1520px] mx-auto">{children}</main>
    </div>
  );
}
