import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { bodiesFor, fakeApi } from "../test/fakeApi";
import { renderAt } from "../test/render";

describe("ComparePage", () => {
  it("compares all models and marks the cheapest in chart and table", async () => {
    fakeApi();
    renderAt("/compare?in=3k&out=800&day=5000");

    expect(await screen.findByRole("heading", { name: "Monthly cost" })).toBeInTheDocument();
    expect(screen.getByText("$105.00 · cheapest")).toBeInTheDocument();

    const table = screen.getByRole("table");
    const rows = within(table).getAllByRole("row").slice(1);
    // Cells after the row header: provider, per request, per day, per month.
    expect(rows.map((r) => within(r).getAllByRole("cell")[3]?.textContent)).toEqual([
      "$105.00",
      "$10,500.00",
    ]);
    expect(within(rows[0]!).getByText("Cheapest")).toBeInTheDocument();
  });

  it("charts cost per request when there is no daily volume", async () => {
    fakeApi();
    renderAt("/compare");

    expect(
      await screen.findByRole("heading", { name: "Cost per request" }),
    ).toBeInTheDocument();
    expect(screen.queryByText("Per month")).not.toBeInTheDocument();
  });

  it("narrows the comparison when models are unticked", async () => {
    const user = userEvent.setup();
    const api = fakeApi();
    renderAt("/compare");
    await screen.findByRole("heading", { name: "Cost per request" });

    await user.click(screen.getByLabelText("Big model"));

    await waitFor(async () =>
      expect((await bodiesFor(api, "/api/v1/compare")).at(-1)).toMatchObject({
        model_ids: ["cheap-model"],
      }),
    );
  });
});
