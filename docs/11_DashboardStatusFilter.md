# Dashboard Status Filter Guide

## Overview

The Dashboard has been enhanced with status-based row filtering functionality. When you select a status, the Dashboard sheet automatically displays all corresponding rows from your main sheet, allowing you to:

- ✅ View all rows with a specific status
- ✅ Quickly identify issues by filtering failed items
- ✅ Monitor pending items and track progress
- ✅ Analyze success rates by examining successful topics

## Dashboard Sheet Layout

The Dashboard sheet is organized into two main sections:

### Section 1: Statistics (Columns A-B)
```
Metric                        | Count
------------------------------|-------
Success                       | [auto-updated]
Failed                        | [auto-updated]
Skipped - Duplicate Topic     | [auto-updated]
Total Runs                    | [auto-updated]
                              |
Live Success Rate (%)         | [formula]
Total Published Articles      | [formula]
```

### Section 2: Status Filter & Results (Columns D-J)
```
D                          | E
Select Status to View:     |
Status Filter:             | [CURRENT STATUS]
                          |
Filtered Results for:      |
Topic | Keyword | Category | Status | Blog URL | Post ID | Error Log
[Rows matching selected status appear here...]
```

## How to Use

### Option 1: Command Line Script (Recommended)

**Install dependencies** (if not already installed):
```bash
pip install -r requirements.txt
```

**Show status summary:**
```bash
python scripts/dashboard_filter.py
```

Output:
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
```

**Filter by specific status:**
```bash
# View all successful articles
python scripts/dashboard_filter.py --status "Success"

# View all failed articles
python scripts/dashboard_filter.py --status "Failed"

# View all pending articles
python scripts/dashboard_filter.py --status "Pending"
```

**List all available statuses:**
```bash
python scripts/dashboard_filter.py --list
```

**Interactive mode:**
```bash
python scripts/dashboard_filter.py --interactive
```
This will:
1. Show all statuses and their counts
2. Prompt you to select one by number
3. Display and update the Dashboard with filtered results

### Option 2: Direct Python Usage

```python
from config import settings
from core.sheets_manager import SheetsManager

# Initialize
sheets = SheetsManager(settings.GOOGLE_SHEET_ID, settings.GCP_SERVICE_ACCOUNT)

# Get status summary
summary = sheets.get_status_summary()
print(summary)
# Output: {'Success': 128, 'Failed': 3, 'Pending': 15, 'Skipped - Duplicate Topic': 42}

# Display rows for a specific status
rows = sheets.display_rows_by_status("Success")
for row in rows:
    print(row)

# Or just fetch rows without updating dashboard
rows = sheets.get_rows_by_status("Failed")
```

### Option 3: Automatic Updates During Pipeline Execution

The Dashboard filter is automatically initialized when `update_dashboard_stats()` is first called (usually during the first run of the main pipeline).

## Practical Examples

### Example 1: Monitor Failed Articles
```bash
$ python scripts/dashboard_filter.py --status "Failed"

Fetching all rows with status: 'Failed'...

════════════════════════════════════════════════════════════════════════
Filtered Results: Failed (3 rows)
════════════════════════════════════════════════════════════════════════

Topic          | Keyword      | Category | Status | Blog URL | Post ID | Error Log
───────────────|──────────────|──────────|────────|──────────|─────────|─────────────────────
Best Running   | Running Gear | Sports   | Failed |          |         | Image upload failed
Coffee Review  | Coffee Maker | Kitchen  | Failed |          |         | Content too short
Bike Guide     | Mountain Bike| Sports   | Failed |          |         | API timeout error

✓ Dashboard sheet updated with 3 rows for status: 'Failed'
  You can view these results in the Dashboard sheet in Google Sheets.
```

### Example 2: Review Pending Items
```bash
$ python scripts/dashboard_filter.py --status "Pending"

Fetching all rows with status: 'Pending'...

════════════════════════════════════════════════════════════════════════
Filtered Results: Pending (15 rows)
════════════════════════════════════════════════════════════════════════

Topic          | Keyword      | Category | Status  | Blog URL | Post ID | Error Log
───────────────|──────────────|──────────|─────────|──────────|─────────|───────────
Smart TV Guide | Smart TV     | Tech     | Pending |          |         |
Vacuum Review  | Robot Vacuum | Home     | Pending |          |         |
Gaming Mouse   | Gaming Gear  | Tech     | Pending |          |         |
... (12 more rows)
```

### Example 3: Check Duplicates That Were Skipped
```bash
$ python scripts/dashboard_filter.py --status "Skipped - Duplicate Topic"
```

## How It Works Behind the Scenes

1. **Data Retrieval**: Script reads all rows from the main sheet
2. **Status Filtering**: Rows are filtered by the selected status
3. **Dashboard Update**: 
   - Sets the filter indicator (column E3) to the selected status
   - Clears previous results (up to 100 rows)
   - Writes new filtered rows starting at D6
4. **Google Sheets Display**: Results are immediately visible in the Dashboard sheet

## Status Types

By default, the following statuses are used:

| Status | Meaning |
|--------|---------|
| **Pending** | Waiting to be processed |
| **Success** | Article published successfully |
| **Failed** | Processing failed - check Error Log |
| **Skipped - Duplicate Topic** | Topic already processed, skipped to avoid duplicates |

Additional custom statuses may exist depending on your workflow modifications.

## Tips & Best Practices

1. **Regular Monitoring**: Run the script periodically to identify and address failed articles
2. **Error Resolution**: Use the Error Log column to understand why articles failed
3. **Progress Tracking**: Use the Success and Pending counts to monitor pipeline progress
4. **Batch Processing**: Script updates display all rows at once, making it easy to find patterns in failures

## Troubleshooting

### No rows displayed for a status?
- ✓ That status may not exist in your sheet yet
- ✓ All rows with that status may have been archived/deleted
- ✓ Use `--list` option to see available statuses

### Permission denied errors?
- ✓ Ensure your GCP_SERVICE_ACCOUNT credentials are valid
- ✓ Check that the service account has write access to the Google Sheet

### Script not finding statuses?
- ✓ Ensure your main sheet has a "Status" column
- ✓ Check the column naming and spelling

## Integration with Automation

You can automate dashboard updates by adding the script to a scheduled task:

**Cron job** (runs every hour):
```bash
0 * * * * cd /workspaces/Aff_mark_scrapeDoAPI_Antigravity && python scripts/dashboard_filter.py --status "Failed" >> dashboard_checks.log 2>&1
```

**Or use GitHub Actions** (optional - add to your workflow):
```yaml
- name: Update Dashboard
  run: python scripts/dashboard_filter.py --status "Success"
```

## Future Enhancements

Potential improvements:
- [ ] Direct pie chart click integration in Google Sheets (requires Google Apps Script)
- [ ] Scheduled automatic updates
- [ ] Email alerts for failed items
- [ ] Dashboard history/trends visualization
- [ ] Multi-status filtering (show "Success" AND "Failed" together)
