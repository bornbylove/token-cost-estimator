import { screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { fakeApi } from "../test/fakeApi";
import { renderAt } from "../test/render";

describe("PricingPage", () => {
  it("lists prices with long-prompt tiers, sources and staleness", async () => {
    fakeApi();
    renderAt("/prices");

    const table = await screen.findByRole("table");
    const [cheap, big] = within(table).getAllByRole("row").slice(1);
    expect(cheap).toHaveTextContent("$0.50 / $2.50 over 100K input");
    expect(within(cheap!).getByRole("link", { name: "Acme" })).toHaveAttribute(
      "href",
      "https://example.com/pricing",
    );
    expect(big).toHaveTextContent("Same price");
    expect(within(big!).getByText("Out of date")).toBeInTheDocument();
    expect(big).toHaveTextContent("until Nov 30, 2026");
  });

  it("shows a not-found page for unknown routes", () => {
    fakeApi();
    renderAt("/nope");

    expect(screen.getByRole("heading", { name: "Page not found" })).toBeInTheDocument();
  });
});
