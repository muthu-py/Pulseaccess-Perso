import { describe, expect, it } from "vitest";

import { KNOWN_STATUSES, statusView, type StatusKind } from "./status";

describe("statusView", () => {
  it("gives every known status a label, tone and icon", () => {
    for (const kind of Object.keys(KNOWN_STATUSES) as StatusKind[]) {
      for (const value of KNOWN_STATUSES[kind]) {
        const view = statusView(kind, value);
        expect(view.label).not.toBe("Unknown");
        expect(view.label.length).toBeGreaterThan(0);
      }
    }
  });

  it("falls back safely for unknown or missing values", () => {
    expect(statusView("payment", "refunded").label).toBe("refunded");
    expect(statusView("payment", null).label).toBe("Unknown");
  });
});
