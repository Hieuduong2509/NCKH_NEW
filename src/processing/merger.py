import re
from pathlib import Path
from src.utils.file_io import load_json_file, save_json_file

class ScheduleMerger:
    @staticmethod
    def merge_directory(input_dir: Path, output_dir: Path):
        """Logic for Run 3: Merges batch files using Smart Tail logic (3 at end if odd)."""
        working_out = output_dir / "working_schedules"
        working_out.mkdir(parents=True, exist_ok=True)

        # Sort numerically
        files = sorted(
            [f for f in input_dir.glob('*.json')], 
            key=lambda x: int(re.search(r'_(\d+)\.json', x.name).group(1)) if re.search(r'_(\d+)\.json', x.name) else 0
        )
        
        consolidated = []
        idx = 1
        i = 0
        total_files = len(files)

        print(f"  [ScheduleMerger] Merging {total_files} files...")

        while i < total_files:
            remaining = total_files - i
            
            if remaining == 3 and (total_files % 2 != 0):
                merge_count = 3
            elif remaining >= 2:
                merge_count = 2
            else:
                merge_count = 1
                
            chunk = files[i : i + merge_count]
            i += merge_count
            
            merged_batch = []
            for f in chunk:
                data = load_json_file(f)
                if data:
                    # Clean flags
                    for c in data:
                        c.pop('fixed_by_llm_attempt', None)
                        c.pop('hard_violation_types', None)
                    merged_batch.extend(data)
            
            if merged_batch:
                save_json_file(working_out / f"batch_{idx}.json", merged_batch)
                consolidated.extend(merged_batch)
                idx += 1
        
        save_json_file(output_dir / "consolidated_schedule.json", consolidated)