from pathlib import Path
from typing import Tuple, List, Dict
from src.utils.file_io import load_json_file, save_json_file

class ScheduleCleaner:
    @staticmethod
    def clean_and_analyze(agent_output_dir: Path) -> Tuple[Path, int, int]:
        """
        Logic for Run 4:Splits clean/unsolved courses.

        """
        # Auto-discovery
        f = next(agent_output_dir.glob('**/validated_schedule_consolidated*.json'), None)
        if not f: f = next(agent_output_dir.glob('consolidated_schedule*.json'), None)
        
        if not f: raise FileNotFoundError("No consolidated schedule found to clean.")

        full_schedule = load_json_file(f)
        clean = []
        unsolved = []

        for c in full_schedule:
            if c.get('hard_violation_types'):
                unsolved.append(c)
            else:
                c.pop('hard_violation_types', None)
                c.pop('fixed_by_llm_attempt', None)
                clean.append(c)

        out_dir = agent_output_dir / "cleaning_and_analysis_output"
        clean_path = out_dir / "clean_schedule_for_optimizer.json"
        
        save_json_file(clean_path, clean)
        save_json_file(out_dir / "unsolved_courses.json", unsolved)
        
        return clean_path, len(clean), len(unsolved)