import json
import logging
from typing import List, Dict, Any, Optional

from pydantic import BaseModel, Field

from app.models.editing import EditOperationType

logger = logging.getLogger(__name__)

# --- Pydantic Models for Output Generation ---

class EditIntent(BaseModel):
    """Extracted intent from the user's natural language request."""
    intent_type: str = Field(
        description="The general category of the edit: e.g., 'shorten', 'remove_content', 'rearrange', 'style', 'unknown'"
    )
    description: str = Field(description="Detailed description of what the user wants to achieve")
    target_elements: List[str] = Field(
        description="Keywords or descriptions of the content to be affected (e.g., 'intro', 'silence', 'speaker B')"
    )

class StructuredEditOperation(BaseModel):
    """Structured EDL operation returned by the NLP-to-EDL pipeline."""
    target_item_id: Optional[str] = Field(
        default=None, 
        description="The ID of the track item or shot to apply the edit to. Can be null for general additions."
    )
    operation_type: EditOperationType = Field(
        description="Must be one of the supported EditOperationTypes: trim, split, delete, move, add."
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Parameters for the operation (e.g., trim_start, trim_end, split_time, new_start_time, track)."
    )

# --- Prompt Templates ---

INTENT_EXTRACTION_PROMPT = """
You are an expert AI Video Editor.
Your task is to analyze the user's natural language request and extract their editing intent.

User Request: {user_request}

Extract the following information:
1. Intent Type (shorten, remove_content, rearrange, style, unknown)
2. Description of the intent in plain language
3. Target elements or keywords mentioned (e.g., 'intro', 'first 5 seconds', 'the dog clip')

Respond ONLY with a JSON object matching this schema:
{{
  "intent_type": "string",
  "description": "string",
  "target_elements": ["string"]
}}
"""

EDL_GENERATION_PROMPT = """
You are an AI Video Editor translating an intent and context into specific Edit Decision List (EDL) operations.

Editing Intent:
{intent_json}

Current Timeline Context:
{timeline_context}

Available Operation Types:
- trim: Requires parameters {{"trim_start": float, "trim_end": float}}
- split: Requires parameters {{"split_time": float}}
- delete: No additional parameters needed, or {{"soft_delete": bool}}
- move: Requires parameters {{"new_start_time": float, "track": int}}
- add: Requires parameters {{"asset_id": str, "start_time": float}}

Your goal is to output a list of structured edit operations that accomplish the user's intent based on the current timeline context. Use the target_item_id from the context to specify which clip to modify.

Respond ONLY with a JSON array of objects, where each object matches this schema:
{{
  "target_item_id": "string",
  "operation_type": "string",
  "parameters": {{}}
}}
"""

# --- Service Class ---

class NLPEditorService:
    """Service to process natural language into structured Edit Decision List (EDL) operations."""
    
    def __init__(self):
        import openai
        # Connect to Local Custom Llama-3 Model via LM Studio / llama.cpp
        self.client = openai.AsyncOpenAI(
            base_url="https://petite-pugs-hope.loca.lt/v1",
            api_key="lm-studio",
            default_headers={"Bypass-Tunnel-Reminder": "true"}
        )
        self._available = True
        self.model = "local-model" # LM Studio ignores this and uses the loaded model
            
        
    async def extract_intent(self, user_request: str) -> EditIntent:
        """
        Step 1: Parse USER LANGUAGE into a structured INTENT.
        """
        if not self._available:
            logger.warning("OpenAI API key not set. Using fallback intent extraction.")
            return EditIntent(
                intent_type="unknown",
                description=user_request,
                target_elements=[]
            )
            
        prompt = INTENT_EXTRACTION_PROMPT.format(user_request=user_request)
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                response_format={ "type": "json_object" }
            )
            content = response.choices[0].message.content
            data = json.loads(content)
            return EditIntent(**data)
        except Exception as e:
            logger.error(f"Failed to extract intent: {e}")
            return EditIntent(
                intent_type="unknown",
                description=user_request,
                target_elements=[]
            )

    async def generate_edl_operations(
        self, 
        intent: EditIntent, 
        timeline_context: Dict[str, Any]
    ) -> List[StructuredEditOperation]:
        """
        Step 2 & 3: Map intent + CONTEXT -> STRUCTURED EDIT OPERATIONS (EDL).
        """
        if not self._available:
            logger.warning("OpenAI API key not set. Returning empty EDL operations.")
            return []
            
        prompt = EDL_GENERATION_PROMPT.format(
            intent_json=intent.model_dump_json(indent=2),
            timeline_context=json.dumps(timeline_context, indent=2)
        )
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0
            )
            content = response.choices[0].message.content
            
            # Clean up markdown formatting if the model still wrapped it
            if content.startswith("```json"):
                content = content[7:-3]
            elif content.startswith("```"):
                content = content[3:-3]
                
            data = json.loads(content.strip())
            if not isinstance(data, list):
                if isinstance(data, dict) and "operations" in data:
                    data = data["operations"]
                else:
                    data = [data]
            
            # Map string operation types to enum and return validated Pydantic models
            operations = []
            for op in data:
                # Ensure the enum matches exactly
                op["operation_type"] = EditOperationType(op["operation_type"].lower())
                operations.append(StructuredEditOperation(**op))
                
            return operations
        except Exception as e:
            logger.error(f"Failed to generate EDL operations: {e}")
            return []
            
    async def process_natural_language_edit(
        self, 
        user_request: str, 
        timeline_context: Dict[str, Any]
    ) -> List[StructuredEditOperation]:
        """
        End-to-end NLP-to-EDL pipeline:
        USER LANGUAGE -> INTENT -> CONTEXT -> STRUCTURED EDIT OPERATIONS
        """
        logger.info(f"Processing NLP edit request: '{user_request}'")
        
        # 1. Intent recognition
        intent = await self.extract_intent(user_request)
        logger.info(f"Extracted Intent: {intent.model_dump()}")
        
        # 2 & 3. Contextual EDL generation
        operations = await self.generate_edl_operations(intent, timeline_context)
        logger.info(f"Generated {len(operations)} operations.")
        
        return operations

