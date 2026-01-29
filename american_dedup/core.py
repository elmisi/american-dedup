"""Core logic: fdupes wrapper, parser, and file operations."""

import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Callable, Optional, TypedDict

# Setup logging
logging.basicConfig(
    filename='/tmp/american-dedup.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DuplicateInfo(TypedDict):
    """Information about a duplicate file."""
    to_move: str
    kept: str
    all_kept: list[str]
    size: int


class FolderStats(TypedDict):
    """Statistics for a folder."""
    count: int
    size: int
    files: list[str]


class AnalysisResult(TypedDict):
    """Result of duplicate analysis."""
    groups: int
    files_to_move: list[str]
    duplicates: list[DuplicateInfo]
    by_folder: dict[str, FolderStats]
    total_size: int


class MoveStats(TypedDict):
    """Statistics for move operation."""
    success: int
    skipped: int
    not_found: int
    error: int


class MoveResult(TypedDict):
    """Result of move operation."""
    stats: MoveStats
    moves: list[tuple[str, str]]


class UndoStats(TypedDict):
    """Statistics for undo operation."""
    success: int
    error: int


def parse_fdupes_line(line: str) -> list[str]:
    """
    Parse a line of fdupes output (with -1 flag).

    The -1 flag outputs all duplicates in a group on one line,
    separated by spaces. Spaces in paths are escaped as '\\ '.

    Args:
        line: A single line from fdupes output.

    Returns:
        List of file paths in the duplicate group.
    """
    placeholder = "\x00"
    line = line.replace("\\ ", placeholder)
    parts = line.strip().split(" ")
    files = []
    for part in parts:
        if part:
            path = part.replace(placeholder, " ")
            files.append(path)
    return files


def count_files(folders: list[str]) -> int:
    """
    Count total number of files in the specified folders.

    Uses the 'find' command for efficient counting.

    Args:
        folders: List of folder paths to count files in.

    Returns:
        Total number of files found.
    """
    try:
        cmd = ["find"] + folders + ["-type", "f"]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        return result.stdout.count('\n')
    except Exception:
        return 0


def run_fdupes(
    folders: list[str],
    on_progress: Optional[Callable[[str, int], None]] = None
) -> str:
    """
    Run fdupes on the specified folders.

    Uses flags: -c (cache), -r (recursive), -1 (single line per group).

    Args:
        folders: List of folder paths to scan.
        on_progress: Optional callback for progress updates (message, percentage).

    Returns:
        Raw fdupes output as a string.
    """
    import re

    cmd = ["fdupes", "-c", "-r", "-1"] + folders

    logger.info("=== START run_fdupes ===")
    logger.info(f"Command: {' '.join(cmd)}")
    logger.info(f"Folders: {folders}")

    if on_progress:
        on_progress(f"Starting scan of {len(folders)} folders...", 0)

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    logger.info(f"fdupes started, PID: {process.pid}")

    # Regex to parse "Progress [X/Y] Z%"
    progress_pattern = re.compile(r'Progress \[(\d+)/(\d+)\] (\d+)%')

    # Read output, filtering fdupes progress lines
    output_lines: list[str] = []
    total_lines = 0
    for line in process.stdout:
        total_lines += 1
        stripped = line.strip()

        # Check for progress line with percentage
        progress_match = progress_pattern.search(stripped)
        if progress_match:
            current = int(progress_match.group(1))
            total = int(progress_match.group(2))
            percentage = int(progress_match.group(3))
            if on_progress:
                on_progress(f"Comparing files: {current}/{total}", percentage)
            continue

        # Skip fdupes progress lines (e.g., "Building file list - \ | /")
        if stripped and stripped.startswith("Building file list"):
            if on_progress:
                on_progress("Building file list...", -1)  # -1 = indeterminate
            continue

        # Keep actual output lines
        if stripped:
            output_lines.append(line)

    process.wait()

    result = "".join(output_lines)
    logger.info(
        f"fdupes completed: {len(output_lines)} useful lines of {total_lines} total, "
        f"{len(result)} chars, return code: {process.returncode}"
    )
    logger.info("=== END run_fdupes ===")

    return result


def analyze_duplicates(
    fdupes_output: str,
    source_folders: list[str],
    include_internal: bool = False
) -> AnalysisResult:
    """
    Analyze fdupes output and determine which files to move.

    Files are classified by priority:
    - Files NOT in source_folders = high priority (kept)
    - Files IN source_folders = low priority (moved)

    Args:
        fdupes_output: Raw output from fdupes command.
        source_folders: Target folders from which duplicates will be moved.
        include_internal: If True, also move duplicates that exist only
                         within target folders. If False, only move files
                         that have copies in non-target folders.

    Returns:
        Analysis result with files to move and statistics.
    """
    logger.info("=== START analyze_duplicates ===")
    logger.info(f"Target folders: {source_folders}")
    logger.info(f"Include internal duplicates: {include_internal}")
    logger.info(f"Output to analyze: {len(fdupes_output)} chars")

    result: AnalysisResult = {
        "groups": 0,
        "files_to_move": [],
        "duplicates": [],
        "by_folder": {},
        "total_size": 0
    }

    for line in fdupes_output.strip().split("\n"):
        if not line.strip():
            continue

        files = parse_fdupes_line(line)
        if len(files) < 2:
            continue

        # Separate files by priority
        high_priority: list[str] = []  # Files to keep (not in source_folders)
        low_priority: list[str] = []   # Files to move (in source_folders)

        for f in files:
            is_source = any(f.startswith(src) for src in source_folders)
            if is_source:
                low_priority.append(f)
            else:
                high_priority.append(f)

        # Determine what to move and what to keep
        if high_priority:
            # Files exist in high priority folders: move all low_priority
            to_move = low_priority
            kept = high_priority
        elif include_internal:
            # Only files in source_folders AND flag is active: keep first, move rest
            to_move = low_priority[1:]
            kept = [low_priority[0]] if low_priority else []
        else:
            # Only files in source_folders AND flag is inactive: don't move anything
            to_move = []
            kept = []

        if not to_move:
            continue

        result["groups"] += 1

        for f in to_move:
            try:
                size = os.path.getsize(f)
            except OSError:
                size = 0

            result["files_to_move"].append(f)
            result["total_size"] += size

            # Add duplicate info with the kept file
            result["duplicates"].append({
                "to_move": f,
                "kept": kept[0] if kept else "",
                "all_kept": kept,
                "size": size
            })

            # Count per folder
            folder = str(Path(f).parent)
            if folder not in result["by_folder"]:
                result["by_folder"][folder] = {"count": 0, "size": 0, "files": []}
            result["by_folder"][folder]["count"] += 1
            result["by_folder"][folder]["size"] += size
            result["by_folder"][folder]["files"].append(f)

    logger.info("=== END analyze_duplicates ===")
    logger.info(
        f"Result: {result['groups']} groups, {len(result['files_to_move'])} files to move, "
        f"{format_size(result['total_size'])} total"
    )

    return result


def get_top_folder(path: str, source_folders: list[str]) -> str:
    """
    Find the source folder that contains the given path.

    Args:
        path: File path to check.
        source_folders: List of source folder paths.

    Returns:
        The matching source folder, or the parent directory if no match.
    """
    for src in source_folders:
        if path.startswith(src):
            return src
    return str(Path(path).parent)


def execute_move(
    files_to_move: list[str],
    dest_base: str,
    source_folders: list[str],
    on_progress: Optional[Callable[[int, int, str], None]] = None
) -> MoveResult:
    """
    Move files to the destination folder, preserving folder structure.

    Args:
        files_to_move: List of file paths to move.
        dest_base: Base destination directory.
        source_folders: Source folders (used to compute relative paths).
        on_progress: Optional callback(current, total, path) for progress.

    Returns:
        Move result with statistics and list of moves performed.
    """
    logger.info("=== START execute_move ===")
    logger.info(f"Files to move: {len(files_to_move)}")
    logger.info(f"Destination: {dest_base}")

    stats: MoveStats = {"success": 0, "skipped": 0, "not_found": 0, "error": 0}
    moves_done: list[tuple[str, str]] = []

    os.makedirs(dest_base, exist_ok=True)

    total = len(files_to_move)
    for i, src in enumerate(files_to_move, 1):
        if on_progress:
            on_progress(i, total, src)

        try:
            if not os.path.exists(src):
                stats["not_found"] += 1
                continue

            # Find relative path from source folder
            source_base = get_top_folder(src, source_folders)
            rel_path = os.path.relpath(src, os.path.dirname(source_base))
            dst = os.path.join(dest_base, rel_path)

            if os.path.exists(dst):
                stats["skipped"] += 1
                continue

            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.move(src, dst)
            stats["success"] += 1
            moves_done.append((src, dst))

        except Exception as e:
            stats["error"] += 1
            logger.warning(f"Error moving {src}: {e}")

    logger.info("=== END execute_move ===")
    logger.info(
        f"Result: {stats['success']} moved, {stats['skipped']} skipped, "
        f"{stats['not_found']} not found, {stats['error']} errors"
    )

    return {"stats": stats, "moves": moves_done}


def undo_move(
    undo_info: dict,
    on_progress: Optional[Callable[[int, int, str], None]] = None
) -> UndoStats:
    """
    Restore previously moved files to their original locations.

    Args:
        undo_info: Dictionary with 'moves' list and 'dest_dir'.
        on_progress: Optional callback(current, total, path) for progress.

    Returns:
        Undo statistics with success and error counts.
    """
    logger.info("=== START undo_move ===")

    stats: UndoStats = {"success": 0, "error": 0}
    moves = undo_info.get("moves", [])
    logger.info(f"Files to restore: {len(moves)}")

    total = len(moves)
    for i, move in enumerate(moves, 1):
        src = move["dst"]  # Reverse: dst becomes src
        dst = move["src"]  # src becomes dst

        if on_progress:
            on_progress(i, total, dst)

        try:
            if not os.path.exists(src):
                continue

            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.move(src, dst)
            stats["success"] += 1
        except Exception as e:
            stats["error"] += 1
            logger.warning(f"Error restoring {dst}: {e}")

    # Remove duplicates folder if empty
    dest_dir = undo_info.get("dest_dir")
    if dest_dir and os.path.exists(dest_dir):
        try:
            shutil.rmtree(dest_dir)
            logger.info(f"Removed duplicates folder: {dest_dir}")
        except Exception as e:
            logger.warning(f"Error removing folder {dest_dir}: {e}")

    logger.info("=== END undo_move ===")
    logger.info(f"Result: {stats['success']} restored, {stats['error']} errors")

    return stats


def format_size(size: int | float) -> str:
    """
    Format a size in bytes to a human-readable string.

    Args:
        size: Size in bytes.

    Returns:
        Formatted string like "1.5 MB".
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"
