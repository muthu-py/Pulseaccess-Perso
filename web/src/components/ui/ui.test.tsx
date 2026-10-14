import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Alert } from "./Alert";
import { Button } from "./Button";
import { StatusBadge } from "./StatusBadge";
import { TextField } from "./TextField";

describe("Button", () => {
  it("blocks clicks and announces busy while loading", async () => {
    const onClick = vi.fn();
    render(<Button loading onClick={onClick}>Save</Button>);

    const button = screen.getByRole("button", { name: /save/i });
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("aria-busy", "true");
    await userEvent.click(button);
    expect(onClick).not.toHaveBeenCalled();
  });

  it("defaults to type=button so it never submits forms by accident", () => {
    render(<Button>Edit</Button>);
    expect(screen.getByRole("button")).toHaveAttribute("type", "button");
  });
});

describe("TextField", () => {
  it("links the label, hint and error to the input", () => {
    render(<TextField label="Phone" hint="With country code" error="Too short" />);

    const input = screen.getByLabelText("Phone");
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(input).toHaveAccessibleDescription("Too short With country code");
  });

  it("is not marked invalid without an error", () => {
    render(<TextField label="Name" />);
    expect(screen.getByLabelText("Name")).not.toHaveAttribute("aria-invalid");
  });
});

describe("StatusBadge", () => {
  it("shows a text label, not just colour", () => {
    render(<StatusBadge kind="connection" value="NEEDS_ATTENTION" />);
    const badge = screen.getByText("Needs attention");
    expect(badge).toHaveAttribute("data-tone", "warning");
  });

  it("accepts a custom label", () => {
    render(<StatusBadge kind="subscription" value="active" label="Active until 13 Nov" />);
    expect(screen.getByText("Active until 13 Nov")).toBeInTheDocument();
  });
});

describe("Alert", () => {
  it("interrupts screen readers only for danger", () => {
    const { rerender } = render(<Alert tone="danger" title="Failed" />);
    expect(screen.getByRole("alert")).toHaveTextContent("Failed");

    rerender(<Alert tone="info" title="Heads up" />);
    expect(screen.getByRole("status")).toHaveTextContent("Heads up");
  });
});
