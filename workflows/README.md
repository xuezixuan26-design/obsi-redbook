# Workflows

This directory contains workflow adapters that sit above the deterministic importer and analysis scripts.

## DeerFlow Adapter

- `deerflow_adapter.py` reads the structured action plan emitted by `scripts/analyze_notes.py`
- it transforms that plan into a DeerFlow-friendly workflow payload
- it can also render a human-readable task brief for review before plugging the payload into a live DeerFlow runtime
- `run_deerflow_stub.py` simulates a local multi-agent run over that payload so you can inspect task grouping and outputs before integrating a real DeerFlow runtime
- `run_deerflow_runtime.py` materializes one request bundle per task and can optionally execute an external DeerFlow command template when you are ready to wire in a real runtime
- `apply_deerflow_results.py` takes stub or runtime execution results and writes structured enrichment records plus enhanced note copies for review

The adapter does not depend on DeerFlow itself. It defines the contract first so the repository stays useful even before DeerFlow is wired in.
