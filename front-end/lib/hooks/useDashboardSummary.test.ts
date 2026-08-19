import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useDashboardSummary } from "./useDashboardSummary";
import * as api from "@/lib/api";
import type { DashboardSummary } from "@/lib/types";

const SUMMARY = { total_images: 12, avg_severity: 1.2 } as unknown as DashboardSummary;

afterEach(() => {
  vi.restoreAllMocks();
});

describe("useDashboardSummary", () => {
  it("fetches on mount and exposes the result", async () => {
    vi.spyOn(api, "getDashboardSummary").mockResolvedValue(SUMMARY);

    const { result } = renderHook(() => useDashboardSummary());
    expect(result.current.loading).toBe(true);

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data).toEqual(SUMMARY);
    expect(result.current.error).toBeNull();
    expect(result.current.lastUpdated).toBeInstanceOf(Date);
  });

  it("surfaces a fetch failure as an error message", async () => {
    vi.spyOn(api, "getDashboardSummary").mockRejectedValue(new Error("network down"));

    const { result } = renderHook(() => useDashboardSummary());
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.error).toBe("network down");
    expect(result.current.data).toBeNull();
  });

  it("refetch triggers a new fetch and flips loading back to true", async () => {
    const spy = vi.spyOn(api, "getDashboardSummary").mockResolvedValue(SUMMARY);
    const { result } = renderHook(() => useDashboardSummary());
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(spy).toHaveBeenCalledTimes(1);
    act(() => result.current.refetch());
    expect(result.current.loading).toBe(true);

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(spy).toHaveBeenCalledTimes(2);
  });
});
