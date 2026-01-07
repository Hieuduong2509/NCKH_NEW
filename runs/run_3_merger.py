from pathlib import Path
from src.utils.config import OUTPUT_DIR, get_run_output_dir
from src.processing.merger import ScheduleMerger

def main():
    print("--- Merger Runner ---")
    input_str = input("Enter path to 'working_schedules' dir to merge: ").strip()
    tag = input("Enter run tag: ").strip() or "merge_run"
    out_dir = get_run_output_dir(OUTPUT_DIR, "merger", tag)
    
    ScheduleMerger.merge_directory(Path(input_str), out_dir)
    print(f"Done. Output: {out_dir}")

if __name__ == "__main__":
    main()