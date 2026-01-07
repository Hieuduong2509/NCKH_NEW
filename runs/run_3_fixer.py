from pathlib import Path
from src.utils.config import OUTPUT_DIR, DATA_DIR, FIXER_PROMPT_FILE, get_run_output_dir
from src.agents.fixer import FixerAgent

def main():
    print("--- Fixer Runner ---")
    input_str = input("Enter path to AGENT output dir (containing validation_output): ").strip()
    input_dir = Path(input_str)
    
    tag = input("Enter run tag: ").strip() or "fix_run"
    out_dir = get_run_output_dir(OUTPUT_DIR, "fixer", tag)

    agent = FixerAgent(input_dir, out_dir, DATA_DIR, FIXER_PROMPT_FILE)
    agent.run()
    
    print(f"Done. Output: {out_dir}")

if __name__ == "__main__":
    main()