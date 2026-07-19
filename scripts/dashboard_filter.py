#!/usr/bin/env python3
"""
Dashboard Filter Utility

This script provides an interactive way to:
1. View a summary of all statuses and their counts
2. Filter and display all rows for a specific status in the Dashboard sheet
3. Update the Dashboard with filtered results

Usage:
    python scripts/dashboard_filter.py                 # Show status summary
    python scripts/dashboard_filter.py --status "Success"  # Show all Success rows
    python scripts/dashboard_filter.py --list          # List available statuses
    python scripts/dashboard_filter.py --interactive   # Interactive mode
"""

import sys
import argparse
from config.logger import get_logger
from config import settings
from core.sheets_manager import SheetsManager
from tabulate import tabulate

logger = get_logger("dashboard_filter")


def main():
    parser = argparse.ArgumentParser(
        description="Dashboard Filter Utility - View rows by status",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/dashboard_filter.py                    # Show status summary
  python scripts/dashboard_filter.py --status Success   # Filter by Success status
  python scripts/dashboard_filter.py --interactive      # Interactive mode
        """
    )
    
    parser.add_argument(
        "--status",
        type=str,
        help="Filter and display rows by status (e.g., 'Success', 'Failed', 'Pending')"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available statuses"
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Interactive mode - select status from available options"
    )
    
    args = parser.parse_args()
    
    # Initialize sheets manager
    try:
        sheets = SheetsManager(settings.GOOGLE_SHEET_ID, settings.GCP_SERVICE_ACCOUNT)
    except Exception as e:
        logger.error(f"Failed to initialize SheetsManager: {e}")
        sys.exit(1)
    
    # Get status summary
    status_summary = sheets.get_status_summary()
    
    if not status_summary:
        logger.warning("No status data found in the sheet.")
        sys.exit(0)
    
    # Show status summary
    print("\n" + "="*60)
    print("Dashboard Status Summary")
    print("="*60)
    
    summary_table = [[status, count] for status, count in sorted(status_summary.items())]
    print(tabulate(summary_table, headers=["Status", "Count"], tablefmt="grid"))
    print()
    
    # Handle different modes
    if args.interactive:
        print("Available statuses:")
        statuses = list(status_summary.keys())
        for idx, status in enumerate(statuses, 1):
            print(f"  {idx}. {status} ({status_summary[status]} rows)")
        
        try:
            choice = input("\nEnter status number to view (or press Enter to skip): ").strip()
            if choice and choice.isdigit():
                status_idx = int(choice) - 1
                if 0 <= status_idx < len(statuses):
                    selected_status = statuses[status_idx]
                    display_filtered_results(sheets, selected_status)
        except KeyboardInterrupt:
            print("\nCancelled.")
            sys.exit(0)
    
    elif args.list:
        print("Available statuses:")
        for status in sorted(status_summary.keys()):
            print(f"  • {status}: {status_summary[status]} rows")
    
    elif args.status:
        if args.status in status_summary:
            display_filtered_results(sheets, args.status)
        else:
            logger.error(f"Status '{args.status}' not found.")
            logger.info(f"Available statuses: {', '.join(sorted(status_summary.keys()))}")
            sys.exit(1)


def display_filtered_results(sheets, status):
    """Display filtered results for a given status."""
    print(f"\nFetching all rows with status: '{status}'...")
    matching_rows = sheets.display_rows_by_status(status)
    
    if not matching_rows or len(matching_rows) <= 1:
        logger.warning(f"No rows found with status: {status}")
        return
    
    # Display as table
    headers = matching_rows[0]
    rows = matching_rows[1:]
    
    print(f"\n{'='*120}")
    print(f"Filtered Results: {status} ({len(rows)} rows)")
    print(f"{'='*120}\n")
    
    print(tabulate(rows, headers=headers, tablefmt="grid", maxcolwidths=20))
    
    print(f"\n✓ Dashboard sheet updated with {len(rows)} rows for status: '{status}'")
    print("  You can view these results in the Dashboard sheet in Google Sheets.")


if __name__ == "__main__":
    main()
