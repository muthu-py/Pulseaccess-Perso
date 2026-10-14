/** Public site settings. Everything here comes from env so nothing is invented in the code. */
export const SITE_URL = (process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000").replace(/\/$/, "");

export const SITE_NAME = "PulseAccess";

export const PUBLIC_PAGES = [
  { path: "/", label: "Home" },
  { path: "/how-it-works", label: "How it works" },
  { path: "/telegram-bot", label: "The Telegram bot" },
  { path: "/faq", label: "FAQ" },
  { path: "/privacy", label: "Privacy" },
  { path: "/terms", label: "Terms" },
  { path: "/contact", label: "Contact" },
] as const;
