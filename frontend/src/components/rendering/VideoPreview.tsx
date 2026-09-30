'use client';

import { useState, useRef, useEffect } from 'react';
import { RenderJob } from '@/types';
import { Play, Pause, Download, Loader2, AlertCircle } from 'lucide-react';
import { cn, formatDuration, formatDateTime } from '@/lib/utils';

interface VideoPreviewProps {
  renderJob: RenderJob | null;
  onDownload?: (url: string, filename: string) => void;
}

export function VideoPreview({ renderJob, onDownload }: VideoPreviewProps) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [volume, setVolume] = useState(1);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Handle video events
  const handleLoadedMetadata = () => {
    if (videoRef.current) {
      setDuration(videoRef.current.duration);
    }
  };

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime);
    }
  };

  const handleError = () => {
    if (videoRef.current) {
      setError(videoRef.current.error?.message || 'Failed to load video');
    }
  };

  const handleCanPlay = () => {
    setError(null);
  };

  const togglePlay = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause();
      } else {
        videoRef.current.play().catch(err => {
          console.error('Play failed:', err);
          setError('Failed to play video');
        });
      }
      setIsPlaying(!isPlaying);
    }
  };

  const toggleMute = () => {
    if (videoRef.current) {
      videoRef.current.muted = !isMuted;
      setIsMuted(!isMuted);
    }
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const vol = parseFloat(e.target.value);
    setVolume(vol);
    if (videoRef.current) {
      videoRef.current.volume = vol;
      videoRef.current.muted = vol === 0;
      setIsMuted(vol === 0);
    }
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const time = parseFloat(e.target.value);
    setCurrentTime(time);
    if (videoRef.current) {
      videoRef.current.currentTime = time;
    }
  };

  const toggleFullscreen = () => {
    if (containerRef.current) {
      if (!isFullscreen) {
        containerRef.current.requestFullscreen().catch(err => {
          console.error('Fullscreen failed:', err);
        });
      } else {
        document.exitFullscreen().catch(err => {
          console.error('Exit fullscreen failed:', err);
        });
      }
      setIsFullscreen(!isFullscreen);
    }
  };

  const handleDownload = () => {
    if (renderJob && onDownload && renderJob.output_storage_key) {
      // The actual download will be handled by the parent using the API
      // This is a placeholder - the real download uses the API endpoint
      const url = `/api/v1/projects/${renderJob.project_id}/renders/${renderJob.id}/download`;
      const filename = `render_${renderJob.id.slice(0, 8)}_${renderJob.job_type}.mp4`;
      onDownload(url, filename);
    }
  };

  if (!renderJob) {
    return (
      <div className="flex flex-col w-full h-full bg-nle-bg relative">
        <div className="flex-1 flex items-center justify-center bg-black m-2 border border-nle-border rounded-sm">
          <div className="text-center text-nle-textMuted">
            <p>No render selected</p>
            <p className="text-nle-xs mt-1">Complete a render to preview</p>
          </div>
        </div>
      </div>
    );
  }

  if (renderJob.status !== 'completed') {
    return (
      <div className="flex flex-col w-full h-full bg-nle-bg relative">
        <div className="flex-1 flex items-center justify-center bg-black m-2 border border-nle-border rounded-sm">
          <div className="text-center text-nle-textMuted flex flex-col items-center">
            <Loader2 className="h-8 w-8 animate-spin text-nle-accent mb-2" />
            <p className="text-nle-sm">Render in progress...</p>
            <p className="text-nle-xs">Status: {renderJob.status}</p>
          </div>
        </div>
      </div>
    );
  }

  if (error || !renderJob.output_storage_key) {
    return (
      <div className="flex flex-col w-full h-full bg-nle-bg relative">
         <div className="flex-1 flex items-center justify-center bg-black m-2 border border-nle-border rounded-sm">
          <div className="text-center text-[#f39c12] flex flex-col items-center">
            <AlertCircle className="h-8 w-8 mb-2" />
            <p className="text-nle-sm">Unable to load video</p>
            <p className="text-nle-xs">{error || 'No output file available'}</p>
          </div>
        </div>
      </div>
    );
  }

  const videoUrl = `/api/v1/projects/${renderJob.project_id}/renders/${renderJob.id}/download`;

  return (
    <div className="flex flex-col w-full h-full bg-nle-bg relative group">
      {/* Top toolbar */}
      <div className="h-8 flex items-center justify-between px-2 text-nle-xs text-nle-textMuted absolute top-0 left-0 right-0 z-10 bg-nle-panel/80 opacity-0 group-hover:opacity-100 transition-opacity">
         <div>{renderJob.width}x{renderJob.height} @ {renderJob.fps}fps</div>
         <div className="flex gap-1">
            <button onClick={handleDownload} title="Download" className="hover:text-nle-text transition-colors">
              <Download className="h-3 w-3" />
            </button>
         </div>
      </div>

      <div 
        ref={containerRef}
        className={cn(
          'flex-1 flex items-center justify-center bg-black m-2 mb-10 border border-nle-border rounded-sm overflow-hidden relative',
          isFullscreen && 'fixed inset-0 m-0 z-50 border-none rounded-none'
        )}
      >
        <video
          ref={videoRef}
          src={videoUrl}
          className="w-full h-full object-contain"
          onLoadedMetadata={handleLoadedMetadata}
          onTimeUpdate={handleTimeUpdate}
          onError={handleError}
          onCanPlay={handleCanPlay}
          onPlay={() => setIsPlaying(true)}
          onPause={() => setIsPlaying(false)}
          onEnded={() => setIsPlaying(false)}
        />
      </div>

      {/* Monitor Controls (Bottom toolbar) */}
      <div className="h-10 absolute bottom-0 left-0 right-0 px-2 flex items-center justify-between bg-nle-panel border-t border-nle-border">
          {/* Timecode Left */}
          <div className="font-mono text-nle-accent text-nle-sm bg-nle-bg px-2 py-1 rounded">
            {formatDuration(currentTime)}
          </div>

          {/* Center Transport Controls */}
          <div className="flex items-center gap-4">
             <button onClick={() => { if (videoRef.current) { videoRef.current.currentTime = 0; setCurrentTime(0); } }} className="text-nle-textMuted hover:text-nle-text" title="Go to start">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="19 20 9 12 19 4 19 20"></polygon><line x1="5" y1="19" x2="5" y2="5"></line></svg>
             </button>
             <button onClick={togglePlay} className="text-nle-text hover:text-white bg-nle-borderHover rounded p-1">
                {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" fill="currentColor" />}
             </button>
             <button onClick={() => { if (videoRef.current) { videoRef.current.currentTime = duration; setCurrentTime(duration); } }} className="text-nle-textMuted hover:text-nle-text" title="Go to end">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="5 4 15 12 5 20 5 4"></polygon><line x1="19" y1="5" x2="19" y2="19"></line></svg>
             </button>
          </div>

          {/* Timecode Right */}
          <div className="font-mono text-nle-textMuted text-nle-xs">
            {formatDuration(duration)}
          </div>
      </div>
    </div>
  );
}
