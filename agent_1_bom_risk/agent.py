# =============================================================================
# Agent 1: BOM Risk Detector
# Construction Project Management Portfolio
#
# This script reads a Bill of Materials (BOM) CSV file for a construction
# project, sends it to Claude (an AI model), and asks Claude to identify
# any materials or contractors that could halt the project within the next
# 20 days. The results are printed as a clean risk report in the terminal.
# =============================================================================

import json
import re
import sys
from datetime import date

import anthropic
import pandas as pd
from dotenv import load_dotenv

# =============================================================================
# CONFIGURATION
# =============================================================================

# The Claude model we want to use for analysis
MODEL = "claude-sonnet-4-6"

# How many days ahead to look for risks
RISK_WINDOW_DAYS = 20

# Default path to the BOM CSV file
DEFAULT_BOM_PATH = "sample_data/bom_data.csv"

# =============================================================================
# STEP 1: LOAD ENVIRONMENT VARIABLES
# Load the Anthropic API key from the .env file so it never has to be
# hard-coded into the script. python-dotenv reads the .env file and makes
# the key available as an environment variable.
# =============================================================================

load_dotenv()

# anthropic.Anthropic() automatically reads ANTHROPIC_API_KEY from env
client = anthropic.Anthropic()


# =============================================================================
# STEP 2: LOAD THE BOM CSV
# pandas reads the CSV into a DataFrame (a table-like structure), then we
# convert it to a list of plain dictionaries so it can be serialized to JSON
# and sent to Claude.
# =============================================================================

def load_bom(filepath: str) -> list[dict]:
    """Load BOM data from a CSV file and return it as a list of row dicts."""
    try:
        df = pd.read_csv(filepath)
    except FileNotFoundError:
        print(f"ERROR: Could not find BOM file at '{filepath}'")
        sys.exit(1)

    # Convert every cell to a string so JSON serialization doesn't choke on
    # NaN or mixed numeric/string columns
    df = df.fillna("").astype(str)

    print(f"Loaded {len(df)} BOM items from '{filepath}'")
    return df.to_dict(orient="records")


# =============================================================================
# STEP 3: BUILD THE SYSTEM PROMPT
# The system prompt tells Claude exactly what role to play and what format
# to return results in. Being specific here produces consistent, parseable
# output. We inject today's date so Claude can reason about which items
# fall within the 20-day risk window.
# =============================================================================

def build_system_prompt(today: str, risk_window: int) -> str:
    return f"""You are a senior construction project risk analyst reviewing a project Bill of Materials (BOM).

Today's date is {today}. Your job is to identify any materials or contractors
that could cause a project halt or major delay within the next {risk_window} days
(i.e., by {today} + {risk_window} days).

When evaluating each row, consider:
- Items with status "delayed" or "not started" that have upcoming scheduled dates
- Items where lead_time_days is long enough that the order is already late or at risk
- Contractors who are not confirmed or are understaffed for imminent start dates
- Dependencies: if a material is delayed, does that block a contractor from starting?

Return ONLY a valid JSON object with this exact structure (no markdown, no explanation):
{{
  "analysis_date": "{today}",
  "risk_window_days": {risk_window},
  "overall_project_risk": "high | medium | low",
  "overall_summary": "One to two sentence plain-English summary of the biggest risks.",
  "at_risk_items": [
    {{
      "item_id": "the item_id from the CSV",
      "item_name": "the item_name from the CSV",
      "category": "material | contractor",
      "risk_level": "high | medium | low",
      "days_until_scheduled": <integer, days from today to scheduled_date>,
      "reason": "Clear explanation of why this item is at risk.",
      "downstream_impact": "What gets blocked or delayed if this item fails.",
      "recommended_action": "Specific, actionable step the project manager should take immediately."
    }}
  ]
}}

Only include items that are genuinely at risk. Items that are confirmed and on
track with sufficient lead time do not need to be listed.
"""


