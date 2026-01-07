import time
import json
import datetime
from pathlib import Path
from collections import defaultdict
from typing import List, Dict

from src.agents.base import BaseAgent
from src.utils.config import FIXER_MODEL_NAME
from src.utils.file_io import load_json_file, save_json_file, load_text_file
from src.models.schemas import ScheduleAssignment 

class FixerAgent(BaseAgent):
    def __init__(self, agent_output_dir: Path, run_output_dir: Path, static_data_dir: Path, prompt_file: Path):
        super().__init__(agent_name="fixer", run_output_dir=run_output_dir, model_name=FIXER_MODEL_NAME)
        self.validator_dir = agent_output_dir / "validation_output"
        self.static_data_dir = static_data_dir
        self.prompt_file = prompt_file

    def _load_static_data(self) -> dict:
        data = {
            "constraints": load_json_file(self.static_data_dir / "constraints.json"),
            "instructors": load_json_file(self.static_data_dir / "instructors.json"),
            "rooms": load_json_file(self.static_data_dir / "rooms.json"),
            "prompt_template": load_text_file(self.prompt_file, "Fixer Prompt")
        }

        if not all(data.values()):
            raise RuntimeError("Missing static data (constraints / instructors / rooms / prompt).")

        return data


    def run(self):
        self.logger.log("MILESTONE", {"summary": "--- Fixer Agent Started ---"})
        start_time = time.time()

        try:
            static_data = self._load_static_data()
            batch_dirs = sorted([d for d in self.validator_dir.iterdir() if d.is_dir() and d.name.startswith('batch_')])
            
            if not batch_dirs:
                self.logger.log("WARNING", {"summary": "No batch directories found."})
                return

            global_schedule = {} 
            batch_map = {} 

            for b_dir in batch_dirs:
                f_path = next(b_dir.glob('validated_schedule_*.json'), None)
                if f_path:
                    courses = load_json_file(f_path)
                    batch_map[b_dir.name] = []
                    for c in courses:
                        global_schedule[c['course_id']] = c
                        batch_map[b_dir.name].append(c['course_id'])

            report_data = []
            
            for b_name, c_ids in batch_map.items():
                self.logger.log("INFO", {"summary": f"Scanning {b_name} for violations..."})
                batch_metrics = defaultdict(float)
                batch_metrics['batch_id'] = b_name
                
                courses_to_fix = [global_schedule[cid] for cid in c_ids if global_schedule[cid].get('hard_violation_types')]
                
                if not courses_to_fix:
                    batch_metrics['status'] = "Skipped (Clean)"
                else:
                    batch_metrics['status'] = "Processed"
                    for c in courses_to_fix:
                        c['time_slot'] = "<>"
                        c['room_id'] = "<>"

                    for course in courses_to_fix:
                        cid = course['course_id']
                        violations = course.get('hard_violation_types', [])
                        
                        # sem = static_data['course_to_semester'].get(cid.split('-')[0])
                        # peers = [pid for pid, s in static_data['course_to_semester'].items() if s == sem]
                        
                        prompt = f"""{static_data['prompt_template']}
# --- Data ---
## Constraints
{json.dumps(static_data['constraints'], indent=2)}
## Instructors
{json.dumps(static_data['instructors'], indent=2)}
## Rooms
{json.dumps(static_data['rooms'], indent=2)}

## Current Global Schedule
{json.dumps(list(global_schedule.values()), indent=2)}
## Course to Fix
{json.dumps(course, indent=2)}
## Violations Detected
{json.dumps(violations, indent=2)}

# --- End ---
"""
                        # --- CHANGED: Added response_schema ---
                        response, m = self.call_llm(
                            prompt, 
                            {'course_id': cid, 'batch_id': b_name},
                            response_schema=ScheduleAssignment
                        )
                        for k, v in m.items(): batch_metrics[k] += v

                        if response and response.get('time_slot') and response.get('time_slot') != "NO_FIX_FOUND":
                            course['time_slot'] = response.get('time_slot')
                            course['room_id'] = response.get('room_id')
                            course['fixed_by_llm_attempt'] = True
                            course.pop('hard_violation_types', None) 
                            batch_metrics['fixed_count'] += 1
                        else:
                            batch_metrics['failed_count'] += 1
                
                report_data.append(dict(batch_metrics))

            for b_name, c_ids in batch_map.items():
                batch_data = [global_schedule[cid] for cid in c_ids]
                clean_name = b_name.replace("validated_schedule_", "")
                save_json_file(self.working_schedules_dir / f"{clean_name}.json", batch_data)

            save_json_file(self.run_output_dir / "consolidated_schedule_DEBUG.json", list(global_schedule.values()))
            self._write_report(report_data, time.time() - start_time)

        except Exception as e:
            self.logger.log("FATAL_ERROR", {"summary": f"Fixer failed: {e}"})

    def _write_report(self, data: List[Dict], duration: float):
        path = self.run_output_dir / "run_report_fixer.txt"
        
        total_fixed = sum(d.get('fixed_count', 0) for d in data)
        total_failed = sum(d.get('failed_count', 0) for d in data)
        total_in = sum(d.get('in_tokens', 0) for d in data)
        total_out = sum(d.get('out_tokens', 0) for d in data)
        total_think = sum(d.get('think_tokens', 0) for d in data)
        total_all = sum(d.get('total_tokens', 0) for d in data)

        with open(path, "w", encoding='utf-8') as f:
            f.write(f"--- Fixer Run Report ---\n")
            f.write(f"Date: {datetime.datetime.now().isoformat()}\n")
            f.write(f"Model: {self.model_name}\n")
            f.write(f"Total Duration: {duration:.2f}s\n\n")

            f.write(f"--- Global Totals ---\n")
            f.write(f"Courses Fixed: {int(total_fixed)}\n")
            f.write(f"Courses Failed: {int(total_failed)}\n")
            f.write(f"Total Tokens: {total_all} (In: {total_in}, Out: {total_out}, Think: {total_think})\n\n")

            f.write(f"--- Per Batch Details ---\n")
            for item in data:
                f.write(f"Batch {item['batch_id']}: {item['status']}\n")
                if item['status'] == "Processed":
                    f.write(f"  Fixed: {int(item.get('fixed_count', 0))} | Failed: {int(item.get('failed_count', 0))}\n")
                    f.write(f"  Calls: {item.get('calls', 0)}\n")
                    f.write(f"  Duration: {item.get('duration', 0.0):.2f}s\n")
                    f.write(f"  Tokens -> In: {item.get('in_tokens',0)} | Out: {item.get('out_tokens',0)} | Think: {item.get('think_tokens',0)}\n")
                f.write("-" * 30 + "\n")