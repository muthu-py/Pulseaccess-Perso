import type { MetadataRoute } from "next";

import { PUBLIC_PAGES, SITE_URL } from "@/lib/site";

// Only public marketing pages. The app (/app), member area (/m, /c) and /ui are noindex and left out.
export default function sitemap(): MetadataRoute.Sitemap {
  return PUBLIC_PAGES.map(({ path }) => ({ url: `${SITE_URL}${path === "/" ? "" : path}` }));
}
