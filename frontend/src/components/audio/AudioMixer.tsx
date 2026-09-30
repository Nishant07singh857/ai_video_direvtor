import React, { useState } from 'react';
import { SlidersHorizontal } from 'lucide-react';
import { Card } from '@/components/Card';
import { cn } from '@/lib/utils';

interface TrackState {
  id: string;
  name: string;
  volume: number; // 0 to 100
  muted: boolean;
  solo: boolean;
  type: 'dialogue' | 'music' | 'sfx' | 'master';
}

const INITIAL_TRACKS: TrackState[] = [
  { id: 't1', name: 'A1 (Dial)', volume: 75, muted: false, solo: false, type: 'dialogue' },
  { id: 't2', name: 'A2 (Music)', volume: 40, muted: false, solo: false, type: 'music' },
  { id: 't3', name: 'A3 (SFX)', volume: 60, muted: false, solo: false, type: 'sfx' },
  { id: 'master', name: 'Master', volume: 80, muted: false, solo: false, type: 'master' },
];
import { aiDirectorApi } from '@/lib/api';
import { useEffect } from 'react';

export function AudioMixer({ className, projectId, activeTimelineId }: { className?: string; projectId?: string; activeTimelineId?: string }) {
  const [tracks, setTracks] = useState<TrackState[]>(INITIAL_TRACKS);
  const [autoDuck, setAutoDuck] = useState(false);

  useEffect(() => {
    if (!projectId || !activeTimelineId) return;
    const timeout = setTimeout(() => {
      aiDirectorApi.updateTimeline(projectId, activeTimelineId, {
        audio_mix: { tracks, autoDuck }
      }).catch((err: any) => console.error('Failed to sync audio mix', err));
    }, 1000);
    return () => clearTimeout(timeout);
  }, [tracks, autoDuck, projectId, activeTimelineId]);

  const handleVolumeChange = (id: string, newVolume: number) => {
    setTracks(tracks.map(t => t.id === id ? { ...t, volume: newVolume } : t));
  };

  const toggleMute = (id: string) => {
    setTracks(tracks.map(t => t.id === id ? { ...t, muted: !t.muted } : t));
  };

  const toggleSolo = (id: string) => {
    setTracks(tracks.map(t => t.id === id ? { ...t, solo: !t.solo } : t));
  };

  return (
    <Card className={cn("flex flex-col bg-gray-900 text-gray-100 p-4 w-full h-full border-gray-800", className)}>
      <div className="flex items-center justify-between mb-6 border-b border-gray-800 pb-4">
        <div className="flex items-center gap-2 text-primary-400">
          <SlidersHorizontal className="w-5 h-5" />
          <h2 className="text-lg font-semibold text-gray-100">Audio Mixer</h2>
        </div>
        <div className="flex items-center gap-3">
          <button 
            onClick={() => setAutoDuck(!autoDuck)}
            className={cn(
              "px-3 py-1.5 text-sm font-medium rounded-md transition-colors border",
              autoDuck 
                ? "bg-primary-600/20 border-primary-500/50 text-primary-400" 
                : "bg-gray-800 border-gray-700 text-gray-400 hover:bg-gray-700 hover:text-gray-300"
            )}
          >
            Auto-Duck Music against Dialogue {autoDuck ? '(ON)' : '(OFF)'}
          </button>
        </div>
      </div>

      <div className="flex gap-6 overflow-x-auto pb-4 flex-1">
        {tracks.map((track) => (
          <div 
            key={track.id} 
            className={cn(
              "flex flex-col items-center p-4 rounded-xl min-w-[100px] border",
              track.type === 'master' ? 'border-primary-900/50 bg-primary-950/20' : 'border-gray-800 bg-gray-800/50'
            )}
          >
            <div className="text-xs font-medium text-gray-400 mb-4 truncate w-full text-center">
              {track.name}
            </div>

            <div className="flex gap-2 mb-6">
              {track.type !== 'master' && (
                <button
                  onClick={() => toggleSolo(track.id)}
                  className={cn(
                    "w-8 h-8 flex items-center justify-center rounded text-xs font-bold transition-colors",
                    track.solo ? "bg-yellow-500 text-black" : "bg-gray-700 text-gray-400 hover:bg-gray-600"
                  )}
                  title="Solo"
                >
                  S
                </button>
              )}
              <button
                onClick={() => toggleMute(track.id)}
                className={cn(
                  "w-8 h-8 flex items-center justify-center rounded text-xs font-bold transition-colors",
                  track.muted ? "bg-red-500 text-white" : "bg-gray-700 text-gray-400 hover:bg-gray-600"
                )}
                title={track.muted ? "Unmute" : "Mute"}
              >
                M
              </button>
            </div>

            <div className="relative flex-1 flex flex-col items-center justify-end w-full py-4 min-h-[150px]">
              {/* Level meter placeholder */}
              <div className="absolute left-2 top-0 bottom-0 w-1.5 bg-gray-900 rounded-full overflow-hidden flex flex-col-reverse">
                <div 
                  className={cn(
                    "w-full transition-all duration-100", 
                    track.muted ? "bg-gray-600" : track.volume > 90 ? "bg-red-500" : track.volume > 75 ? "bg-yellow-400" : "bg-green-500"
                  )}
                  style={{ height: `${track.muted ? 0 : track.volume}%` }}
                />
              </div>

              {/* Volume Slider */}
              <input
                type="range"
                min="0"
                max="100"
                {...{ orient: 'vertical' }}
                value={track.volume}
                onChange={(e) => handleVolumeChange(track.id, parseInt(e.target.value))}
                className="w-2 h-32 bg-gray-700 rounded-lg appearance-none cursor-pointer focus:outline-none focus:ring-2 focus:ring-primary-500 [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:bg-white [&::-webkit-slider-thumb]:rounded-full [&::-moz-range-thumb]:w-4 [&::-moz-range-thumb]:h-4 [&::-moz-range-thumb]:bg-white [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:border-0"
                style={{
                  writingMode: 'vertical-lr',
                  WebkitAppearance: 'slider-vertical'
                } as any}
              />
            </div>

            <div className="mt-8 pt-4 border-t border-gray-700 w-full flex flex-col items-center gap-1">
              <span className="text-sm font-mono text-gray-300">
                {track.volume} <span className="text-xs text-gray-500">dB</span>
              </span>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
