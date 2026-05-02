"use client";
import { useState } from "react";
import { api } from "@/lib/api";

export default function ForgotPage() {
  const [email, setEmail] = useState("");
  const [msg, setMsg] = useState("");
  const [loading, setLoading] = useState(false);
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault(); setLoading(true);
    try { const d = await api.forgot(email); setMsg(d.message); }
    catch (err: any) { setMsg(err.message); }
    finally { setLoading(false); }
  };
  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <h1 className="text-2xl font-bold text-t1 mb-1">Reset Password</h1>
        <p className="text-t3 text-sm mb-8">Enter email for reset link</p>
        {msg && <div className="bg-acc/10 border border-acc/30 text-acc text-sm rounded-md px-4 py-2 mb-4">{msg}</div>}
        <form onSubmit={handleSubmit} className="space-y-4">
          <input type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} className="w-full px-4 py-2.5 bg-bg-3 border border-border rounded-md text-t1 text-sm focus:outline-none focus:border-acc" required />
          <button type="submit" disabled={loading} className="w-full py-2.5 bg-acc text-bg font-semibold text-sm rounded-md hover:opacity-90 transition disabled:opacity-50">{loading ? "Sending..." : "Send Reset Link"}</button>
        </form>
        <p className="text-t3 text-xs mt-6 text-center"><a href="/login" className="text-acc hover:underline">Back to sign in</a></p>
      </div>
    </div>
  );
}
