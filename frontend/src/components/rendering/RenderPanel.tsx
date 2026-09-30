'use client';

import { useState, useEffect, useCallback } from 'react';
import { Button } from '@/components/Button';
import { Card, CardContent, CardHeader } from '@/components/Card';
import { renderingApi } from '@/lib/api';
import { RenderJob, RenderPreset, RenderJobStatus, RenderJobType } from '@/types';
import { Download, X, RotateCcw, Trash2, Play, Settings, AlertCircle, Loader2, CheckCircle, Clock, Zap } from 'lucide-react';
import { cn, formatDateTime, formatFileSize } from '@/lib/utils';

interface RenderPanelProps {
  projectId: string;
  timelineId: string;
  onRenderComplete?: (job: RenderJob) => void;
}

export function RenderPanel({ projectId, timelineId, onRenderComplete }: RenderPanelProps) {
  const [isPreviewRendering, setIsPreviewRendering] = useState(false);
  const [isExportRendering, setIsExportRendering] = useState(false);
  const [showExportModal, setShowExportModal] = useState(false);
  const [presets, setPresets] = useState<RenderPreset[]>([]);
  const [selectedPresetId, setSelectedPresetId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadPresets().catch(console.error);
  }, []);

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
    }
  };

  const handlePreviewRender = async () => {
    setError(null);
    setIsPreviewRendering(true);
    try {
      const response = await renderingApi.createPreviewRender(projectId, timelineId);
      if (onRenderComplete) {
        // Will be updated via polling
        console.log('Preview render queued:', response.data.render_job_id);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to start preview render');
    } finally {
      setIsPreviewRendering(false);
    }
  };

  const handleExportRender = async () => {
    if (!selectedPresetId) {
      setError('Please select an export preset');
      return;
    }
    setError(null);
    setIsExportRendering(true);
    try {
      const response = await renderingApi.createExportRender(projectId, timelineId, selectedPresetId);
      if (onRenderComplete) {
        console.log('Export render queued:', response.data.render_job_id);
      }
      setShowExportModal(false);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to start export render');
    } finally {
      setIsExportRendering(false);
    }
  };

  const getStatusColor = (status: RenderJobStatus) => {
    switch (status) {
      case 'completed': return 'text-green-600 bg-green-100';
      case 'running': return 'text-blue-600 bg-blue-100';
      case 'queued': return 'text-yellow-600 bg-yellow-100';
      case 'failed': return 'text-red-600 bg-red-100';
      case 'cancelled': return 'text-gray-600 bg-gray-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const getStatusIcon = (status: RenderJobStatus) => {
    switch (status) {
      case 'completed': return <CheckCircle className="h-4 w-4" />;
      case 'running': return <Loader2 className="h-4 w-4 animate-spin" />;
      case 'queued': return <Clock className="h-4 w-4" />;
      case 'failed': return <AlertCircle className="h-4 w-4" />;
      case 'cancelled': return <X className="h-4 w-4" />;
      default: return <Clock className="h-4 w-4" />;
    }
  };

  return (
    <Card>
      <CardHeader>
        <h2 className="text-lg font-semibold text-gray-900">Render & Export</h2>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm flex items-center gap-2">
            <AlertCircle className="h-4 w-4" />
            {error}
          </div>
        )}

        {/* Preview Render Button */}
        <Button
          onClick={handlePreviewRender}
          disabled={isPreviewRendering}
          className="w-full justify-start"
        >
          <Zap className="mr-2 h-4 w-4" />
          {isPreviewRendering ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Rendering Preview...
            </>
          ) : (
            'Preview Render (Fast)'
          )}
        </Button>

        {/* Export Button */}
        <Button
          variant="outline"
          onClick={() => setShowExportModal(true)}
          disabled={isExportRendering}
          className="w-full justify-start"
        >
          <Settings className="mr-2 h-4 w-4" />
          {isExportRendering ? 'Exporting...' : 'Export (High Quality)'}
        </Button>

        {/* Export Preset Selection Modal */}
        {showExportModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
            <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
              <div className="p-4 border-b">
                <h3 className="text-lg font-semibold">Export Settings</h3>
              </div>
              <div className="p-4 space-y-3 max-h-[60vh] overflow-y-auto">
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
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{preset.name}</span>
                          {preset.is_default && (
                            <span className="px-1.5 py-0.5 text-xs bg-primary-100 text-primary-700 rounded">Default</span>
                          )}
                        </div>
                        <div className="text-sm text-gray-500">
                          {preset.width}×{preset.height} @ {preset.fps}fps • CRF {preset.crf} • {preset.preset}
                        </div>
                      </div>
                    </label>
                  ))}
                </div>
              </div>
              <div className="p-4 border-t flex gap-2 justify-end">
                <Button variant="outline" onClick={() => setShowExportModal(false)}>
                  Cancel
                </Button>
                <Button onClick={handleExportRender} disabled={isExportRendering}>
                  {isExportRendering ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Exporting...
                    </>
                  ) : (
                    'Start Export'
                  )}
                </Button>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
