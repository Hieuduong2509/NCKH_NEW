import os
from pathlib import Path
from dotenv import load_dotenv

# --- Core Path Configuration ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
print(f"Project Root Detected: {PROJECT_ROOT}")

# Load environment variables from a .env file at the project root
dotenv_path = PROJECT_ROOT / '.env'
load_dotenv(dotenv_path=dotenv_path)
print(f"Loading .env from: {dotenv_path}")

# --- API and Model Configuration ---
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
IS_GEMINI_CONFIGURED = bool(GOOGLE_API_KEY)

# Centralized model names
GENERATOR_MODEL_NAME = "gemini-2.5-flash" 
FIXER_MODEL_NAME = "gemini-2.5-flash"
OPTIMIZER_MODEL_NAME = "gemini-2.5-flash"

# --- LLM Call Settings ---
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 30 #60 or 10, or even faster if risk acceptable

# --- Directory Paths ---
DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = PROJECT_ROOT / "log"
PROMPT_DIR = PROJECT_ROOT / "src" / "prompt"
OUTPUT_DIR = PROJECT_ROOT / "output" # central directory for all generated outputs

# --- Static Data File Paths ---
# These files are the initial inputs and are considered static throughout the process.
COURSES_FILE = DATA_DIR / "courses.json"
INSTRUCTORS_FILE = DATA_DIR / "instructors.json"
ROOMS_FILE = DATA_DIR / "rooms.json"
CONSTRAINTS_FILE = DATA_DIR / "constraints.json"
SEMESTERS_RULE_FILE = DATA_DIR / "curriculum.json"

# --- Prompt File Paths ---
GENERATOR_PROMPT_FILE = PROMPT_DIR / "generator_prompt" / "generator.txt"
FIXER_PROMPT_FILE = PROMPT_DIR / "fixer_prompt" / "fixer.txt"
OPTIMIZER_PROMPT_FILE = PROMPT_DIR / "optimizer_prompt" / "optimizer.txt"

# --- Data Preparation & Batching ---
# Settings for the initial data preparation script (phase_0_dataprep.txt)
BATCH_SIZE = 20
BATCH_COURSES_DIR_NAME = f"courses_batches_{BATCH_SIZE:02d}"
BATCH_INSTRUCTORS_DIR_NAME = f"instructors_batches_{BATCH_SIZE:02d}"
BATCH_COURSES_DIR = DATA_DIR / BATCH_COURSES_DIR_NAME
BATCH_INSTRUCTORS_DIR = DATA_DIR / BATCH_INSTRUCTORS_DIR_NAME

# --- Initial Check ---
if not GOOGLE_API_KEY:
    print("CRITICAL: GOOGLE_API_KEY is not set in the .env file. LLM calls will fail.")
else:
    print("INFO: GOOGLE_API_KEY is loaded successfully.")

# --- Helper to create a unique run directory ---
# The controller will use this to ensure each pipeline run saves to a new folder.
def get_run_output_dir(base_output_dir: Path, agent_name: str, run_tag: str) -> Path:
    
    # We no longer use a timestamp, relying on the user's tag for uniqueness.
    run_dir = base_output_dir / f"{agent_name}_{run_tag}"
    
    # Safety check: If the directory already exists, we append a timestamp to avoid data loss.
    if run_dir.exists():
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        original_run_dir = run_dir
        run_dir = base_output_dir / f"{agent_name}_{run_tag}_{timestamp}"
        print(f"WARNING: Directory '{original_run_dir}' already exists. Using new timestamped name to avoid overwrite: '{run_dir}'")

    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir
