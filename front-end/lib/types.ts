export interface DashboardSummary {
  dataset_name: string;
  total_images: number;
  damaged_images: number;
  undamaged_images: number;
  total_defects: number;
  potholes_count: number;
  cracks_count: number;
  other_count: number;
  avg_severity: number;
  composite_damage_score: number;
  surveyed_area_m2: number;
  verified_pavement_m2: number;
  class_distribution: Record<string, number>;
  is_demo_data?: boolean;
}

export interface SystemInfo {
  status: string;
  torch_version: string;
  cuda_available: boolean;
  device: string;
  models_loaded: string[];
  models_available?: string[];
  fine_tuned?: boolean;
}

export interface SamplesList {
  samples: string[];
}

export interface DetectionBox {
  index: number;
  code: string;
  name: string;
  category: string;
  severity: string;
  severity_score: number;
  color: string;
  confidence: number;
  box: [number, number, number, number];
  area: number;
}

export interface DetectionResult {
  success: boolean;
  inference_time_ms: number;
  total_defects: number;
  severity_score: number;
  composite_damage_score: number;
  boxes: DetectionBox[];
  annotated_image: string;
  original_image: string;
  road_mask: string;
}

export interface UploadedItem {
  filename: string;
  defects_found: number;
  width: number;
  height: number;
}

export interface UploadPotholeImagesResult {
  success: boolean;
  message: string;
  dataset_path: string;
  items: UploadedItem[];
}

export type TrainingStatus = "idle" | "training" | "completed" | "failed";

export interface TrainingLossEntry {
  epoch: number;
  loss: number;
}

export interface TrainingJobStatus {
  status: TrainingStatus;
  progress: number;
  current_epoch: number;
  total_epochs: number;
  current_loss: number;
  losses: TrainingLossEntry[];
  checkpoint_path: string;
  error: string | null;
}

export interface StartTrainingResult {
  success: boolean;
  message: string;
  epochs?: number;
  architecture?: string;
}

export interface StartTrainingParams {
  epochs: number;
  batch_size: number;
  learning_rate: number;
  architecture: string;
}

export interface GisDataPoint {
  id: number;
  damage_code: string;
  damage_type: string;
  category: string;
  severity: string;
  severity_score: number;
  confidence: number;
  municipality: string;
  lat: number;
  lon: number;
  color_r: number;
  color_g: number;
  color_b: number;
  color_hex: string;
}

export interface DatasetStats {
  total_images: number;
  damaged_images: number;
  undamaged_images: number;
  total_boxes: number;
  class_distribution: Record<string, number>;
}

export type TabKey = "detect" | "analytics" | "train";
