import type {
  DashboardSummary,
  SystemInfo,
  SamplesList,
  DetectionResult,
  UploadPotholeImagesResult,
  TrainingJobStatus,
  StartTrainingResult,
  StartTrainingParams,
  GisDataPoint,
  DatasetStats,
} from "./types";

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(path);
  if (!res.ok) {
    throw new Error(`${path} failed: ${res.status}`);
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

export function getGisData(): Promise<GisDataPoint[]> {
  return getJson<GisDataPoint[]>("/api/gis-data");
}

export function getDatasetStats(): Promise<DatasetStats> {
  return getJson<DatasetStats>("/api/dataset-stats");
}
