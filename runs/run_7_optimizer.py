from pathlib import Path
from src.utils.config import OUTPUT_DIR, DATA_DIR, OPTIMIZER_PROMPT_FILE, get_run_output_dir
from src.agents.optimizer import OptimizerAgent

def main():
    print("--- Optimizer Runner ---")
    input_str = input("Enter path to rebatched/optimizer directory: ").strip()
    input_dir = Path(input_str)
    
    tag = input("Enter run tag: ").strip() or "opt_run"
    out_dir = get_run_output_dir(OUTPUT_DIR, "optimizer", tag)
    
    agent = OptimizerAgent(input_dir, out_dir, DATA_DIR, OPTIMIZER_PROMPT_FILE)
    agent.run()
    
    print(f"Done. Output: {out_dir}")

if __name__ == "__main__":
    main()