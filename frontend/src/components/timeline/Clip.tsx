import React from 'react';
import { useDraggable } from '@dnd-kit/core';
import { useTimeline } from './TimelineContext';

export interface ClipData {
  id: string;
  name: string;
  startTime: number; // in seconds
  duration: number; // in seconds
  color?: string;
  trackId?: string; // added this so we know which track a clip comes from if needed
}

interface ClipProps {
  clip: ClipData;
}

export const Clip: React.FC<ClipProps> = ({ clip }) => {
  const { zoom, selectedClipId, setSelectedClipId } = useTimeline();
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: clip.id,
    data: { clip },
  });

  const isSelected = selectedClipId === clip.id;

  const style: React.CSSProperties = {
    left: `${clip.startTime * zoom}px`,
    width: `${clip.duration * zoom}px`,
    transform: transform ? `translate3d(${transform.x}px, ${transform.y}px, 0)` : undefined,
    zIndex: isDragging ? 50 : isSelected ? 20 : 10,
    opacity: isDragging ? 0.8 : 1,
    // Add transition ONLY when not dragging, so drop snaps back smoothly
    transition: isDragging ? 'none' : 'transform 0.1s ease, left 0.1s ease', 
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      setSelectedClipId(clip.id);
    }
  };

  const handleClick = () => {
    setSelectedClipId(clip.id);
  };

  return (
    <div
      ref={setNodeRef}
      {...listeners}
      {...attributes}
      className={`absolute h-full top-0 rounded-sm border ${isSelected ? 'border-primary-500 ring-2 ring-primary-500' : 'border-black/30'} shadow-sm overflow-hidden flex items-center px-2 text-nle-xs text-white cursor-grab active:cursor-grabbing hover:opacity-90 ${clip.color || 'bg-nle-accent'} focus:outline-none focus:ring-2 focus:ring-primary-500`}
      style={style}
      role="button"
      tabIndex={0}
      aria-label={`Clip ${clip.name}, starts at ${clip.startTime} seconds, duration ${clip.duration} seconds`}
       aria-pressed={isSelected}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
    >
      <span className="truncate w-full font-medium text-shadow-sm">{clip.name}</span>
    </div>
  );
};
