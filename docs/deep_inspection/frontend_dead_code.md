# Frontend Deep Inspection: Dead Code & Unwired Features Report

## 1. Dead Code (Completely Unused Components)
The following 15 components are fully defined in the `components/` directory but are **never imported or rendered** anywhere in the Next.js application (`app/` or `components/`). They represent orphaned code that the user can never reach from the UI:

- **Film/Script:** `components/film/ScreenplayPanel.tsx`
- **Media:** `components/media/ImageProperties.tsx`, `components/media/ProjectBin.tsx`
- **Multicam:** `components/multicam/AngleViewer.tsx`
- **Project History/Export:** `components/project/ExportInterchangeModal.tsx`, `components/project/HistoryPanel.tsx`
- **Rendering:** `components/rendering/ExportModal.tsx`, `components/rendering/RenderJobList.tsx`, `components/rendering/RenderPanel.tsx`, `components/rendering/VideoPreview.tsx`
- **Review/Collab:** `components/review/CommentPanel.tsx`, `components/review/ShareModal.tsx`
- **Styles/Templates:** `components/styles/StyleClonerModal.tsx`, `components/templates/TemplateLibrary.tsx`
- **Transcripts:** `components/transcript/TranscriptPanel.tsx`

## 2. Unwired Features (UI Rendered but Disconnected from API)
In the main project workspace (`app/projects/[id]/page.tsx`), the Non-Linear Editor (NLE) layout includes several panels that look fully functional but are purely visual. They either have empty props, local-only state, or `console.log` handlers, and do not connect to `api.ts`:

- **`TransformPanel`**: Rendered with a dummy event handler: `onChange={(state) => console.log('Transform changed:', state)}`. Updates are lost on refresh.
- **`EssentialGraphicsPanel`**: Rendered with a dummy event handler: `onUpdate={(data) => console.log('Graphics updated:', data)}`.
- **`AudioMixer`**: Rendered with no props (`<AudioMixer className="..." />`). Sliders manipulate local component state but are completely disconnected from timeline audio tracks.
- **`LumetriPanel`**: Maintains fully isolated local state (`exposure`, `contrast`, `LUT`). Not bound to the active timeline clip.
- **`EffectsPanel`**: Isolated local state, disconnected from the actual backend pipeline.

## 3. Hardcoded Placeholders and Mock Data
Several components rely on hardcoded dummy data rather than fetching dynamically from `api.ts`. 

### Rendered Components:
- **`MediaBrowser.tsx`**: Fakes API integration. It uses a hardcoded `MOCK_RESULTS` array and wraps its search functionality in a `setTimeout` to mimic network latency. It completely ignores `mediaApi`.

### Dead/Unused Components (also full of mock data):
- **`HistoryPanel.tsx`**: Relies on a hardcoded `DUMMY_HISTORY` array.
- **`TemplateLibrary.tsx`**: Uses a hardcoded `MOCK_TEMPLATES` array and fakes application via `console.log('Applying template:', selectedTemplate)`.
- **`CommentPanel.tsx`**: Hardcodes all new comment timestamps to `'00:00:00'`.
- **`ShareModal.tsx`**: Generates a fake share link using `Math.random()` (`setLink('https://review.aivideodirector.com/' + Math.random().toString(36).substring(7))`).

## 4. Hooks / State Anomalies
- The NLE panels (Lumetri, Transform, Audio, Effects) define many `useState` hooks internally that track user input visually but **never bubble up** to a parent container or trigger `useEffect` hooks for API synchronization.
- While `timelines` and `mediaAssets` correctly fetch from `aiDirectorApi` and `mediaApi` in the `[id]/page.tsx` view, the actual editing interactions in the aforementioned tools fail to execute PUT/PATCH requests to save the user's progress.
