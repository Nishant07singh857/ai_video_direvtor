# AI and Video Processing Engine Audit Report

## Executive Summary
An in-depth architectural and code-level audit was conducted on the **AI and Video Processing Engine**, primarily focusing on the AI orchestration layer (`swarm_orchestrator.py`, `ai_director.py`) and the rendering engine (`ffmpeg_renderer.py`, `timeline_to_ffmpeg.py`). 

Several critical vulnerabilities were discovered related to asynchronous event loop blocking, unbound memory growth, and lack of resilience in LLM integrations.

---

## 1. FFmpeg Subprocess Blocking and Event Loop Hangs
### A. Broken Timeout Mechanism in FFmpeg Renderer
**Location:** `video_engine/rendering/ffmpeg_renderer.py` -> `render()`
**Issue:** The timeout logic intended to kill hanging renders is flawed and will not work if the subprocess pipes stay open.
```python
await asyncio.gather(read_stdout(), read_stderr())
try:
    return_code = await asyncio.wait_for(self._process.wait(), timeout=self.timeout)
```
The `asyncio.gather` call reads stdout and stderr asynchronously. However, it blocks until both streams are closed. If FFmpeg hangs mid-process and stops outputting data without closing the pipes, `gather` will block forever. The `wait_for` timeout is placed *after* the `gather` statement, meaning it is never reached if `gather` hangs. 
**Remediation:** Wrap the entire operation (including the stream reads and the process wait) in a single `asyncio.wait_for()`, or utilize `asyncio.as_completed()` with appropriate timeout handling.

### B. Unbounded Subprocess Execution in Vision Director
**Location:** `backend/app/services/swarm_orchestrator.py` -> `VisionDirectorAgent.process()`
**Issue:** The `ffprobe` commands for extracting video metadata and scene cuts lack timeout configurations:
```python
stdout_meta, _ = await proc_meta.communicate()
...
stdout_scene, _ = await proc_scene.communicate()
```
If a user uploads a malformed or corrupt video file that causes `ffprobe` to hang in an infinite loop, `await proc_scene.communicate()` will block indefinitely. This permanently blocks the specific AI orchestrator task and could exhaust server resources over time.
**Remediation:** Add an explicit `asyncio.wait_for(..., timeout=XX.X)` around the `communicate()` calls and implement graceful fallback/error handling for corrupt files.

---

## 2. LLM Resiliency: Rate Limits and JSON Parsing
### A. Instant Retry Hammering on HTTP Errors (Rate Limits)
**Location:** `backend/app/services/swarm_orchestrator.py` -> `BaseVideoAgent.call_llm()`
**Issue:** While the `call_llm` method features a basic loop (`for attempt in range(retries)`), it does not implement any backoff.
```python
if response.status_code != 200:
    print(f"LLM API Error")
    if attempt == retries - 1: return get_mock_fallback()
    continue
```
If the LLM provider returns a `429 Too Many Requests` or `503 Service Unavailable`, the loop instantly re-fires the request without delay. This almost guarantees subsequent failures and exacerbates rate limits.
**Remediation:** Introduce an exponential backoff with jitter (e.g., `await asyncio.sleep(2 ** attempt)`) before the `continue` statement.

### B. Masked Exceptions in JSON Extraction Fallback
**Location:** `backend/app/services/swarm_orchestrator.py` -> `BaseVideoAgent.call_llm()`
**Issue:** When the LLM outputs malformed JSON, a regex fallback is triggered:
```python
try:
    return json.loads(match.group(1))
except Exception:
    pass
```
Swallowing `Exception` outright makes debugging incredibly difficult and masks underlying parsing bugs. Additionally, the regex `r'(\{.*\}|\[.*\])'` using `re.DOTALL` is greedy and prone to extracting trailing markdown or conversational text, which will consistently fail the `json.loads` fallback.
**Remediation:** Log the exception details via a structured logger. Improve the JSON boundary extraction logic or rely on strict JSON schema enforcing via the LLM API's tool/function-calling features.

---

## 3. Memory Leaks and Scale Limitations
### A. Unbounded Stderr Buffer (Memory Leak)
**Location:** `video_engine/rendering/ffmpeg_renderer.py` -> `render().read_stderr()`
**Issue:** The asynchronous stderr reader appends every single output line to a list:
```python
stderr_lines.append(line_str)
```
For heavy post-production workflows, FFmpeg can output hundreds of thousands of lines of warnings, debug info, or filter logs. Over a long-running render (e.g., 1-2 hours), this list grows unboundedly, consuming massive amounts of RAM and leading to a potential Out-Of-Memory (OOM) exception.
**Remediation:** Replace the standard list with `collections.deque(maxlen=100)`. Generally, only the last N lines are required for debugging crash contexts.

### B. Filter Complex Command Line Length Limits
**Location:** `video_engine/rendering/timeline_to_ffmpeg.py` -> `compile()`
**Issue:** The `filter_complex` variable aggregates all video scaling, color correction, ken burns, overlays, and audio mixing into a single string. For a large AI-directed video with hundreds of micro-clips and graphics, this string easily exceeds standard OS command-line length limits (e.g., Windows limits are historically ~8191 or 32768 characters).
**Remediation:** For complex timelines, write the `filter_complex` string to a temporary `.txt` file and pass it to FFmpeg using the `-filter_complex_script /path/to/script.txt` parameter.
