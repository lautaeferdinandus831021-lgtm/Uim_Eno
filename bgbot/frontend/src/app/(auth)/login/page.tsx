"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault(); setError(""); setLoading(true);
    try { await login(email, password); router.push("/setup"); }
    catch (err: any) { setError(err.message); }
    finally { setLoading(false); }
  };
  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <h1 className="text-2xl font-bold text-t1 mb-1">BG-BOT <span className="text-acc">v5</span></h1>
        <p className="text-t3 text-sm mb-8">Sign in to continue</p>
        {error && <div className="bg-red/10 border border-red/30 text-red text-sm rounded-md px-4 py-2 mb-4">{error}</div>}
        <form onSubmit={handleSubmit} className="space-y-4">
          <input type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} className="w-full px-4 py-2.5 bg-bg-3 border border-border rounded-md text-t1 text-sm focus:outline-none focus:border-acc" required />
          <input type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} className="w-full px-4 py-2.5 bg-bg-3 border border-border rounded-md text-t1 text-sm focus:outline-none focus:border-acc" required />
          <button type="submit" disabled={loading} className="w-full py-2.5 bg-acc text-bg font-semibold text-sm rounded-md hover:opacity-90 transition disabled:opacity-50">{loading ? "Signing in..." : "Sign In"}</button>
        </form>
        <p className="text-t3 text-xs mt-6 text-center">No account? <a href="/register" className="text-acc hover:underline">Register</a></p>
      </div>
    </div>
  );
}
