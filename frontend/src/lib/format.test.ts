import { describe, expect, it } from "vitest";

import { formatCompact, formatUsd, niceTicks, parseCount } from "./format";

describe("parseCount", () => {
  it.each([
    ["3000", 3000],
    ["3,000", 3000],
    ["3_000", 3000],
    ["3k", 3000],
    ["3K", 3000],
    ["1.5M", 1_500_000],
    ["1.1k", 1100],
    [" 0 ", 0],
  ])("parses %j", (text, expected) => {
    expect(parseCount(text)).toBe(expected);
  });

  it.each(["", "abc", "1.5", "-1", "1.0001k", "1e3", "Infinity"])("rejects %j", (text) => {
    expect(parseCount(text)).toBeNull();
  });
});

describe("formatUsd", () => {
  it.each([
    ["0.000000", "$0.00"],
    ["0.000700", "$0.0007"],
    ["0.014000", "$0.014"],
    ["105.000000", "$105.00"],
    ["10500.000000", "$10,500.00"],
    ["1.600016", "$1.600016"],
    ["1440000000000000.000000", "$1,440,000,000,000,000.00"],
  ])("formats %s as %s", (amount, expected) => {
    expect(formatUsd(amount)).toBe(expected);
  });
});

describe("formatCompact", () => {
  it.each([
    [100_000, "100K"],
    [272_000, "272K"],
    [1_500_000, "1.5M"],
    [1_234, "1,234"],
  ])("formats %d", (value, expected) => {
    expect(formatCompact(value)).toBe(expected);
  });
});

describe("niceTicks", () => {
  it("covers the max with round steps", () => {
    expect(niceTicks(10_500)).toEqual([0, 5000, 10000, 15000]);
    expect(niceTicks(0.07)).toEqual([0, 0.02, 0.04, 0.06, 0.08]);
    expect(niceTicks(100)).toEqual([0, 50, 100]);
  });

  it("handles zero", () => {
    expect(niceTicks(0)).toEqual([0]);
  });
});
