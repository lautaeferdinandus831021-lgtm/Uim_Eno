"use client";
import { useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { api } from "@/lib/api";

export default function ResetPage() {
  const router = useRouter();
  const params = useParams();
  const token = params.token as string;
  const [form, setForm] = useState({password: "", confirm: ""});
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault(); setError(""); setLoading(true);
    try { await api.reset(token, form.password, form.confirm); router.push("/login"); }
    catch (err: any) { setError(err.message); }
    finally { setLoading(false); }
  };
  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <h1 className="text-2xl font-bold text-t1 mb-1">New Password</h1>
        {error && <div className="bg-red/10 border border-red/30 text-red text-sm rounded-md px-4 py-2 mb-4">{error}</div>}
        <form onSubmit={handleSubmit} className="space-y-4">
          <input type="password" placeholder="New password" value={form.password} onChange={(e) => setForm({...form, password: e.target.value})} className="w-full px-4 py-2.5 bg-bg-3 border border-border rounded-md text-t1 text-sm focus:outline-none focus:border-acc" required />
          <input type="password" placeholder="Confirm" value={form.confirm} onChange={(e) => setForm({...form, confirm: e.target.value})} className="w-full px-4 py-2.5 bg-bg-3 border border-border rounded-md text-t1 text-sm focus:outline-none focus:border-acc" required />
          <button type="submit" disabled={loading} className="w-full py-2.5 bg-acc text-bg font-semibold text-sm rounded-md hover:opacity-90 transition disabled:opacity-50">{loading ? "Resetting..." : "Reset Password"}</button>
        </form>
      </div>
    </div>
  );
}