# =============================================================================
# STEP 4: CALL CLAUDE
# We send the BOM data as a user message along with the system prompt above.
# Claude returns a JSON string which we then parse in the next step.
# =============================================================================

def analyze_bom(bom_items: list[dict], today: str) -> dict:
    """Send BOM data to Claude and return the parsed risk analysis dict."""

    # Serialize the BOM rows into a readable JSON string for the prompt
    bom_json = json.dumps(bom_items, indent=2)

    user_message = (
        f"Here is the current Bill of Materials for the project. "
        f"Please analyze it for risks within the next {RISK_WINDOW_DAYS} days.\n\n"
        f"{bom_json}"
    )

    print(f"\nSending {len(bom_items)} BOM items to Claude for risk analysis...")

    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=build_system_prompt(today, RISK_WINDOW_DAYS),
        messages=[{"role": "user", "content": user_message}],
    )

    raw_text = response.content[0].text

    # Claude sometimes wraps JSON in markdown fences (```json ... ```) even
    # when instructed not to. This strips those fences if present.
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw_text.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"\nERROR: Claude returned output that could not be parsed as JSON.\n")
        print("Raw response:\n", raw_text)
        sys.exit(1)


# =============================================================================
# STEP 5: PRINT THE RISK REPORT
# We take the parsed JSON from Claude and format it into a readable terminal
# report. Risk levels are visually distinguished using text labels so the
# report is easy to scan quickly.
# =============================================================================

# Maps risk level strings to a simple visual label for the terminal
RISK_LABELS = {
    "high":   "!! HIGH RISK",
    "medium": ">> MEDIUM RISK",
    "low":    "-- LOW RISK",
}


def print_report(analysis: dict) -> None:
    """Print a formatted risk report to the terminal."""

    overall_risk = analysis.get("overall_project_risk", "unknown").upper()
    summary = analysis.get("overall_summary", "")
    at_risk = analysis.get("at_risk_items", [])
    analysis_date = analysis.get("analysis_date", "")
    window = analysis.get("risk_window_days", RISK_WINDOW_DAYS)

    # ---- Header ----
    print("\n" + "=" * 65)
    print("  CONSTRUCTION PROJECT — BOM RISK REPORT")
    print(f"  Analysis Date : {analysis_date}")
    print(f"  Risk Window   : Next {window} days")
    print(f"  Overall Risk  : {overall_risk}")
    print("=" * 65)
    print(f"\n{summary}\n")

    if not at_risk:
        print("No at-risk items identified within the risk window.")
        return

    # ---- Sort items so HIGH risks appear first ----
    order = {"high": 0, "medium": 1, "low": 2}
    at_risk.sort(key=lambda x: order.get(x.get("risk_level", "low"), 3))

    print(f"AT-RISK ITEMS ({len(at_risk)} found):")
    print("-" * 65)

    for item in at_risk:
        level = item.get("risk_level", "unknown").lower()
        label = RISK_LABELS.get(level, f"[{level.upper()}]")
        days = item.get("days_until_scheduled", "?")

        print(f"\n{label}")
        print(f"  Item     : [{item.get('item_id')}] {item.get('item_name')}  ({item.get('category', '')})")
        print(f"  Scheduled: {days} days from today")
        print(f"  Reason   : {item.get('reason')}")
        print(f"  Impact   : {item.get('downstream_impact')}")
        print(f"  Action   : {item.get('recommended_action')}")
        print("-" * 65)

    print()


# =============================================================================
# MAIN — ties everything together
# =============================================================================

def main():
    today = date.today().isoformat()   # e.g. "2026-04-27"

    # Load the BOM CSV into a list of row dictionaries
    bom_items = load_bom(DEFAULT_BOM_PATH)

    # Send the data to Claude and get back the structured risk analysis
    analysis = analyze_bom(bom_items, today)

    # Print the formatted report to the terminal
    print_report(analysis)


if __name__ == "__main__":
    main()
