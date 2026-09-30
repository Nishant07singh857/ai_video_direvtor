from pydantic import BaseModel
from typing import List, Dict, Any
import json
import httpx
import re

class CriticIssue(BaseModel):
    issue: str
    timestamp: float
    severity: str  # "Low", "Medium", "High"
    explanation: str
    suggested_fix: str
    confidence: float

class CriticReport(BaseModel):
    issues: List[CriticIssue]
    overall_pacing_score: float
    continuity_score: float

class AICriticService:
    def __init__(self):
        ...

    async def analyze(self, timeline: Dict[str, Any]) -> CriticReport:
        prompt = self._build_llm_prompt(timeline)
        retries = 2
        async with httpx.AsyncClient() as client:
            for attempt in range(retries):
                try:
                    response = await client.post(
                        "http://localhost:1234/v1/chat/completions",
                        json={
                            "model": "llama-3",
                            "messages": [{"role": "user", "content": prompt}],
                            "response_format": {"type": "json_object"}
                        },
                        timeout=30.0
                    )
                    response.raise_for_status()
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    
                    parsed_data = None
                    try:
                        parsed_data = json.loads(content)
                    except json.JSONDecodeError:
                        match = re.search(r'(\{.*\}|\[.*\])', content, re.DOTALL)
                        if match:
                            try:
                                parsed_data = json.loads(match.group(1))
                            except json.JSONDecodeError:
                                pass
                    
                    if parsed_data is not None:
                        if isinstance(parsed_data, dict) and 'issues' in parsed_data:
                            issues_list = parsed_data.get('issues', [])
                        elif isinstance(parsed_data, list):
                            issues_list = parsed_data
                        else:
                            issues_list = []
                            
                        issues = [CriticIssue(**i) for i in issues_list if isinstance(i, dict)]
                        return CriticReport(issues=issues, overall_pacing_score=0.8, continuity_score=0.9)
                        
                except Exception as e:
                    if attempt == retries - 1:
                        pass
        return CriticReport(issues=[], overall_pacing_score=0.0, continuity_score=0.0)



    def _evaluate_pacing(self, timeline: Dict[str, Any]) -> List[CriticIssue]:
        issues = []
        tracks = timeline.get("tracks", [])
        for track in tracks:
            if track.get("type") == "video":
                clips = track.get("clips", [])
                for clip in clips:
                    duration = clip.get("end", 0) - clip.get("start", 0)
                    if duration > 0 and duration < 0.5:
                        issues.append(
                            CriticIssue(
                                issue="Clip too short",
                                timestamp=clip.get("start", 0),
                                severity="Medium",
                                explanation=f"Clip duration of {duration:.2f}s is too short and may cause visual stuttering.",
                                suggested_fix="Extend the clip duration to at least 1 second or remove it.",
                                confidence=0.9
                            )
                        )
                    elif duration > 10.0:
                        issues.append(
                            CriticIssue(
                                issue="Clip too long",
                                timestamp=clip.get("start", 0),
                                severity="Low",
                                explanation=f"Clip duration of {duration:.2f}s might drag the pacing down.",
                                suggested_fix="Consider trimming the clip or adding b-roll.",
                                confidence=0.7
                            )
                        )
        return issues

    def _evaluate_repetition(self, timeline: Dict[str, Any]) -> List[CriticIssue]:
        issues = []
        # Basic heuristic: Check if adjacent clips come from the same source asset
        tracks = timeline.get("tracks", [])
        for track in tracks:
            if track.get("type") == "video":
                clips = sorted(track.get("clips", []), key=lambda x: x.get("start", 0))
                for i in range(1, len(clips)):
                    prev_clip = clips[i-1]
                    curr_clip = clips[i]
                    if prev_clip.get("asset_id") == curr_clip.get("asset_id") and curr_clip.get("asset_id") is not None:
                        issues.append(
                            CriticIssue(
                                issue="Repetitive shot source",
                                timestamp=curr_clip.get("start", 0),
                                severity="High",
                                explanation="Adjacent clips use the same source asset, which can look jarring unless intended as a jump cut.",
                                suggested_fix="Insert a different shot in between or apply a transition/scaling effect.",
                                confidence=0.85
                            )
                        )
        return issues

    def _evaluate_continuity(self, timeline: Dict[str, Any]) -> List[CriticIssue]:
        issues = []
        # Basic heuristic: Check for overlapping clips on the same track if not supported,
        # or gaps in the primary video track
        tracks = timeline.get("tracks", [])
        for track in tracks:
            if track.get("type") == "video":
                clips = sorted(track.get("clips", []), key=lambda x: x.get("start", 0))
                for i in range(1, len(clips)):
                    prev_clip = clips[i-1]
                    curr_clip = clips[i]
                    gap = curr_clip.get("start", 0) - prev_clip.get("end", 0)
                    if gap > 0.1:
                        issues.append(
                            CriticIssue(
                                issue="Flash frame or gap detected",
                                timestamp=prev_clip.get("end", 0),
                                severity="High",
                                explanation=f"There is a black gap of {gap:.2f}s between clips.",
                                suggested_fix="Close the gap by extending the previous clip or moving the next clip earlier.",
                                confidence=0.95
                            )
                        )
                    elif gap < -0.1:
                         issues.append(
                            CriticIssue(
                                issue="Overlapping clips",
                                timestamp=curr_clip.get("start", 0),
                                severity="High",
                                explanation=f"Clips overlap by {abs(gap):.2f}s on the same track.",
                                suggested_fix="Move clips to separate tracks or adjust timing so they don't overlap.",
                                confidence=0.95
                            )
                        )
        return issues

    def _build_llm_prompt(self, timeline: Dict[str, Any]) -> str:
        """
        Builds the prompt structure for when we integrate a real LLM.
        """
        prompt = (
            "You are an expert film editor and AI Critic. Evaluate the following timeline JSON for pacing, "
            "shot repetition, and continuity.\n\n"
            f"Timeline: {timeline}\n\n"
            "Identify any issues and return a JSON list of issues, each with 'issue', 'timestamp', 'severity' (Low, Medium, High), "
            "'explanation', 'suggested_fix', and 'confidence' (0.0 to 1.0).\n"
        )
        return prompt
