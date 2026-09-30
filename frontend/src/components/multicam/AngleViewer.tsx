import React from 'react';

export interface Angle {
  id: string;
  name: string;
  thumbnailUrl?: string;
}

interface AngleViewerProps {
  angles: Angle[];
  activeAngleId: string | null;
  onAngleSelect: (angleId: string) => void;
  gridType?: '2x2' | '3x3';
}

export const AngleViewer: React.FC<AngleViewerProps> = ({
  angles,
  activeAngleId,
  onAngleSelect,
  gridType = '2x2',
}) => {
  const gridClass = gridType === '2x2' ? 'grid-cols-2' : 'grid-cols-3';

  return (
    <div className="flex flex-col h-full w-full bg-neutral-900 text-neutral-100 p-2">
      <div className="flex items-center justify-between mb-2 px-2">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-neutral-400">Multicam Angles</h2>
        <span className="text-xs text-neutral-500">{angles.length} Angles ({gridType})</span>
      </div>
      <div className={`grid ${gridClass} gap-1 flex-1 min-h-0`}>
        {angles.map((angle) => {
          const isActive = angle.id === activeAngleId;
          return (
            <div
              key={angle.id}
              onClick={() => onAngleSelect(angle.id)}
              className={`
                relative flex items-center justify-center bg-black cursor-pointer overflow-hidden border-2
                ${isActive ? 'border-red-500' : 'border-transparent hover:border-neutral-600'}
              `}
            >
              {/* Placeholder for video/thumbnail */}
              {angle.thumbnailUrl ? (
                <img src={angle.thumbnailUrl} alt={angle.name} className="w-full h-full object-cover" />
              ) : (
                <span className="text-neutral-600 select-none">No Signal</span>
              )}
              
              {/* Overlay info */}
              <div className="absolute top-2 left-2 bg-black/60 px-1.5 py-0.5 rounded text-xs text-white">
                {angle.name}
              </div>
              {isActive && (
                <div className="absolute top-2 right-2 bg-red-600 px-1.5 py-0.5 rounded text-xs text-white font-bold">
                  ACTIVE
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
