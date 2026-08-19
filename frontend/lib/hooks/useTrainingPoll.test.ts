import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useTrainingPoll } from "./useTrainingPoll";
import * as api from "@/lib/api";
import type { TrainingJobStatus } from "@/lib/types";

function status(overrides: Partial<TrainingJobStatus>): TrainingJobStatus {
  return {
    status: "training",
    progress: 0,
    current_epoch: 0,
    total_epochs: 5,
    current_loss: 0,
    losses: [],
    checkpoint_path: "",
    error: null,
    ...overrides,
  };
}

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("useTrainingPoll", () => {
  it("polls /api/train-status every 800ms after a successful start, and stops on completion", async () => {
    vi.spyOn(api, "startTraining").mockResolvedValue({ success: true, message: "started" });
    const statusSpy = vi
      .spyOn(api, "getTrainingStatus")
      .mockResolvedValueOnce(status({ current_epoch: 1, progress: 0.2 }))
      .mockResolvedValueOnce(status({ current_epoch: 2, progress: 0.4 }))
      .mockResolvedValueOnce(status({ status: "completed", progress: 1 }));

    const onCompleted = vi.fn();
    const { result } = renderHook(() => useTrainingPoll(onCompleted));

    await act(async () => {
      await result.current.start({ epochs: 5, batch_size: 4, learning_rate: 0.005, architecture: "x" });
    });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(800);
    });
    expect(result.current.status?.current_epoch).toBe(1);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(800);
    });
    expect(result.current.status?.current_epoch).toBe(2);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(800);
    });
    expect(result.current.status?.status).toBe("completed");
    expect(onCompleted).toHaveBeenCalledTimes(1);

    const callsAtCompletion = statusSpy.mock.calls.length;
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3200);
    });
    expect(statusSpy.mock.calls.length).toBe(callsAtCompletion);
  });

  it("surfaces a failed start without polling", async () => {
    vi.spyOn(api, "startTraining").mockResolvedValue({ success: false, message: "already training" });
    const statusSpy = vi.spyOn(api, "getTrainingStatus");

    const { result } = renderHook(() => useTrainingPoll());
    await act(async () => {
      await result.current.start({ epochs: 5, batch_size: 4, learning_rate: 0.005, architecture: "x" });
    });

    expect(result.current.startError).toBe("already training");
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });
    expect(statusSpy).not.toHaveBeenCalled();
  });

  it("stops polling on unmount instead of leaking the interval (fix vs. the original)", async () => {
    vi.spyOn(api, "startTraining").mockResolvedValue({ success: true, message: "started" });
    const statusSpy = vi.spyOn(api, "getTrainingStatus").mockResolvedValue(status({ current_epoch: 1 }));

    const { result, unmount } = renderHook(() => useTrainingPoll());
    await act(async () => {
      await result.current.start({ epochs: 5, batch_size: 4, learning_rate: 0.005, architecture: "x" });
    });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(800);
    });
    const callsBeforeUnmount = statusSpy.mock.calls.length;
    expect(callsBeforeUnmount).toBeGreaterThan(0);

    unmount();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(4000);
    });
    expect(statusSpy.mock.calls.length).toBe(callsBeforeUnmount);
  });
});
