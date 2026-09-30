import React, { useRef } from 'react';
import { useTimeline } from './TimelineContext';

export const Playhead = () => {
  const { currentTime, zoom } = useTimeline();
  const playheadRef = useRef<HTMLDivElement>(null);
  
  return (
    <div
      ref={playheadRef}
      className="absolute top-0 bottom-0 w-px bg-nle-accent z-50 pointer-events-none shadow-[0_0_4px_rgba(43,130,217,0.5)]"
      style={{ left: `${currentTime * zoom}px` }}
    >
      {/* Triangle marker at the top */}
      <div className="absolute top-0 -left-[5px] w-0 h-0 border-l-[5px] border-l-transparent border-r-[5px] border-r-transparent border-t-[8px] border-t-nle-accent drop-shadow" />
    </div>
  );
};
