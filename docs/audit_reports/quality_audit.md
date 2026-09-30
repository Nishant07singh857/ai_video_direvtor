# Code Quality and Repo Clutter Audit Report

**Date:** 2026-09-28
**Scope:** `d:\ai-video-director`
**Focus Areas:** Extreme complexity hotspots, Scattered ad-hoc scripts, Missing `.gitignore` rules (tracked media), and Duplicated logic.

## 1. Executive Summary
An in-depth audit of the repository reveals several structural and maintainability issues that need immediate attention. The repository suffers from scattered ad-hoc utility scripts, tracked media/database files due to incomplete `.gitignore` rules, and a few high-complexity hotspots within the video engine module. Addressing these issues will greatly improve the developer experience and project maintainability.

## 2. Extreme Complexity Hotspots
Static analysis of the repository identified the following files exceeding the recommended limits (length > 500 lines or cyclomatic complexity > 15):

*   **`video_engine/rendering/timeline_to_ffmpeg.py`**
    *   **Length:** 675 lines
    *   **Complexity:** Max function complexity of 46 (Critical)
    *   **Recommendation:** Refactor this module immediately. A cyclomatic complexity of 46 indicates heavily nested logic, likely within a massive monolithic translation function. Split this into smaller, testable strategy classes or helper functions for different node types.
*   **`video_engine/rendering/ffmpeg_renderer.py`**
    *   **Length:** 411 lines
    *   **Complexity:** Max function complexity of 16 (Warning)
    *   **Recommendation:** Minor refactoring needed to break down complex rendering phases.
*   **`video_engine/timeline/builder.py`**
    *   **Length:** 240 lines
    *   **Complexity:** Max function complexity of 22 (High)
    *   **Recommendation:** Although under 500 lines, the high complexity suggests a single function is bearing too much responsibility for timeline assembly.

## 3. Scattered Ad-Hoc Scripts
The repository is polluted with numerous top-level and backend-level ad-hoc scripts (`fix_*`, `check_*`, `test_*`) that are not properly organized into a `scripts/` or `tests/` directory. This creates significant repository clutter.

**Root Level:**
*   `check_rels.py`
*   `fix_imports.py`
*   `fix_indexes.py`
*   `fix_indexes2.py`
*   `fix_models.py`

**`backend/` Directory:**
*   `check_db.py`, `check_path.py`, `check_timelines.py`, `check_t_json.py`
*   `fix_assets.py`, `fix_awaits.py`, `fix_bom.py`, `fix_fallback.py`, `fix_fallback_clean.py`, `fix_fk.py`, `fix_index.py`, `fix_llm.py`, `fix_media.py`
*   `test_ai.py`, `test_perf.py`, `test_phase3_e2e.py`, `test_phase4_e2e.py`

**Recommendation:** 
1. Create a `scripts/` directory for operational, one-off, and migration scripts.
2. Move e2e and specific test scripts into the `tests/` directory suite.
3. Remove obsolete scripts.

## 4. Tracked Media and Missing `.gitignore` Rules
A significant issue is the tracking of binary media files (`.mp4`), database files (`.db`), and cache files, which bloats the repository size and slows down cloning/operations. The `.gitignore` is either missing or incorrectly configured.

**Tracked Artifacts Include:**
*   **Root Level:** `test.mp4`, `test_ai_video_director.db`
*   **Backend Level:** `ai_video_director.db`, `test_e2e.mp4`, `test_final_e2e.mp4`, `test_full_analysis.mp4`, `test_shot_detect.mp4`
*   **Mypy Cache:** 16+ SQLite databases under `backend/.mypy_cache/3.11/`
*   **User Uploads/Media:** Dozens of `.mp4` files tracked within:
    *   `backend/media/projects/*/*.mp4`
    *   `uploads/*/*.mp4`

**Recommendation:** 
1. Add `*.mp4`, `*.db`, `.mypy_cache/`, `backend/media/`, and `uploads/` to `.gitignore`.
2. Run `git rm --cached` on the existing files to untrack them without deleting the local copies.

## 5. Duplicated Logic (DRY Violations)
An exact-match file analysis did not reveal full file duplications; however, the presence of paired scripts (e.g., `fix_indexes.py` and `fix_indexes2.py`, `fix_fallback.py` and `fix_fallback_clean.py`) heavily suggests duplicated ad-hoc logic or multiple iterations of the same task that haven't been cleaned up. 

**Recommendation:** Consolidate these paired scripts. Review the `video_engine` codebase with a structural similarity checker to uncover further logical duplications.

---
**Audit Conclusion:** The project requires immediate cleanup of its repository structure. Refactoring the video engine rendering modules and securing the `.gitignore` are the highest priority items to ensure future scalability and team velocity.
