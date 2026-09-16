import type {
  DashboardSummary,
  SystemInfo,
  SamplesList,
  DetectionResult,
  UploadPotholeImagesResult,
  TrainingJobStatus,
  StartTrainingResult,
  StartTrainingParams,
  DatasetStats,
  GeocodeResult,
  Inspection,
  InspectionCreateParams,
  Contractor,
  Portal,
  Stage,
  CaseView,
  PipelineEvent,
  PipelineStats,
  MapPoint,
} from "./types";


/**
 * FastAPI reports problems as `{ detail: "..." }`. Surfacing that instead of a
 * bare status code is the difference between "award failed: 400" and
 * "Contractor 9 did not bid on case 4" in the UI.
 */
export async function describeFailure(res: Response, action: string): Promise<string> {
  try {
    const body = await res.json();
    const detail = (body as { detail?: unknown }).detail;
    if (typeof detail === "string" && detail) return detail;
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0] as { msg?: string };
      if (first?.msg) return `${action} failed: ${first.msg}`;
    }
  } catch {
    // Non-JSON error body (proxy error page, network reset) — fall through.
  }
  return `${action} failed: ${res.status}`;
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(await describeFailure(res, path));
  }
  return res.json() as Promise<T>;
}

async function postAction<T>(path: string): Promise<T> {
  const res = await fetch(path, { method: "POST" });
  if (!res.ok) {
    throw new Error(await describeFailure(res, path));
  }
  return res.json() as Promise<T>;
}

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(path);
  if (!res.ok) {
    throw new Error(await describeFailure(res, path));
  }
  return res.json() as Promise<T>;
}

export function getDashboardSummary(): Promise<DashboardSummary> {
  return getJson<DashboardSummary>("/api/dashboard-summary");
}

export function getSystemInfo(): Promise<SystemInfo> {
  return getJson<SystemInfo>("/api/system-info");
}

export function getSamples(): Promise<SamplesList> {
  return getJson<SamplesList>("/api/samples");
}

export function sampleImageUrl(name: string): string {
  return `/api/sample/${encodeURIComponent(name)}`;
}

export async function detectFromFile(
  file: File,
  confThreshold: number
): Promise<DetectionResult> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("conf_threshold", String(confThreshold));

  const res = await fetch("/api/detect", { method: "POST", body: formData });
  if (!res.ok) {
    throw new Error(`detect failed: ${res.status}`);
  }
  return res.json() as Promise<DetectionResult>;
}

export async function detectFromSample(
  sampleName: string,
  confThreshold: number
): Promise<DetectionResult> {
  const formData = new FormData();
  formData.append("sample_name", sampleName);
  formData.append("conf_threshold", String(confThreshold));

  const res = await fetch("/api/detect", { method: "POST", body: formData });
  if (!res.ok) {
    throw new Error(`detect failed: ${res.status}`);
  }
  return res.json() as Promise<DetectionResult>;
}

