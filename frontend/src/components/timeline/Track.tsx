import React from 'react';
import { useDroppable } from '@dnd-kit/core';
import { Clip, ClipData } from './Clip';
import { useTimeline } from './TimelineContext';

export interface TrackData {
  id: string;
  name: string;
  type: 'video' | 'audio' | 'text';
  trackIndex?: number;
  clips: ClipData[];
}

interface TrackProps {
  track: TrackData;
}

export const Track: React.FC<TrackProps> = ({ track }) => {
  const { duration, zoom } = useTimeline();
  const { setNodeRef, isOver } = useDroppable({
    id: track.id,
    data: { type: 'track', trackId: track.id }
  });

  return (
    <div className="flex w-full border-b border-nle-border h-[80px] group bg-nle-trackBg even:bg-nle-trackAltBg">
      {/* Track Header */}
      <div className="w-48 flex-shrink-0 bg-nle-panel border-r border-nle-border px-3 py-2 flex flex-col justify-center sticky left-0 z-30 shadow-[2px_0_4px_rgba(0,0,0,0.1)]">
        <h3 className="text-nle-sm font-semibold text-nle-text truncate">{track.name}</h3>
        <span className="text-[10px] uppercase font-bold text-nle-textMuted tracking-wider mt-0.5">{track.type}</span>
      </div>
      
      {/* Track Content Area */}
      <div 
        ref={setNodeRef}
        className={`relative flex-grow overflow-hidden transition-colors ${isOver ? 'bg-white/5' : 'bg-transparent group-hover:bg-white/[0.02]'}`}
      >
        <div 
          className="relative h-full py-[2px]"
          style={{ width: `${duration * zoom}px`, minWidth: '100%' }}
        >
        {track.clips.map(clip => (
            <Clip key={clip.id} clip={{ ...clip, trackId: track.id }} />
          ))}
        </div>
      </div>
    </div>
  );
};
