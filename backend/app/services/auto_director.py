from app.services.swarm_orchestrator import SwarmOrchestrator
from app.services.video_cloner import get_video_style_cloner
from app.services.template_engine import get_template_engine

class InvincibleAutoDirector:
    """
    The 'Invincible' AI Core.
    This class unites the 17-Category Master Index, the 22-Agent Swarm, 
    and the Style Cloning engines into a single, unstoppable video editor.
    """
    def __init__(self):
        # The 22-Agent Assembly Line grouped into 4 Macro Teams
        self.swarm = SwarmOrchestrator()
        
        # Phase 51 & 52: The Template and Viral Style Cloning engines
        self.cloner = get_video_style_cloner()
        self.template_engine = get_template_engine()
        
        # Load the 17-Category Master Feature Index so the AI knows every tool
        self.dictionary_path = "docs/MASTER_FEATURE_INDEX.md"




AutoDirectorBrain = InvincibleAutoDirector
