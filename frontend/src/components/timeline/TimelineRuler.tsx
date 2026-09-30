import React, { useRef } from 'react';
import { useTimeline } from './TimelineContext';

export const TimelineRuler = () => {
  const { duration, zoom, setCurrentTime } = useTimeline();
  const rulerRef = useRef<HTMLDivElement>(null);

  const handleRulerClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!rulerRef.current) return;
    const rect = rulerRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const time = Math.max(0, Math.min(x / zoom, duration));
    setCurrentTime(time);
  };

  // Generate ticks based on zoom level and duration
  const ticks = [];
  const tickInterval = zoom > 50 ? 1 : zoom > 10 ? 5 : 10; // seconds per tick
  for (let i = 0; i <= duration; i += tickInterval) {
    ticks.push(i);
  }

  function formatTime(seconds: number): string {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
  }

  return (
    <div
      ref={rulerRef}
      className="relative h-8 bg-nle-panelLight border-b border-nle-border cursor-pointer overflow-hidden group"
      style={{ width: `${duration * zoom}px`, minWidth: '100%' }}
      onClick={handleRulerClick}
    >
      {ticks.map((tick) => (
        <div
          key={tick}
          className="absolute top-0 bottom-0 border-l border-nle-border flex flex-col justify-end text-[10px] text-nle-textMuted pl-1 pb-0.5 select-none"
          style={{ left: `${tick * zoom}px` }}
        >
          {formatTime(tick)}
        </div>
      ))}
    </div>
  );
};
