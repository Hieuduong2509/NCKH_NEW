import json
import os
import datetime
from pathlib import Path

from .config import LOG_DIR

class DetailedLogger:
    """
    A centralized logger that saves logs to a structured directory.
    - Creates a main run log and a separate log for raw LLM responses.
    - Creates a separate log for LLM thought summaries. (CORRECTED)
    - Organizes logs into subdirectories for each agent (generator, fixer, optimizer).
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        # This makes the logger a Singleton, ensuring we only have one instance
        # throughout the application, so all logs go to the same files.
        if not cls._instance:
            cls._instance = super(DetailedLogger, cls).__new__(cls)
        return cls._instance

    def __init__(self, agent_name: str, run_name: str):
        # Check if the logger has already been initialized for this run
        if hasattr(self, 'log_dir') and self.run_name == run_name:
            return

        self.agent_name = agent_name
        self.run_name = run_name
        
        # Create a structured log directory: log/{agent_name}/{run_name}/
        self.log_dir = LOG_DIR / agent_name / run_name
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Define file paths for the logs within the structured directory
        self.log_file_main = self.log_dir / "run_main.log"
        self.log_file_llm_responses = self.log_dir / "llm_raw_responses.log"
        self.log_file_llm_thoughts = self.log_dir / "llm_thoughts.log"
        
        # Announce initialization once
        print(f"Logger initialized for '{agent_name}'. Logs will be saved in: {self.log_dir}")


    def log(self, message_type: str, data: dict):
        """
        Logs a message to the console and the appropriate log file.
        
        Args:
            message_type (str): The category of the log (e.g., "INFO", "ERROR", "LLM_OUTPUT").
            data (dict): The data to be logged. Must contain a 'summary' key for console output.
        """
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "type": message_type,
            "data": data
        }
        
        # Always print a summary to the console for real-time feedback.
        summary = data.get('summary', str(data))
        print(f"LOG [{self.agent_name.upper()}|{message_type}]: {summary}")

        # Route log content to the correct file based on its type.
        if message_type == "LLM_RAW_OUTPUT_TEXT":
            self._write_to_file(self.log_file_llm_responses, self._format_llm_log(data, "RAW RESPONSE"))
        elif message_type == "LLM_THOUGHT_SUMMARY":
            self._write_to_file(self.log_file_llm_thoughts, self._format_llm_log(data, "THOUGHT SUMMARY"))
        else:
            # All other logs go to the main log file as structured JSON.
            with open(self.log_file_main, "a", encoding='utf-8') as f:
                f.write(json.dumps(log_entry, indent=2) + "\n---\n")

    def _format_llm_log(self, data: dict, log_type: str) -> str:
        """Helper to format LLM-specific log entries for readability."""
        timestamp = datetime.datetime.now().isoformat()
        header = f"--- {log_type} | Batch: {data.get('batch_id', 'N/A')} | Course: {data.get('course_id', 'N/A')} @ {timestamp} ---\n"
        content = data.get("raw_response_str") or data.get("thought_summary", "No content.")
        footer = f"\n--- END {log_type} ---\n\n"
        return header + content + footer

    def _write_to_file(self, filepath: Path, content: str):
        """Appends content to a specified file."""
        try:
            with open(filepath, "a", encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            print(f"CRITICAL: Failed to write to log file {filepath}: {e}")