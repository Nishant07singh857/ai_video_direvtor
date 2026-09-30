import React, { useState, useEffect } from 'react';
import { ColorWheels } from './ColorWheels';
import { aiDirectorApi } from '@/lib/api';

interface LumetriPanelProps { projectId?: string; activeTimelineId?: string; }
export const LumetriPanel: React.FC<LumetriPanelProps> = ({ projectId, activeTimelineId }) => {
  const [exposure, setExposure] = useState(0);
  const [contrast, setContrast] = useState(0);
  const [highlights, setHighlights] = useState(0);
  const [shadows, setShadows] = useState(0);
  const [lut, setLut] = useState('none');
  // Sync to API when values change
  useEffect(() => {
    if (!projectId || !activeTimelineId) return;
    const timeout = setTimeout(() => {
      aiDirectorApi.updateTimeline(projectId, activeTimelineId, {
        color_grading: { exposure, contrast, highlights, shadows, lut }
      }).catch((err: any) => console.error('Failed to sync color', err));
    }, 1000);
    return () => clearTimeout(timeout);
  }, [exposure, contrast, highlights, shadows, lut, projectId, activeTimelineId]);


  return (
    <div className="w-80 h-full bg-gray-900 border-l border-gray-800 p-4 overflow-y-auto flex flex-col text-gray-200">
      <h2 className="text-xl font-bold mb-4 text-white">Lumetri Color</h2>

      {/* LUT Selection */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-400 mb-2">Input LUT</label>
        <select
          value={lut}
          onChange={(e) => setLut(e.target.value)}
          className="w-full bg-gray-800 border border-gray-700 rounded p-2 text-sm text-white focus:outline-none focus:border-blue-500 transition-colors"
        >
          <option value="none">None</option>
          <option value="alexa-v3">Alexa V3 to Rec.709</option>
          <option value="phantom">Phantom LOG</option>
          <option value="s-log3">Sony S-Log3</option>
          <option value="v-log">Panasonic V-Log</option>
        </select>
      </div>

      {/* Basic Correction */}
      <div className="space-y-6 border-t border-gray-800 pt-6 mb-6">
        <h3 className="text-lg font-semibold text-white">Basic Correction</h3>
        
        {/* Exposure */}
        <div>
          <div className="flex justify-between mb-2">
            <label className="text-sm text-gray-400">Exposure</label>
            <span className="text-sm font-mono text-gray-300">{exposure.toFixed(1)}</span>
          </div>
          <input
            type="range"
            min="-5"
            max="5"
            step="0.1"
            value={exposure}
            onChange={(e) => setExposure(parseFloat(e.target.value))}
            className="w-full h-1.5 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
          />
        </div>

        {/* Contrast */}
        <div>
          <div className="flex justify-between mb-2">
            <label className="text-sm text-gray-400">Contrast</label>
            <span className="text-sm font-mono text-gray-300">{contrast}</span>
          </div>
          <input
            type="range"
            min="-100"
            max="100"
            value={contrast}
            onChange={(e) => setContrast(parseInt(e.target.value))}
            className="w-full h-1.5 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
          />
        </div>

        {/* Highlights */}
        <div>
          <div className="flex justify-between mb-2">
            <label className="text-sm text-gray-400">Highlights</label>
            <span className="text-sm font-mono text-gray-300">{highlights}</span>
          </div>
          <input
            type="range"
            min="-100"
            max="100"
            value={highlights}
            onChange={(e) => setHighlights(parseInt(e.target.value))}
            className="w-full h-1.5 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
          />
        </div>

        {/* Shadows */}
        <div>
          <div className="flex justify-between mb-2">
            <label className="text-sm text-gray-400">Shadows</label>
            <span className="text-sm font-mono text-gray-300">{shadows}</span>
          </div>
          <input
            type="range"
            min="-100"
            max="100"
            value={shadows}
            onChange={(e) => setShadows(parseInt(e.target.value))}
            className="w-full h-1.5 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
          />
        </div>
      </div>

      {/* Color Wheels Section */}
      <div className="border-t border-gray-800 pt-6">
        <ColorWheels />
      </div>
    </div>
  );
};
