import time
import json
import datetime
from pathlib import Path
from collections import defaultdict
from typing import List, Dict

from src.agents.base import BaseAgent
from src.utils.config import OPTIMIZER_MODEL_NAME
from src.utils.file_io import load_json_file, save_json_file, load_text_file
from src.constraints import ScheduleValidator
from src.models.schemas import ScheduleAssignment 

class OptimizerAgent(BaseAgent):
    def __init__(self, agent_output_dir: Path, run_output_dir: Path, static_data_dir: Path, prompt_file: Path):
        super().__init__(agent_name="optimizer", run_output_dir=run_output_dir, model_name=OPTIMIZER_MODEL_NAME)
        self.validator_dir = agent_output_dir / "sc_validation_output"
        self.static_data_dir = static_data_dir
        self.prompt_file = prompt_file

    def _load_data(self):
        static = {
            "instructors": load_json_file(self.static_data_dir / "instructors.json"),
            "rooms": load_json_file(self.static_data_dir / "rooms.json"),
            "courses": load_json_file(self.static_data_dir / "courses.json"),
            "constraints": load_json_file(self.static_data_dir / "constraints.json"),
            "semesters": load_json_file(self.static_data_dir / "curriculum.json"),
            "prompt_template": load_text_file(self.prompt_file, "Optimizer Prompt")
        }
        schedule = load_json_file(self.validator_dir / "validated_schedule_with_sc_score.json")
        sc_report = load_json_file(self.validator_dir / "soft_validation_report.json")
        if not all([static['instructors'], schedule, sc_report]):
            raise RuntimeError("Missing data for optimizer.")
        return static, schedule, sc_report

    def _identify_candidates(self, schedule, sc_report) -> List[Dict]:
        candidates = []
        gap_details = sc_report.get("soft_constraint_evaluation", {}).get("penalties", {}).get("instructor_gaps", {}).get("details", {})
        
        for inst_id, days in gap_details.items():
            for day, gap_size in days.items():
                relevant = [c for c in schedule if str(c['assigned_instructor']) == str(inst_id) and c['time_slot'].startswith(f"{day}-")]
                for c in relevant:
                    candidates.append({
                        "course": c,
                        "goal": f"Reduce {gap_size}-period gap for Instructor {inst_id} on Day {day}"
                    })
        return candidates

    def run(self):
        self.logger.log("MILESTONE", {"summary": "--- Optimizer Agent Started ---"})
        start_time = time.time()
        
        try:
            static, schedule, sc_report = self._load_data()
            validator = ScheduleValidator(static['instructors'], static['courses'], static['rooms'], static['semesters'])
            
            candidates = self._identify_candidates(schedule, sc_report)
            self.logger.log("INFO", {"summary": f"Identified {len(candidates)} optimization candidates."})
            
            metrics = defaultdict(float)
            optimized_count = 0
            
            schedule_map = {c['course_id']: c for c in schedule}

            for item in candidates:
                course = item['course']
                goal = item['goal']
                cid = course['course_id']
                
                prompt = f"""{static['prompt_template']}
# --- Data ---
## Constraints
{json.dumps(static['constraints'], indent=2)}
## Instructors
{json.dumps(static['instructors'], indent=2)}
## Rooms
{json.dumps(static['rooms'], indent=2)}
## Current Full Schedule
{json.dumps(list(schedule_map.values()), indent=2)}
## Target Course
{json.dumps(course, indent=2)}
## Goal
{goal}
# --- End ---
"""
 
                response, m = self.call_llm(
                    prompt, 
                    {'course_id': cid, 'goal': goal},
                    response_schema=ScheduleAssignment
                )
                for k,v in m.items(): metrics[k] += v
                
                if response and response.get('time_slot'):
                    original_ts = schedule_map[cid]['time_slot']
                    original_room = schedule_map[cid]['room_id']
                    
                    schedule_map[cid]['time_slot'] = response['time_slot']
                    schedule_map[cid]['room_id'] = response['room_id']
                    
                    violating_ids, _ = validator.validate_hard_constraints(list(schedule_map.values()))
                    
                    if not violating_ids:
                        self.logger.log("SUCCESS_SUMMARY", {"summary": f"Optimization accepted for {cid}"})
                        optimized_count += 1
                    else:
                        schedule_map[cid]['time_slot'] = original_ts
                        schedule_map[cid]['room_id'] = original_room
                        self.logger.log("WARNING", {"summary": f"Optimization rejected (Hard Violation) for {cid}"})
            
            final_schedule = list(schedule_map.values())
            save_json_file(self.run_output_dir / "optimized_schedule.json", final_schedule)
            
            self._write_report(metrics, len(candidates), optimized_count, time.time() - start_time)

        except Exception as e:
            self.logger.log("FATAL_ERROR", {"summary": f"Optimizer failed: {e}"})

    def _write_report(self, metrics: Dict, candidates_count: int, optimized_count: int, duration: float):
            with open(self.run_output_dir / "run_report_optimizer.txt", "w", encoding='utf-8') as f:
                f.write(f"--- Optimizer Run Report ---\n")
                f.write(f"Date: {datetime.datetime.now().isoformat()}\n")
                f.write(f"Model: {self.model_name}\n")
                f.write(f"Total Duration: {duration:.2f}s\n\n")

                f.write(f"--- Summary ---\n")
                f.write(f"Candidates Identified: {candidates_count}\n")
                f.write(f"Courses Optimized:     {optimized_count}\n")
                f.write(f"Rejected/Failed:       {candidates_count - optimized_count}\n\n")

                f.write(f"--- Token & API Usage ---\n")
                f.write(f"Total API Calls: {int(metrics.get('calls', 0))}\n")
                f.write(f"Total Tokens:    {int(metrics.get('total_tokens', 0))}\n")
                f.write(f"  - Input:       {int(metrics.get('in_tokens', 0))}\n")
                f.write(f"  - Output:      {int(metrics.get('out_tokens', 0))}\n")
                f.write(f"  - Thinking:    {int(metrics.get('think_tokens', 0))}\n")