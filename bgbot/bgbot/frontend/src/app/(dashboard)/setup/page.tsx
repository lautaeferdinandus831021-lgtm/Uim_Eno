"use client";
import { useState, useEffect, Component, ReactNode } from "react";
import { Card, CardHeader } from "@/components/ui/Card";
import { StatCard } from "@/components/ui/StatCard";
import { ApiConfigForm } from "@/components/forms/ApiConfigForm";
import { BotConfigForm } from "@/components/forms/BotConfigForm";
import { api } from "@/lib/api";

class PageBoundary extends Component<{children: ReactNode}, {err: boolean}> {
  constructor(p: any) { super(p); this.state = { err: false }; }
  static getDerivedStateFromError() { return { err: true }; }
  render() {
    if (this.state.err) return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] gap-4">
        <p className="text-red text-sm">Something went wrong.</p>
        <button onClick={() => location.reload()} className="px-4 py-2 bg-bg-3 border border-border rounded-md text-t2 text-sm hover:text-t1">Reload</button>
      </div>
    );
    return this.props.children;
  }
}

function Content() {
  const [user, setUser] = useState<any>(null);
  const [apiStatus, setApiStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let ok = true;
    Promise.all([
      api.me().then((u) => { if (ok) setUser(u); }).catch(() => {}),
      api.testApi().then((s) => { if (ok) setApiStatus(s); }).catch(() => { if (ok) setApiStatus({ok:false}); }),
    ]).finally(() => { if (ok) setLoading(false); });
    return () => { ok = false; };
  }, []);

  if (loading) return <div className="flex items-center justify-center min-h-[50vh]"><div className="text-t3 text-sm">Loading...</div></div>;

  return (
    <div className="space-y-6 animate-in">
      <h1 className="text-xl font-bold text-t1">Setup</h1>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard label="Account" value={user?.email || "..."} sub={user?.provider} />
        <StatCard label="API" value={apiStatus?.ok ? "Connected" : "Not Set"} color={apiStatus?.ok ? "text-acc" : "text-red"} />
        <StatCard label="Balance" value={apiStatus?.balance != null ? "$" + Number(apiStatus.balance).toFixed(2) : "$0.00"} />
        <StatCard label="Mode" value={apiStatus?.ok ? "Live" : "Simulation"} color={apiStatus?.ok ? "text-acc" : "text-yel"} />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader title="API Configuration" subtitle="Connect your Bitget exchange account" />
          <ApiConfigForm onSaved={() => api.testApi().then(setApiStatus).catch(() => {})} />
        </Card>
        <Card>
          <CardHeader title="Bot Configuration" subtitle="Trading parameters and strategy settings" />
          <BotConfigForm />
        </Card>
      </div>
    </div>
  );
}

export default function SetupPage() {
  return <PageBoundary><Content /></PageBoundary>;
}
