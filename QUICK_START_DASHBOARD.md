# Dashboard Status Filter - Quick Reference

## What's New?

Your Dashboard now has **status-based filtering** that allows you to:
- View all rows for a selected status
- Quickly identify failed articles or pending items
- Monitor progress by status
- Analyze success patterns

## Files Modified/Created

### Modified Files
- ✅ `core/sheets_manager.py` - Added 5 new methods
- ✅ `requirements.txt` - Added `tabulate` dependency

### New Files
- ✅ `scripts/dashboard_filter.py` - Interactive filtering script
- ✅ `tests/test_dashboard_filter.py` - Unit tests
- ✅ `docs/11_DashboardStatusFilter.md` - Full documentation
- ✅ `QUICK_START_DASHBOARD.md` - This file

## 30-Second Setup

```bash
# Install dependencies (if needed)
pip install -r requirements.txt

# View status summary
python scripts/dashboard_filter.py

# Show all successful articles
python scripts/dashboard_filter.py --status "Success"

# Interactive mode
python scripts/dashboard_filter.py --interactive
```

## New Methods in SheetsManager

```python
# Get a dict of all statuses and their counts
summary = sheets.get_status_summary()

# Fetch rows with a specific status
rows = sheets.get_rows_by_status("Success")

# Display rows AND update Dashboard sheet
rows = sheets.display_rows_by_status("Failed")

# Update Dashboard with filtered results
sheets.update_dashboard_filtered_results("Pending")
```

## Dashboard Sheet Updates

Your Dashboard sheet now has:

**Left side (A-B):** Statistics (unchanged)
```
Metric                    | Count
Success                   | auto-updated
Failed                    | auto-updated
Skipped - Duplicate       | auto-updated
Total Runs                | auto-updated
Success Rate (%)          | formula
Total Published           | formula
```

**Right side (D-J):** NEW - Status Filter & Results
```
Column D-E: Status Filter Control
  Select Status to View: [description]
  Status Filter: [SUCCESS/FAILED/PENDING/etc]

Column D-J: Filtered Results (auto-populated)
  Topic | Keyword | Category | Status | Blog URL | Post ID | Error Log
  [All rows with selected status]
```

## Common Tasks

### Check Failed Articles
```bash
python scripts/dashboard_filter.py --status "Failed"
```
View error details in the "Error Log" column

### Monitor Pending Items
```bash
python scripts/dashboard_filter.py --status "Pending"
```
Tracks what's waiting to be processed

### View Success Rate
```bash
python scripts/dashboard_filter.py
```
Shows success count vs total runs

### Find Duplicate Skips
```bash
python scripts/dashboard_filter.py --status "Skipped - Duplicate Topic"
```
Identify topics that were skipped as duplicates

## Feature Highlights

| Feature | Benefit |
|---------|---------|
| **Status Summary** | Quick overview of all statuses at a glance |
| **Row Filtering** | Find all articles with specific status instantly |
| **Error Analysis** | Review error logs for all failed items together |
| **Progress Tracking** | Monitor pending vs completed work |
| **Google Sheets Integration** | Results update automatically in your Dashboard tab |
| **Command Line & Python** | Use via script or in code |

## Data Flow

```
Main Sheet (with all topics)
        ↓
    Filter by Status (e.g., "Success")
        ↓
    Matching Rows Retrieved
        ↓
    Dashboard Sheet Updated (Columns D-J)
        ↓
    View in Google Sheets
```

## Example Output

```
============================================================
Dashboard Status Summary
============================================================
╒════════════════════════╤═════════╕
│ Status                 │ Count   │
╞════════════════════════╪═════════╡
│ Failed                 │ 3       │
│ Pending                │ 15      │
│ Skipped - Duplicate    │ 42      │
│ Success                │ 128     │
╘════════════════════════╧═════════╛

$ python scripts/dashboard_filter.py --status "Failed"

Fetching all rows with status: 'Failed'...

════════════════════════════════════════════════════════════════════════
Filtered Results: Failed (3 rows)
════════════════════════════════════════════════════════════════════════

Topic          │ Keyword      │ Category │ Status │ Blog URL │ Post ID │ Error Log
───────────────┼──────────────┼──────────┼────────┼──────────┼─────────┼──────────────────────
Best Running   │ Running Gear │ Sports   │ Failed │          │         │ Image upload failed
Coffee Review  │ Coffee Maker │ Kitchen  │ Failed │          │         │ Content too short
Bike Guide     │ Mountain Bike│ Sports   │ Failed │          │         │ API timeout error

✓ Dashboard sheet updated with 3 rows for status: 'Failed'
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "No rows found" | Status doesn't exist in sheet yet |
| Permission denied | Check GCP_SERVICE_ACCOUNT credentials |
| Module not found (tabulate) | Run: `pip install -r requirements.txt` |
| Script not found | Ensure you're in `/workspaces/Aff_mark_scrapeDoAPI_Antigravity` |

## Full Documentation

For detailed usage, examples, and advanced features, see:
📖 [Full Dashboard Status Filter Guide](docs/11_DashboardStatusFilter.md)

## Questions or Issues?

- Check the logs: `tail -f logs/app.log`
- Run tests: `python -m pytest tests/test_dashboard_filter.py -v`
- Review code: `core/sheets_manager.py` (new methods start at line ~271)

---

**Happy filtering! 📊**
