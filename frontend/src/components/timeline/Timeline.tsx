import React, { useState } from 'react';
import { DndContext, DragEndEvent, DragOverlay, useSensor, useSensors, PointerSensor } from '@dnd-kit/core';
import { restrictToWindowEdges } from '@dnd-kit/modifiers';
import { TimelineProvider, useTimeline } from './TimelineContext';
import { TimelineRuler } from './TimelineRuler';
import { Playhead } from './Playhead';
import { Track, TrackData } from './Track';
import { Clip, ClipData } from './Clip';

interface TimelineProps {
  initialTracks: TrackData[];
  duration?: number;
  onChange?: (tracks: TrackData[]) => void | Promise<void>;
  disabled?: boolean;
}

const TimelineInner: React.FC<{
  tracks: TrackData[];
  setTracks: React.Dispatch<React.SetStateAction<TrackData[]>>;
  onChange?: (tracks: TrackData[]) => void | Promise<void>;
  disabled?: boolean;
}> = ({ tracks, setTracks, onChange, disabled = false }) => {
  const { zoom, setZoom, duration } = useTimeline();
  const [activeClip, setActiveClip] = useState<ClipData | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 5, // require 5px movement before drag starts to allow clicking
      },
    })
  );

  const handleDragStart = (event: any) => {
    const { active } = event;
    const clip = active.data.current?.clip as ClipData;
    if (clip) {
      setActiveClip(clip);
    }
  };

  const handleDragEnd = (event: DragEndEvent) => {
    setActiveClip(null);
    if (disabled) return;
    const { active, over, delta } = event;
    
    if (!over || !active.data.current) return;

    const clip = active.data.current.clip as ClipData;
    const sourceTrackId = clip.trackId;
    const targetTrackId = (over.data.current?.trackId || over.id) as string;
    
    // Calculate new start time based on horizontal pixel movement
    // delta.x is the movement in pixels. 
    // newTime = oldTime + (delta.x / zoom)
    let newStartTime = clip.startTime + (delta.x / zoom);
    
    // Constrain to timeline boundaries (0 to duration - clip.duration)
    newStartTime = Math.max(0, Math.min(newStartTime, duration - clip.duration));

    const currentTracks = tracks;
    const sourceTrack = currentTracks.find(track => track.id === sourceTrackId);
    const targetTrack = currentTracks.find(track => track.id === targetTrackId);
    if (!sourceTrack || !targetTrack || sourceTrack.type !== targetTrack.type) return;
    const newTracks = currentTracks.map(track => ({ ...track, clips: [...track.clips] }));

      // Create a deep copy to mutate safely
      // Find source track and remove clip
      const srcTrackIndex = newTracks.findIndex(t => t.id === sourceTrackId);
      if (srcTrackIndex === -1) return;
      
      const clipIndex = newTracks[srcTrackIndex].clips.findIndex(c => c.id === clip.id);
      if (clipIndex === -1) return;
      
      const [movedClip] = newTracks[srcTrackIndex].clips.splice(clipIndex, 1);
      
      // Update clip time
      movedClip.startTime = newStartTime;
      movedClip.trackId = targetTrackId;
      
      // Find target track and add clip
      const targetTrackIndex = newTracks.findIndex(t => t.id === targetTrackId);
      if (targetTrackIndex !== -1) {
        newTracks[targetTrackIndex].clips.push(movedClip);
      }
      setTracks(newTracks);
      // Persistence is deliberately outside the state updater. This callback is
      // an effect of the committed drag, never a side effect during React's
      // render/update calculation. A rejected save rolls the optimistic drag
      // back so the canvas cannot claim an edit was persisted when it was not.
      void Promise.resolve(onChange?.(newTracks)).catch(() => {
        setTracks(current => current === newTracks ? tracks : current);
      });
  };

  return (
    <DndContext 
      sensors={sensors}
      onDragStart={handleDragStart} 
      onDragEnd={handleDragEnd}
      modifiers={[restrictToWindowEdges]}
    >
      <div className="flex flex-col w-full h-full bg-nle-bg text-nle-text overflow-hidden border-t border-nle-border font-nle">
        {/* Toolbar / Header */}
        <div className="flex justify-between items-center p-2 bg-nle-panelLight border-b border-nle-border z-20">
          <h2 className="text-nle-xs font-semibold text-nle-textMuted uppercase tracking-wider">Timeline · drag clips to compatible tracks</h2>
          <div className="flex items-center space-x-2 bg-nle-bg rounded p-1 border border-nle-border">
            <button 
              className="px-2 py-0.5 hover:bg-nle-panelLight rounded text-nle-xs transition-colors"
               disabled={disabled}
               onClick={() => setZoom(Math.max(1, zoom - 5))}
            >
              -
            </button>
            <span className="text-[10px] text-nle-textMuted font-mono w-16 text-center">{zoom} px/s</span>
            <button 
              className="px-2 py-0.5 hover:bg-nle-panelLight rounded text-nle-xs transition-colors"
               disabled={disabled}
               onClick={() => setZoom(Math.min(100, zoom + 5))}
            >
              +
            </button>
          </div>
        </div>

        <div className="flex-grow flex flex-col overflow-auto relative">
          <div className="flex w-full sticky top-0 z-40 bg-nle-panel">
             {/* Header placeholder matching track header width */}
             <div className="w-48 flex-shrink-0 bg-nle-panelLight border-r border-nle-border border-b border-nle-border" />
             {/* Ruler */}
             <div className="flex-grow relative overflow-hidden bg-nle-panelLight border-b border-nle-border">
               <TimelineRuler />
             </div>
          </div>

          {/* Tracks Area */}
          <div className="relative flex-grow w-full overflow-y-auto overflow-x-auto bg-nle-trackAltBg">
             {/* Playhead overlay covering all tracks */}
             <div className="absolute top-0 bottom-0 left-48 right-0 pointer-events-none overflow-hidden z-20">
               <div className="relative w-full h-full">
                 <Playhead />
               </div>
             </div>

             <div className="flex flex-col w-full min-w-max">
               {tracks.map(track => (
                 <Track key={track.id} track={track} />
               ))}
             </div>
          </div>
        </div>
      </div>
      
      <DragOverlay dropAnimation={null}>
        {activeClip ? (
           <div
           className={`absolute top-0 rounded-sm border border-black/50 shadow-sm overflow-hidden flex items-center px-2 text-nle-xs text-white opacity-80 ${activeClip.color || 'bg-nle-accent'}`}
           style={{
             width: `${activeClip.duration * zoom}px`,
             height: '76px', // match the track inner height
             marginTop: '2px'
           }}
         >
           <span className="truncate w-full font-medium">{activeClip.name}</span>
         </div>
        ) : null}
      </DragOverlay>
    </DndContext>
  );
}

export const Timeline: React.FC<TimelineProps> = ({ initialTracks, duration = 60, onChange, disabled = false }) => {
  const [tracks, setTracks] = useState<TrackData[]>(initialTracks);

  React.useEffect(() => {
    setTracks(initialTracks);
  }, [initialTracks]);

  return (
    <TimelineProvider initialDuration={duration}>
        <TimelineInner tracks={tracks} setTracks={setTracks} onChange={onChange} disabled={disabled} />
    </TimelineProvider>
  );
};
