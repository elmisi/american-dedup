#!/usr/bin/env python3
"""
Automated screenshot generator for american-dedup documentation.

Uses Textual's pilot mode to navigate through the app and capture screenshots.
Run this script after UI changes to update documentation images.

Usage:
    python scripts/take_screenshots.py

Output:
    screenshots/*.svg - Vector screenshots (can be converted to PNG)
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from textual.pilot import Pilot

from american_dedup.app import AmericanDedupApp


SCREENSHOTS_DIR = Path(__file__).parent.parent / "screenshots"


async def take_screenshots():
    """Navigate through the app and take screenshots of each screen."""

    SCREENSHOTS_DIR.mkdir(exist_ok=True)

    # Create app instance
    app = AmericanDedupApp(start_path="/home")

    async with app.run_test(size=(120, 35)) as pilot:
        # Wait for app to load
        await pilot.pause()

        # Screenshot 1: Main selection screen (empty)
        app.save_screenshot(str(SCREENSHOTS_DIR / "01_main_screen.svg"))
        print("✓ 01_main_screen.svg")

        # Click "Add" button to open folder picker
        await pilot.click("#add-scan")
        await pilot.pause()

        # Screenshot 2: Folder picker modal
        app.save_screenshot(str(SCREENSHOTS_DIR / "02_folder_picker.svg"))
        print("✓ 02_folder_picker.svg")

        # Cancel the modal
        await pilot.click("#cancel")
        await pilot.pause()

        # For the remaining screenshots, we need to simulate having folders
        # We'll add some demo data directly to show the UI states

        # Add demo folders to the app state
        main_screen = app.screen
        if hasattr(main_screen, 'scan_folders'):
            main_screen.scan_folders = [
                "/home/user/Pictures",
                "/home/user/Downloads",
                "/media/backup/Photos",
            ]
            main_screen.target_folders = {"/home/user/Downloads"}
            main_screen._refresh_lists()
            await pilot.pause()

            # Screenshot 3: Main screen with folders selected
            app.save_screenshot(str(SCREENSHOTS_DIR / "03_folders_selected.svg"))
            print("✓ 03_folders_selected.svg")

        print(f"\nScreenshots saved to: {SCREENSHOTS_DIR}")


def main():
    """Entry point."""
    print("Generating screenshots for american-dedup...\n")
    asyncio.run(take_screenshots())
    print("\nDone!")


if __name__ == "__main__":
    main()
