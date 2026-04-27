# Agent 1: BOM Risk Analyzer

Analyzes a construction Bill of Materials (BOM) for supply chain risk, price volatility, and procurement lead times.

## Usage

```bash
python agent.py --bom sample_data/sample_bom.csv
```

## Sample Data

Place BOM files (CSV or JSON) in `sample_data/`.

Expected CSV columns: `item`, `quantity`, `unit`, `supplier`, `lead_time_days`, `unit_cost`

## How It Works

1. Loads a BOM from a file or structured input
2. Sends each line item to Claude for risk analysis
3. Returns a risk-scored report with recommendations
