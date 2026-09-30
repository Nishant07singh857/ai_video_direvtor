'use client';

import { useState, useEffect } from 'react';
import { X, Check } from 'lucide-react';
import { Button } from '@/components/Button';
import { renderingApi } from '@/lib/api';
import { RenderPreset, RenderPresetPlatform } from '@/types';
import { cn } from '@/lib/utils';
import { useFocusTrap } from '@/lib/useFocusTrap';

interface ExportModalProps {
  isOpen: boolean;
  onClose: () => void;
  onExport: (presetId: string) => void;
  isLoading?: boolean;
}

export function ExportModal({ isOpen, onClose, onExport, isLoading }: ExportModalProps) {
  const [presets, setPresets] = useState<RenderPreset[]>([]);
  const [selectedPresetId, setSelectedPresetId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const modalRef = useFocusTrap(isOpen);

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      loadPresets().catch(console.error);
    }
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  const loadPresets = async () => {
    try {
      const response = await renderingApi.listRenderPresets();
      setPresets(response.data.presets);
      // Auto-select first default preset
      const defaultPreset = response.data.presets.find((p: RenderPreset) => p.is_default);
      if (defaultPreset) {
        setSelectedPresetId(defaultPreset.id);
      } else if (response.data.presets.length > 0) {
        setSelectedPresetId(response.data.presets[0].id);
      }
    } catch (err) {
      console.error('Failed to load presets:', err);
      setError('Failed to load export presets');
    }
  };

  const getPlatformLabel = (platform: RenderPresetPlatform) => {
    switch (platform) {
      case 'youtube': return 'YouTube';
      case 'instagram': return 'Instagram';
      case 'shorts': return 'Shorts/Reels';
      case 'reels': return 'Reels';
      case 'generic': return 'Generic';
      case 'custom': return 'Custom';
      default: return platform;
    }
  };

  const getPlatformColor = (platform: RenderPresetPlatform) => {
    switch (platform) {
      case 'youtube': return 'bg-red-100 text-red-700';
      case 'instagram': return 'bg-pink-100 text-pink-700';
      case 'shorts': return 'bg-green-100 text-green-700';
      case 'reels': return 'bg-purple-100 text-purple-700';
      case 'generic': return 'bg-blue-100 text-blue-700';
      case 'custom': return 'bg-gray-100 text-gray-700';
      default: return 'bg-gray-100 text-gray-700';
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="export-modal-title"
        className="bg-white rounded-lg shadow-xl max-w-lg w-full mx-4 max-h-[80vh] overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <h3 id="export-modal-title" className="text-lg font-semibold">Export Settings</h3>
          <Button variant="ghost" size="sm" onClick={onClose} aria-label="Close modal">
            <X className="h-5 w-5" aria-hidden="true" />
          </Button>
        </div>

        {/* Preset List */}
        <div className="p-4 space-y-2 max-h-[60vh] overflow-y-auto">
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              {error}
            </div>
          )}

          <div className="space-y-2">
            {presets.map(preset => (
              <label
                key={preset.id}
                className={cn(
                  'flex items-center gap-3 p-3 border rounded-lg cursor-pointer transition-colors',
                  selectedPresetId === preset.id
                    ? 'border-primary-500 bg-primary-50'
                    : 'border-gray-200 hover:border-gray-300'
                )}
              >
                <input
                  type="radio"
                  name="export-preset"
                  value={preset.id}
                  checked={selectedPresetId === preset.id}
                  onChange={() => setSelectedPresetId(preset.id)}
                  className="text-primary-600 focus:ring-primary-500"
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium truncate">{preset.name}</span>
                    <span className={cn('px-1.5 py-0.5 text-xs rounded', getPlatformColor(preset.platform))}>
                      {getPlatformLabel(preset.platform)}
                    </span>
                    {preset.is_default && (
                      <span className="px-1.5 py-0.5 text-xs bg-primary-100 text-primary-700 rounded">Default</span>
                    )}
                  </div>
                  <div className="text-sm text-gray-500 mt-1">
                    {preset.width}×{preset.height} @ {preset.fps}fps • CRF {preset.crf} • {preset.preset} • {preset.video_codec} / {preset.audio_codec}
                  </div>
                </div>
                {selectedPresetId === preset.id && (
                  <Check className="h-5 w-5 text-primary-600" />
                )}
              </label>
            ))}
          </div>

          {presets.length === 0 && (
            <div className="text-center py-8 text-gray-500">
              No export presets available
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t flex gap-2 justify-end">
          <Button variant="outline" onClick={onClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button
            onClick={() => {
              if (selectedPresetId) {
                onExport(selectedPresetId);
              }
            }}
            disabled={isLoading || !selectedPresetId}
          >
            {isLoading ? (
              <>
                <span className="animate-spin">⏳</span> Exporting...
              </>
            ) : (
              'Start Export'
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
