# Backend Architecture Audit Report

## 1. Executive Summary
An in-depth architectural audit of the `backend/app/` directory for the AI Video Director platform has revealed several critical vulnerabilities, severe performance bottlenecks, and structural anti-patterns. Immediate remediation is required to ensure system stability, security, and scalability.

## 2. Findings & Analysis

### 2.1 Database & Query Performance (N+1, Pagination, Leaks)
**High Connection Pool Settings (`core/database.py`)**
- **Issue:** The `create_async_engine` configures a massive connection pool: `pool_size=100` and `max_overflow=200`. For PostgreSQL, default `max_connections` is usually 100. This configuration will rapidly exhaust database connections under moderate load, leading to immediate connection refusal and cascading failures.
- **Recommendation:** Reduce `pool_size` to `10-20` and `max_overflow` to `10`. Use a connection bouncer like PgBouncer for handling higher concurrencies.

**Severe N+1 Query Problem (`api/rendering.py`)**
- **Issue:** In the `list_render_jobs` endpoint, the system fetches a list of jobs via `render_job_service.list_jobs()`, then iterates over the result set in a loop, calling `await render_job_service.get_job_info(job)` for each item. This executes $N$ additional database queries sequentially per request.
- **Recommendation:** Refactor `list_jobs` to use eager loading (e.g., `selectinload` or `joinedload`) to fetch all associated job info in a single SQL query. 

### 2.2 API Boundaries & Error Handling
**Catastrophic Global Exception Handlers (`main.py`)**
- **Issue:** The global exception handlers in `main.py` intercept `RequestValidationError` and `Exception` (specifically DB errors), returning a **200 OK** status code with `{"status": "bypass"}`.
- **Impact:** This destroys HTTP semantics, masks critical system failures from monitoring tools (like Prometheus or Datadog), and prevents clients from correctly handling bad requests or outages.
- **Recommendation:** Remove these testing bypasses. Return standard 422 for validation errors and 500 for unhandled internal exceptions. 

**Broken Object Level Authorization (BOLA/IDOR) (`api/media.py`)**
- **Issue:** The `stream_media` endpoint looks up a media asset by `media_id` without validating that the asset belongs to the `current_user` (in fact, `current_user` is completely missing from the FastAPI dependencies for this route). 
- **Recommendation:** Enforce ownership validation by injecting `Depends(get_current_user)` and ensuring the media's `project.user_id` matches the requester's ID.

**Dummy Authentication Backdoors (`main.py`)**
- **Issue:** `dummy_auth` endpoints are overriding `/api/v1/auth/register` and `/api/v1/auth/login`, issuing a hardcoded `"access_token": "dummy_bypass_token_123"`.
- **Recommendation:** Immediately remove these development mock endpoints to prevent unauthorized backdoor access in production environments.

### 2.3 Concurrency & Async Misuse
**Unsafe Fire-and-Forget Tasks (`api/media.py`, `api/rendering.py`)**
- **Issue:** Widespread misuse of `asyncio.create_task(process_and_run_pipeline())` inside request handlers without retaining a strong reference to the task. 
- **Impact:** Python's garbage collector can destroy these background tasks mid-execution. Furthermore, failures inside these tasks are silently swallowed (`except Exception as e: ...`), leaving the system in an inconsistent state without logging.
- **Recommendation:** Use a robust background task queue (e.g., Celery, RQ) for processing media and rendering. For lightweight tasks, use FastAPI's built-in `BackgroundTasks` properly.

**Synchronous ML Execution in HTTP Routes (`api/ai_director.py`)**
- **Issue:** The `/projects/{project_id}/ai-director/analyze` endpoint executes the entire AI pipeline inline via `await service.run_full_pipeline(...)`. 
- **Impact:** Given the heavy nature of video ML pipelines, this will invariably cause HTTP timeouts (e.g., beyond 30-60s) for end users.
- **Recommendation:** Refactor to an asynchronous job model: return a `job_id` immediately (202 Accepted) and require the client to poll a status endpoint or receive a WebSocket event upon completion.

### 2.4 Configuration & Secrets Management
**Hardcoded Secrets & Defaults (`core/config.py`)**
- **Issue:** Sensitive configurations such as `SECRET_KEY = "dev-secret-key-change-in-production"` and `DATABASE_URL` containing plaintext credentials (`postgres:postgres`) are hardcoded as fallback defaults.
- **Recommendation:** Use Pydantic's `BaseSettings` strictly without insecure fallbacks. The application should fast-fail on startup if `SECRET_KEY` or `DATABASE_URL` environment variables are missing in non-development environments.

## 3. Action Plan
1. **Critical:** Remove dummy auth endpoints and fix global exception handlers in `main.py`.
2. **Critical:** Secure the `stream_media` route to prevent unauthorized media access.
3. **High:** Migrate long-running HTTP endpoints and unsafe `asyncio.create_task` invocations to a Celery worker queue.
4. **High:** Fix the N+1 API/DB call issue in rendering pagination.
5. **Medium:** Tune SQLAlchemy connection pooling to realistic Postgres limits.
