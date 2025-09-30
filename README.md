
# VMC Predictive Maintenance Assistant (Streamlit)

This is a self-contained app for VMC operations:
- Before/After shift checklists
- Production logging
- Troubleshooting assistant (multi-issue) with 25+ VMC problems
- Tool life tracking + end-of-life alerts
- Basic RUL (Remaining Useful Life) estimate for tools & spindle
- Handover markdown report download

## 1) Setup

```bash
pip install -r requirements.txt
```

## 2) Run

```bash
streamlit run app.py
```

Then open the local URL shown in the terminal.

## 3) Data

The app stores CSV files under `./data/`:
- `checklists.csv`
- `production.csv`
- `tools.csv`
- `diagnostics.csv`
- `handover.csv`

All files are UTF-8 encoded.

## 4) Notes

- This app does not require any sensors. Operators input observations and parameters manually.
- The troubleshooting bot processes multiple problems separated by comma and logs each diagnosis.
- You can export a markdown handover report from the "Logbook / Export" tab and print to PDF if needed.
