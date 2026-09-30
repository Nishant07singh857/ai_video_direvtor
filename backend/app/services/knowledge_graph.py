import uuid
from sqlalchemy import select
from app.models import (
    AudioAnalysis,
    Keyframe,
    KnowledgeEdge,
    KnowledgeEdgeType,
    KnowledgeNode,
    KnowledgeNodeType,
    MediaAsset,
    Project,
    TranscriptSegment,
    VideoScene,
    VideoShot,
)
from typing import Dict, Any, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import database
from app.services.storage import get_storage_service


class KnowledgeGraphService:
    """Builds and maintains a project-level knowledge graph from Phase 3 analysis results."""
    
    def __init__(self):
        self._storage = get_storage_service()
    
    async def build_graph(self, project_id: uuid.UUID) -> Dict[str, Any]:
        """Build knowledge graph for a project from its analyzed media assets."""
        async with database.async_session_maker() as db:
            # Verify project exists
            result = await db.execute(select(Project).where(Project.id == project_id))
            project = result.scalar_one_or_none()
            if not project:
                raise ValueError(f"Project {project_id} not found")
            
            # Get all media assets with analysis
            media_result = await db.execute(
                select(MediaAsset).where(MediaAsset.project_id == project_id)
            )
            media_assets = media_result.scalars().all()
            
            if not media_assets:
                return {"nodes": [], "edges": [], "message": "No media assets found"}
            
            # Clear existing graph for this project (rebuild from scratch)
            await self._clear_project_graph(db, project_id)
            
            nodes = []
            edges = []
            
            # Process each media asset
            for media in media_assets:
                media_nodes, media_edges = await self._process_media_asset(db, media)
                nodes.extend(media_nodes)
                edges.extend(media_edges)
            
            # Add cross-media temporal edges
            temporal_edges = self._add_temporal_edges(nodes)
            edges.extend(temporal_edges)
            
            # Persist to database
            await self._persist_graph(db, project_id, nodes, edges)
            await db.commit()
            
            return {
                "nodes": len(nodes),
                "edges": len(edges),
                "media_assets_processed": len(media_assets),
            }
    
    async def _clear_project_graph(self, db: AsyncSession, project_id: uuid.UUID) -> None:
        """Remove existing knowledge graph for a project."""
        await db.execute(
            KnowledgeEdge.__table__.delete().where(KnowledgeEdge.project_id == project_id)
        )
        await db.execute(
            KnowledgeNode.__table__.delete().where(KnowledgeNode.project_id == project_id)
        )
    
    async def _process_media_asset(
        self, db: AsyncSession, media: MediaAsset
    ) -> Tuple[List[Dict], List[Dict]]:
        """Extract knowledge from a single media asset's analysis."""
        nodes = []
        edges = []
        
        # Get all analysis results for this media
        shots_result = await db.execute(
            select(VideoShot).where(VideoShot.media_asset_id == media.id).order_by(VideoShot.shot_index)
        )
        shots = shots_result.scalars().all()
        
        scenes_result = await db.execute(
            select(VideoScene).where(VideoScene.media_asset_id == media.id).order_by(VideoScene.scene_index)
        )
        scenes = scenes_result.scalars().all()
        
        keyframes_result = await db.execute(
            select(Keyframe).where(Keyframe.media_asset_id == media.id).order_by(Keyframe.timestamp)
        )
        keyframes = keyframes_result.scalars().all()
        
        transcript_result = await db.execute(
            select(TranscriptSegment).where(TranscriptSegment.media_asset_id == media.id).order_by(TranscriptSegment.start_time)
        )
        transcripts = transcript_result.scalars().all()
        
        audio_result = await db.execute(
            select(AudioAnalysis).where(AudioAnalysis.media_asset_id == media.id)
        )
        audio = audio_result.scalar_one_or_none()
        
        node_id_map = {}  # Track nodes for edge creation
        
        # Create shot nodes
        for shot in shots:
            node_id = uuid.uuid4()
            node_id_map[f"shot_{shot.id}"] = node_id
            nodes.append({
                "id": node_id,
                "node_type": KnowledgeNodeType.SHOT,
                "source_id": shot.id,
                "label": f"Shot {shot.shot_index}",
                "properties": {
                    "start_time": shot.start_time,
                    "end_time": shot.end_time,
                    "duration": shot.duration,
                    "shot_index": shot.shot_index,
                    "detection_method": shot.detection_method,
                    "confidence": shot.confidence,
                },
                "confidence": shot.confidence,
            })
        
        # Create scene nodes and link shots to scenes
        for scene in scenes:
            node_id = uuid.uuid4()
            node_id_map[f"scene_{scene.id}"] = node_id
            nodes.append({
                "id": node_id,
                "node_type": KnowledgeNodeType.SCENE,
                "source_id": scene.id,
                "label": scene.label or f"Scene {scene.scene_index}",
                "properties": {
                    "start_time": scene.start_time,
                    "end_time": scene.end_time,
                    "scene_index": scene.scene_index,
                    "description": scene.description,
                    "detection_method": scene.detection_method,
                    "confidence": scene.confidence,
                },
                "confidence": scene.confidence,
            })
            
            # Link shots that fall within this scene
            for shot in shots:
                if shot.start_time >= scene.start_time and shot.end_time <= scene.end_time:
                    edges.append({
                        "source_node_id": node_id_map[f"shot_{shot.id}"],
                        "target_node_id": node_id,
                        "edge_type": KnowledgeEdgeType.TEMPORAL,
                        "weight": 1.0,
                        "properties": {"relationship": "shot_in_scene"},
                    })
        
        # Create keyframe nodes (link to shots)
        for kf in keyframes:
            if kf.shot_id:
                node_id = uuid.uuid4()
                nodes.append({
                    "id": node_id,
                    "node_type": KnowledgeNodeType.ENTITY,
                    "source_id": kf.id,
                    "label": f"Keyframe @ {kf.timestamp:.1f}s",
                    "properties": {
                        "timestamp": kf.timestamp,
                        "frame_index": kf.frame_index,
                        "storage_key": kf.storage_key,
                        "width": kf.width,
                        "height": kf.height,
                    },
                    "confidence": 0.8,
                })
                
                # Link to shot
                if f"shot_{kf.shot_id}" in node_id_map:
                    edges.append({
                        "source_node_id": node_id_map[f"shot_{kf.shot_id}"],
                        "target_node_id": node_id,
                        "edge_type": KnowledgeEdgeType.TEMPORAL,
                        "weight": 0.9,
                        "properties": {"relationship": "keyframe_of"},
                    })
        
        # Create transcript nodes
        for ts in transcripts:
            node_id = uuid.uuid4()
            node_id_map[f"transcript_{ts.id}"] = node_id
            nodes.append({
                "id": node_id,
                "node_type": KnowledgeNodeType.AUDIO_EVENT,
                "source_id": ts.id,
                "label": ts.text[:50] + ("..." if len(ts.text) > 50 else ""),
                "properties": {
                    "start_time": ts.start_time,
                    "end_time": ts.end_time,
                    "text": ts.text,
                    "confidence": ts.confidence,
                    "speaker_id": ts.speaker_id,
                    "language": ts.language,
                },
                "confidence": ts.confidence,
            })
            
            # Find containing shot
            for shot in shots:
                if ts.start_time >= shot.start_time and ts.end_time <= shot.end_time:
                    edges.append({
                        "source_node_id": node_id_map[f"shot_{shot.id}"],
                        "target_node_id": node_id,
                        "edge_type": KnowledgeEdgeType.TEMPORAL,
                        "weight": 0.8,
                        "properties": {"relationship": "audio_in_shot"},
                    })
                    break
        
        # Create audio analysis node if present
        if audio and audio.has_audio:
            node_id = uuid.uuid4()
            node_id_map[f"audio_{media.id}"] = node_id
            nodes.append({
                "id": node_id,
                "node_type": KnowledgeNodeType.AUDIO_EVENT,
                "source_id": audio.id,
                "label": f"Audio: {audio.codec}, {audio.channels}ch, {audio.sample_rate}Hz",
                "properties": {
                    "has_audio": audio.has_audio,
                    "audio_streams": audio.audio_streams,
                    "sample_rate": audio.sample_rate,
                    "channels": audio.channels,
                    "codec": audio.codec,
                    "bitrate": audio.bitrate,
                    "duration": audio.duration,
                },
                "confidence": 0.9,
            })
            
            # Link audio to media
            for shot in shots:
                edges.append({
                    "source_node_id": node_id_map[f"shot_{shot.id}"],
                    "target_node_id": node_id,
                    "edge_type": KnowledgeEdgeType.TEMPORAL,
                    "weight": 0.7,
                    "properties": {"relationship": "audio_accompanies"},
                })
        
        return nodes, edges
    
    def _add_temporal_edges(self, nodes: List[Dict]) -> List[Dict]:
        """Add temporal edges between consecutive shots."""
        edges = []
        shot_nodes = [n for n in nodes if n["node_type"] == KnowledgeNodeType.SHOT]
        shot_nodes.sort(key=lambda n: n["properties"]["start_time"])
        
        for i in range(len(shot_nodes) - 1):
            edges.append({
                "source_node_id": shot_nodes[i]["id"],
                "target_node_id": shot_nodes[i + 1]["id"],
                "edge_type": KnowledgeEdgeType.TEMPORAL,
                "weight": 1.0,
                "properties": {"relationship": "temporal_sequence"},
            })
        
        return edges
    
    async def _persist_graph(
        self, db: AsyncSession, project_id: uuid.UUID, nodes: List[Dict], edges: List[Dict]
    ) -> None:
        """Persist nodes and edges to database."""
        node_id_map = {}
        
        # Create nodes
        for node_data in nodes:
            node = KnowledgeNode(
                project_id=project_id,
                node_type=node_data["node_type"],
                source_id=node_data.get("source_id"),
                label=node_data.get("label"),
                properties=node_data.get("properties"),
                confidence=node_data.get("confidence"),
            )
            db.add(node)
            await db.flush()
            node_id_map[node_data["id"]] = node.id
        
        # Create edges
        for edge_data in edges:
            source_id = node_id_map.get(edge_data["source_node_id"])
            target_id = node_id_map.get(edge_data["target_node_id"])
            
            if source_id and target_id:
                edge = KnowledgeEdge(
                    project_id=project_id,
                    source_node_id=source_id,
                    target_node_id=target_id,
                    edge_type=edge_data["edge_type"],
                    weight=edge_data.get("weight"),
                    properties=edge_data.get("properties"),
                )
                db.add(edge)
    
    async def get_graph(self, project_id: uuid.UUID) -> Dict[str, Any]:
        """Retrieve knowledge graph for a project."""
        async with database.async_session_maker() as db:
            nodes_result = await db.execute(
                select(KnowledgeNode).where(KnowledgeNode.project_id == project_id)
            )
            nodes = nodes_result.scalars().all()
            
            edges_result = await db.execute(
                select(KnowledgeEdge).where(KnowledgeEdge.project_id == project_id)
            )
            edges = edges_result.scalars().all()
            
            return {
                "nodes": [
                    {
                        "id": str(n.id),
                        "node_type": n.node_type.value,
                        "source_id": str(n.source_id) if n.source_id else None,
                        "label": n.label,
                        "properties": n.properties,
                        "confidence": n.confidence,
                    }
                    for n in nodes
                ],
                "edges": [
                    {
                        "id": str(e.id),
                        "source_node_id": str(e.source_node_id),
                        "target_node_id": str(e.target_node_id),
                        "edge_type": e.edge_type.value,
                        "weight": e.weight,
                        "properties": e.properties,
                    }
                    for e in edges
                ],
            }


# Singleton
_knowledge_graph_service: Optional["KnowledgeGraphService"] = None

def get_knowledge_graph_service(): return KnowledgeGraphService()

