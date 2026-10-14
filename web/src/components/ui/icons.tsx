import type { ReactNode, SVGProps } from "react";

import type { StatusIcon } from "@/lib/status";

const base: SVGProps<SVGSVGElement> = {
  width: 14,
  height: 14,
  viewBox: "0 0 16 16",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.75,
  strokeLinecap: "round",
  strokeLinejoin: "round",
  "aria-hidden": true,
  focusable: false,
};

const paths: Record<StatusIcon | "info", ReactNode> = {
  check: <path d="M3.5 8.5l3 3 6-7" />,
  alert: (
    <>
      <path d="M8 2.5l6 11H2l6-11z" />
      <path d="M8 6.5v3" />
      <path d="M8 11.75v.01" />
    </>
  ),
  clock: (
    <>
      <circle cx="8" cy="8" r="5.75" />
      <path d="M8 5v3.25l2 1.25" />
    </>
  ),
  x: (
    <>
      <circle cx="8" cy="8" r="5.75" />
      <path d="M6 6l4 4M10 6l-4 4" />
    </>
  ),
  info: (
    <>
      <circle cx="8" cy="8" r="5.75" />
      <path d="M8 7.25v3.5" />
      <path d="M8 5.25v.01" />
    </>
  ),
  dot: <circle cx="8" cy="8" r="2.5" fill="currentColor" stroke="none" />,
};

export function Icon({ name, ...props }: { name: StatusIcon | "info" } & SVGProps<SVGSVGElement>) {
  return (
    <svg {...base} {...props}>
      {paths[name]}
    </svg>
  );
}
