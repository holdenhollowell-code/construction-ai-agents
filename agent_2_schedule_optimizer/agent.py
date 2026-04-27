import argparse
import json
import anthropic

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """You are a construction project scheduler with expertise in critical path method (CPM) and resource leveling.
Given a project schedule as a list of tasks, analyze it and return a JSON object with:
- critical_path: list of task IDs on the critical path
- resource_conflicts: list of conflicts (task IDs + description)
- optimizations: list of suggested changes (task, suggestion, estimated_days_saved)
- overall_risk: low/medium/high with a brief rationale
"""


def load_schedule(filepath: str) -> list[dict]:
    with open(filepath, encoding="utf-8") as f:
        return json.load(f)


def optimize_schedule(tasks: list[dict]) -> dict:
    client = anthropic.Anthropic()

    user_message = f"Analyze and optimize the following construction schedule:\n\n{json.dumps(tasks, indent=2)}"

    message = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    raw = message.content[0].text
    return json.loads(raw)


def print_report(result: dict) -> None:
    print("\n=== Schedule Optimization Report ===\n")

    cp = result.get("critical_path", [])
    print(f"Critical Path: {' -> '.join(str(t) for t in cp)}\n")

    conflicts = result.get("resource_conflicts", [])
    if conflicts:
        print("Resource Conflicts:")
        for c in conflicts:
            print(f"  - {c}")
    else:
        print("No resource conflicts detected.")

    print("\nOptimization Suggestions:")
    for opt in result.get("optimizations", []):
        days = opt.get("estimated_days_saved", 0)
        print(f"  [{days}d saved] {opt.get('task')}: {opt.get('suggestion')}")

    risk = result.get("overall_risk", {})
    print(f"\nOverall Risk: {risk}")


def main():
    parser = argparse.ArgumentParser(description="Construction Schedule Optimizer")
    parser.add_argument("--schedule", required=True, help="Path to schedule JSON file")
    args = parser.parse_args()

    tasks = load_schedule(args.schedule)
    print(f"Loaded {len(tasks)} tasks from {args.schedule}")

    result = optimize_schedule(tasks)
    print_report(result)


if __name__ == "__main__":
    main()
