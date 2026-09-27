"""DraftAgent evaluation harness.

Deterministic assertions (assertions.py) run offline and are unit-tested in CI.
The LLM-judge (judge.py, gpt-4o) scores faithfulness/relevance/tone and is run on
demand by run_eval.py. The dataset (dataset.py) is a curated set of threads with
expected-behavior annotations.
"""
