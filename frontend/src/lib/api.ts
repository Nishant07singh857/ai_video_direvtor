import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api/v1';

export const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for auth
api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Globally catch and log API errors
    console.error('API Error:', error.response?.data?.message || error.message);
    
    // Fix Pydantic validation error array rendering in React
    if (error.response?.data?.detail && Array.isArray(error.response.data.detail)) {
      error.response.data.detail = error.response.data.detail.map((err: any) => err.msg || JSON.stringify(err)).join(', ');
    } else if (error.response?.data?.detail && typeof error.response.data.detail === 'object') {
      error.response.data.detail = JSON.stringify(error.response.data.detail);
    }
    
    if (error.response?.status === 401) {
      if (typeof window !== 'undefined') {
        localStorage.removeItem('access_token');
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authApi = {
  register: (data: { email: string; password: string; full_name?: string }) =>
    api.post('/auth/register', data),
  login: (email: string, password: string) => {
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);
    return api.post('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
  },
  me: () => api.get('/auth/me'),
};

// Projects API
export const projectsApi = {
  list: (page = 1, pageSize = 20) =>
    api.get('/projects', { params: { page, page_size: pageSize } }),
  create: (data: { name: string; description?: string; platform?: string }) =>
    api.post('/projects', data),
  get: (id: string) => api.get(`/projects/${id}`),
  update: (id: string, data: { name?: string; description?: string; platform?: string; status?: string }) =>
    api.patch(`/projects/${id}`, data),
  delete: (id: string) => api.delete(`/projects/${id}`),
};

// Media API
export const mediaApi = {
  list: (projectId: string, page = 1, pageSize = 20) =>
    api.get(`/projects/${projectId}/media`, { params: { page, page_size: pageSize } }),
  upload: (projectId: string, file: File, onProgress?: (progress: number) => void) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post(`/projects/${projectId}/media`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(progress);
        }
      },
    });
  },
  get: (mediaId: string) => api.get(`/media/${mediaId}`),
  streamBlob: (mediaId: string, signal?: AbortSignal) =>
    api.get<Blob>(`/media/${mediaId}/stream`, { responseType: 'blob', signal }),
  delete: (mediaId: string) => api.delete(`/media/${mediaId}`),
};

// Health API
export const healthApi = {
  check: () => api.get('/health'),
  db: () => api.get('/health/db'),
  redis: () => api.get('/health/redis'),
};

// AI Director API
export const aiDirectorApi = {
  // Knowledge Graph
  buildKnowledgeGraph: (projectId: string) =>
    api.post(`/projects/${projectId}/knowledge-graph/build`),
  getKnowledgeGraph: (projectId: string) =>
    api.get(`/projects/${projectId}/knowledge-graph`),

  // Shot Rankings
  rankShots: (projectId: string, storyCandidateId?: string) =>
    api.post(`/projects/${projectId}/shots/rank`, { story_candidate_id: storyCandidateId }),
  getShotRankings: (projectId: string, storyCandidateId?: string) =>
    api.get(`/projects/${projectId}/shots/rankings`, { params: { story_candidate_id: storyCandidateId } }),

  // Stories
  generateStories: (projectId: string, maxCandidates = 5) =>
    api.post(`/projects/${projectId}/stories`, { max_candidates: maxCandidates }),
  listStories: (projectId: string) =>
    api.get(`/projects/${projectId}/stories`),
  getStory: (projectId: string, storyId: string) =>
    api.get(`/projects/${projectId}/stories/${storyId}`),
  rankStories: (projectId: string, storyId: string) =>
    api.post(`/projects/${projectId}/stories/${storyId}/rank`),

  // Sequence Planning
  planSequence: (projectId: string, storyId: string) =>
    api.post(`/projects/${projectId}/stories/${storyId}/sequence`),

  // Timelines
  generateTimeline: (projectId: string, storyCandidateId: string) =>
    api.post(`/projects/${projectId}/timelines`, { story_candidate_id: storyCandidateId }),
  listTimelines: (projectId: string) =>
    api.get(`/projects/${projectId}/timelines`),
  getTimeline: (projectId: string, timelineId: string) =>
    api.get(`/projects/${projectId}/timelines/${timelineId}`),
  regenerateTimeline: (projectId: string, timelineId: string) =>
    api.post(`/projects/${projectId}/timelines/${timelineId}/regenerate`),

  // Full AI Director Pipeline
  runAIDirector: (projectId: string, maxStoryCandidates = 5) =>
    api.post(`/projects/${projectId}/ai-director/analyze`, { max_story_candidates: maxStoryCandidates }),
  updateTimeline: (projectId: string, timelineId: string, data: any) =>
    api.patch(`/projects/${projectId}/timelines/${timelineId}`, data),
  getStatus: (projectId: string) =>
    api.get(`/projects/${projectId}/ai-director/status`),
  promptEdit: (projectId: string, prompt: string, timelineId?: string) =>
    api.post(`/projects/${projectId}/ai-director/prompt`, { prompt, timeline_id: timelineId }),
  getVisionAnalysis: (projectId: string) =>
    api.get(`/projects/${projectId}/ai-director/vision-analysis`),
};

// Rendering API
export const renderingApi = {
  // Preview Render
  createPreviewRender: (projectId: string, timelineId: string) =>
    api.post(`/rendering/projects/${projectId}/timelines/${timelineId}/preview`),

  // Export Render
  createExportRender: (projectId: string, timelineId: string, presetId?: string) =>
    api.post(`/rendering/projects/${projectId}/timelines/${timelineId}/export`, { preset_id: presetId }),

  // Render Jobs
  listRenderJobs: (projectId: string, params?: { timeline_id?: string; job_type?: string; status?: string; limit?: number; offset?: number }) =>
    api.get(`/rendering/projects/${projectId}/renders`, { params }),
  getRenderJob: (projectId: string, renderJobId: string) =>
    api.get(`/rendering/projects/${projectId}/renders/${renderJobId}`),
  downloadRender: (projectId: string, renderJobId: string, signal?: AbortSignal) =>
    api.get<Blob>(`/rendering/projects/${projectId}/renders/${renderJobId}/download`, { responseType: 'blob', signal }),
  cancelRenderJob: (projectId: string, renderJobId: string) =>
    api.delete(`/rendering/projects/${projectId}/renders/${renderJobId}`),
  retryRenderJob: (projectId: string, renderJobId: string) =>
    api.post(`/rendering/projects/${projectId}/renders/${renderJobId}/retry`),
  deleteRenderJob: (projectId: string, renderJobId: string) =>
    api.delete(`/rendering/projects/${projectId}/renders/${renderJobId}/delete`),

  // Render Presets
  listRenderPresets: () =>
    api.get('/rendering/render-presets'),
  getRenderPreset: (presetId: string) =>
    api.get(`/rendering/render-presets/${presetId}`),
};

// Template-first editing API. The project-scoped endpoint keeps both the
// reference and raw footage inside the authenticated project boundary.
export const templateApi = {
  list: () => api.get('/templates'),
  applyProjectStyle: (projectId: string, templateId: string, rawMediaIds: string[]) =>
    api.post(`/templates/projects/${projectId}/apply`, { template_id: templateId, raw_media_ids: rawMediaIds }),
  cloneProjectStyle: (projectId: string, referenceMediaId: string, rawMediaIds: string[]) =>
    api.post(`/templates/projects/${projectId}/clone`, {
      reference_media_id: referenceMediaId,
      raw_media_ids: rawMediaIds,
    }),
};
// Search API
export const searchApi = {
  semanticSearch: (query: string, projectId?: string) =>
    api.get('/search', { params: { query, project_id: projectId } }),
};
