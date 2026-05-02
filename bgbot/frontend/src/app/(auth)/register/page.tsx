"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const [form, setForm] = useState({email: "", password: "", confirm: ""});
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault(); setError(""); setLoading(true);
    try { await api.register(form.email, form.password, form.confirm); router.push("/login"); }
    catch (err: any) { setError(err.message); }
    finally { setLoading(false); }
  };
  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <h1 className="text-2xl font-bold text-t1 mb-1">Create Account</h1>
        <p className="text-t3 text-sm mb-8">Get started with BG-BOT</p>
        {error && <div className="bg-red/10 border border-red/30 text-red text-sm rounded-md px-4 py-2 mb-4">{error}</div>}
        <form onSubmit={handleSubmit} className="space-y-4">
          <input type="email" placeholder="Email" value={form.email} onChange={(e) => setForm({...form, email: e.target.value})} className="w-full px-4 py-2.5 bg-bg-3 border border-border rounded-md text-t1 text-sm focus:outline-none focus:border-acc" required />
          <input type="password" placeholder="Password (min 6)" value={form.password} onChange={(e) => setForm({...form, password: e.target.value})} className="w-full px-4 py-2.5 bg-bg-3 border border-border rounded-md text-t1 text-sm focus:outline-none focus:border-acc" required />
          <input type="password" placeholder="Confirm" value={form.confirm} onChange={(e) => setForm({...form, confirm: e.target.value})} className="w-full px-4 py-2.5 bg-bg-3 border border-border rounded-md text-t1 text-sm focus:outline-none focus:border-acc" required />
          <button type="submit" disabled={loading} className="w-full py-2.5 bg-acc text-bg font-semibold text-sm rounded-md hover:opacity-90 transition disabled:opacity-50">{loading ? "Creating..." : "Create Account"}</button>
        </form>
        <p className="text-t3 text-xs mt-6 text-center">Have account? <a href="/login" className="text-acc hover:underline">Sign in</a></p>
      </div>
    </div>
  );
}
