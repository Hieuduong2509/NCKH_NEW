import json
import os
import re
from pathlib import Path
from typing import Any, Optional, Union

def load_json_file(filepath: Union[str, Path], entity_name: str = "JSON file") -> Optional[Any]:
    """Loads a JSON file with comprehensive error handling."""
    path = Path(filepath)
    if not path.exists():
        print(f"ERROR: Cannot load {entity_name}. File not found at: {path}")
        return None
    try:
        with open(path, "r", encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to decode {entity_name} from {path}: {e}")
        return None
    except Exception as e:
        print(f"ERROR: Unexpected error loading {entity_name} from {path}: {e}")
        return None

def save_json_file(filepath: Union[str, Path], data: Any, entity_name: str = "JSON file") -> bool:
    """Saves data to a JSON file."""
    try:
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        return True
    except Exception as e:
        print(f"ERROR: Failed to save {entity_name} to {filepath}: {e}")
        return False

def load_text_file(filepath: Union[str, Path], entity_name: str = "Text file") -> Optional[str]:
    """Loads a plain text file."""
    path = Path(filepath)
    if not path.exists():
        print(f"ERROR: Cannot load {entity_name}. File not found at: {path}")
        return None
    try:
        with open(path, "r", encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"ERROR: Error reading {entity_name} from {path}: {e}")
        return None
    
def extract_json_from_response(raw_text: str) -> Optional[Any]:
    """
    Robustly extracts a JSON object or array from a string (LLM response).
    Handles markdown code blocks and raw JSON strings.
    """
    if not isinstance(raw_text, str):
        return None
    
    # 1. Try finding markdown code blocks first (most reliable)
    # This regex captures content inside ```json ... ``` or just ``` ... ```
    match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', raw_text, re.DOTALL)
    if match:
        json_str = match.group(1)
    else:
        # 2. Fallback: Find the first open brace/bracket and last close brace/bracket
        # This helps if the LLM output some conversational text before/after the JSON
        start_brace = raw_text.find('{')
        start_bracket = raw_text.find('[')
        
        if start_brace == -1 and start_bracket == -1:
            return None
            
        # Determine if it's likely an Object or an Array
        if start_bracket != -1 and (start_brace == -1 or start_bracket < start_brace):
            start_index = start_bracket
            end_index = raw_text.rfind(']')
        else:
            start_index = start_brace
            end_index = raw_text.rfind('}')

        if start_index != -1 and end_index != -1:
            json_str = raw_text[start_index : end_index + 1]
        else:
            json_str = raw_text

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return None