'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import {
  AlertCircle, ArrowLeft, Check, ChevronDown, Clapperboard, Film, FolderOpen,
  Layers3, Loader2, MonitorPlay, Plus, RefreshCw, Scissors, Sparkles, Upload,
  Wand2, X,
} from 'lucide-react';
import { aiDirectorApi, mediaApi, projectsApi, renderingApi, templateApi } from '@/lib/api';
import { Timeline } from '@/components/timeline';
import { RenderJobList } from '@/components/rendering/RenderJobList';
import { useProjectStore } from '@/lib/store';
import { MediaAsset, Project, RenderPreset } from '@/types';
import {
  CanonicalTrack, DirectorDecision, EditorTimeline, SavedTemplate, TimelineJSON,
  errorMessage, isConflict, reconcileTracks, timecode, toTracks,
} from '@/lib/editor';

type Monitor = 'program' | 'source';
type BinMode = 'media' | 'reference';
type InspectorTab = 'timeline' | 'color' | 'audio' | 'render';

function ErrorNotice({ children, onRetry }: { children: string; onRetry?: () => void }) {
  return <div className="director-notice error" role="alert"><AlertCircle size={15} /><span className="flex-1">{children}</span>{onRetry && <button className="director-btn" onClick={onRetry}>Retry</button>}</div>;
}

function Badge({ status }: { status: string }) {
  const tone = ['ready', 'uploaded', 'completed'].includes(status.toLowerCase()) ? 'good' : ['failed', 'error'].includes(status.toLowerCase()) ? 'bad' : 'busy';
  return <span className={`director-badge ${tone}`}>{status}</span>;
}

