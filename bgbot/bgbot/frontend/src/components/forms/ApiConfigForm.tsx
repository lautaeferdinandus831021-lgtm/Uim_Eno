"use client";
import { useState, useEffect } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { api } from "@/lib/api";

interface Props { onSaved?: () => void; }

export function ApiConfigForm({ onSaved }: Props) {
  const [form, setForm] = useState({ api_key: "", api_secret: "", api_passphrase: "", demo: true });
  const [loading, setLoading] = useState(false);
  const [testing, setTesting] = useState(false);
  const [result, setResult] = useState<{ok:boolean;msg?:string}|null>(null);

  useEffect(() => {
    api.getConfig().then((cfg: any) => {
      if (cfg) setForm({ api_key: cfg.api_key || "", api_secret: cfg.api_secret || "", api_passphrase: cfg.api_passphrase || "", demo: cfg.demo !== false });
    }).catch(() => {});
  }, []);

  const handleSave = async () => {
    setLoading(true);
    try { await api.saveApi(form); setResult({ok:true,msg:"Saved!"}); onSaved?.(); }
    catch(e:any) { setResult({ok:false,msg:e.message}); }
    setLoading(false);
  };

  const handleTest = async () => {
    setTesting(true);
    try { const r = await api.testApi(); setResult(r); }
    catch(e:any) { setResult({ok:false,msg:e.message}); }
    setTesting(false);
  };

  return (
    <div className="space-y-4">
      <Input label="API Key" value={form.api_key} onChange={(e) => setForm({...form, api_key: e.target.value})} placeholder="Your Bitget API Key" />
      <Input label="API Secret" type="password" value={form.api_secret} onChange={(e) => setForm({...form, api_secret: e.target.value})} placeholder="Your API Secret" />
      <Input label="API Passphrase" type="password" value={form.api_passphrase} onChange={(e) => setForm({...form, api_passphrase: e.target.value})} placeholder="Your Passphrase" />
      <label className="flex items-center gap-2 text-sm text-t2 cursor-pointer">
        <input type="checkbox" checked={form.demo} onChange={(e) => setForm({...form, demo: e.target.checked})} className="rounded" />
        Demo Trading
      </label>
      {result && (
        <div className={`text-xs rounded-md px-3 py-2 ${result.ok ? "bg-acc/10 border border-acc/30 text-acc" : "bg-red/10 border border-red/30 text-red"}`}>
          {result.msg}
        </div>
      )}
      <div className="flex gap-2">
        <Button onClick={handleSave} loading={loading} size="sm">Save API</Button>
        <Button onClick={handleTest} loading={testing} variant="secondary" size="sm">Test Connection</Button>
      </div>
    </div>
  );
}
