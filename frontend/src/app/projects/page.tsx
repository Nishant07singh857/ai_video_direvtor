'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ArrowRight, Clapperboard, Loader2, Plus, Trash2, X } from 'lucide-react';
import { projectsApi } from '@/lib/api';
import { ProjectCreate } from '@/types';
import { useProjectStore } from '@/lib/store';
import { formatDate, getPlatformLabel } from '@/lib/utils';

export default function ProjectsPage() {
  const router = useRouter();
  const { projects, setProjects, addProject, removeProject } = useProjectStore();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [deleting, setDeleting] = useState('');
  const [form, setForm] = useState<ProjectCreate>({ name: '', description: '', platform: undefined });

  const load = useCallback(async () => {
    setLoading(true); setError('');
    try { const response = await projectsApi.list(); setProjects(response.data.projects || []); }
    catch { setError('Could not load projects.'); }
    finally { setLoading(false); }
  }, [setProjects]);
  useEffect(() => { void load(); }, [load]);

  const create = async (event: React.FormEvent) => {
    event.preventDefault(); setCreating(true); setError('');
    try { const response = await projectsApi.create(form); addProject(response.data); setShowCreate(false); setForm({ name: '', description: '', platform: undefined }); router.push(`/projects/${response.data.id}`); }
    catch (err: any) { setError(err.response?.data?.detail || 'Could not create project.'); }
    finally { setCreating(false); }
  };
  const remove = async (id: string) => {
    if (!window.confirm('Delete this project? This cannot be undone.')) return;
    setDeleting(id); try { await projectsApi.delete(id); removeProject(id); } catch { setError('Could not delete project.'); } finally { setDeleting(''); }
  };

  return <div className="director">
    <header className="director-bar"><Link href="/" className="director-mark"><Clapperboard size={19} /></Link><div className="flex-1"><div className="director-kicker">AI Video Director</div><h1 className="mt-1 text-base font-semibold">Projects</h1></div><button className="director-btn primary" onClick={() => setShowCreate(true)}><Plus size={15} /> New project</button></header>
    <main className="mx-auto max-w-6xl px-5 py-10 sm:px-8"><div className="mb-8 flex items-end justify-between gap-4"><div><div className="director-kicker">Workspace</div><h2 className="mt-2 text-2xl font-semibold">Your productions</h2><p className="mt-2 director-muted">Open a project to edit a canonical timeline, inspect AI decisions, and render outputs.</p></div><span className="director-badge">{projects.length} project{projects.length === 1 ? '' : 's'}</span></div>
      {error && <div className="director-notice error mb-5">{error}</div>}
      {loading ? <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">{[1, 2, 3].map(item => <div className="h-44 animate-pulse rounded-xl border border-[#29313b] bg-[#15191f]" key={item} />)}</div> : projects.length === 0 ? <div className="director-panel rounded-xl border border-dashed border-[#42505e] p-16 text-center"><Clapperboard size={32} className="mx-auto text-[#7890a1]" /><h3 className="mt-4 text-base font-medium">No projects yet</h3><p className="mt-2 director-muted">Start with a project and bring your footage into the media bin.</p><button className="director-btn primary mt-6" onClick={() => setShowCreate(true)}><Plus size={15} /> Create project</button></div> : <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">{projects.map(project => <article className="director-panel rounded-xl border border-[#29313b] p-5 transition hover:border-[#516274]" key={project.id}><div className="flex items-start justify-between gap-3"><div className="min-w-0"><h3 className="truncate text-base font-semibold">{project.name}</h3><p className="mt-2 min-h-10 line-clamp-2 text-xs director-muted">{project.description || 'Untitled production'}</p></div><button className="director-btn icon text-rose-300" onClick={() => void remove(project.id)} disabled={deleting === project.id} title="Delete project">{deleting === project.id ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={14} />}</button></div><div className="mt-5 flex items-center gap-2">{project.platform && <span className="director-badge">{getPlatformLabel(project.platform)}</span>}<span className="director-badge">{project.status}</span></div><div className="mt-5 flex items-center justify-between border-t border-[#29313b] pt-4"><span className="text-[10px] director-muted">Created {formatDate(project.created_at)}</span><Link className="director-btn" href={`/projects/${project.id}`}>Open <ArrowRight size={14} /></Link></div></article>)}</div>}
    </main>
    {showCreate && <div className="fixed inset-0 z-50 grid place-items-center bg-black/70 p-4" role="dialog" aria-modal="true"><form className="director-panel w-full max-w-md rounded-xl border border-[#3a4652] p-6 shadow-2xl" onSubmit={create}><div className="mb-6 flex items-center justify-between"><div><div className="director-kicker">New production</div><h2 className="mt-1 text-lg font-semibold">Create project</h2></div><button type="button" className="director-btn icon" onClick={() => setShowCreate(false)} aria-label="Close"><X size={15} /></button></div><label className="director-label" htmlFor="project-name">Project name</label><input id="project-name" className="director-input" autoFocus required value={form.name} onChange={event => setForm({ ...form, name: event.target.value })} placeholder="Summer campaign" /><label className="director-label mt-4" htmlFor="project-description">Description</label><textarea id="project-description" className="director-input min-h-20" value={form.description} onChange={event => setForm({ ...form, description: event.target.value })} placeholder="What are you making?" /><label className="director-label mt-4" htmlFor="project-platform">Platform</label><select id="project-platform" className="director-input" value={form.platform || ''} onChange={event => setForm({ ...form, platform: (event.target.value || undefined) as ProjectCreate['platform'] })}><option value="">Not selected</option><option value="youtube">YouTube</option><option value="instagram">Instagram</option><option value="shorts">YouTube Shorts</option></select>{error && <div className="director-notice error mt-4">{error}</div>}<div className="mt-6 flex justify-end gap-2"><button type="button" className="director-btn" onClick={() => setShowCreate(false)}>Cancel</button><button className="director-btn primary" type="submit" disabled={creating}>{creating ? <Loader2 size={14} className="animate-spin" /> : <Plus size={15} />} Create project</button></div></form></div>}
  </div>;
}
