const inr = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", minimumFractionDigits: 0, maximumFractionDigits: 2 });

/** "499.00" or 49900 paise → "₹499". Keeps paise only when there are some: "₹499.50". */
export function formatRupees(value: string | number, unit: "rupees" | "paise" = "rupees"): string {
  const rupees = unit === "paise" ? Number(value) / 100 : Number(value);
  return inr.format(rupees);
}

export function formatDays(n: number): string {
  return `${n} ${n === 1 ? "day" : "days"}`;
}

const dateFmt = new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short", year: "numeric" });
const dateTimeFmt = new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" });

export const formatDate = (iso: string) => dateFmt.format(new Date(iso));
export const formatDateTime = (iso: string) => dateTimeFmt.format(new Date(iso));
