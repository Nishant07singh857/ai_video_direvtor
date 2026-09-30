'use client';

import React, { useState, useEffect } from 'react';
import { aiDirectorApi } from '@/lib/api';
import { Sparkles, Sliders, Zap, Film, Gauge, Eye, Check } from 'lucide-react';

interface EffectsPanelProps {
  projectId?: string;
  activeTimelineId?: string;
}

export const EffectsPanel: React.FC<EffectsPanelProps> = ({ projectId, activeTimelineId }) => {
  const [activeTab, setActiveTab] = useState<'transitions' | 'filters' | 'chroma' | 'speed'>('transitions');

  // Transition state
  const [transitionType, setTransitionType] = useState('crossfade');
  const [transitionDuration, setTransitionDuration] = useState(1.0);

  // Filters state
  const [blur, setBlur] = useState(0);
  const [sharpen, setSharpen] = useState(0);
  const [vignette, setVignette] = useState(0);
  const [glow, setGlow] = useState(0);

  // Chroma Key state
  const [chromaEnabled, setChromaEnabled] = useState(false);
  const [chromaColor, setChromaColor] = useState('#00FF00');
  const [chromaSimilarity, setChromaSimilarity] = useState(0.3);
  const [chromaBlend, setChromaBlend] = useState(0.1);

  // Speed state
  const [speedMultiplier, setSpeedMultiplier] = useState(1.0);

  // Status feedback
  const [isSynced, setIsSynced] = useState(true);

  // Auto-sync debounced state to backend
  useEffect(() => {
    if (!projectId || !activeTimelineId) return;
    setIsSynced(false);

    const timeout = setTimeout(() => {
      aiDirectorApi.updateTimeline(projectId, activeTimelineId, {
        effects: {
          blur,
          sharpen,
          vignette,
          glow,
        },
        transition: {
          type: transitionType,
          duration: transitionDuration,
        },
        chromakey: {
          enabled: chromaEnabled,
          color: chromaColor,
          similarity: chromaSimilarity,
          blend: chromaBlend,
        },
        speed: speedMultiplier,
      })
      .then(() => setIsSynced(true))
      .catch((err) => console.error('Failed to sync effects state:', err));
    }, 800);

    return () => clearTimeout(timeout);
  }, [
    projectId,
    activeTimelineId,
    transitionType,
    transitionDuration,
    blur,
    sharpen,
    vignette,
    glow,
    chromaEnabled,
    chromaColor,
    chromaSimilarity,
    chromaBlend,
    speedMultiplier,
  ]);

  const TRANSITIONS = [
    { id: 'crossfade', name: 'Crossfade', desc: 'Smooth dissolve blend' },
    { id: 'fade', name: 'Fade to Black', desc: 'Dip to black transition' },
    { id: 'wipeleft', name: 'Wipe Left', desc: 'Linear wipe to left' },
    { id: 'wiperight', name: 'Wipe Right', desc: 'Linear wipe to right' },
    { id: 'slideup', name: 'Slide Up', desc: 'Push from bottom' },
    { id: 'zoomin', name: 'Zoom In', desc: 'Dynamic scale burst' },
    { id: 'dissolve', name: 'Dissolve', desc: 'Granular dissolve' },
    { id: 'pixelize', name: 'Pixelize', desc: 'Digital pixelation' },
    { id: 'hblur', name: 'Motion Blur', desc: 'Directional blur wipe' },
    { id: 'glitch', name: 'Cyber Glitch', desc: 'RGB displacement glitch' },
  ];

  return (
    <div className="flex flex-col w-64 h-full bg-gray-900 text-gray-200 border-l border-gray-800 text-xs overflow-hidden">
      {/* Header */}
      <div className="p-3 border-b border-gray-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-primary-400" />
          <span className="font-semibold text-white tracking-wider uppercase text-[11px]">FX & Transitions</span>
        </div>
        <div className="flex items-center gap-1 text-[10px] text-gray-400">
          <span className={`w-1.5 h-1.5 rounded-full ${isSynced ? 'bg-emerald-500' : 'bg-amber-500 animate-pulse'}`} />
          {isSynced ? 'Synced' : 'Saving...'}
        </div>
      </div>

      {/* Tabs */}
      <div className="grid grid-cols-4 border-b border-gray-800 text-[10px] bg-gray-950/50">
        <button
          onClick={() => setActiveTab('transitions')}
          className={`py-2 px-1 text-center font-medium border-b-2 transition-colors ${
            activeTab === 'transitions'
              ? 'border-primary-500 text-primary-400 bg-gray-800/40'
              : 'border-transparent text-gray-400 hover:text-gray-200'
          }`}
        >
          Transitions
        </button>
        <button
          onClick={() => setActiveTab('filters')}
          className={`py-2 px-1 text-center font-medium border-b-2 transition-colors ${
            activeTab === 'filters'
              ? 'border-primary-500 text-primary-400 bg-gray-800/40'
              : 'border-transparent text-gray-400 hover:text-gray-200'
          }`}
        >
          Filters
        </button>
        <button
          onClick={() => setActiveTab('chroma')}
          className={`py-2 px-1 text-center font-medium border-b-2 transition-colors ${
            activeTab === 'chroma'
              ? 'border-primary-500 text-primary-400 bg-gray-800/40'
              : 'border-transparent text-gray-400 hover:text-gray-200'
          }`}
        >
          Chroma
        </button>
        <button
          onClick={() => setActiveTab('speed')}
          className={`py-2 px-1 text-center font-medium border-b-2 transition-colors ${
            activeTab === 'speed'
              ? 'border-primary-500 text-primary-400 bg-gray-800/40'
              : 'border-transparent text-gray-400 hover:text-gray-200'
          }`}
        >
          Speed
        </button>
      </div>

      {/* Tab Contents */}
      <div className="flex-1 overflow-y-auto p-3 space-y-4">
        {/* TRANSITIONS TAB */}
        {activeTab === 'transitions' && (
          <div className="space-y-4">
            <div>
              <label className="text-gray-400 block mb-1">Duration: {transitionDuration.toFixed(1)}s</label>
              <input
                type="range"
                min="0.2"
                max="2.0"
                step="0.1"
                value={transitionDuration}
                onChange={(e) => setTransitionDuration(parseFloat(e.target.value))}
                className="w-full accent-primary-500"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-[10px] uppercase tracking-wider text-gray-400 block">Transition Presets</label>
              <div className="space-y-1">
                {TRANSITIONS.map((t) => (
                  <button
                    key={t.id}
                    onClick={() => setTransitionType(t.id)}
                    className={`w-full text-left p-2 rounded flex items-center justify-between transition-colors ${
                      transitionType === t.id
                        ? 'bg-primary-900/40 border border-primary-500 text-white'
                        : 'bg-gray-800/60 hover:bg-gray-800 text-gray-300 border border-transparent'
                    }`}
                  >
                    <div>
                      <div className="font-medium text-xs leading-none">{t.name}</div>
                      <div className="text-[10px] text-gray-400 mt-0.5">{t.desc}</div>
                    </div>
                    {transitionType === t.id && <Check className="w-3.5 h-3.5 text-primary-400" />}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* FILTERS TAB */}
        {activeTab === 'filters' && (
          <div className="space-y-4">
            <div>
              <div className="flex justify-between mb-1">
                <span className="text-gray-400">Gaussian Blur</span>
                <span className="font-mono text-[10px]">{blur} px</span>
              </div>
              <input
                type="range"
                min="0"
                max="20"
                step="1"
                value={blur}
                onChange={(e) => setBlur(parseInt(e.target.value))}
                className="w-full accent-primary-500"
              />
            </div>

            <div>
              <div className="flex justify-between mb-1">
                <span className="text-gray-400">Sharpen / Clarity</span>
                <span className="font-mono text-[10px]">{sharpen}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                step="5"
                value={sharpen}
                onChange={(e) => setSharpen(parseInt(e.target.value))}
                className="w-full accent-primary-500"
              />
            </div>

            <div>
              <div className="flex justify-between mb-1">
                <span className="text-gray-400">Cinematic Vignette</span>
                <span className="font-mono text-[10px]">{vignette}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                step="5"
                value={vignette}
                onChange={(e) => setVignette(parseInt(e.target.value))}
                className="w-full accent-primary-500"
              />
            </div>

            <div>
              <div className="flex justify-between mb-1">
                <span className="text-gray-400">Bloom Glow</span>
                <span className="font-mono text-[10px]">{glow}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                step="5"
                value={glow}
                onChange={(e) => setGlow(parseInt(e.target.value))}
                className="w-full accent-primary-500"
              />
            </div>

            <button
              onClick={() => { setBlur(0); setSharpen(0); setVignette(0); setGlow(0); }}
              className="w-full py-1 text-center bg-gray-800 hover:bg-gray-700 text-gray-400 hover:text-white rounded text-[11px] transition-colors"
            >
              Reset Filters
            </button>
          </div>
        )}

        {/* CHROMA KEY TAB */}
        {activeTab === 'chroma' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between p-2 bg-gray-800/80 rounded border border-gray-700">
              <span className="font-medium text-white">Enable Green Screen</span>
              <input
                type="checkbox"
                checked={chromaEnabled}
                onChange={(e) => setChromaEnabled(e.target.checked)}
                className="w-4 h-4 accent-primary-500 cursor-pointer rounded"
              />
            </div>

            {chromaEnabled && (
              <div className="space-y-3 pt-1 animate-fadeIn">
                <div>
                  <label className="text-gray-400 block mb-1">Key Color</label>
                  <div className="flex items-center gap-2 bg-gray-800 p-1.5 rounded border border-gray-700">
                    <input
                      type="color"
                      value={chromaColor}
                      onChange={(e) => setChromaColor(e.target.value)}
                      className="w-6 h-6 rounded bg-transparent border-0 cursor-pointer"
                    />
                    <span className="font-mono uppercase text-xs">{chromaColor}</span>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between mb-1">
                    <span className="text-gray-400">Similarity Threshold</span>
                    <span className="font-mono text-[10px]">{Math.round(chromaSimilarity * 100)}%</span>
                  </div>
                  <input
                    type="range"
                    min="0.05"
                    max="0.8"
                    step="0.05"
                    value={chromaSimilarity}
                    onChange={(e) => setChromaSimilarity(parseFloat(e.target.value))}
                    className="w-full accent-primary-500"
                  />
                </div>

                <div>
                  <div className="flex justify-between mb-1">
                    <span className="text-gray-400">Edge Smoothness / Blend</span>
                    <span className="font-mono text-[10px]">{Math.round(chromaBlend * 100)}%</span>
                  </div>
                  <input
                    type="range"
                    min="0.0"
                    max="0.5"
                    step="0.02"
                    value={chromaBlend}
                    onChange={(e) => setChromaBlend(parseFloat(e.target.value))}
                    className="w-full accent-primary-500"
                  />
                </div>
              </div>
            )}
          </div>
        )}

        {/* SPEED TAB */}
        {activeTab === 'speed' && (
          <div className="space-y-4">
            <div className="flex justify-between items-center mb-2">
              <span className="text-gray-400">Playback Speed:</span>
              <span className="text-sm font-bold text-primary-400 font-mono">{speedMultiplier}x</span>
            </div>

            <div className="grid grid-cols-3 gap-1.5">
              {[
                { label: '0.25x (Slow)', val: 0.25 },
                { label: '0.5x (Half)', val: 0.5 },
                { label: '1.0x (Normal)', val: 1.0 },
                { label: '1.5x (Fast)', val: 1.5 },
                { label: '2.0x (2x)', val: 2.0 },
                { label: '4.0x (Hyper)', val: 4.0 },
              ].map((s) => (
                <button
                  key={s.val}
                  onClick={() => setSpeedMultiplier(s.val)}
                  className={`p-2 rounded text-center font-medium transition-colors ${
                    speedMultiplier === s.val
                      ? 'bg-primary-600 text-white font-bold'
                      : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                  }`}
                >
                  <div className="text-[11px]">{s.val}x</div>
                </button>
              ))}
            </div>

            <div className="pt-2">
              <input
                type="range"
                min="0.2"
                max="4.0"
                step="0.1"
                value={speedMultiplier}
                onChange={(e) => setSpeedMultiplier(parseFloat(e.target.value))}
                className="w-full accent-primary-500"
              />
              <div className="flex justify-between text-[10px] text-gray-500 mt-1">
                <span>0.2x (Super Slow)</span>
                <span>4.0x (Hyperlapse)</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
