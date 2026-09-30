import React, { createContext, useContext, useState, ReactNode } from 'react';

interface TimelineState {
  currentTime: number; // in seconds
  duration: number; // in seconds
  zoom: number; // pixels per second
  selectedClipId: string | null;
  setCurrentTime: (time: number) => void;
  setZoom: (zoom: number) => void;
  setDuration: (duration: number) => void;
  setSelectedClipId: (id: string | null) => void;
}

const TimelineContext = createContext<TimelineState | undefined>(undefined);

export const TimelineProvider = ({ children, initialDuration = 60 }: { children: ReactNode, initialDuration?: number }) => {
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(initialDuration);
  const [zoom, setZoom] = useState(10); // 10 pixels per second as default
  const [selectedClipId, setSelectedClipId] = useState<string | null>(null);

  return (
    <TimelineContext.Provider value={{ currentTime, duration, zoom, selectedClipId, setCurrentTime, setZoom, setDuration, setSelectedClipId }}>
      {children}
    </TimelineContext.Provider>
  );
};

export const useTimeline = () => {
  const context = useContext(TimelineContext);
  if (!context) {
    throw new Error('useTimeline must be used within a TimelineProvider');
  }
  return context;
};
