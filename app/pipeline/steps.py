

from pathlib import Path

from src.utils.config import (
    OUTPUT_DIR, DATA_DIR, BATCH_COURSES_DIR, BATCH_INSTRUCTORS_DIR,
    GENERATOR_PROMPT_FILE, FIXER_PROMPT_FILE, OPTIMIZER_PROMPT_FILE,
    COURSES_FILE, INSTRUCTORS_FILE, ROOMS_FILE, SEMESTERS_RULE_FILE,
    get_run_output_dir
)
from src.utils.file_io import load_json_file, save_json_file

# --- AGENTS ---
from src.agents.generator import GeneratorAgent
from src.agents.fixer import FixerAgent
from src.agents.optimizer import OptimizerAgent

# --- PROCESSING LOGIC (The Lego Bricks) ---
from src.constraints import ScheduleValidator
from src.processing.batcher import BatchProcessor
from src.processing.merger import ScheduleMerger
from src.processing.cleaner import ScheduleCleaner


def run_dataprep_step():
    print("\n--- Step: Data Prep ---")
    courses = load_json_file(COURSES_FILE)
    instructors = load_json_file(INSTRUCTORS_FILE)
    BatchProcessor.prepare_initial_batches(courses, instructors)

def run_generator(run_tag: str) -> Path:
    print("\n--- Step: Generator ---")
    out_dir = get_run_output_dir(OUTPUT_DIR, "generator", run_tag)
    agent = GeneratorAgent(
        out_dir, BATCH_COURSES_DIR, BATCH_INSTRUCTORS_DIR, DATA_DIR, GENERATOR_PROMPT_FILE
    )
    agent.run()
    return out_dir

def run_validator(agent_output_dir: Path) -> Path:
    print("\n--- Step: Hard Validator ---")
    val_out_dir = agent_output_dir / "validation_output"
    
    # 1. Load Static Data
    v = ScheduleValidator(
        load_json_file(INSTRUCTORS_FILE),
        load_json_file(COURSES_FILE),
        load_json_file(ROOMS_FILE),
        load_json_file(SEMESTERS_RULE_FILE)
    )

    # 2. Identify Files to Validate
    files = []
    if (f := next(agent_output_dir.glob('consolidated_schedule*.json'), None)): 
        files.append(f)
    working = agent_output_dir / "working_schedules"
    if working.is_dir():
        files.extend(sorted(working.glob('batch_*.json')))

    # 3. Perform Validation
    for f in files:
        # Create sub-folder per batch (Fixer expects this structure)
        batch_out_dir = val_out_dir / f.stem
        batch_out_dir.mkdir(parents=True, exist_ok=True)
        
        schedule = load_json_file(f)
        violating_ids, details = v.validate_hard_constraints(schedule)
        
        # Annotate schedule
        for c in schedule:
            cid = str(c.get('course_id'))
            if cid in details:
                c['hard_violation_types'] = sorted(list(set(details[cid])))
            else:
                c.pop('hard_violation_types', None)

        save_json_file(batch_out_dir / f"validated_schedule_{f.stem}.json", schedule)
        
        # Save Report
        report = {
            "source_file": str(f),
            "total_unique_courses_violating": len(violating_ids),
            "violations_details": details
        }
        save_json_file(batch_out_dir / f"validation_report_{f.stem}.json", report)

    return val_out_dir

def run_fixer(validator_output_dir: Path, run_tag: str) -> Path:
    print("\n--- Step: Fixer ---")
    out_dir = get_run_output_dir(OUTPUT_DIR, "fixer", run_tag)
    # Fixer agent expects the parent dir of validation_output
    agent = FixerAgent(validator_output_dir.parent, out_dir, DATA_DIR, FIXER_PROMPT_FILE)
    agent.run()
    return out_dir

def run_merger(fixer_output_dir: Path, run_tag: str) -> Path:
    print("\n--- Step: Merger ---")
    out_dir = get_run_output_dir(OUTPUT_DIR, "merger", run_tag)
    ScheduleMerger.merge_directory(fixer_output_dir / "working_schedules", out_dir)
    return out_dir

def run_cleaner_and_analyzer(agent_output_dir: Path) -> Path:
    print("\n--- Step: Cleaner ---")
    clean_path, _, _ = ScheduleCleaner.clean_and_analyze(agent_output_dir)
    return clean_path

def run_rebatcher(clean_schedule_path: Path, run_tag: str) -> Path:
    print("\n--- Step: Rebatcher ---")
    out_dir = get_run_output_dir(OUTPUT_DIR, "rebatched_for_optimizer", run_tag)
    data = load_json_file(clean_schedule_path)
    BatchProcessor.rebatch_schedule(data, out_dir)
    return out_dir

def run_sc_validator(agent_output_dir: Path) -> Path:
    print("\n--- Step: Soft Validator ---")
    f = next(agent_output_dir.glob('*_schedule.json'), None)
    if not f: return agent_output_dir # Handle edge case

    data = load_json_file(f)
    v = ScheduleValidator(
        load_json_file(INSTRUCTORS_FILE),
        load_json_file(COURSES_FILE),
        load_json_file(ROOMS_FILE),
        load_json_file(SEMESTERS_RULE_FILE)
    )
    
    # Run Checks
    sc_res = v.validate_soft_constraints(data)
    
    out_dir = agent_output_dir / "sc_validation_output"
    out_dir.mkdir(exist_ok=True)
    save_json_file(out_dir / "soft_validation_report.json", {"soft_constraint_evaluation": sc_res})
    save_json_file(out_dir / "validated_schedule_with_sc_score.json", data)
    return out_dir

def run_optimizer(rebatched_dir: Path, run_tag: str) -> Path:
    print("\n--- Step: Optimizer ---")
    out_dir = get_run_output_dir(OUTPUT_DIR, "optimizer", run_tag)
    agent = OptimizerAgent(rebatched_dir, out_dir, DATA_DIR, OPTIMIZER_PROMPT_FILE)
    agent.run()
    return out_dir

def is_schedule_fully_fixed(validation_dir: Path) -> bool:
    """Checks if any validation report contains violations."""
    reports = list(validation_dir.glob('batch_*/validation_report_*.json'))
    if not reports: return False
    total = sum(load_json_file(r).get("total_unique_courses_violating", 0) for r in reports)
    return total == 0

def get_batch_file_count(agent_output_dir: Path) -> int:
    """Helper to determine if merging is required."""
    working = agent_output_dir / "working_schedules"
    if not working.is_dir(): return 0
    return len(list(working.glob('batch_*.json')))