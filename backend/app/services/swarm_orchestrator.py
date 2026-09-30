import asyncio
import json
import logging
import re
import httpx

from app.core.config import settings
from app.core.timeline import normalize_timeline


logger = logging.getLogger(__name__)

class AgentPipelineMessage:
    def __init__(self, project_id: str, timeline_state: dict, metadata: dict):
        self.project_id = project_id
        self.timeline_state = timeline_state
        self.metadata = metadata

class BaseVideoAgent:
    async def process(self, message: AgentPipelineMessage) -> AgentPipelineMessage:
        if 'agents_completed' not in message.metadata:
            message.metadata['agents_completed'] = []
        message.metadata['agents_completed'].append(self.__class__.__name__)
        return message

    async def call_llm(self, prompt: str, retries: int = 2) -> dict:
        api_url = settings.LLM_API_URL
        model = settings.LLM_MODEL

        def get_mock_fallback() -> dict:
            name = self.__class__.__name__
            if "AudioIntelligenceAgent" in name:
                return {"transcript": "Mock transcript", "keywords": ["mock", "test"], "emotions": [{"label": "happy", "score": 0.9}]}
            elif "MasterStoryEditorAgent" in name:
                return {"narrative_arc": {"setup": "intro"}, "selected_clips": [{"start": 0, "end": 5, "reason": "mock"}, {"start": 10, "end": 15, "reason": "action"}]}
            elif "PostProductionAgent" in name:
                return {"post_processing": {"color_grade": "vibrant"}}
            elif "ExecutiveProducerAgent" in name:
                return {"export_plan": {"resolution": "1080p"}}
            return {}

        if not settings.LLM_ENABLED or not api_url or not model:
            if settings.ALLOW_MOCK_AI:
                logger.warning("LLM is not configured; mock AI is explicitly enabled")
                return get_mock_fallback()
            raise RuntimeError(
                "LLM is not configured. Set LLM_ENABLED=true, LLM_API_URL and LLM_MODEL in the environment."
            )

        headers = {}
        if settings.LLM_API_KEY:
            headers["Authorization"] = f"Bearer {settings.LLM_API_KEY}"

        last_error: Exception | None = None
        async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_SECONDS) as client:
            for attempt in range(max(1, retries)):
                try:
                    response = await client.post(
                        api_url,
                        json={
                            "model": model,
                            "messages": [{"role": "user", "content": prompt}],
                            "response_format": {"type": "json_object"}
                        },
                        headers=headers,
                    )
                    if response.status_code != 200:
                        last_error = RuntimeError(f"LLM provider returned HTTP {response.status_code}")
                        if attempt == max(1, retries) - 1:
                            break
                        await asyncio.sleep(2 ** attempt)
                        continue
                        
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError:
                        match = re.search(r'(\{.*\}|\[.*\])', content, re.DOTALL)
                        if match:
                            try:
                                return json.loads(match.group(1))
                            except json.JSONDecodeError as exc:
                                last_error = exc
                        if attempt == max(1, retries) - 1:
                            break
                        continue
                except Exception as e:
                    last_error = e
                    logger.warning("LLM request failed on attempt %s", attempt + 1)
                    if attempt < max(1, retries) - 1:
                        await asyncio.sleep(2 ** attempt)
        if settings.ALLOW_MOCK_AI:
            logger.warning("LLM provider failed; mock AI is explicitly enabled")
            return get_mock_fallback()
        raise RuntimeError(f"LLM provider failed: {last_error or 'invalid response'}")

