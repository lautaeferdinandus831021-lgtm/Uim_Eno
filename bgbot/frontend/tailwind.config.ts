import type { Config } from "tailwindcss";
const config: Config = {content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"], theme: {extend: {colors: {bg: {DEFAULT: "#06080d", 2: "#0c1018", 3: "#111822", 4: "#0a0f18"}, border: "#1a2536", acc: "#00d4aa", red: "#ff4757", blu: "#3b82f6", yel: "#ffc312", org: "#f97316", pur: "#a855f7", t1: "#e8edf5", t2: "#7a8ba8", t3: "#4a5568"}, fontFamily: {sans: ["Inter", "system-ui", "sans-serif"]}}}, plugins: []};
export default config;
