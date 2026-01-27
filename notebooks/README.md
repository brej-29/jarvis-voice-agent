# Intent EDA and Baseline Notebook

This folder contains notebooks and utilities to explore **intent classification**
for the Jarvis Voice Agent, focusing on the types of commands we expect from
a voice-first assistant (weather queries, reminders, notes, general Q&amp;A).

## Files

- `intent_eda_and_baseline.ipynb`
  - Main notebook with:
    - Problem framing and context.
    - Dataset inspection and EDA.
    - Baseline model (TF-IDF + linear classifier).
    - Metrics and feature importance.
    - Error analysis and design decisions for production NLU.

- `../data/sample_intents.csv`
  - Small offline dataset with a few example utterances and intents.
  - Used as a fallback when the full dataset is not available.

- `../scripts/download_intent_dataset.py`
  - Optional script that downloads the **DeepPavlov/clinc_oos** dataset from
    Hugging Face Datasets and writes it to `data/clinc_oos_intents.csv`.

- `../requirements-notebook.txt`
  - Extra dependencies required for running the notebook.
  - Kept separate from backend runtime dependencies to avoid bloating the
    production container.

## How to Run

1. Create and activate a virtual environment (recommended):

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. Install notebook-specific dependencies:

   ```bash
   pip install -r requirements-notebook.txt
   ```

3. (Optional) Download the full CLINC OOS intent dataset:

   ```bash
   python scripts/download_intent_dataset.py
   ```

   If this step fails (e.g., no internet or no HF access), the notebook will
   still run using `data/sample_intents.csv`.

4. Launch Jupyter and open the notebook:

   ```bash
   jupyter notebook notebooks/intent_eda_and_baseline.ipynb
   ```

## Dataset Fallback Logic

Inside the notebook:

- First, it will try to load `data/clinc_oos_intents.csv` if present.
- If not found, it will fall back to `data/sample_intents.csv`.
- This ensures the notebook is **self-contained and runnable offline**.

## Goals

The notebook is meant to:

- Ground future NLU/intent classification work in actual data.
- Provide a clear explanation of:
  - Which metrics we care about (accuracy, macro F1, confusion matrix).
  - What a reasonable baseline looks like (TF-IDF + linear model).
  - How feature importance can guide UX and data collection.
- Document decisions that can feed back into:
  - Tool routing.
  - Prompt design.
  - Future on-device NLU models.