# University Timetabling with Generative AI Agents (Automated Controller System)

This document provides a comprehensive guide for running the university timetabling system. It describes both the new automated controller for standard runs and the original manual step-by-step process for debugging and advanced use.

## Project Structure

The project is organized into a modular structure to separate concerns and improve maintainability. The system supports both a fully automated pipeline and a manual, step-by-step workflow for debugging.

```
university-timetabling-project/
├── data/                                   # All static input data (courses, instructors, curriculum, etc.)
├── log/                                    # Centralized logs, organized by agent and run.
├── output/                                 # All generated outputs (schedules, reports).
├── prompt/                                 # Prompt templates for the AI agents.
├── controller/                             # Orchestration logic for the automated pipeline.
│   ├── controller.py                       # Main entry point for the automated pipeline.
│   └── workflows/                          # Logic for each step called by the controller.
│       └── steps.py
├── src/                                    # All source code.
│   ├── agents/                             # Core AI agent logic (Generator, Fixer, Optimizer).
│   ├── hard_constraints/                   # Hard-constraint validation logic.
│   ├── soft_constraints/                   # Soft-constraint validation logic.
│   └── utils/                              # Shared utilities (config, file I/O, logging).
├── ORIGINAL_EXPERIMENTS_RESULT_GEMINI.zip  # Reference results from a pre-refactoring pipeline run.
├── run_0_dataprep.py                       # Phase 0: Data preparation
├── run_1_generator.py                      # Phase 1: Initial schedule generation
├── run_2_validator.py                      # Hard-constraint validation
├── run_3_fixer.py                          # Phase 2: Hard-constraint fixing
├── run_3_merger.py                        # Batch merging during Phase 2
├── run_4_cleaner_and_analyzer.py           # Phase 3: Final validation and analysis
├── run_5_optimizer_setup.py                # Optimization setup
├── run_6_sc_validator.py                   # Soft-constraint validation
├── run_7_optimizer.py                      # Phase 4: Soft-constraint optimization
├── .env                                    # Environment variables (e.g., API keys)
└── requirements.txt                        # Python dependencies
```
## Setup and Installation

### Prerequisites
*   Python 3.10 or higher.
*   A `GOOGLE_API_KEY` for using the Gemini models.

### Step 1: Set Up Python Environment
It is highly recommended to use a virtual environment to isolate project dependencies.

1.  **Open a terminal** (Command Prompt, PowerShell, or Terminal on macOS/Linux).
2.  **Navigate to the project's root directory.**
3.  **Create and activate a virtual environment:**
    *   On **Windows**:
        ```cmd
        python -m venv venv
        venv\Scripts\activate
        ```
    *   On **macOS and Linux**:
        ```bash
        python3 -m venv venv
        source venv/bin/activate
        ```

### Step 2: Install Dependencies
This project includes a `requirements.txt` file that lists all necessary packages.

1.  **Ensure your virtual environment is activated.**
2.  **Install the packages.** You can use either of the following options:

    **Option A: Using the `requirements.txt` file (Recommended)**
    ```bash
    pip install -r requirements.txt
    ```

    **Option B: Manual Installation**
    Alternatively, you can install the packages directly with pip:
    ```bash
    pip install google-generativeai python-dotenv notebook
    ```

### Step 3: Set Up Your API Key
1.  In the project's root directory, create a new file named `.env`.
2.  Add your Google API key to the file:
    ```
    GOOGLE_API_KEY="your_api_key_here"
    ```
    Replace `your_api_key_here` with your actual key.

## Execution Modes

This system offers two modes of operation: a fully automated pipeline for end-to-end runs and a manual, step-by-step workflow for detailed control and debugging.

---

### Method 1: Fully Automated Pipeline (Recommended)**

The controller orchestrates the entire process, from data preparation to final optimization, in a single command. It provides detailed logs and creates a traceable output structure.

#### **Configuration**

The system's configuration is split into two levels for ease of use and flexibility.

**1. Experiment Configuration (in `controller/controller.py`)**

For most runs, you will only need to edit the constants at the top of the main `controller.py` file. These parameters control the behavior of a specific automated pipeline run.

*   `MAX_FIXER_ITERATIONS_PER_LEVEL`: The maximum number of fix-validate attempts the controller will perform on a single set of batches before forcing a merge and moving to the next level. This acts as a safeguard to prevent infinite loops.
*   `MAX_OPTIMIZER_ITERATIONS`: The number of times the optimizer will run and be re-validated to progressively improve the soft constraint score.

**2. System-Level Configuration (in `src/utils/config.py`)**

For more fundamental changes to the system's core behavior, you can edit the central configuration file.

*   **File Location:** `src/utils/config.py`

Key settings you might want to change here include:

*   `BATCH_SIZE`: The number of courses to include in each batch during the initial data preparation. This has a significant impact on the entire workflow.
*   `GENERATOR_MODEL_NAME`, `FIXER_MODEL_NAME`, `OPTIMIZER_MODEL_NAME`: Allows you to specify different Gemini models (e.g., `gemini-1.5-pro` vs. `gemini-1.5-flash`) for each agent individually.
*   `MAX_RETRIES`, `RETRY_DELAY_SECONDS`: Controls the low-level API call retry mechanism for all agents.

