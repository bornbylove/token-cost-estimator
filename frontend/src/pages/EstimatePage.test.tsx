import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { bodiesFor, fakeApi } from "../test/fakeApi";
import { renderAt } from "../test/render";

describe("EstimatePage", () => {
  it("estimates the first model with default usage", async () => {
    const api = fakeApi();
    renderAt("/");

    expect(await screen.findByText("$0.0007", { selector: ".hero-value" })).toBeInTheDocument();
    expect(screen.getByText("Per request", { selector: ".hero-label" })).toBeInTheDocument();
    expect(await bodiesFor(api, "/api/v1/estimate")).toEqual([
      {
        model_id: "cheap-model",
        input_tokens: 3000,
        output_tokens: 800,
        requests_per_day: null,
      },
    ]);
  });

  it("reads usage and model from the URL and shows the monthly projection", async () => {
    fakeApi();
    renderAt("/?model=big-model&in=3k&out=800&day=5k");

    expect(await screen.findByText("$10,500.00", { selector: ".hero-value" })).toBeInTheDocument();
    expect(screen.getByText("Per month")).toBeInTheDocument();
    expect(screen.getByText(/\$350.00 per day/)).toBeInTheDocument();
  });

  it("warns about stale prices and shows notes", async () => {
    fakeApi();
    renderAt("/?model=big-model");

    expect(await screen.findByText(/Prices may be out of date/)).toBeInTheDocument();
    expect(screen.getByText(/Price rises on 2026-12-01/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Globex pricing" })).toHaveAttribute(
      "href",
      "https://example.org/pricing",
    );
  });

  it("flags invalid input inline and does not call the API", async () => {
    const user = userEvent.setup();
    const api = fakeApi();
    renderAt("/");
    await screen.findByText("$0.0007", { selector: ".hero-value" });

    const input = screen.getByLabelText("Input tokens");
    await user.clear(input);
    await user.type(input, "lots");

    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByText(/Enter a whole number/)).toBeInTheDocument();
    expect(screen.getByText(/Fix the highlighted fields/)).toBeInTheDocument();
    expect(await bodiesFor(api, "/api/v1/estimate")).toHaveLength(1);
  });

  it("explains long-prompt pricing", async () => {
    fakeApi();
    renderAt("/?in=200k");

    expect(await screen.findByText(/Long-prompt pricing applies/)).toBeInTheDocument();
    expect(screen.getByText(/more than 100K input tokens/)).toBeInTheDocument();
  });

  it("counts tokens from pasted text and uses them as input", async () => {
    const user = userEvent.setup();
    const api = fakeApi();
    renderAt("/");
    await screen.findByText("$0.0007", { selector: ".hero-value" });

    await user.click(screen.getByText(/Paste your prompt/));
    await user.type(screen.getByLabelText("Prompt text"), "Hello world");
    await user.click(screen.getByRole("button", { name: /Count and use/ }));

    await waitFor(() => expect(screen.getByLabelText("Input tokens")).toHaveValue("1234"));
    expect(screen.getByText(/≈ 1,234 tokens/)).toBeInTheDocument();
    await waitFor(async () =>
      expect((await bodiesFor(api, "/api/v1/estimate")).at(-1)).toMatchObject({
        input_tokens: 1234,
      }),
    );
  });

  it("shows API errors", async () => {
    fakeApi({
      "POST /api/v1/estimate": () => ({
        status: 429,
        json: { error: { code: "rate_limited", message: "Too many requests." } },
      }),
    });
    renderAt("/");

    expect(await screen.findByText("Too many requests.")).toBeInTheDocument();
  });

  it("shows a friendly message when the server is unreachable", async () => {
    fakeApi({
      "GET /api/v1/models": () => {
        throw new TypeError("Failed to fetch");
      },
    });
    renderAt("/");

    expect(await screen.findByText(/Can't reach the server/)).toBeInTheDocument();
  });
});
