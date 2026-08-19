import { describe, expect, it } from "vitest";
import { computeEqualizerDots, computeMicroBars, severityLevel } from "./equalizer";

describe("computeEqualizerDots", () => {
  it("fills red slots for potholes and teal slots for cracks", () => {
    const dots = computeEqualizerDots(2, 7);
    const redCount = dots.filter((d) => d === "red").length;
    const tealCount = dots.filter((d) => d === "teal").length;
    expect(redCount).toBe(6); // min(80, 2*3)
    expect(tealCount).toBe(14); // min(80-6, 7*2)
  });

  it("never exceeds the 80-slot grid even with huge counts", () => {
    const dots = computeEqualizerDots(1000, 1000);
    expect(dots).toHaveLength(80);
    expect(dots.filter((d) => d === "red")).toHaveLength(80);
    expect(dots.filter((d) => d === "teal")).toHaveLength(0);
  });

  it("returns all-empty for zero counts", () => {
    const dots = computeEqualizerDots(0, 0);
    expect(dots.every((d) => d === "empty")).toBe(true);
  });
});

describe("computeMicroBars", () => {
  it("computes percentage height relative to the max class count", () => {
    const bars = computeMicroBars({ D00: 3, D10: 3, D20: 1, D40: 2 });
    const d00 = bars.find((b) => b.code === "D00")!;
    expect(d00.value).toBe(3);
    expect(d00.pct).toBe(90); // max class, so 90% (round(3/3*90))
  });

  it("floors the bar height at 15% so zero-count classes stay visible", () => {
    const bars = computeMicroBars({ D00: 10 });
    const d40 = bars.find((b) => b.code === "D40")!;
    expect(d40.value).toBe(0);
    expect(d40.pct).toBe(15);
  });

  it("handles a fully empty distribution without dividing by zero", () => {
    const bars = computeMicroBars({});
    expect(bars.every((b) => b.value === 0 && b.pct === 15)).toBe(true);
  });
});

describe("severityLevel", () => {
  it("classifies low/medium/high at the documented thresholds", () => {
    expect(severityLevel(0)).toBe("low");
    expect(severityLevel(1.49)).toBe("low");
    expect(severityLevel(1.5)).toBe("medium");
    expect(severityLevel(2.49)).toBe("medium");
    expect(severityLevel(2.5)).toBe("high");
    expect(severityLevel(5)).toBe("high");
  });
});
