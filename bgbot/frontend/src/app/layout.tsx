import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = { title: "BG-BOT v5", description: "Trading Engine" };
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (<html lang="id"><body className="bg-bg antialiased">{children}</body></html>);
}
