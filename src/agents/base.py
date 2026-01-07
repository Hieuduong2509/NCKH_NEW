import time
import json
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, Type
from collections import defaultdict

from google import genai
from google.genai import types
from pydantic import BaseModel

from src.utils.config import (
    GOOGLE_API_KEY, IS_GEMINI_CONFIGURED, MAX_RETRIES, RETRY_DELAY_SECONDS
)
from src.utils.logger import DetailedLogger

class BaseAgent:
    def __init__(self, agent_name: str, run_output_dir: Path, model_name: str):
        self.agent_name = agent_name
        self.run_output_dir = run_output_dir
        self.model_name = model_name
        self.logger = DetailedLogger(agent_name=agent_name, run_name=run_output_dir.name)
        
        self.working_schedules_dir = self.run_output_dir / "working_schedules"
        self.working_schedules_dir.mkdir(parents=True, exist_ok=True)

    def call_llm(
        self, 
        prompt: str, 
        log_context: Dict[str, Any], 
        response_schema: Type[BaseModel] = None
    ) -> Tuple[Optional[Any], Dict[str, float]]:
        
        if not IS_GEMINI_CONFIGURED:
            self.logger.log("CRITICAL_ERROR", {"summary": "Gemini API key missing."})
            return None, {}

        metrics = defaultdict(float)
        
        for attempt in range(MAX_RETRIES):
            start_time = time.time()
            try:
                client = genai.Client(api_key=GOOGLE_API_KEY)
                
                if response_schema:
                    config = types.GenerateContentConfig(
                        thinking_config=types.ThinkingConfig(thinking_budget=-1, include_thoughts=True),
                        response_mime_type="application/json",
                        response_schema=response_schema
                    )
                else:
                    config = types.GenerateContentConfig(
                        thinking_config=types.ThinkingConfig(thinking_budget=-1, include_thoughts=True),
                        response_mime_type="application/json"
                    )
                
                contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]
                
                response_chunks = client.models.generate_content_stream(
                    model=self.model_name,
                    contents=contents,
                    config=config
                )

                response_text = ""
                final_chunk = None
                
                for chunk in response_chunks:
                    if chunk.candidates:
                        for part in chunk.candidates[0].content.parts:
                            if hasattr(part, 'thought') and part.thought:
                                self.logger.log("LLM_THOUGHT_SUMMARY", {
                                    **log_context,
                                    "summary": "Reasoning",
                                    "thought_summary": part.text
                                })
                            elif part.text:
                                response_text += part.text
                    final_chunk = chunk

                duration = time.time() - start_time
                metrics['duration'] += duration
                metrics['calls'] += 1

                if final_chunk and final_chunk.usage_metadata:
                    meta = final_chunk.usage_metadata
                    metrics['in_tokens'] = meta.prompt_token_count or 0
                    metrics['out_tokens'] = meta.candidates_token_count or 0
                    metrics['think_tokens'] = getattr(meta, 'thoughts_token_count', 0)
                    
                    metrics['total_tokens'] = meta.total_token_count or 0

                self.logger.log("LLM_RAW_OUTPUT_TEXT", {
                    **log_context, 
                    "summary": f"Response (Attempt {attempt+1})", 
                    "raw_response_str": response_text
                })

                # Parsing
                if response_schema:
                    clean_text = response_text.replace("```json", "").replace("```", "").strip()
                    validated_obj = response_schema.model_validate_json(clean_text)
                    return validated_obj.model_dump(), dict(metrics)
                else:
                    clean_text = response_text.replace("```json", "").replace("```", "").strip()
                    return json.loads(clean_text), dict(metrics)
            
            except Exception as e:
                self.logger.log("ERROR", {"summary": f"LLM Error (Attempt {attempt+1}): {e}"})
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY_SECONDS)

        return None, dict(metrics)