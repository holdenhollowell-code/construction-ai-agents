# Agent 2: Schedule Optimizer

Analyzes a construction project schedule and suggests optimizations using critical path analysis, resource leveling, and constraint reasoning.

## Usage

```bash
python agent.py --schedule sample_data/sample_schedule.json
```

## Sample Data

Place schedule files (JSON or CSV) in `sample_data/`.

Expected JSON format: a list of tasks with `id`, `name`, `duration_days`, `dependencies`, and `resources`.

## How It Works

1. Loads a project schedule
2. Identifies the critical path and resource conflicts
3. Uses Claude to suggest sequencing improvements and flag risks
