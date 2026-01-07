from pathlib import Path
from src.utils.config import OUTPUT_DIR, get_run_output_dir
from src.utils.file_io import load_json_file
from src.processing.batcher import BatchProcessor

def main():
    print("--- Rebatcher ---")
    input_str = input("Enter path to agent output dir (containing cleaning_and_analysis_output): ").strip()
    clean_file = Path(input_str) / "cleaning_and_analysis_output" / "clean_schedule_for_optimizer.json"
    
    if not clean_file.exists():
        print("Clean schedule not found. Run Cleaner first.")
        return

    tag = input("Enter run tag: ").strip() or "rebatch"
    out_dir = get_run_output_dir(OUTPUT_DIR, "rebatched_for_optimizer", tag)
    
    data = load_json_file(clean_file)
    BatchProcessor.rebatch_schedule(data, out_dir)
    print(f"Done. Output: {out_dir}")

if __name__ == "__main__":
    main()