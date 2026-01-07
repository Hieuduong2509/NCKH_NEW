from pathlib import Path
from src.utils.config import COURSES_FILE, INSTRUCTORS_FILE, ROOMS_FILE, SEMESTERS_RULE_FILE
from src.utils.file_io import load_json_file, save_json_file
from src.constraints import ScheduleValidator

def perform_hard_constraint_validation(input_schedule_path: Path, output_dir: Path):
    """
    Validates a single schedule file using the unified ScheduleValidator.
    """
    run_identifier = input_schedule_path.stem
    print(f"--- Validating: {run_identifier} ---")

    # Load Static Data
    instructors = load_json_file(INSTRUCTORS_FILE)
    courses = load_json_file(COURSES_FILE)
    rooms = load_json_file(ROOMS_FILE)
    curriculum = load_json_file(SEMESTERS_RULE_FILE)

    if not all([instructors, courses, rooms, curriculum]):
        print("CRITICAL: Failed to load static data.")
        return

    # Initialize Validator
    validator = ScheduleValidator(instructors, courses, rooms, curriculum)
    
    # Load Schedule
    schedule_data = load_json_file(input_schedule_path)
    if not schedule_data:
        print(f"ERROR: Empty schedule at {input_schedule_path}")
        return

  
    total_entries = len(schedule_data)
    entries_fully_scheduled = sum(
        1 for c in schedule_data 
        if c.get('time_slot') not in [None, "<>"] and c.get('room_id') not in [None, "<>"]
    )

    # Run Validation
    violating_ids, details = validator.validate_hard_constraints(schedule_data)

    print(f"Validation Complete. Violations found: {len(violating_ids)}")

    # Annotate Schedule
    output_schedule = []
    for course in schedule_data:
        cid = str(course.get('course_id'))
        if cid in details:
            course['hard_violation_types'] = sorted(list(set(details[cid])))
        else:
            course.pop('hard_violation_types', None)
        output_schedule.append(course)

    # Save Annotated Schedule
    output_dir.mkdir(parents=True, exist_ok=True)
    save_json_file(output_dir / f"validated_schedule_{run_identifier}.json", output_schedule)
    
    # Generate Summary Report
    violations_summary = {}
    for cid, violation_list in details.items():
        for v_type in violation_list:
            violations_summary[v_type] = violations_summary.get(v_type, 0) + 1

    report = {
        "source_file": str(input_schedule_path),
        "total_entries_in_input_schedule": total_entries,       
        "entries_fully_scheduled_for_checks": entries_fully_scheduled, 
        "total_unique_courses_violating": len(violating_ids),
        "violations_summary_by_type": violations_summary,
        "violations_details_per_course": details
    }
    
    # Save the report
    report_path = output_dir / f"validation_report_{run_identifier}.json"
    save_json_file(report_path, report)
    print(f"Saved validation report to: {report_path}")

def main():
    print("--- Hard Constraint Validator Script ---")
    while True:
        path_str = input("Enter path to directory containing schedules: ")
        schedule_dir = Path(path_str)
        if schedule_dir.is_dir(): break
        print("Invalid directory.")

    # Find files
    files = []
    consolidated = next(schedule_dir.glob('consolidated_schedule*.json'), None)
    if consolidated: files.append(consolidated)
    
    working_dir = schedule_dir / "working_schedules"
    if working_dir.is_dir():
        files.extend(sorted(working_dir.glob('batch_*.json')))

    if not files:
        print("No schedule files found.")
        return

    validation_out = schedule_dir / "validation_output"
    for f in files:
        out_subdir = validation_out / f.stem
        perform_hard_constraint_validation(f, out_subdir)

if __name__ == "__main__":
    main()