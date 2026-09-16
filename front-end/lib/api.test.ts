import { afterEach, describe, expect, it, vi } from "vitest";
import {
  detectFromFile,
  detectFromSample,
  getDashboardSummary,
  getDatasetStats,
  getMapPoints,
  getSamples,
  getSystemInfo,
  sampleImageUrl,
  startTraining,
  uploadPotholeImages,
  logInspection,
  getInspections,
  getContractors,
  getPortals,
  getPipelineStats,
  getPipelineEvents,
  getCases,
  getCase,
  createCase,
  submitCase,
  tenderCase,
  awardCase,
  verifyCase,
  closeCase,
  dossierUrl,
  certificateUrl,
  caseJsonUrl,
  caseCsvUrl,
  reverseGeocode,
  searchPlaces,
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

  it("getMapPoints hits /api/gis-data", async () => {
    const fetchMock = mockFetchOnce([]);
    await getMapPoints();
    expect(fetchMock).toHaveBeenCalledWith("/api/gis-data");
  });

  it("getDatasetStats hits /api/dataset-stats", async () => {
    const fetchMock = mockFetchOnce({ total_images: 0 });
    await getDatasetStats();
    expect(fetchMock).toHaveBeenCalledWith("/api/dataset-stats");
  });

  it("throws on a non-ok response, surfacing the API's own detail", async () => {
    mockFetchOnce({ detail: "nope" }, false);
    await expect(getDashboardSummary()).rejects.toThrow("nope");
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

describe("Civic pipeline wrappers", () => {
  it("logInspection posts JSON to /api/inspections", async () => {
    const fetchMock = mockFetchOnce({ id: 1 });
    await logInspection({
      filename: "a.jpg",
      road_name: "MG Road",
      lat: 1,
      lon: 2,
      total_defects: 1,
      severity_score: 3,
      composite_damage_score: 50,
      boxes: [],
      annotated_image: "data:image/jpeg;base64,x",
    });
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/inspections");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body).road_name).toBe("MG Road");
  });

  it("getInspections hits /api/inspections", async () => {
    const fetchMock = mockFetchOnce([]);
    await getInspections();
    expect(fetchMock).toHaveBeenCalledWith("/api/inspections");
  });

  it("getContractors hits /api/contractors", async () => {
    const fetchMock = mockFetchOnce([]);
    await getContractors();
    expect(fetchMock).toHaveBeenCalledWith("/api/contractors");
  });

  it("getPortals hits /api/civic/portals", async () => {
    const fetchMock = mockFetchOnce([]);
    await getPortals();
    expect(fetchMock).toHaveBeenCalledWith("/api/civic/portals");
  });

  it("getPipelineStats hits /api/civic/stats", async () => {
    const fetchMock = mockFetchOnce({ total_cases: 0 });
    await getPipelineStats();
    expect(fetchMock).toHaveBeenCalledWith("/api/civic/stats");
  });

  it("getPipelineEvents passes the limit through", async () => {
    const fetchMock = mockFetchOnce([]);
    await getPipelineEvents(25);
    expect(fetchMock).toHaveBeenCalledWith("/api/civic/events?limit=25");
  });

  it("getCases hits /api/civic/cases", async () => {
    const fetchMock = mockFetchOnce([]);
    await getCases();
    expect(fetchMock).toHaveBeenCalledWith("/api/civic/cases");
  });

  it("getCase hits the per-case path", async () => {
    const fetchMock = mockFetchOnce({ id: 4 });
    await getCase(4);
    expect(fetchMock).toHaveBeenCalledWith("/api/civic/cases/4");
  });

  it("createCase posts inspection_ids", async () => {
    const fetchMock = mockFetchOnce({ id: 1 });
    await createCase([1, 2]);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/civic/cases");
    expect(JSON.parse(init.body)).toEqual({ inspection_ids: [1, 2] });
  });

  it("submitCase posts to the submit action", async () => {
    const fetchMock = mockFetchOnce({ status: "SUBMITTED" });
    await submitCase(7);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/civic/cases/7/submit");
    expect(init.method).toBe("POST");
  });

  it("tenderCase posts to the tender action", async () => {
    const fetchMock = mockFetchOnce({ status: "TENDERED" });
    await tenderCase(7);
    expect(fetchMock.mock.calls[0][0]).toBe("/api/civic/cases/7/tender");
  });

  it("awardCase posts the chosen contractor", async () => {
    const fetchMock = mockFetchOnce({ status: "WORK_ORDERED" });
    await awardCase(7, 3);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/civic/cases/7/award");
    expect(JSON.parse(init.body)).toEqual({ contractor_id: 3 });
  });

  it("verifyCase uploads the after-photo as multipart", async () => {
    const fetchMock = mockFetchOnce({ status: "VERIFIED" });
    const file = new File(["after"], "after.jpg", { type: "image/jpeg" });
    await verifyCase(7, file);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/civic/cases/7/verify");
    expect(init.method).toBe("POST");
    expect((init.body as FormData).get("file")).toBe(file);
  });

  it("closeCase posts to the close action", async () => {
    const fetchMock = mockFetchOnce({ status: "CLOSED" });
    await closeCase(7);
    expect(fetchMock.mock.calls[0][0]).toBe("/api/civic/cases/7/close");
  });

  it("builds every deliverable url from the case id", () => {
    expect(dossierUrl(7)).toBe("/api/civic/cases/7/dossier.pdf");
    expect(certificateUrl(7)).toBe("/api/civic/cases/7/certificate.pdf");
    expect(caseJsonUrl(7)).toBe("/api/civic/cases/7/export.json");
    expect(caseCsvUrl(7)).toBe("/api/civic/cases/7/export.csv");
  });
});

describe("Geocoding wrappers", () => {
  it("reverseGeocode passes the coordinate through", async () => {
    const fetchMock = mockFetchOnce({ road_name: "Hill Road" });
    await reverseGeocode(19.0596, 72.8295);
    expect(fetchMock).toHaveBeenCalledWith("/api/geocode/reverse?lat=19.0596&lon=72.8295");
  });

  it("searchPlaces url-encodes the query", async () => {
    const fetchMock = mockFetchOnce([]);
    await searchPlaces("MG Road, Pune", 3);
    expect(fetchMock).toHaveBeenCalledWith("/api/geocode/search?q=MG%20Road%2C%20Pune&limit=3");
  });
});

describe("error surfacing", () => {
  it("raises the FastAPI detail string instead of a bare status", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 400,
        json: async () => ({ detail: "Contractor 9 did not bid on case 4" }),
      })
    );
    await expect(awardCase(4, 9)).rejects.toThrow("Contractor 9 did not bid on case 4");
  });

  it("falls back to the status code when the body is not JSON", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 502,
        json: async () => {
          throw new Error("not json");
        },
      })
    );
    await expect(getCases()).rejects.toThrow("502");
  });
});