export async function uploadPotholeImages(
  files: FileList | File[]
): Promise<UploadPotholeImagesResult> {
  const formData = new FormData();
  Array.from(files).forEach((f) => formData.append("files", f));

  const res = await fetch("/api/upload-pothole-images", {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    throw new Error(`upload-pothole-images failed: ${res.status}`);
  }
  return res.json() as Promise<UploadPotholeImagesResult>;
}

export async function startTraining(
  params: StartTrainingParams
): Promise<StartTrainingResult> {
  const formData = new FormData();
  formData.append("epochs", String(params.epochs));
  formData.append("batch_size", String(params.batch_size));
  formData.append("learning_rate", String(params.learning_rate));
  formData.append("architecture", params.architecture);

  const res = await fetch("/api/train-model", {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    throw new Error(`train-model failed: ${res.status}`);
  }
  return res.json() as Promise<StartTrainingResult>;
}

export function getTrainingStatus(): Promise<TrainingJobStatus> {
  return getJson<TrainingJobStatus>("/api/train-status");
}

export function getDatasetStats(): Promise<DatasetStats> {
  return getJson<DatasetStats>("/api/dataset-stats");
}

/* ── Geocoding (real OpenStreetMap lookups) ─────────────────────────────── */

export function reverseGeocode(lat: number, lon: number): Promise<GeocodeResult> {
  return getJson<GeocodeResult>(`/api/geocode/reverse?lat=${lat}&lon=${lon}`);
}

export function searchPlaces(query: string, limit = 5): Promise<GeocodeResult[]> {
  return getJson<GeocodeResult[]>(
    `/api/geocode/search?q=${encodeURIComponent(query)}&limit=${limit}`
  );
}

/* ── Map ────────────────────────────────────────────────────────────────── */

export function getMapPoints(): Promise<MapPoint[]> {
  return getJson<MapPoint[]>("/api/gis-data");
}

/* ── Findings ───────────────────────────────────────────────────────────── */

export function logInspection(params: InspectionCreateParams): Promise<Inspection> {
  return postJson<Inspection>("/api/inspections", params);
}

export function getInspections(): Promise<Inspection[]> {
  return getJson<Inspection[]>("/api/inspections");
}

export function getContractors(): Promise<Contractor[]> {
  return getJson<Contractor[]>("/api/contractors");
}

/* ── Civic pipeline ─────────────────────────────────────────────────────── */

export function getPortals(): Promise<Portal[]> {
  return getJson<Portal[]>("/api/civic/portals");
}

export function getStages(): Promise<Stage[]> {
  return getJson<Stage[]>("/api/civic/stages");
}

export function getPipelineStats(): Promise<PipelineStats> {
  return getJson<PipelineStats>("/api/civic/stats");
}

export function getPipelineEvents(limit = 60): Promise<PipelineEvent[]> {
  return getJson<PipelineEvent[]>(`/api/civic/events?limit=${limit}`);
}

export function getCases(): Promise<CaseView[]> {
  return getJson<CaseView[]>("/api/civic/cases");
}

export function getCase(caseId: number): Promise<CaseView> {
  return getJson<CaseView>(`/api/civic/cases/${caseId}`);
}

export function createCase(inspectionIds: number[]): Promise<CaseView> {
  return postJson<CaseView>("/api/civic/cases", { inspection_ids: inspectionIds });
}

export function submitCase(caseId: number): Promise<CaseView> {
  return postAction<CaseView>(`/api/civic/cases/${caseId}/submit`);
}

export function tenderCase(caseId: number): Promise<CaseView> {
  return postAction<CaseView>(`/api/civic/cases/${caseId}/tender`);
}

export function awardCase(caseId: number, contractorId: number): Promise<CaseView> {
  return postJson<CaseView>(`/api/civic/cases/${caseId}/award`, { contractor_id: contractorId });
}

export async function verifyCase(caseId: number, afterPhoto: File): Promise<CaseView> {
  const formData = new FormData();
  formData.append("file", afterPhoto);
  const res = await fetch(`/api/civic/cases/${caseId}/verify`, { method: "POST", body: formData });
  if (!res.ok) {
    throw new Error(await describeFailure(res, "re-inspection"));
  }
  return res.json() as Promise<CaseView>;
}

export function closeCase(caseId: number): Promise<CaseView> {
  return postAction<CaseView>(`/api/civic/cases/${caseId}/close`);
}

/* ── Deliverables ───────────────────────────────────────────────────────── */

export function dossierUrl(caseId: number): string {
  return `/api/civic/cases/${caseId}/dossier.pdf`;
}

export function certificateUrl(caseId: number): string {
  return `/api/civic/cases/${caseId}/certificate.pdf`;
}

export function caseJsonUrl(caseId: number): string {
  return `/api/civic/cases/${caseId}/export.json`;
}

export function caseCsvUrl(caseId: number): string {
  return `/api/civic/cases/${caseId}/export.csv`;
}
