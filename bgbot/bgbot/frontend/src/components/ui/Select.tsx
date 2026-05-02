"use client";
import { SelectHTMLAttributes, forwardRef } from "react";

interface Props extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  options: { value: string; label: string }[];
}

export const Select = forwardRef<HTMLSelectElement, Props>(
  ({ label, options, className = "", ...props }, ref) => (
    <div className="space-y-1">
      {label && <label className="text-t2 text-xs font-medium">{label}</label>}
      <select
        ref={ref}
        className={`w-full px-3 py-2 bg-bg-3 border border-border rounded-md text-t1 text-sm focus:outline-none focus:border-acc transition ${className}`}
        {...props}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
    </div>
  )
);
Select.displayName = "Select";