export default function ProjectDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const projectId = params.id;
  const { projects, setCurrentProject, removeProject } = useProjectStore();
  const [project, setProject] = useState<Project | null>(null);
  const [media, setMedia] = useState<MediaAsset[]>([]);
  const [timelines, setTimelines] = useState<EditorTimeline[]>([]);
  const [selectedTimelineId, setSelectedTimelineId] = useState('');
  const [templates, setTemplates] = useState<SavedTemplate[]>([]);
  const [presets, setPresets] = useState<RenderPreset[]>([]);
  const [selectedMediaId, setSelectedMediaId] = useState('');
  const [referenceId, setReferenceId] = useState('');
  const [rawIds, setRawIds] = useState<string[]>([]);
  const [binMode, setBinMode] = useState<BinMode>('media');
  const [monitor, setMonitor] = useState<Monitor>('program');
  const [inspectorTab, setInspectorTab] = useState<InspectorTab>('timeline');
  const [isLoading, setIsLoading] = useState(true);
  const [mediaLoading, setMediaLoading] = useState(false);
  const [pageError, setPageError] = useState('');
  const [timelineError, setTimelineError] = useState('');
  const [templateMessage, setTemplateMessage] = useState('');
  const [aiMessage, setAiMessage] = useState('');
  const [aiRunning, setAiRunning] = useState(false);
  const [templateBusy, setTemplateBusy] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [renderingPreview, setRenderingPreview] = useState(false);
  const [renderingExport, setRenderingExport] = useState(false);
  const [refreshJobs, setRefreshJobs] = useState(0);
  const [selectedPresetId, setSelectedPresetId] = useState('');
  const [programUrl, setProgramUrl] = useState<string | null>(null);
  const [sourceUrl, setSourceUrl] = useState<string | null>(null);
  const [sourceLoading, setSourceLoading] = useState(false);
  const [sourceError, setSourceError] = useState('');
  const [deleting, setDeleting] = useState(false);
  const [settingsSaving, setSettingsSaving] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  const selectedTimeline = useMemo(() => timelines.find(item => item.id === selectedTimelineId) || timelines[0], [timelines, selectedTimelineId]);
  const selectedMedia = useMemo(() => media.find(item => item.id === selectedMediaId), [media, selectedMediaId]);
  const tracks = useMemo(() => toTracks(selectedTimeline, media), [selectedTimeline, media]);
  const decisions = useMemo(() => selectedTimeline?.timeline_json.metadata?.director?.decisions || [], [selectedTimeline]);
  const stages = useMemo(() => selectedTimeline?.timeline_json.metadata?.director?.stages || [], [selectedTimeline]);
  const clipCount = useMemo(() => tracks.reduce((total, track) => total + track.clips.length, 0), [tracks]);

  const fetchTimelines = useCallback(async () => {
    const response = await aiDirectorApi.listTimelines(projectId);
    const data = Array.isArray(response.data) ? response.data : response.data?.timelines;
    if (!Array.isArray(data)) throw new Error('Timeline response was not an array.');
    const sorted = [...data].sort((a: EditorTimeline, b: EditorTimeline) => b.version_number - a.version_number);
    setTimelines(sorted);
    setSelectedTimelineId(current => sorted.some(item => item.id === current) ? current : sorted[0]?.id || '');
    return sorted;
  }, [projectId]);

  const fetchMedia = useCallback(async () => {
    setMediaLoading(true);
    try {
      const response = await mediaApi.list(projectId);
      const assets: MediaAsset[] = response.data.media_assets || [];
      setMedia(assets);
      setSelectedMediaId(current => assets.some(item => item.id === current) ? current : assets[0]?.id || '');
    } catch (error) { setPageError(errorMessage(error, 'Could not load media bin.')); }
    finally { setMediaLoading(false); }
  }, [projectId]);

  const loadProject = useCallback(async () => {
    setIsLoading(true); setPageError('');
    try {
      const [projectResponse] = await Promise.all([projectsApi.get(projectId), fetchMedia(), fetchTimelines()]);
      setProject(projectResponse.data); setCurrentProject(projectResponse.data);
      try {
        const templateResponse = await templateApi.list();
        setTemplates(Array.isArray(templateResponse.data) ? templateResponse.data : templateResponse.data?.templates || []);
      } catch { setTemplates([]); }
      try {
        const presetResponse = await renderingApi.listRenderPresets();
        const available: RenderPreset[] = presetResponse.data.presets || [];
        setPresets(available); setSelectedPresetId(current => current || available.find(item => item.is_default)?.id || available[0]?.id || '');
      } catch { setPresets([]); }
    } catch (error) { setPageError(errorMessage(error, 'Could not load this project.')); }
    finally { setIsLoading(false); }
  }, [fetchMedia, fetchTimelines, projectId, setCurrentProject]);

  useEffect(() => { void loadProject(); }, [loadProject]);

  // Source media is fetched through the authenticated axios client. No token
  // is ever put in a media URL. Blob URLs are revoked when the selection changes.
  useEffect(() => {
    if (!selectedMedia || selectedMedia.media_type !== 'video') { setSourceUrl(null); return; }
    const controller = new AbortController(); let objectUrl: string | null = null;
    setSourceLoading(true); setSourceError('');
    mediaApi.streamBlob(selectedMedia.id, controller.signal).then(response => {
      if (controller.signal.aborted) return;
      objectUrl = URL.createObjectURL(response.data); setSourceUrl(objectUrl);
    }).catch(error => { if (!controller.signal.aborted) setSourceError(errorMessage(error, 'Source preview unavailable.')); })
      .finally(() => { if (!controller.signal.aborted) setSourceLoading(false); });
    return () => { controller.abort(); if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [selectedMedia]);

  useEffect(() => () => { if (programUrl) URL.revokeObjectURL(programUrl); }, [programUrl]);

  const upload = async (file: File) => {
    setUploading(true); setUploadProgress(0); setPageError('');
    try {
      const response = await mediaApi.upload(projectId, file, setUploadProgress);
      setMedia(current => [response.data, ...current]); setSelectedMediaId(response.data.id);
    } catch (error) { setPageError(errorMessage(error, 'Upload failed.')); }
    finally { setUploading(false); }
  };

  const updateTimelineJson = useCallback(async (nextJson: TimelineJSON) => {
    if (!selectedTimeline) return;
    setTimelineError('');
    try {
      const response = await aiDirectorApi.updateTimeline(projectId, selectedTimeline.id, { ...nextJson, expected_version: selectedTimeline.version_number });
      const updated = response.data?.timeline || response.data;
      if (updated?.id) setTimelines(current => current.map(item => item.id === updated.id ? updated : item));
      else await fetchTimelines();
    } catch (error) {
      if (isConflict(error)) { setTimelineError('This timeline changed elsewhere. Reloaded the latest version; review your edit before saving again.'); await fetchTimelines(); }
      else setTimelineError(errorMessage(error, 'Could not save timeline edit.'));
    }
  }, [fetchTimelines, projectId, selectedTimeline]);

  const persistTracks = useCallback((nextTracks: Parameters<typeof reconcileTracks>[1]) => {
    if (!selectedTimeline) return;
    try { void updateTimelineJson(reconcileTracks(selectedTimeline.timeline_json, nextTracks)); }
    catch (error) { setTimelineError(errorMessage(error, 'Timeline edit was not valid.')); }
  }, [selectedTimeline, updateTimelineJson]);

  const saveSettings = async (patch: Partial<TimelineJSON>) => {
    if (!selectedTimeline) return;
    setSettingsSaving(true); setTimelineError('');
    try { await updateTimelineJson({ ...selectedTimeline.timeline_json, ...patch }); }
    finally { setSettingsSaving(false); }
  };

  const runDirector = async () => {
    setAiRunning(true); setAiMessage('');
    try {
      const response = await aiDirectorApi.runAIDirector(projectId);
      const result = response.data;
      if (!result?.success) setAiMessage(result?.error || 'AI Director could not create a timeline.');
      else { setAiMessage('Analysis complete. The new canonical timeline is ready.'); await fetchTimelines(); }
    } catch (error) { setAiMessage(errorMessage(error, 'AI Director failed.')); }
    finally { setAiRunning(false); }
  };

  const cloneReference = async () => {
    if (!referenceId || rawIds.length === 0) return;
    setTemplateBusy(true); setTemplateMessage('Analysing reference pacing…');
    try { await templateApi.cloneProjectStyle(projectId, referenceId, rawIds); setTemplateMessage('Reference edit persisted as a new timeline.'); await fetchTimelines(); }
    catch (error) { setTemplateMessage(errorMessage(error, 'Reference analysis failed.')); }
    finally { setTemplateBusy(false); }
  };
  const applyTemplate = async (templateId: string) => {
    if (!templateId || rawIds.length === 0) return;
    setTemplateBusy(true); setTemplateMessage('Applying saved template…');
    try { await templateApi.applyProjectStyle(projectId, templateId, rawIds); setTemplateMessage('Saved template applied.'); await fetchTimelines(); }
    catch (error) { setTemplateMessage(errorMessage(error, 'Template application failed.')); }
    finally { setTemplateBusy(false); }
  };

  const queuePreview = async () => {
    if (!selectedTimeline) return;
    setRenderingPreview(true); setTimelineError('');
    try { await renderingApi.createPreviewRender(projectId, selectedTimeline.id); setRefreshJobs(value => value + 1); setInspectorTab('render'); }
    catch (error) { setTimelineError(errorMessage(error, 'Could not queue preview render.')); }
    finally { setRenderingPreview(false); }
  };
  const queueExport = async () => {
    if (!selectedTimeline || !selectedPresetId) return;
    setRenderingExport(true); setTimelineError('');
    try { await renderingApi.createExportRender(projectId, selectedTimeline.id, selectedPresetId); setRefreshJobs(value => value + 1); setInspectorTab('render'); }
    catch (error) { setTimelineError(errorMessage(error, 'Could not queue export.')); }
    finally { setRenderingExport(false); }
  };
  const deleteProject = async () => {
    if (!window.confirm('Delete this project? This cannot be undone.')) return;
    setDeleting(true); try { await projectsApi.delete(projectId); removeProject(projectId); router.push('/projects'); }
    catch (error) { setPageError(errorMessage(error, 'Could not delete project.')); } finally { setDeleting(false); }
  };

  if (isLoading) return <div className="director director-loading"><div className="flex items-center gap-3"><Loader2 className="animate-spin" size={18} /> Loading project workspace…</div></div>;
  if (!project) return <div className="director director-loading"><div className="max-w-md"><ErrorNotice onRetry={() => void loadProject()}>{pageError || 'Project not found.'}</ErrorNotice><Link className="director-btn mt-4" href="/projects"><ArrowLeft size={14} /> Back to projects</Link></div></div>;

  const json = selectedTimeline?.timeline_json;
  const color = json?.color_settings || {};
  const audio = json?.audio_settings || {};
  const videoMedia = media.filter(item => item.media_type === 'video');
  const ready = (asset: MediaAsset) => asset.status === 'ready' || asset.status === 'uploaded';

  return <div className="director">
    <header className="director-bar">
      <Link href="/projects" className="director-btn ghost icon" aria-label="Back to projects"><ArrowLeft size={16} /></Link>
      <div className="director-mark"><Clapperboard size={19} /></div>
      <div className="min-w-0 flex-1"><div className="director-kicker">AI Video Director / Project</div><h1 className="mt-1 truncate text-base font-semibold">{project.name}</h1></div>
      <div className="hidden items-center gap-3 lg:flex"><span className="director-muted text-[11px]">{media.length} media · {timelines.length} versions</span><Badge status={project.status} /></div>
      <button className="director-btn" onClick={() => void fetchTimelines()} disabled={isLoading}><RefreshCw size={14} /> Refresh</button>
      <button className="director-btn" onClick={() => void runDirector()} disabled={aiRunning || media.length === 0}>{aiRunning ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />} {aiRunning ? 'Analysing…' : 'AI auto edit'}</button>
      <button className="director-btn primary" onClick={() => void queueExport()} disabled={!selectedTimeline || !selectedPresetId || renderingExport}>{renderingExport ? <Loader2 size={14} className="animate-spin" /> : <MonitorPlay size={14} />} Export</button>
    </header>
    {pageError && <ErrorNotice onRetry={() => void loadProject()}>{pageError}</ErrorNotice>}
    {aiMessage && <div className={`director-notice ${aiMessage.includes('failed') || aiMessage.includes('could not') ? 'error' : ''}`}><Sparkles size={15} />{aiMessage}</div>}
    {timelineError && <ErrorNotice onRetry={() => void fetchTimelines()}>{timelineError}</ErrorNotice>}

    <main className="director-workspace">
      <aside className="director-panel">
        <div className="director-panel-title"><h2>Media bin</h2><button className="director-btn icon" onClick={() => fileInput.current?.click()} disabled={uploading} title="Upload media"><Plus size={15} /></button></div>
        <div className="director-panel-body pb-3">
          <button className="director-btn w-full border-dashed" onClick={() => fileInput.current?.click()} disabled={uploading}><Upload size={14} /> {uploading ? `Uploading ${uploadProgress}%` : 'Import media'}</button>
          <input ref={fileInput} type="file" className="hidden" accept="video/*,audio/*,image/*" onChange={event => { const file = event.target.files?.[0]; if (file) void upload(file); event.target.value = ''; }} />
          {uploading && <div className="mt-3 director-progress"><div style={{ width: `${uploadProgress}%` }} /></div>}
        </div>
        <div className="director-tabs mx-3"><button aria-pressed={binMode === 'media'} onClick={() => setBinMode('media')}>All media</button><button aria-pressed={binMode === 'reference'} onClick={() => setBinMode('reference')}>Reference edit</button></div>
        {binMode === 'media' ? <div className="director-media">
          {mediaLoading && <div className="director-empty">Loading media…</div>}
          {!mediaLoading && media.length === 0 && <div className="director-empty"><FolderOpen size={28} /><strong>Your bin is empty</strong>Import a video, audio file, or image to get started.</div>}
          {media.map(asset => <button key={asset.id} className="director-media-item" aria-pressed={asset.id === selectedMediaId} onClick={() => { setSelectedMediaId(asset.id); setMonitor('source'); }}>
            <span className="director-thumbnail">{asset.media_type === 'video' ? <Film size={18} /> : <Layers3 size={18} />}</span><span className="min-w-0 flex-1 text-left"><span className="block truncate text-xs">{asset.original_filename}</span><span className="mt-1 flex gap-1"><span className="director-muted text-[10px]">{asset.media_type}</span><Badge status={asset.status} /></span></span>
          </button>)}
        </div> : <ReferencePanel media={videoMedia} referenceId={referenceId} setReferenceId={setReferenceId} rawIds={rawIds} setRawIds={setRawIds} templates={templates} onClone={() => void cloneReference()} onApply={applyTemplate} busy={templateBusy} message={templateMessage} />}
      </aside>

      <section className="director-panel director-monitor">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3"><div className="director-tabs w-auto"><button aria-pressed={monitor === 'program'} onClick={() => setMonitor('program')}><MonitorPlay className="mr-1 inline" size={13} /> Program</button><button aria-pressed={monitor === 'source'} onClick={() => setMonitor('source')}><Scissors className="mr-1 inline" size={13} /> Source</button></div><div className="flex items-center gap-2 text-[11px] director-muted">{selectedTimeline ? <><span>v{selectedTimeline.version_number}</span><span>·</span><span>{timecode(selectedTimeline.total_duration)}</span></> : <span>No canonical timeline</span>}</div></div>
        <div className="director-screen">
          {monitor === 'program' && programUrl ? <video src={programUrl} controls autoPlay className="h-full w-full object-contain" /> : monitor === 'source' && sourceUrl ? <video src={sourceUrl} controls className="h-full w-full object-contain" /> : <div className="director-empty">{monitor === 'program' ? <><MonitorPlay size={35} /><strong>Program monitor</strong>{selectedTimeline ? 'Queue a preview render to see the persisted output here.' : 'Run AI auto edit or apply a reference to create a canonical timeline.'}</> : sourceLoading ? <><Loader2 size={30} className="animate-spin" /><strong>Loading source preview…</strong></> : <><Film size={35} /><strong>{selectedMedia ? selectedMedia.original_filename : 'Select source media'}</strong>{sourceError || 'Choose a video from the bin to preview it.'}</>}</div>}
        </div>
        {monitor === 'source' && selectedMedia && selectedMedia.file_size > 500 * 1024 * 1024 && <div className="mt-3 text-[10px] director-muted">Source preview uses an authenticated blob stream for now; large files may take longer to buffer.</div>}
        <div className="mt-4 flex items-center justify-between gap-3"><div className="min-w-0"><div className="director-kicker">{monitor === 'program' ? 'Rendered output' : 'Source monitor'}</div><div className="mt-1 truncate text-xs">{monitor === 'program' ? (programUrl ? 'Latest preview render' : 'No preview loaded') : (selectedMedia?.original_filename || 'No source selected')}</div></div><button className="director-btn" onClick={() => void queuePreview()} disabled={!selectedTimeline || renderingPreview}>{renderingPreview ? <Loader2 size={14} className="animate-spin" /> : <MonitorPlay size={14} />} Queue preview</button></div>
      </section>

      <aside className="director-panel director-inspector">
        <div className="director-panel-title"><h2>Inspector</h2><span className="director-muted text-[10px]">canonical fields only</span></div>
        <div className="director-panel-body">
          <div className="director-tabs mb-4"><button aria-pressed={inspectorTab === 'timeline'} onClick={() => setInspectorTab('timeline')}>Timeline</button><button aria-pressed={inspectorTab === 'color'} onClick={() => setInspectorTab('color')}>Color</button><button aria-pressed={inspectorTab === 'audio'} onClick={() => setInspectorTab('audio')}>Audio</button><button aria-pressed={inspectorTab === 'render'} onClick={() => setInspectorTab('render')}>Jobs</button></div>
          {inspectorTab === 'timeline' && <TimelineInspector timelines={timelines} selectedId={selectedTimeline?.id || ''} onSelect={setSelectedTimelineId} onRefresh={() => void fetchTimelines()} stages={stages} decisions={decisions} clipCount={clipCount} />}
          {inspectorTab === 'color' && <SettingsInspector title="Color settings" hint="Saved to timeline_json.color_settings" saving={settingsSaving} fields={[['brightness', color.brightness ?? 0, -100, 100], ['contrast', color.contrast ?? 0, -100, 100], ['saturation', color.saturation ?? 0, -100, 100]].map(([key, value, min, max]) => ({ key: key as string, value: Number(value), min: Number(min), max: Number(max) }))} onChange={(key, value) => void saveSettings({ color_settings: { ...color, [key]: value } })} />}
          {inspectorTab === 'audio' && <AudioInspector settings={audio} saving={settingsSaving} onChange={(key, value) => void saveSettings({ audio_settings: { ...audio, [key]: value } })} />}
          {inspectorTab === 'render' && <div className="space-y-5"><div><label className="director-label" htmlFor="preset">Export preset</label><select id="preset" className="director-input" value={selectedPresetId} onChange={event => setSelectedPresetId(event.target.value)}><option value="">Select a preset…</option>{presets.map(preset => <option key={preset.id} value={preset.id}>{preset.name} · {preset.width}×{preset.height} · {preset.fps}fps</option>)}</select>{presets.length === 0 && <p className="mt-2 text-[11px] director-muted">No render presets are available.</p>}</div><button className="director-btn primary w-full" onClick={() => void queueExport()} disabled={!selectedTimeline || !selectedPresetId || renderingExport}>{renderingExport ? <Loader2 size={14} className="animate-spin" /> : <MonitorPlay size={14} />} Queue export</button><RenderJobList projectId={projectId} timelineId={selectedTimeline?.id} refreshKey={refreshJobs} onPreviewReady={url => { if (programUrl) URL.revokeObjectURL(programUrl); setProgramUrl(url); setMonitor('program'); }} /></div>}
          <div className="mt-6 border-t border-[#29313b] pt-4"><button className="director-btn w-full text-rose-300" onClick={() => void deleteProject()} disabled={deleting}>{deleting ? <Loader2 size={14} className="animate-spin" /> : <X size={14} />} Delete project</button></div>
        </div>
      </aside>
    </main>

    <section className="director-sequence border-t border-[#29313b]">
      <div className="director-panel-title"><div className="flex items-center gap-3"><h2>Sequence</h2><span className="director-muted text-[10px]">{selectedTimeline ? `Version ${selectedTimeline.version_number} · ${clipCount} clips` : 'No timeline loaded'}</span></div><div className="flex items-center gap-2"><span className="director-muted text-[10px]">{selectedTimeline ? `${timecode(selectedTimeline.total_duration)} duration` : 'Create a timeline to edit'}</span></div></div>
      <div className="director-sequence-body">{selectedTimeline ? <Timeline key={selectedTimeline.id + ':' + selectedTimeline.version_number} initialTracks={tracks} duration={Math.max(1, selectedTimeline.total_duration)} onChange={persistTracks} /> : <div className="director-empty"><Scissors size={28} /><strong>Timeline is ready when you are</strong>Import footage, then run AI auto edit or use Reference edit in the media bin.</div>}</div>
    </section>
  </div>;
}

function ReferencePanel({ media, referenceId, setReferenceId, rawIds, setRawIds, templates, onClone, onApply, busy, message }: { media: MediaAsset[]; referenceId: string; setReferenceId: (value: string) => void; rawIds: string[]; setRawIds: (value: string[]) => void; templates: SavedTemplate[]; onClone: () => void; onApply: (id: string) => void; busy: boolean; message: string }) {
  const reference = media.find(item => item.id === referenceId);
  const ready = (asset?: MediaAsset) => Boolean(asset && (asset.status === 'ready' || asset.status === 'uploaded'));
  const readyRawCount = rawIds.filter(id => ready(media.find(item => item.id === id))).length;
  const allRawReady = rawIds.length > 0 && readyRawCount === rawIds.length;
  return <div className="p-3">
    <div className="director-kicker">Reference edit</div><p className="mt-2 text-[11px] leading-5 director-muted">Use an uploaded edit as the reference, or reuse a saved template. Raw footage is persisted by media ID.</p>
    <label className="director-label mt-4" htmlFor="reference">Reference video</label><select id="reference" className="director-input" value={referenceId} onChange={event => setReferenceId(event.target.value)}><option value="">Select reference…</option>{media.map(item => <option key={item.id} value={item.id}>{item.original_filename}</option>)}</select>
    <label className="director-label mt-4">Raw footage</label><div className="max-h-40 overflow-auto">{media.filter(item => item.id !== referenceId).map(item => <label className="director-check" key={item.id}><input type="checkbox" checked={rawIds.includes(item.id)} onChange={event => setRawIds(event.target.checked ? [...rawIds, item.id] : rawIds.filter(id => id !== item.id))} /><span className="min-w-0 flex-1 truncate">{item.original_filename}</span><Badge status={item.status} /></label>)}{media.length < 2 && <p className="text-[11px] director-muted">Add at least one reference and one raw video.</p>}</div>
    <div className="mt-3 flex items-center justify-between text-[10px]"><span className="director-muted">Readiness</span><span className={ready(reference) && allRawReady ? 'text-[#a9e9cc]' : 'text-[#e8c98c]'}>{ready(reference) ? 'Reference ready' : 'Reference processing'} · {readyRawCount}/{rawIds.length || 0} raw ready</span></div>
    <button className="director-btn primary mt-3 w-full" onClick={onClone} disabled={!ready(reference) || !allRawReady || busy}>{busy ? <Loader2 size={14} className="animate-spin" /> : <Wand2 size={14} />} Clone reference</button>
    <div className="my-5 border-t border-[#29313b]" /><label className="director-label" htmlFor="saved-template">Saved template</label><select id="saved-template" className="director-input" defaultValue="" onChange={event => { if (event.target.value) onApply(event.target.value); }} disabled={busy || !allRawReady}><option value="">Select saved template…</option>{templates.map(template => <option key={template.id} value={template.id}>{template.name}</option>)}</select>{templates.length === 0 && <p className="mt-2 text-[11px] director-muted">No saved templates available.</p>}{rawIds.length > 0 && !allRawReady && <p className="mt-2 text-[10px] text-[#e8c98c]">Wait for selected raw media to finish processing before applying a template.</p>}
    {message && <p className="mt-3 text-[11px] text-[#a9e9cc]">{message}</p>}
  </div>;
}

function TimelineInspector({ timelines, selectedId, onSelect, onRefresh, stages, decisions, clipCount }: { timelines: EditorTimeline[]; selectedId: string; onSelect: (id: string) => void; onRefresh: () => void; stages: { stage: string; status: string; message?: string }[]; decisions: DirectorDecision[]; clipCount: number }) {
  return <div className="space-y-5"><div><div className="flex items-center justify-between"><label className="director-label mb-0" htmlFor="timeline-version">Canonical version</label><button className="director-btn icon" onClick={onRefresh} title="Refetch timelines"><RefreshCw size={13} /></button></div><select id="timeline-version" className="director-input mt-2" value={selectedId} onChange={event => onSelect(event.target.value)}><option value="">No version</option>{timelines.map(item => <option key={item.id} value={item.id}>Version {item.version_number} · {timecode(item.total_duration)}</option>)}</select></div><div className="grid grid-cols-2 gap-2"><Metric label="Cuts" value={clipCount} /><Metric label="Decisions" value={decisions.length} /></div><div><div className="director-kicker mb-3">Decision trace</div>{stages.length === 0 && decisions.length === 0 && <p className="text-[11px] director-muted">No director metadata is present on this canonical timeline.</p>}{stages.map(stage => <div className="director-trace" key={`${stage.stage}-${stage.status}`}><div className="text-xs">{stage.stage}</div><div className="mt-1 text-[10px] director-muted">{stage.status}{stage.message ? ` · ${stage.message}` : ''}</div></div>)}{decisions.slice(0, 8).map(decision => <div className="border-t border-[#29313b] py-2" key={`${decision.clip_id}-${decision.start}`}><div className="text-[11px] text-[#dbe8e2]">{timecode(decision.start)} → {timecode(decision.end)}</div><div className="mt-1 text-[10px] director-muted">{decision.reason}</div></div>)}{decisions.length > 8 && <p className="text-[10px] director-muted">Showing 8 of {decisions.length} decisions.</p>}</div></div>;
}
function Metric({ label, value }: { label: string; value: string | number }) { return <div className="rounded-md bg-[#10151c] p-2"><div className="text-[10px] director-muted">{label}</div><strong className="mt-1 block text-sm">{value}</strong></div>; }
function SettingsInspector({ title, hint, fields, onChange, saving }: { title: string; hint: string; fields: { key: string; value: number; min: number; max: number }[]; onChange: (key: string, value: number) => void; saving: boolean }) { return <div><div className="director-kicker">{title}</div><p className="mt-2 text-[11px] director-muted">{hint}</p>{fields.map(field => <label key={field.key} className="mt-5 block"><div className="flex justify-between text-xs"><span className="capitalize">{field.key}</span><span className="director-muted">{field.value}</span></div><input className="mt-2 w-full" type="range" min={field.min} max={field.max} value={field.value} disabled={saving} onChange={event => onChange(field.key, Number(event.target.value))} /></label>)}{saving && <p className="mt-3 text-[10px] director-muted">Saving canonical settings…</p>}</div>; }
function AudioInspector({ settings, onChange, saving }: { settings: { normalize?: boolean; ducking?: boolean }; onChange: (key: string, value: boolean) => void; saving: boolean }) { return <div><div className="director-kicker">Audio settings</div><p className="mt-2 text-[11px] director-muted">Only persisted timeline audio fields are exposed.</p><label className="director-check mt-4"><input type="checkbox" checked={Boolean(settings.normalize)} disabled={saving} onChange={event => onChange('normalize', event.target.checked)} /> Normalize dialogue</label><label className="director-check"><input type="checkbox" checked={Boolean(settings.ducking)} disabled={saving} onChange={event => onChange('ducking', event.target.checked)} /> Duck music under dialogue</label>{saving && <p className="mt-3 text-[10px] director-muted">Saving canonical settings…</p>}</div>; }
