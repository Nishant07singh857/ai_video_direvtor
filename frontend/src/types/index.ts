export interface User {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
  updated_at: string;
}

export interface Project {
  id: string;
  user_id: string;
  name: string;
  description: string | null;
  platform: 'youtube' | 'instagram' | 'shorts' | null;
  status: 'draft' | 'processing' | 'completed' | 'failed';
  created_at: string;
  updated_at: string;
}

export interface ProjectCreate {
  name: string;
  description?: string;
  platform?: 'youtube' | 'instagram' | 'shorts';
}

export interface ProjectUpdate {
  name?: string;
  description?: string;
  platform?: 'youtube' | 'instagram' | 'shorts';
  status?: 'draft' | 'processing' | 'completed' | 'failed';
}

export interface ProjectListResponse {
  projects: Project[];
  total: number;
  page: number;
  page_size: number;
}

export interface Token {
  access_token: string;
  token_type: string;
}

export interface MediaAsset {
  id: string;
  project_id: string;
  original_filename: string;
  media_type: 'video' | 'audio' | 'image';
  mime_type: string;
  file_size: number;
  checksum: string;
  status: 'uploading' | 'uploaded' | 'processing' | 'ready' | 'failed';
  error_message: string | null;
  duration: number | null;
  width: number | null;
  height: number | null;
  fps: number | null;
  video_codec: string | null;
  audio_codec: string | null;
  bitrate: number | null;
  created_at: string;
  updated_at: string;
}

export interface MediaAssetListResponse {
  media_assets: MediaAsset[];
  total: number;
  page: number;
  page_size: number;
}

export interface HealthResponse {
  status: string;
  app?: string;
  version?: string;
  database?: string;
  redis?: string;
  error?: string;
}

export type RenderJobType = 'preview' | 'export';
export type RenderJobStatus = 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
export type RenderPresetPlatform = 'generic' | 'youtube' | 'instagram' | 'shorts' | 'reels' | 'custom';

export interface RenderPreset {
  id: string;
  name: string;
  platform: RenderPresetPlatform;
  width: number;
  height: number;
  fps: number;
  video_codec: string;
  video_bitrate: string | null;
  crf: number;
  preset: string;
  audio_codec: string;
  audio_bitrate: string;
  pixel_format: string;
  container: string;
  is_default: boolean;
  created_at: string;
}

export interface RenderJob {
  id: string;
  project_id: string;
  timeline_id: string | null;
  job_type: RenderJobType;
  status: RenderJobStatus;
  progress: number;
  output_storage_key: string | null;
  output_size: number | null;
  duration: number | null;
  width: number | null;
  height: number | null;
  fps: number | null;
  video_codec: string | null;
  bitrate: number | null;
  error_message: string | null;
  ffmpeg_cmd: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  preset_name: string | null;
  preset_platform: string | null;
}

export interface RenderJobListResponse {
  renders: RenderJob[];
  total: number;
}

export interface RenderPresetsResponse {
  presets: RenderPreset[];
}

export interface CreatePreviewRenderResponse {
  render_job_id: string;
  status: string;
}

export interface CreateExportRenderRequest {
  preset_id?: string;
}

export interface CreateExportRenderResponse {
  render_job_id: string;
  status: string;
}