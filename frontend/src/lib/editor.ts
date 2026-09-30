import axios from 'axios';
import { MediaAsset } from '@/types';
import { TrackData } from '@/components/timeline';

export interface DirectorStage { stage: string; status: string; message?: string }
export interface DirectorDecision { clip_id: string; media_asset_id: string; start: number; end: number; reason: string }
export interface CanonicalClip {
  id: string;
  source: { media_asset_id: string; storage_key?: string; [key: string]: unknown };
  source_start: number;
  source_end: number;
  timeline_start: number;
  timeline_duration: number;
  timeline_end: number;
  sequence_order: number;
  properties?: Record<string, unknown>;
  [key: string]: unknown;
}
export interface CanonicalTrack {
  id: string;
  type: 'video' | 'audio' | 'text';
  name?: string;
  track_index: number;
  clips: CanonicalClip[];
  [key: string]: unknown;
}
export interface TimelineJSON {
  tracks: CanonicalTrack[];
  color_settings?: { brightness?: number; contrast?: number; saturation?: number; [key: string]: unknown };
  audio_settings?: { normalize?: boolean; ducking?: boolean; [key: string]: unknown };
  metadata?: { director?: { mode?: string; stages?: DirectorStage[]; decisions?: DirectorDecision[] }; [key: string]: unknown };
  [key: string]: unknown;
}
export interface EditorTimeline {
  id: string;
  version_number: number;
  total_duration: number;
  timeline_json: TimelineJSON;
  created_at?: string;
  updated_at?: string;
}
export interface SavedTemplate { id: string; name: string; description?: string }

export function errorMessage(error: unknown, fallback = 'Something went wrong. Please try again.'): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === 'string') return detail;
    if (error.code === 'ERR_NETWORK') return 'Cannot reach the editing service. Check your connection and try again.';
  }
  return error instanceof Error ? error.message : fallback;
}
export function isConflict(error: unknown) { return axios.isAxiosError(error) && error.response?.status === 409; }
export function timecode(seconds: number) {
  const value = Number.isFinite(seconds) ? Math.max(0, seconds) : 0;
  return `${Math.floor(value / 60).toString().padStart(2, '0')}:${(value % 60).toFixed(2).padStart(5, '0')}`;
}
export function toTracks(timeline: EditorTimeline | undefined, media: MediaAsset[]): TrackData[] {
  return (timeline?.timeline_json.tracks || []).map(track => ({
    id: track.id, name: track.name || `${track.type} ${track.track_index + 1}`, type: track.type,
    clips: track.clips.map(clip => ({
      id: clip.id, trackId: track.id,
      name: media.find(asset => asset.id === clip.source?.media_asset_id)?.original_filename || `Clip ${clip.sequence_order + 1}`,
      startTime: clip.timeline_start, duration: clip.timeline_duration,
      color: track.type === 'audio' ? 'bg-violet-700' : 'bg-teal-800',
    })),
  }));
}

// Reconcile UI coordinates with canonical objects, retaining source ranges,
// properties, track layers, and every field the editor does not own.
export function reconcileTracks(source: TimelineJSON, next: TrackData[]): TimelineJSON {
  const clips = new Map(source.tracks.flatMap(track => track.clips.map(clip => [clip.id, clip] as const)));
  const tracks = next.map(track => {
    const original = source.tracks.find(item => item.id === track.id);
    if (!original) throw new Error('Track no longer exists. Reload this timeline.');
    return { ...original, clips: [...track.clips].sort((a, b) => a.startTime - b.startTime).map((item, order) => {
      const clip = clips.get(item.id);
      const sourceTrack = source.tracks.find(candidate => candidate.clips.some(c => c.id === item.id));
      if (!clip || !sourceTrack || sourceTrack.type !== original.type) throw new Error('Clips can only move between compatible tracks.');
      if (!Number.isFinite(item.startTime) || item.startTime < 0 || !Number.isFinite(item.duration) || item.duration <= 0) throw new Error('Clip timing is invalid.');
      return { ...clip, timeline_start: item.startTime, timeline_duration: item.duration,
        timeline_end: item.startTime + item.duration, sequence_order: order };
    }) };
  });
  const total = Math.max(0, ...tracks.flatMap(track => track.clips.map(clip => clip.timeline_end)));
  return { ...source, tracks, total_duration: total, duration: total };
}
