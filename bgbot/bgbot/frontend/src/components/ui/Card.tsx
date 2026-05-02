"use client";
import { ReactNode } from "react";

interface Props {
  children: ReactNode;
  className?: string;
  padding?: "none" | "sm" | "md" | "lg";
  hover?: boolean;
}

const paddings = { none: "", sm: "p-3", md: "p-4", lg: "p-6" };

export function Card({ children, className = "", padding = "md", hover = false }: Props) {
  return (
    <div className={`bg-bg-2 border border-border rounded-lg ${paddings[padding]} ${hover ? "hover:border-t3 transition-colors" : ""} ${className}`}>
      {children}
    </div>
  );
}

export function CardHeader({ title, subtitle, action }: { title: string; subtitle?: string; action?: ReactNode }) {
  return (
    <div className="flex items-center justify-between mb-4">
      <div>
        <h3 className="text-t1 font-semibold text-sm">{title}</h3>
        {subtitle && <p className="text-t3 text-xs mt-0.5">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}
