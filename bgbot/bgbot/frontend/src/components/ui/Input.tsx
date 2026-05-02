"use client";
import { InputHTMLAttributes, forwardRef } from "react";

interface Props extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const Input = forwardRef<HTMLInputElement, Props>(
  ({ label, error, className = "", ...props }, ref) => (
    <div className="space-y-1">
      {label && <label className="text-t2 text-xs font-medium">{label}</label>}
      <input
        ref={ref}
        className={`w-full px-3 py-2 bg-bg-3 border rounded-md text-t1 text-sm placeholder:text-t3 focus:outline-none focus:border-acc transition ${error ? "border-red" : "border-border"} ${className}`}
        {...props}
      />
      {error && <p className="text-red text-xs">{error}</p>}
    </div>
  )
);
Input.displayName = "Input";
