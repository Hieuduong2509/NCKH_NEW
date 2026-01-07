import sys
from pathlib import Path

# --- User-Editable Controller Configuration ---
MAX_FIXER_ITERATIONS_PER_LEVEL = 2
MAX_OPTIMIZER_ITERATIONS = 2

# --- Import step logic from the 'controller' sub-directory ---
from app.pipeline.steps import (
    run_dataprep_step, run_generator, run_validator, run_fixer, run_merger,
    run_cleaner_and_analyzer, run_rebatcher, run_sc_validator, run_optimizer,
    is_schedule_fully_fixed, get_batch_file_count
)

def run_pipeline(pipeline_run_tag: str, start_from_dir: str = None):
    
    print(f"--- STARTING AUTOMATED PIPELINE: {pipeline_run_tag} ---")
    print(f"CONFIG: Max Fixer Iterations Per Level = {MAX_FIXER_ITERATIONS_PER_LEVEL}")
    print(f"CONFIG: Max Optimizer Iterations = {MAX_OPTIMIZER_ITERATIONS}")

    final_hc_valid_dir = None

    if start_from_dir:
        # --- RESUME LOGIC ---
        print(f"\n{'#'*60}\n--- CONTROLLER: RESUMING PIPELINE ---\n{'#'*60}")
        final_hc_valid_dir = Path(start_from_dir)
        if not final_hc_valid_dir.is_dir():
            print(f"CRITICAL ERROR: The specified 'start from' directory does not exist: {start_from_dir}")
            return
        print(f"Skipping Phases 0-2 and starting from existing directory: {final_hc_valid_dir}")
    else:
        # --- FULL RUN LOGIC (Phases 0, 1, 2) ---
        run_dataprep_step()
        current_schedule_dir = run_generator(run_tag=pipeline_run_tag)

        level = 1
        while True:
            print(f"\n{'#'*60}\n--- CONTROLLER: Starting Hard Constraint Fixing: LEVEL {level} ---\n{'#'*60}")
            is_level_fixed = False
            for i in range(MAX_FIXER_ITERATIONS_PER_LEVEL):
                iteration_tag = f"L{level}_fix_run{i+1}"
                print(f"\n--- FIXER ITERATION {i+1}/{MAX_FIXER_ITERATIONS_PER_LEVEL} (Tag: {iteration_tag}) ---")
                validation_dir = run_validator(current_schedule_dir)
                if is_schedule_fully_fixed(validation_dir):
                    print(f"--- SUCCESS: Level {level} is fully fixed. ---")
                    is_level_fixed = True
                    break
                current_schedule_dir = run_fixer(validation_dir, run_tag=iteration_tag)
            
            if not is_level_fixed:
                print(f"WARNING: Max fixer iterations ({MAX_FIXER_ITERATIONS_PER_LEVEL}) reached. Forcing merge.")
                run_validator(current_schedule_dir)
            
            if get_batch_file_count(current_schedule_dir) <= 1:
                print(f"\n--- Hard Constraint Fixing Phase Complete ---")
                break
            
            merge_tag = f"L{level}_merge_to_L{level+1}"
            current_schedule_dir = run_merger(current_schedule_dir, run_tag=merge_tag)
            level += 1
        
        final_hc_valid_dir = current_schedule_dir

    # # --- PHASE 3: Cleaning and Re-batching for Optimization ---
    # print(f"\n{'#'*60}\n--- CONTROLLER: Starting Preparation for Optimization ---\n{'#'*60}")
    # clean_schedule_path = run_cleaner_and_analyzer(final_hc_valid_dir)
    # rebatched_dir_for_opt = run_rebatcher(clean_schedule_path, run_tag=f"{pipeline_run_tag}_rebatch")

    # # --- PHASE 4: Soft Constraint Optimization Loop ---
    # print(f"\n{'#'*60}\n--- CONTROLLER: Starting Soft Constraint Optimization ---\n{'#'*60}")
    # current_opt_dir = rebatched_dir_for_opt

    # for i in range(MAX_OPTIMIZER_ITERATIONS):
    #     iteration_tag = f"opt_run{i+1}"
    #     print(f"\n--- OPTIMIZER ITERATION {i+1}/{MAX_OPTIMIZER_ITERATIONS} (Tag: {iteration_tag}) ---")
    #     run_sc_validator(current_opt_dir)
    #     optimized_dir = run_optimizer(current_opt_dir, run_tag=iteration_tag)
    #     current_opt_dir = optimized_dir
    
    # print("\n--- Running Final Soft Constraint Validation ---")
    # run_sc_validator(current_opt_dir)

    # print(f"\n{'#'*60}\n--- AUTOMATED PIPELINE {pipeline_run_tag} FINISHED ---\n{'#'*60}")
    # print(f"The final, optimized schedule can be found in the latest optimizer run directory: {current_opt_dir}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  For a full run: python controller.py <pipeline_run_tag>")
        print("  To resume a run: python controller.py <pipeline_run_tag> --start_from <path_to_directory>")
        print("\nExample (full run): python controller.py exp01_automated")
        print("Example (resume):   python controller.py exp01_opt_phase --start_from output/fixer_L3_fix_run2")
    else:
        tag = sys.argv[1]
        start_dir = None
        if len(sys.argv) > 3 and sys.argv[2] == '--start_from':
            start_dir = sys.argv[3]
        
        run_pipeline(tag, start_from_dir=start_dir)