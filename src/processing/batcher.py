import math
import shutil
from pathlib import Path
from typing import List, Dict

from src.utils.config import BATCH_SIZE, BATCH_COURSES_DIR, BATCH_INSTRUCTORS_DIR
from src.utils.file_io import save_json_file

class BatchProcessor:
    @staticmethod
    def prepare_initial_batches(courses: List[Dict], instructors: List[Dict]):
        """
        Logic for Run 0: Sorts, adds placeholders, filters instructors, saves batches.

        """
        if not courses or not instructors:
            print("CRITICAL: Master data missing.")
            return

        # 1. Sort by complexity
        courses.sort(key=lambda c: c.get('num_students', 0), reverse=True)

        # 2. Reset directories
        for d in [BATCH_COURSES_DIR, BATCH_INSTRUCTORS_DIR]:
            if d.exists(): shutil.rmtree(d)
            d.mkdir(parents=True, exist_ok=True)

        num_batches = math.ceil(len(courses) / BATCH_SIZE)
        inst_map = {i['instructor_id']: i for i in instructors}

        print(f"  [BatchProcessor] Creating {num_batches} batches...")

        for i in range(num_batches):
            subset = courses[i * BATCH_SIZE : (i + 1) * BATCH_SIZE]
            
            for c in subset:
                c['time_slot'] = "<>"
                c['room_id'] = "<>"

            relevant_ids = {c['assigned_instructor'] for c in subset}
            relevant_insts = [inst_map[iid] for iid in relevant_ids if iid in inst_map]

            b_num = i + 1
            save_json_file(BATCH_COURSES_DIR / f"batch_courses_{b_num}.json", subset)
            save_json_file(BATCH_INSTRUCTORS_DIR / f"batch_instructors_{b_num}.json", relevant_insts)
            print(f"    - Batch {b_num}: {len(subset)} courses")

    @staticmethod
    def rebatch_schedule(clean_schedule: List[Dict], output_dir: Path):
        """
        
        Logic for Run 5: Takes a clean list, splits it, saves to working_schedules

        """
        working_dir = output_dir / "working_schedules"
        working_dir.mkdir(parents=True, exist_ok=True)
        
        save_json_file(output_dir / "consolidated_schedule.json", clean_schedule)

        print(f"  [BatchProcessor] Splitting {len(clean_schedule)} courses...")
        
        for i in range(0, len(clean_schedule), BATCH_SIZE):
            chunk = clean_schedule[i : i + BATCH_SIZE]
            b_num = (i // BATCH_SIZE) + 1
            save_json_file(working_dir / f"batch_{b_num}.json", chunk)