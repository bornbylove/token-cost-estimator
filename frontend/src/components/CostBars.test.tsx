import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { CostBars } from "./CostBars";

const bars = [
  { id: "a", label: "Model A", value: "105.000000", highlighted: true },
  { id: "b", label: "Model B", value: "105.000000", highlighted: true },
  { id: "c", label: "Model C", value: "10500.000000", highlighted: false },
];

describe("CostBars", () => {
  it("renders bars in the given order with accessible labels", () => {
    render(<CostBars bars={bars} measure="Monthly cost" />);

    const rows = screen.getAllByRole("listitem");
    expect(rows.map((r) => r.getAttribute("aria-label"))).toEqual([
      "Model A: $105.00, cheapest",
      "Model B: $105.00, cheapest",
      "Model C: $10,500.00",
    ]);
  });

  it("labels only the cheapest bars, never color alone", () => {
    render(<CostBars bars={bars} measure="Monthly cost" />);

    expect(screen.getAllByText("$105.00 · cheapest")).toHaveLength(2);
    expect(screen.queryByText(/\$10,500\.00/)).not.toBeInTheDocument();
  });

  it("scales bar widths to the top axis tick", () => {
    const { container } = render(<CostBars bars={bars} measure="Monthly cost" />);

    const widths = [...container.querySelectorAll<HTMLElement>(".cost-bars-bar")].map(
      (b) => parseFloat(b.style.width),
    );
    // Ticks run 0..15,000, so $10,500 is 70% of the track and $105 is 0.7%.
    expect(widths[0]).toBeCloseTo(0.7);
    expect(widths[1]).toBeCloseTo(0.7);
    expect(widths[2]).toBeCloseTo(70);
  });

  it("shows a tooltip with the value on hover and keyboard focus", async () => {
    const user = userEvent.setup();
    render(<CostBars bars={bars} measure="Monthly cost" />);

    await user.tab();
    await user.tab();
    await user.tab();
    expect(screen.getByRole("tooltip")).toHaveTextContent("$10,500.00Model C");

    await user.hover(screen.getByText("Model A"));
    expect(screen.getByRole("tooltip")).toHaveTextContent("$105.00Model A");
  });

  it("explains when everything costs nothing", () => {
    render(
      <CostBars
        bars={[{ id: "a", label: "A", value: "0.000000", highlighted: true }]}
        measure="Cost"
      />,
    );

    expect(screen.getByText(/costs \$0.00/)).toBeInTheDocument();
  });
});
