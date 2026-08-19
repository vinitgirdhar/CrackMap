import { afterEach, describe, expect, it, vi } from "vitest";
import {
  detectFromFile,
  detectFromSample,
  getDashboardSummary,
  getDatasetStats,
  getGisData,
  getSamples,
  getSystemInfo,
  sampleImageUrl,
  startTraining,
  uploadPotholeImages,
} from "./api";

function mockFetchOnce(body: unknown, ok = true) {
  const fetchMock = vi.fn().mockResolvedValue({
    ok,
    status: ok ? 200 : 500,
    json: async () => body,
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("GET wrappers", () => {
  it("getDashboardSummary calls the right path and returns parsed JSON", async () => {
    const fetchMock = mockFetchOnce({ total_images: 12 });
    const result = await getDashboardSummary();
    expect(fetchMock).toHaveBeenCalledWith("/api/dashboard-summary");
    expect(result).toEqual({ total_images: 12 });
  });

  it("getSystemInfo hits /api/system-info", async () => {
    const fetchMock = mockFetchOnce({ status: "online" });
    await getSystemInfo();
    expect(fetchMock).toHaveBeenCalledWith("/api/system-info");
  });

  it("getSamples hits /api/samples", async () => {
    const fetchMock = mockFetchOnce({ samples: ["a.jpg"] });
    await getSamples();
    expect(fetchMock).toHaveBeenCalledWith("/api/samples");
  });

  it("getGisData hits /api/gis-data", async () => {
    const fetchMock = mockFetchOnce([]);
    await getGisData();
    expect(fetchMock).toHaveBeenCalledWith("/api/gis-data");
  });

  it("getDatasetStats hits /api/dataset-stats", async () => {
    const fetchMock = mockFetchOnce({ total_images: 0 });
    await getDatasetStats();
    expect(fetchMock).toHaveBeenCalledWith("/api/dataset-stats");
  });

  it("throws on a non-ok response instead of resolving with an error body", async () => {
    mockFetchOnce({ detail: "nope" }, false);
    await expect(getDashboardSummary()).rejects.toThrow("/api/dashboard-summary failed: 500");
  });

  it("sampleImageUrl builds the per-sample path and encodes the name", () => {
    expect(sampleImageUrl("sample 01.jpg")).toBe("/api/sample/sample%2001.jpg");
  });
});

describe("POST wrappers", () => {
  it("detectFromSample posts multipart form data with sample_name + conf_threshold", async () => {
    const fetchMock = mockFetchOnce({ success: true });
    await detectFromSample("sample_001.jpg", 0.3);

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/detect");
    expect(init.method).toBe("POST");
    const body = init.body as FormData;
    expect(body.get("sample_name")).toBe("sample_001.jpg");
    expect(body.get("conf_threshold")).toBe("0.3");
  });

  it("detectFromFile posts multipart form data with the file + conf_threshold", async () => {
    const fetchMock = mockFetchOnce({ success: true });
    const file = new File(["x"], "road.jpg", { type: "image/jpeg" });
    await detectFromFile(file, 0.25);

    const [, init] = fetchMock.mock.calls[0];
    const body = init.body as FormData;
    expect(body.get("file")).toBe(file);
    expect(body.get("conf_threshold")).toBe("0.25");
  });

  it("uploadPotholeImages appends every file under the same 'files' field", async () => {
    const fetchMock = mockFetchOnce({ success: true, items: [] });
    const files = [
      new File(["a"], "a.jpg", { type: "image/jpeg" }),
      new File(["b"], "b.jpg", { type: "image/jpeg" }),
    ];
    await uploadPotholeImages(files);

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/upload-pothole-images");
    const body = init.body as FormData;
    expect(body.getAll("files")).toEqual(files);
  });

  it("startTraining sends every hyperparameter as a string form field", async () => {
    const fetchMock = mockFetchOnce({ success: true });
    await startTraining({ epochs: 5, batch_size: 4, learning_rate: 0.005, architecture: "fasterrcnn_mobilenet" });

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/train-model");
    const body = init.body as FormData;
    expect(body.get("epochs")).toBe("5");
    expect(body.get("batch_size")).toBe("4");
    expect(body.get("learning_rate")).toBe("0.005");
    expect(body.get("architecture")).toBe("fasterrcnn_mobilenet");
  });
});
