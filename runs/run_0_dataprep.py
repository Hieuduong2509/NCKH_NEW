from src.utils.config import COURSES_FILE, INSTRUCTORS_FILE
from src.utils.file_io import load_json_file
from src.processing.batcher import BatchProcessor

def main():
    print("--- Data Preparation ---")
    courses = load_json_file(COURSES_FILE)
    instructors = load_json_file(INSTRUCTORS_FILE)
    BatchProcessor.prepare_initial_batches(courses, instructors)
    print("--- Data Prep Complete ---")

if __name__ == "__main__":
    main()