from pathlib import Path
from src.processing.cleaner import ScheduleCleaner

def main():
    print("--- Cleaner & Analyzer ---")
    input_str = input("Enter path to agent output dir: ").strip()
    try:
        path, clean_c, dirty_c = ScheduleCleaner.clean_and_analyze(Path(input_str))
        print(f"Analysis: {clean_c} clean, {dirty_c} unsolved.")
        print(f"Clean schedule saved to: {path}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()