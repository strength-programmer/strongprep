import { describe, expect, it } from "vitest";
import { errorLines, fmtDate, kg, numOrNull, ratioText } from "./format";

describe("format helpers", () => {
  it("formats loads with explicit per-hand labelling", () => {
    expect(kg(80, true)).toBe("80 kg per hand");
    expect(kg(72.5)).toBe("72.5 kg");
    expect(kg(null)).toBe("—");
  });

  it("keeps missing numbers missing rather than 0", () => {
    expect(numOrNull("")).toBeNull();
    expect(numOrNull("  ")).toBeNull();
    expect(numOrNull("0")).toBe(0);
    expect(numOrNull("abc")).toBeNull();
    expect(ratioText(null)).toBe("—");
    expect(ratioText(1.125)).toBe("1.13");
  });

  it("flattens the three FastAPI error shapes", () => {
    expect(errorLines("nope")).toEqual(["nope"]);
    expect(errorLines({ message: "Failed", errors: ["a", "b"] })).toEqual(["Failed", "a", "b"]);
    expect(errorLines([{ loc: ["body", "age"], msg: "too small" }])).toEqual(["age: too small"]);
  });

  it("formats ISO dates without timezone shifting", () => {
    expect(fmtDate("2026-01-05")).toContain("5");
    expect(fmtDate(null)).toBe("—");
  });
});
