import React, { useState } from 'react';

interface TransformState {
  scale: number;
  positionX: number;
  positionY: number;
  rotation: number;
  opacity: number;
  blendMode: string;
}

import { aiDirectorApi } from '@/lib/api';
import { useEffect } from 'react';

interface TransformPanelProps {
  initialState?: Partial<TransformState>;
  onChange?: (state: TransformState) => void;
  projectId?: string;
  activeTimelineId?: string;
}

export const TransformPanel: React.FC<TransformPanelProps> = ({ initialState, onChange, projectId, activeTimelineId }) => {
  const [state, setState] = useState<TransformState>({
    scale: initialState?.scale ?? 100,
    positionX: initialState?.positionX ?? 0,
    positionY: initialState?.positionY ?? 0,
    rotation: initialState?.rotation ?? 0,
    opacity: initialState?.opacity ?? 100,
    blendMode: initialState?.blendMode ?? 'normal',
  });

  useEffect(() => {
    if (!projectId || !activeTimelineId) return;
    const timeout = setTimeout(() => {
      aiDirectorApi.updateTimeline(projectId, activeTimelineId, {
        transform: state
      }).catch((err: any) => console.error('Failed to sync transform', err));
    }, 1000);
    return () => clearTimeout(timeout);
  }, [state, projectId, activeTimelineId]);

  const handleChange = (key: keyof TransformState, value: string | number) => {
    const newState = { ...state, [key]: value };
    setState(newState);
    onChange?.(newState);
  };

  return (
    <div className="flex flex-col w-64 h-full bg-gray-900 text-gray-200 border-l border-gray-800 p-4 space-y-6 overflow-y-auto">
      <div className="text-sm font-semibold tracking-wider text-gray-400 uppercase mb-2">Transform</div>

      {/* Position */}
      <div className="space-y-3">
        <label className="text-xs text-gray-400">Position</label>
        <div className="flex space-x-2">
          <div className="flex-1 flex items-center bg-gray-800 rounded px-2 focus-within:ring-1 focus-within:ring-blue-500">
            <span className="text-gray-500 text-xs w-4">X</span>
            <input
              type="number"
              className="w-full bg-transparent text-sm text-right outline-none p-1"
              value={state.positionX}
              onChange={(e) => handleChange('positionX', Number(e.target.value))}
            />
          </div>
          <div className="flex-1 flex items-center bg-gray-800 rounded px-2 focus-within:ring-1 focus-within:ring-blue-500">
            <span className="text-gray-500 text-xs w-4">Y</span>
            <input
              type="number"
              className="w-full bg-transparent text-sm text-right outline-none p-1"
              value={state.positionY}
              onChange={(e) => handleChange('positionY', Number(e.target.value))}
            />
          </div>
        </div>
      </div>

      {/* Scale */}
      <div className="space-y-2">
        <div className="flex justify-between">
          <label className="text-xs text-gray-400">Scale</label>
          <span className="text-xs">{state.scale}%</span>
        </div>
        <input
          type="range"
          min="0"
          max="200"
          className="w-full accent-blue-500"
          value={state.scale}
          onChange={(e) => handleChange('scale', Number(e.target.value))}
        />
      </div>

      {/* Rotation */}
      <div className="space-y-2">
        <div className="flex justify-between items-center bg-gray-800 rounded px-2 focus-within:ring-1 focus-within:ring-blue-500">
          <label className="text-xs text-gray-400 py-1">Rotation</label>
          <div className="flex items-center">
            <input
              type="number"
              className="w-16 bg-transparent text-sm text-right outline-none p-1"
              value={state.rotation}
              onChange={(e) => handleChange('rotation', Number(e.target.value))}
            />
            <span className="text-gray-500 text-xs ml-1">°</span>
          </div>
        </div>
      </div>

      <div className="border-t border-gray-800 my-4"></div>

      <div className="text-sm font-semibold tracking-wider text-gray-400 uppercase mb-2">Compositing</div>

      {/* Opacity */}
      <div className="space-y-2">
        <div className="flex justify-between">
          <label className="text-xs text-gray-400">Opacity</label>
          <span className="text-xs">{state.opacity}%</span>
        </div>
        <input
          type="range"
          min="0"
          max="100"
          className="w-full accent-blue-500"
          value={state.opacity}
          onChange={(e) => handleChange('opacity', Number(e.target.value))}
        />
      </div>

      {/* Blend Mode */}
      <div className="space-y-2">
        <label className="text-xs text-gray-400">Blend Mode</label>
        <select
          className="w-full bg-gray-800 text-sm rounded outline-none p-2 appearance-none focus:ring-1 focus:ring-blue-500"
          value={state.blendMode}
          onChange={(e) => handleChange('blendMode', e.target.value)}
        >
          <option value="normal">Normal</option>
          <option value="darken">Darken</option>
          <option value="multiply">Multiply</option>
          <option value="color-burn">Color Burn</option>
          <option value="lighten">Lighten</option>
          <option value="screen">Screen</option>
          <option value="color-dodge">Color Dodge</option>
          <option value="overlay">Overlay</option>
          <option value="soft-light">Soft Light</option>
          <option value="hard-light">Hard Light</option>
        </select>
      </div>
    </div>
  );
};