*(Other settings like file paths are also located here but typically do not need to be changed.)*

---

#### **Running the Controller**
1.  **Open a terminal** in the project's root directory.
2.  **Run the command**, providing a unique tag for the entire pipeline run. This tag will be used to name the output folders for easy identification.

    ```bash
    python controller/controller.py <your_pipeline_run_tag>
    ```
    **Example:**
    ```bash
    python controller/controller.py exp01_automated_run
    ```

The controller will now execute all phases automatically and will print progress updates to the console. All outputs will be saved in the `/output` directory, and all logs will be saved in the `/log` directory, organized by agent and run tag.

---

### Method 2: Manual Step-by-Step Execution (Legacy Workflow)

This method reflects the original, manual workflow involving Jupyter Notebooks and direct script execution from the project root. It is preserved for detailed debugging and requires manually editing file paths inside each script before running.

#### **Recommended Output Naming Convention**

Adopt the following convention for all output directories to maintain traceability:
*   **`expXX`:** An Experiment Tag for an entire run (e.g., `exp01`).
*   **`L_`:** The Hard Constraint Fixing Level (e.g., `L1`).
*   **`runXX`:** The iteration number within a fixing level (e.g., `L1_run01`).

---

#### **Phase 0: Data Preparation**

1.  **Script:** `run_0_dataprep.py` (Python Script in root)
2.  **ACTION: Adjust the `BATCH_SIZE` as needed.**
3.  **Command:** `python run_0_dataprep.py`

---

#### **Phase 1: Initial Schedule Generation**

1.  **Script:** `run_1_generator.py` (Jupyter Notebook in root)
2.  **ACTION:** Open the notebook and edit the `OUTPUT_SCHEDULE_DIR` variable.
3.  **Command:** Run all cells in the Jupyter notebook.

---

#### **Phase 2: Hard Constraint Fixing (Iterative Loop)**

**Level 1, Run 1: First Validation**
1.  **Script:** `run_2_validator_on_generator.py` (in root)
2.  **ACTION:** Edit paths for `BASE_SCHEDULE_OUTPUT_DIR` (input) and `VALIDATION_OUTPUT_BASE_DIR` (output).
3.  **Command:** `python run_2_validator_on_generator.py`

**The Validate -> Fix Cycle**
1.  **Run the Fixer:** `run_3_fixer.py` (in root)
2.  **Validate the Fixer's Output:** `run_2a_validator_on_fixer.py` (in root)

**Repeat this cycle (Fixer -> Validator) until reports show zero violations.**

**Advancing Levels with the Merger**
1.  **Run the Merger:** `run_3a_merger.py` (in root)
2.  **Validate the Merged Batches:** `run_2b_validator_on_merge.py` (in root)

**After validating the merge, start the Validate -> Fix Cycle again on the new level (`L2_...`).** Repeat until you have one final, clean, consolidated schedule.

---

#### **Phase 3: Preparing for Optimization**

1.  **Run the Cleaner & Analyzer:** `run_4_cleaner_and_analyzer.py` (in root)
2.  **Run the Optimizer Input Setup:** `run_5_optimizer_setup.py` (in root)

---

#### **Phase 4: Soft Constraint Optimization**

1.  **Get a Baseline Score:** `run_6_sc_validator.py` (in root)
2.  **Run the Optimizer:** `run_7_optimizer.py` (in root)
3.  **Check the Final Score:** Run `run_6_sc_validator.py` again on the optimizer's output.

---

### **Explanation of `ORIGINAL_EXPERIMENTS_RESULT_GEMINI.zip`**

The `ORIGINAL_EXPERIMENTS_RESULT_GEMINI.zip` file contains the complete set of output artifacts from a single, successful end-to-end run of the pipeline.

**Important Context:**
*   These results were generated using the **legacy version of the code**, prior to the current refactoring. The core logic is the same, but the file structure and logging mechanisms are different.
*   Due to the legacy system's design, the location of log files is inconsistent. For the sake of data integrity, **these original experiment artifacts have not been tampered with or reorganized.** The new, refactored system correctly saves all logs to the central `/log` directory.

#### **Directory Structure and Purpose**

Here is a breakdown of each top-level folder found within the ZIP file:

*   **`generator_output/`**: Contains the initial schedule draft, run report, and logs (`log_generator/`) from the Generator agent.

*   **`hc_fixer/`**: Corresponds to `after_fixer/` in the legacy system. It stores the validated output from the Hard Constraint Validator after each step.

*   **`fixer_output/`**: The output of the Fixer agent. It contains the fixed schedules, run reports, fixer logs, and importantly, the output of the Merger agent (in folders with `MERGER` in the name).

*   **`soft_fixer_output/`**: Corresponds to `sc_fixing_output/` in the legacy system. It holds the prepared input for the optimization phase (in a folder ending in `run00`) and the final, optimized schedule from the Optimizer agent.

*   **`sc_fixer/`**: Corresponds to `sc_validator_output/` in the legacy system. It contains the soft constraint validation reports, including the baseline score and the final score after optimization.

python -m controller.controller experiment_01
