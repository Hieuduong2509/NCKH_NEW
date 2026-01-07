from pathlib import Path
from src.utils.config import COURSES_FILE, INSTRUCTORS_FILE, ROOMS_FILE, SEMESTERS_RULE_FILE
from src.utils.file_io import load_json_file, save_json_file
from src.constraints import ScheduleValidator

def main():
    print("--- Soft Constraint Validator ---")
    while True:
        path_str = input("Enter path to directory: ")
        schedule_dir = Path(path_str)
        if schedule_dir.is_dir(): break
        print("Invalid directory.")

    # Load Static
    instructors = load_json_file(INSTRUCTORS_FILE)
    courses = load_json_file(COURSES_FILE)
    rooms = load_json_file(ROOMS_FILE)
    curriculum = load_json_file(SEMESTERS_RULE_FILE)
    
    validator = ScheduleValidator(instructors, courses, rooms, curriculum)

    # Find Schedule
    f = next(schedule_dir.glob('*_schedule.json'), None)
    if not f:
        print("No schedule found.")
        return

    schedule = load_json_file(f)
    
    # 1. Check Hard Constraints (Safety Check)
    violating_ids, h_details = validator.validate_hard_constraints(schedule)
    print(f"Hard Constraint Violations: {len(violating_ids)}")

    # 2. Check Soft Constraints
    sc_result = validator.validate_soft_constraints(schedule)
    print(f"Soft Constraint Score: {sc_result['total_weighted_penalty']}")

    # Save
    out_dir = schedule_dir / "sc_validation_output"
    out_dir.mkdir(exist_ok=True)

    report = {
        "hard_validation": {"violating_count": len(violating_ids), "details": h_details},
        "soft_constraint_evaluation": sc_result
    }
    save_json_file(out_dir / "soft_validation_report.json", report)
    
    # Annotate (keep hard violations visible)
    for c in schedule:
        cid = str(c.get('course_id'))
        if cid in h_details:
            c['hard_violation_types'] = h_details[cid]
            
    save_json_file(out_dir / "validated_schedule_with_sc_score.json", schedule)

if __name__ == "__main__":
    main()