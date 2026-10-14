export function Spinner({ label = "Loading", className = "" }: { label?: string; className?: string }) {
  return (
    <svg
      role="status"
      aria-label={label}
      className={`size-4 animate-spin ${className}`}
      viewBox="0 0 16 16"
      fill="none"
    >
      <circle cx="8" cy="8" r="6" stroke="currentColor" strokeOpacity="0.25" strokeWidth="2" />
      <path d="M14 8a6 6 0 00-6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}
