from src.utils.config import OUTPUT_DIR, DATA_DIR, BATCH_COURSES_DIR, BATCH_INSTRUCTORS_DIR, GENERATOR_PROMPT_FILE, get_run_output_dir
from src.agents.generator import GeneratorAgent

def main():
    print("--- Generator Runner ---")
    tag = input("Enter run tag: ").strip() or "default"
    out_dir = get_run_output_dir(OUTPUT_DIR, "generator", tag)
    
    agent = GeneratorAgent(out_dir, BATCH_COURSES_DIR, BATCH_INSTRUCTORS_DIR, DATA_DIR, GENERATOR_PROMPT_FILE)
    agent.run()
    
    print(f"Done. Output: {out_dir}")

if __name__ == "__main__":
    main()