'use client';

import { useState, useEffect, useCallback } from 'react';
import { renderingApi } from '@/lib/api';
import { RenderJob, RenderJobStatus, RenderJobType } from '@/types';
import { Download, X, RotateCcw, Trash2, AlertCircle, Loader2, CheckCircle, Clock, Zap, FileVideo, Settings, RefreshCw } from 'lucide-react';
import { cn, formatDateTime, formatFileSize, formatDuration } from '@/lib/utils';
import { errorMessage } from '@/lib/editor';

interface RenderJobListProps { projectId: string; timelineId?: string; refreshKey?: number; onPreviewReady?: (url: string) => void; }

export function RenderJobList({ projectId, timelineId, refreshKey = 0, onPreviewReady }: RenderJobListProps) {
  const [jobs, setJobs] = useState<RenderJob[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const fetchJobs = useCallback(async () => {
    setIsLoading(true); setError(null);
    try {
      const response = await renderingApi.listRenderJobs(projectId, { limit: 20, ...(timelineId ? { timeline_id: timelineId } : {}) } as any);
      setJobs(response.data.renders || []);
    } catch (err) { setError(errorMessage(err, 'Could not load render jobs.')); }
    finally { setIsLoading(false); }
  }, [projectId, timelineId]);

  useEffect(() => { void fetchJobs(); }, [fetchJobs, refreshKey]);

  // Poll only while this view has active work. Completed history is not
  // needlessly refreshed every few seconds.
  useEffect(() => {
    if (!jobs.some(job => job.status === 'running' || job.status === 'queued')) return;
    const interval = window.setInterval(() => void fetchJobs(), 2200);
    return () => window.clearInterval(interval);
  }, [jobs, fetchJobs]);

  const action = async (id: string, fn: () => Promise<unknown>) => {
    setBusy(id); setError(null);
    try { await fn(); await fetchJobs(); }
    catch (err) { setError(errorMessage(err, 'Render action failed.')); }
    finally { setBusy(null); }
  };

  const download = async (job: RenderJob) => {
    setBusy(job.id); setError(null);
    try {
      const response = await renderingApi.downloadRender(projectId, job.id);
      const url = URL.createObjectURL(response.data);
      if (onPreviewReady && job.job_type === 'preview') {
        onPreviewReady(url);
        // The monitor owns this URL and revokes its previous URL on replacement/unmount.
      } else {
        const anchor = document.createElement('a'); anchor.href = url;
        anchor.download = `director-${job.job_type}-${job.id.slice(0, 8)}.mp4`;
        document.body.appendChild(anchor); anchor.click(); anchor.remove();
        window.setTimeout(() => URL.revokeObjectURL(url), 1000);
      }
    } catch (err) { setError(errorMessage(err, 'Could not download this render.')); }
    finally { setBusy(null); }
  };

  const status = (value: RenderJobStatus) => ({
    completed: ['good', <CheckCircle key="i" size={13} />, 'Ready'],
    running: ['busy', <Loader2 key="i" size={13} className="animate-spin" />, 'Rendering'],
    queued: ['busy', <Clock key="i" size={13} />, 'Queued'],
    failed: ['bad', <AlertCircle key="i" size={13} />, 'Failed'],
    cancelled: ['', <X key="i" size={13} />, 'Cancelled'],
  }[value] || ['', <Clock key="i" size={13} />, value]);
  const typeIcon = (type: RenderJobType) => type === 'preview' ? <Zap size={13} /> : <Settings size={13} />;

  return <section className="space-y-3">
    <div className="flex items-center justify-between">
      <div><div className="director-kicker">Render queue</div><h3 className="mt-1 text-sm font-medium">Exports & previews</h3></div>
      <button className="director-btn icon" onClick={() => void fetchJobs()} disabled={isLoading} title="Refresh render queue"><RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} /></button>
    </div>
    {error && <div className="director-notice error inline"><AlertCircle size={15} /> <span>{error}</span></div>}
    {isLoading && jobs.length === 0 && <div className="director-empty">Loading render history…</div>}
    {!isLoading && jobs.length === 0 && <div className="director-empty" style={{ padding: '25px 12px' }}><FileVideo size={27} /><strong>No renders yet</strong>Queue a preview or export when the timeline is ready.</div>}
    {jobs.map(job => {
      const [tone, icon, label] = status(job.status);
      const active = job.status === 'running' || job.status === 'queued';
      const canRetry = job.status === 'failed' || job.status === 'cancelled';
      return <div className="director-job" key={job.id}>
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0"><span className={cn('director-badge', tone)}>{icon}{label}</span><span className="director-badge">{typeIcon(job.job_type)}{job.job_type}</span><span className="truncate text-[11px] director-muted">{job.preset_name || 'Timeline output'}</span></div>
          <span className="text-[10px] director-muted whitespace-nowrap">{formatDateTime(job.created_at)}</span>
        </div>
        {active && <div className="mt-3 flex items-center gap-2"><div className="director-progress flex-1"><div style={{ width: `${Math.max(2, Math.min(100, job.progress || 0))}%` }} /></div><span className="text-[10px] director-muted">{Math.round(job.progress || 0)}%</span></div>}
        {job.error_message && <div className="mt-2 text-[11px] text-rose-300">{job.error_message}</div>}
        <div className="mt-3 flex items-center justify-between gap-2"><div className="flex flex-wrap gap-2 text-[10px] director-muted">{job.duration ? <span>{formatDuration(job.duration)}</span> : null}{job.output_size ? <span>{formatFileSize(job.output_size)}</span> : null}{job.width && job.height ? <span>{job.width}×{job.height}</span> : null}</div><div className="flex gap-1">
          {job.status === 'completed' && <button className="director-btn icon" onClick={() => void download(job)} disabled={busy === job.id} title={job.job_type === 'preview' ? 'Load preview' : 'Download export'}><Download size={14} /></button>}
          {active && <button className="director-btn icon" onClick={() => void action(job.id, () => renderingApi.cancelRenderJob(projectId, job.id))} disabled={busy === job.id} title="Cancel"><X size={14} /></button>}
          {canRetry && <button className="director-btn icon" onClick={() => void action(job.id, () => renderingApi.retryRenderJob(projectId, job.id))} disabled={busy === job.id} title="Retry"><RotateCcw size={14} /></button>}
          {!active && <button className="director-btn icon" onClick={() => void action(job.id, () => renderingApi.deleteRenderJob(projectId, job.id))} disabled={busy === job.id} title="Delete history"><Trash2 size={14} /></button>}
        </div></div>
      </div>;
    })}
  </section>;
}
