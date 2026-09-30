# Frontend Architecture Audit Report

**Date:** September 28, 2026
**Project:** AI Video Director
**Scope:** Frontend (`frontend/` directory)

---

## 1. Executive Summary
An in-depth code audit of the frontend architecture was conducted, focusing on React hook usage, state management, UI/UX (responsive design & a11y), and application configuration. While the foundation uses Next.js and Tailwind CSS effectively, several critical issues were identified that compromise reliability, user experience, and deployment flexibility. 

The most severe issues include **Server-Side Rendering (SSR) crashes** due to unsafe browser API access, **broken core features** (timeline loading omitted), **hardcoded API URLs** bypassing environment configurations, and **swallowed errors** resulting in misleading UI states.

---

## 2. Critical Findings & Hydration / SSR Issues

### 2.1 Unsafe `localStorage` Access in API Interceptors
**Location:** `src/lib/api.ts` (Lines 13-14)
**Issue:** The Axios request interceptor accesses `localStorage.getItem('access_token')` directly in the module scope. Because Next.js server-renders Client Components on the initial page load, this code executes on the Node.js server where `localStorage` is undefined. 
**Impact:** This will throw a `ReferenceError: localStorage is not defined`, crashing the SSR process and causing a hard 500 error or a fallback to pure client-side rendering with hydration mismatches.
**Recommendation:** Wrap the `localStorage` access in a `typeof window !== 'undefined'` check, or ideally, manage authentication tokens via HTTP-only cookies to support SSR seamlessly.

### 2.2 Unused/Broken Core Feature (Timeline Fetching)
**Location:** `src/app/projects/[id]/page.tsx` (Lines 51-61)
**Issue:** The function `fetchTimelines` is defined via `useCallback` to retrieve timeline data from the AI Director API. However, **it is never called** within any `useEffect` or event handler.
**Impact:** The `timelines` state remains permanently empty (`[]`). Consequently, the core timeline rendering logic defaults to a basic sequence of unedited media assets, completely breaking the AI-generated timeline feature.
**Recommendation:** Add `fetchTimelines()` to the `useEffect` that initializes project data.

### 2.3 Zustand Persist Middleware Hydration Risks
**Location:** `src/lib/store.ts`
**Issue:** `useAuthStore` uses Zustand's `persist` middleware. When components consume this store immediately on mount, the server renders the initial state (empty), while the client instantly hydrates with the persisted `localStorage` state. 
**Impact:** This typically leads to React Hydration Mismatches (e.g., text content did not match server-rendered HTML).
**Recommendation:** Ensure hydration is strictly handled, or wait for the component to mount (via a custom `useStore` hook or a `useEffect` flag) before rendering authenticated UI components.

---

## 3. State Management & Data Fetching

### 3.1 Swallowed Errors & Misleading UI
**Location:** `src/app/projects/page.tsx` (Lines 28-36)
**Issue:** In `loadProjects`, if the `projectsApi.list()` call fails, the error is caught and logged to the console, but no error state is set. The `isLoading` state is set to `false`.
**Impact:** Users will see the "No projects yet. Create your first project" empty state instead of an error message, masking the actual system failure and confusing the user.
**Recommendation:** Implement a dedicated `error` state (e.g., `const [error, setError] = useState(null)`) and display an error alert with a "Retry" button.

### 3.2 Inefficient Polling and Unnecessary Re-renders
**Location:** `src/app/projects/[id]/page.tsx` (Lines 88-97)
**Issue:** The component polls `fetchMediaAssets()` every 5 seconds using `setInterval`. Inside `fetchMediaAssets`, `setMediaLoading(true)` and `setMediaLoading(false)` are called. 
**Impact:** Even though `mediaLoading` isn't actively used in the JSX to show a spinner, invoking state setters every 5 seconds forces the entire NLE Workspace component tree to re-render constantly, consuming excess CPU and potentially interrupting user interactions (like dragging clips on the timeline).
**Recommendation:** Add a boolean parameter `fetchMediaAssets(isPolling = false)` to skip the loading state updates when the function is invoked by the background interval.

### 3.3 State Mutation Anti-Pattern
**Location:** `src/components/timeline/Timeline.tsx` (Line 55)
**Issue:** Deep cloning state via `JSON.parse(JSON.stringify(currentTracks))` is used to mutate tracks.
**Impact:** This drops any non-serializable data (functions, Dates, undefined). While it works for simple data, it is a fragile pattern and negatively impacts performance.
**Recommendation:** Use a library like `immer` or standard immutable spread operators to update nested state arrays safely.

---

## 4. Environment Variables & Hardcoded URLs

### 4.1 Hardcoded Video Stream URL
**Location:** `src/app/projects/[id]/page.tsx` (Line 262)
**Issue:** The video player source is hardcoded to `http://localhost:8000/api/v1/media/${mediaAssets[0].id}/stream`.
**Impact:** This bypasses `process.env.NEXT_PUBLIC_API_URL` entirely. If deployed to production or a staging environment, video playback will fail because it will attempt to fetch from localhost on the user's machine.
**Recommendation:** Replace this with a utility function that concatenates the active `API_URL` (from `src/lib/api.ts` or environment variables) with the specific endpoint.

---

## 5. UI, Responsive Design, and Accessibility (A11y)

### 5.1 Native Confirm Dialogs
**Location:** `src/app/projects/page.tsx` (Line 61) and `src/app/projects/[id]/page.tsx` (Line 101)
**Issue:** Destructive actions (deleting a project) rely on the native browser `confirm()` method.
**Impact:** Native confirm dialogs block the main thread, provide a poor user experience, cannot be styled to match the app's dark theme, and have inconsistent accessibility behaviors across browsers.
**Recommendation:** Implement a custom modal component (like the `CreateProjectModal`) for confirmation dialogs, utilizing proper ARIA roles (`role="alertdialog"`).

### 5.2 Missing ARIA Labels on Icon Buttons
**Location:** `src/components/MediaUpload.tsx` (Line 138-145)
**Issue:** The "Remove file" `<Button>` solely uses an `<X>` icon without accessible text or an `aria-label`.
**Impact:** Screen reader users will not know what the button does.
**Recommendation:** Add `aria-label="Remove file"` to the button or use visually hidden text.

### 5.3 Dead Prop / Incomplete Implementation
**Location:** `src/components/MediaUpload.tsx` (Line 194-200)
**Issue:** The `MediaList` component accepts an `onRefresh` prop, but it is never utilized within the component's JSX (e.g., no refresh button is rendered).
**Impact:** Features relying on manual refresh are broken.
**Recommendation:** Implement a refresh button in the `MediaList` header that invokes `onRefresh()`.

---

## Conclusion
The frontend exhibits a strong structural foundation, but the identified issues in SSR safety, state stability, and hardcoded variables must be addressed before any production deployment. Prioritize fixing the `localStorage` access in `api.ts`, the missing timeline fetch invocation, and the hardcoded video stream URL, as these directly break core application functionality.
