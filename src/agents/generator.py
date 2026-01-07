import time
import json
import shutil
import re
import datetime
from pathlib import Path
from typing import List, Dict

from src.agents.base import BaseAgent
from src.utils.config import GENERATOR_MODEL_NAME
from src.utils.file_io import load_json_file, save_json_file, load_text_file
from src.models.schemas import ScheduleBatchOutput  

class GeneratorAgent(BaseAgent):
    def __init__(self, run_output_dir: Path, batch_courses_dir: Path, batch_instructors_dir: Path, static_data_dir: Path, prompt_file: Path):
        super().__init__(agent_name="generator", run_output_dir=run_output_dir, model_name=GENERATOR_MODEL_NAME)
        self.batch_courses_dir = batch_courses_dir
        self.batch_instructors_dir = batch_instructors_dir
        self.static_data_dir = static_data_dir
        self.prompt_file = prompt_file

    def _load_static_data(self) -> dict:
        data = {
            "constraints": load_json_file(self.static_data_dir / "constraints.json", "Constraints"),
            "rooms": load_json_file(self.static_data_dir / "rooms.json", "Rooms"),
            "prompt_template": load_text_file(self.prompt_file, "Generator Prompt")
        }

        if not all(data.values()):
            raise RuntimeError("Missing static data files (constraints / rooms / prompt).")

        return data

    def _prepare_batches(self) -> List[Dict]:
        if not self.batch_courses_dir.exists():
            raise FileNotFoundError(f"Batch dir not found: {self.batch_courses_dir}")

        files = sorted([f for f in self.batch_courses_dir.iterdir() if f.name.startswith('batch_courses_') and f.suffix == '.json'])
        batch_info = []

        for f in files:
            match = re.search(r'_(\d+)\.json', f.name)
            if match:
                num = int(match.group(1))
                info = {
                    "batch_number": num,
                    "courses_path": f,
                    "instructors_path": self.batch_instructors_dir / f"batch_instructors_{num}.json",
                    "working_path": self.working_schedules_dir / f"batch_{num}.json"
                }
                batch_info.append(info)
                shutil.copy(info["courses_path"], info["working_path"])

        return sorted(batch_info, key=lambda x: x['batch_number'])

    def run(self):
        self.logger.log("MILESTONE", {"summary": "--- Generator Agent Started ---"})
        start_time = time.time()
        
        try:
            static_data = self._load_static_data()
            batches = self._prepare_batches()
            
            already_scheduled = []
            report_data = []

            for batch in batches:
                b_num = batch['batch_number']
                self.logger.log("MILESTONE", {"summary": f"Processing Batch {b_num}"})

                courses = load_json_file(batch['working_path'])
                instructors = load_json_file(batch['instructors_path'])
                
                prompt = f"""{static_data['prompt_template']}
# --- Batch {b_num} Data ---
## Courses to Schedule
{json.dumps(courses, indent=2)}
## Instructors
{json.dumps(instructors, indent=2)}
## Rooms
{json.dumps(static_data['rooms'], indent=2)}
## Constraints
{json.dumps(static_data['constraints'], indent=2)}
# ## Curriculum

## Previously Scheduled Context
{json.dumps(already_scheduled, indent=2)}
# --- End Data ---
"""

                response_data, metrics = self.call_llm(
                    prompt, 
                    log_context={'batch_id': b_num},
                    response_schema=ScheduleBatchOutput 
                )

                metrics['batch_number'] = b_num
                

                if response_data and 'schedules' in response_data:
                    response_list = response_data['schedules']
                    
                    llm_map = {c.get('course_id'): c for c in response_list if c.get('course_id')}
                    updated_courses = []
                    
                    for original in courses:
                        res = llm_map.get(original['course_id'])
                        if res:
                            original['time_slot'] = res.get('time_slot', '<>')
                            original['room_id'] = res.get('room_id', '<>')
                        updated_courses.append(original)

                    save_json_file(batch['working_path'], updated_courses)
                    already_scheduled.extend(updated_courses)
                    metrics['status'] = "Success"
                else:
                    metrics['status'] = "Failed"
                    self.logger.log("ERROR", {"summary": f"Batch {b_num} failed or returned invalid structure."})
                
                report_data.append(metrics)

            save_json_file(self.run_output_dir / "consolidated_schedule.json", already_scheduled)
            self._write_report(report_data, time.time() - start_time)

        except Exception as e:
            self.logger.log("FATAL_ERROR", {"summary": f"Generator failed: {e}"})

    def _write_report(self, data: List[Dict], duration: float):
        path = self.run_output_dir / "run_report_generator.txt"
        
        total_calls = sum(d.get('calls', 0) for d in data)
        total_in = sum(d.get('in_tokens', 0) for d in data)
        total_out = sum(d.get('out_tokens', 0) for d in data)
        total_think = sum(d.get('think_tokens', 0) for d in data)
        total_all = sum(d.get('total_tokens', 0) for d in data)
        success_count = sum(1 for d in data if d['status'] == 'Success')

        with open(path, "w", encoding='utf-8') as f:
            f.write(f"--- Generator Run Report ---\n")
            f.write(f"Date: {datetime.datetime.now().isoformat()}\n")
            f.write(f"Model: {self.model_name}\n")
            f.write(f"Total Duration: {duration:.2f}s\n\n")
            
            f.write(f"--- Global Totals ---\n")
            f.write(f"Batches Processed: {len(data)}\n")
            f.write(f"Successful Batches: {success_count}\n")
            f.write(f"Total API Calls: {total_calls}\n")
            f.write(f"Total Tokens: {total_all} (In: {total_in}, Out: {total_out}, Think: {total_think})\n\n")

            f.write(f"--- Per Batch Details ---\n")
            for item in data:
                f.write(f"Batch {item['batch_number']}: {item['status']}\n")
                f.write(f"  Calls: {item.get('calls', 0)}\n")
                f.write(f"  Duration: {item.get('duration', 0.0):.2f}s\n")
                f.write(f"  Tokens -> In: {item.get('in_tokens',0)} | Out: {item.get('out_tokens',0)} | Think: {item.get('think_tokens',0)} | Total: {item.get('total_tokens',0)}\n")
                f.write("-" * 30 + "\n")