class VisionDirectorAgent(BaseVideoAgent):
    async def process(self, message: AgentPipelineMessage) -> AgentPipelineMessage:
        await super().process(message)
        file_path = message.metadata.get("file_path", "input.mp4")
        
        # ffprobe video metadata
        cmd_meta = [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height,r_frame_rate,codec_name",
            "-of", "json", file_path
        ]
        try:
            proc_meta = await asyncio.create_subprocess_exec(
                *cmd_meta, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout_meta, _ = await asyncio.wait_for(proc_meta.communicate(), timeout=30.0)
            if stdout_meta:
                data = json.loads(stdout_meta.decode('utf-8'))
                stream = data.get("streams", [{}])[0]
                message.metadata["resolution"] = f"{stream.get('width')}x{stream.get('height')}"
                message.metadata["framerate"] = stream.get("r_frame_rate")
                message.metadata["codec"] = stream.get("codec_name")
        except Exception as e:
            ...

        # ffprobe scene cuts
        cmd_scene = [
            "ffprobe", "-v", "error", "-show_frames", "-of", "json",
            "-f", "lavfi", f"movie={file_path},select='gt(scene,0.4)'"
        ]
        try:
            proc_scene = await asyncio.create_subprocess_exec(
                *cmd_scene, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout_scene, _ = await asyncio.wait_for(proc_scene.communicate(), timeout=30.0)
            if stdout_scene:
                data = json.loads(stdout_scene.decode('utf-8'))
                frames = data.get("frames", [])
                message.metadata["scene_cuts"] = [f.get("pkt_pts_time") for f in frames]
            else:
                message.metadata["scene_cuts"] = []
        except Exception as e:
            ...
            message.metadata["scene_cuts"] = []

        # Fetch extra style metadata from video_cloner
        try:
            from app.services.video_cloner import get_video_style_cloner
            cloner = get_video_style_cloner()
            style_data = await cloner.analyze_reference_video(file_path)
            message.metadata["color"] = style_data.get("color_style")
            message.metadata["audio_lufs"] = style_data.get("audio_lufs")
            message.metadata["pacing"] = style_data.get("estimated_pacing")
        except Exception as e:
            ...

        # Deep Computer Vision Analysis (YuNet Face & Speaker Detection, A-Roll/B-Roll, Sharpness, Smart Crop)
        try:
            from video_engine.vision.visual_analyzer import get_visual_analyzer
            analyzer = get_visual_analyzer()
            cuts = [float(c) for c in message.metadata.get("scene_cuts", []) if c is not None]
            vis_result = await analyzer.analyze_video(file_path, cuts)
            message.metadata["visual_analysis"] = vis_result.to_dict()
            message.metadata["ai_vision_summary"] = vis_result.ai_vision_summary
            message.metadata["a_roll_count"] = vis_result.a_roll_count
            message.metadata["b_roll_count"] = vis_result.b_roll_count
            message.metadata["recommended_smart_crop_center"] = vis_result.recommended_reframe_center
            message.metadata["overall_quality"] = vis_result.overall_quality
        except Exception as e:
            message.metadata["ai_vision_summary"] = f"Visual CV: {e}"

        return message

class AudioIntelligenceAgent(BaseVideoAgent):
    async def process(self, message: AgentPipelineMessage) -> AgentPipelineMessage:
        await super().process(message)
        prompt = f"Analyze transcript, speakers, and emotions based on metadata. Return JSON with keys 'transcript', 'keywords', and 'emotions'. Metadata: {json.dumps(message.metadata)}"
        result = await self.call_llm(prompt)
        message.metadata["transcript"] = result.get("transcript", "")
        message.metadata["keywords"] = result.get("keywords", [])
        message.metadata["emotions"] = result.get("emotions", [])
        return message

class MasterStoryEditorAgent(BaseVideoAgent):
    async def process(self, message: AgentPipelineMessage) -> AgentPipelineMessage:
        await super().process(message)
        vision_summary = message.metadata.get("ai_vision_summary", "")
        vis_data = message.metadata.get("visual_analysis") or {}
        prompt = (
            f"Analyze narrative arc and select clips/b-roll for final edit. "
            f"Visual Computer Vision Analysis: {vision_summary}. "
            f"Prioritize crisp A-Roll talking heads for core dialogue, insert B-Roll scenes as cutaways, "
            f"and eliminate any blurry or low-quality shots. "
            f"Return JSON with keys 'narrative_arc' and 'selected_clips' containing start/end times. "
            f"Metadata: {json.dumps(message.metadata)}"
        )
        result = await self.call_llm(prompt)
        selected_clips = result.get("selected_clips", [])
        
        # If LLM returned mock or empty clips, derive intelligent clips from real Computer Vision shots
        if not selected_clips and vis_data.get("shots"):
            real_shots = vis_data["shots"]
            selected_clips = []
            for s in real_shots:
                if s.get("sharpness_label") != "blurry":
                    selected_clips.append({
                        "start": s.get("start_time", 0.0),
                        "end": s.get("end_time", 5.0),
                        "type": s.get("shot_type", "A-ROLL"),
                        "smart_crop_x": s.get("smart_crop_center_x", 0.5),
                        "reason": f"{s.get('shot_type')} shot ({s.get('sharpness_label')}, {s.get('faces_detected')} faces)"
                    })
        elif not selected_clips:
            selected_clips = [{"start": 0, "end": 5, "reason": "intro"}]

        message.metadata["narrative_arc"] = result.get("narrative_arc", {"setup": "intro", "climax": "core"})
        message.metadata["selected_clips"] = selected_clips
        # Keep the swarm's decision state in the same canonical shape used by
        # the editor and renderer.  These clips intentionally remain
        # source-less until a project-scoped timeline generator attaches real
        # media assets; they are never mistaken for renderable footage.
        message.timeline_state = normalize_timeline({
            **message.timeline_state,
            "clips": selected_clips,
        })
        return message

class PostProductionAgent(BaseVideoAgent):
    async def process(self, message: AgentPipelineMessage) -> AgentPipelineMessage:
        await super().process(message)
        prompt = f"Determine post-production steps: timeline pacing, color grading, audio enhancing, captions, and upscale settings. You MUST instruct the use of BLUR, SHARPEN, and blend modes when editing effects. Return JSON with key 'post_processing'. Metadata: {json.dumps(message.metadata)}"
        result = await self.call_llm(prompt)
        message.timeline_state["post_processing"] = result.get("post_processing", {})
        return message

class ExecutiveProducerAgent(BaseVideoAgent):
    async def process(self, message: AgentPipelineMessage) -> AgentPipelineMessage:
        await super().process(message)
        prompt = f"Perform final QA review and create export plan. Return JSON with key 'export_plan'. Timeline State: {json.dumps(message.timeline_state)}"
        result = await self.call_llm(prompt)
        message.timeline_state["export_plan"] = result.get("export_plan", {})
        return message

class SwarmOrchestrator:
    def __init__(self):
        self.vision_director = VisionDirectorAgent()
        self.audio_intelligence = AudioIntelligenceAgent()
        self.master_story_editor = MasterStoryEditorAgent()
        self.post_production = PostProductionAgent()
        self.executive_producer = ExecutiveProducerAgent()
    
    async def run_swarm(self, raw_video_id: str, file_path: str = "input.mp4") -> dict:
        state = AgentPipelineMessage(
            project_id=raw_video_id,
            timeline_state={},
            metadata={"file_path": file_path}
        )
        
        # Step 1: Run VisionDirectorAgent and AudioIntelligenceAgent sequentially
        state = await self.vision_director.process(state)
        state = await self.audio_intelligence.process(state)
        
        # Step 2: Pass their results to MasterStoryEditorAgent
        state = await self.master_story_editor.process(state)
        
        # Step 3: Pass the story results to PostProductionAgent
        state = await self.post_production.process(state)
        
        # Step 4: Finalize with ExecutiveProducerAgent
        state = await self.executive_producer.process(state)
            
        # Enrich timeline state with deep visual intelligence
        if state.metadata.get("visual_analysis"):
            state.timeline_state["visual_analysis"] = state.metadata["visual_analysis"]
            state.timeline_state["ai_vision_summary"] = state.metadata.get("ai_vision_summary")
            state.timeline_state["recommended_smart_crop_center"] = state.metadata.get("recommended_smart_crop_center", 0.5)
            state.timeline_state["a_roll_count"] = state.metadata.get("a_roll_count", 0)
            state.timeline_state["b_roll_count"] = state.metadata.get("b_roll_count", 0)
            state.timeline_state["overall_quality"] = state.metadata.get("overall_quality", "high")

        return state.timeline_state

