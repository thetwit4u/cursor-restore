#!/usr/bin/env python3
"""
Cursor History Restore Script for macOS

This script restores files from Cursor's backup history on macOS by finding the latest
versions of files within a specified directory and time range. It supports both the
traditional History folder method and SQLite database exploration.
"""

import os
import json
import argparse
import shutil
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import unquote
from typing import Dict, List, Tuple, Optional


def parse_timestamp(timestamp_ms: int) -> datetime:
    """Convert millisecond timestamp to datetime object."""
    return datetime.fromtimestamp(timestamp_ms / 1000)


def url_decode_path(url_path: str) -> str:
    """Decode URL-encoded file path."""
    if url_path.startswith('file:///'):
        url_path = url_path[7:]  # Remove 'file://'
    return unquote(url_path)


def normalize_path(path: str) -> str:
    """Normalize path separators and make it comparable."""
    # Handle URL-encoded paths first
    if path.startswith('file:///'):
        path = url_decode_path(path)
    
    # Normalize separators and resolve path
    normalized = os.path.normpath(path).replace('\\', '/')
    
    # Expand user home directory
    if normalized.startswith('~'):
        normalized = os.path.expanduser(normalized).replace('\\', '/')
    
    # Remove trailing slashes for consistency
    if normalized.endswith('/') and len(normalized) > 1:
        normalized = normalized.rstrip('/')
    
    return normalized


def is_path_in_directory(file_path: str, target_dir: str) -> bool:
    """Check if the file path is within the target directory."""
    file_path_norm = normalize_path(file_path)
    target_dir_norm = normalize_path(target_dir)
    
    # Ensure target directory ends with / for proper prefix matching
    if not target_dir_norm.endswith('/'):
        target_dir_norm += '/'
    
    return file_path_norm.startswith(target_dir_norm) or file_path_norm == target_dir_norm.rstrip('/')


def get_relative_path(file_path: str, target_dir: str) -> str:
    """Get the relative path of a file within the target directory."""
    file_path_norm = normalize_path(file_path)
    target_dir_norm = normalize_path(target_dir)
    
    # Ensure target directory ends with / for proper prefix matching
    if not target_dir_norm.endswith('/'):
        target_dir_norm += '/'
    
    if not (file_path_norm.startswith(target_dir_norm) or file_path_norm == target_dir_norm.rstrip('/')):
        raise ValueError(f"File {file_path} is not within directory {target_dir}")
    
    # Remove the target directory prefix
    if file_path_norm == target_dir_norm.rstrip('/'):
        # This is the root directory itself
        return ""
    
    relative = file_path_norm[len(target_dir_norm):]
    return relative


def find_latest_files_from_history(history_dir: str, target_restore_dir: str, 
                                   start_time: datetime, end_time: datetime,
                                   verbose: bool = True) -> Dict[str, Tuple[str, datetime]]:
    """
    Find the latest version of each file within the specified directory and time range.
    Uses the History folder method (entries.json files).
    
    Returns:
        Dict mapping relative file paths to (backup_file_path, timestamp) tuples
    """
    latest_files = {}
    
    history_path = Path(history_dir)
    if not history_path.exists():
        raise FileNotFoundError(f"History directory not found: {history_dir}")
    
    if verbose:
        print(f"Scanning history directory: {history_dir}")
        print(f"Looking for files from: {target_restore_dir}")
        print(f"Time range: {start_time} to {end_time}")
    
    folder_count = 0
    matching_files = 0
    
    # Iterate through all folders in the history directory
    for folder in history_path.iterdir():
        if not folder.is_dir():
            continue
            
        folder_count += 1
        entries_file = folder / "entries.json"
        
        if not entries_file.exists():
            continue
            
        try:
            with open(entries_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            resource_url = data.get('resource', '')
            if not resource_url:
                continue
                
            # Decode the file path
            original_file_path = url_decode_path(resource_url)
            
            # Check if this file is within our target directory
            if not is_path_in_directory(original_file_path, target_restore_dir):
                continue
                
            # Get relative path within the target directory
            try:
                relative_path = get_relative_path(original_file_path, target_restore_dir)
            except ValueError:
                continue
            
            # Find the latest entry within our time range
            latest_entry = None
            latest_timestamp = None
            
            for entry in data.get('entries', []):
                timestamp_ms = entry.get('timestamp')
                if not timestamp_ms:
                    continue
                    
                entry_time = parse_timestamp(timestamp_ms)
                
                # Check if within time range
                if not (start_time <= entry_time <= end_time):
                    continue
                    
                if latest_timestamp is None or entry_time > latest_timestamp:
                    latest_entry = entry
                    latest_timestamp = entry_time
            
            if latest_entry:
                backup_file_path = folder / latest_entry['id']
                if backup_file_path.exists():
                    latest_files[relative_path] = (str(backup_file_path), latest_timestamp)
                    matching_files += 1
                    if verbose:
                        print(f"Found: {relative_path} (from {latest_timestamp})")
        
        except (json.JSONDecodeError, KeyError, OSError) as e:
            if verbose:
                print(f"Warning: Error processing {folder}: {e}")
            continue
    
    if verbose:
        print(f"\nProcessed {folder_count} folders, found {matching_files} matching files")
    return latest_files


def restore_files(latest_files: Dict[str, Tuple[str, datetime]], output_dir: str, verbose: bool = True):
    """Restore the files to the output directory."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    if verbose:
        print(f"\nRestoring files to: {output_dir}")
    
    restored_count = 0
    
    for relative_path, (backup_file_path, timestamp) in latest_files.items():
        # Create the full output path
        output_file_path = output_path / relative_path
        
        # Create parent directories if needed
        output_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Copy the file
            shutil.copy2(backup_file_path, output_file_path)
            if verbose:
                print(f"Restored: {relative_path}")
            restored_count += 1
        except OSError as e:
            if verbose:
                print(f"Error restoring {relative_path}: {e}")
    
    if verbose:
        print(f"\nSuccessfully restored {restored_count} files")
    
    return restored_count


def list_workspaces(cursor_dir: str) -> List[Dict[str, str]]:
    """List all available workspaces with their metadata."""
    workspaces = []
    workspace_storage_dir = Path(cursor_dir) / "workspaceStorage"
    
    if not workspace_storage_dir.exists():
        return workspaces
    
    for workspace_folder in workspace_storage_dir.iterdir():
        if not workspace_folder.is_dir():
            continue
        
        workspace_json = workspace_folder / "workspace.json"
        if workspace_json.exists():
            try:
                with open(workspace_json, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    folder_uri = data.get('folder', '')
                    if folder_uri:
                        folder_path = url_decode_path(folder_uri)
                        workspaces.append({
                            'id': workspace_folder.name,
                            'path': folder_path,
                            'db': str(workspace_folder / 'state.vscdb')
                        })
            except (json.JSONDecodeError, OSError):
                pass
    
    return workspaces


def main():
    parser = argparse.ArgumentParser(
        description='Restore files from Cursor history backups on macOS',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Restore files from the last 7 days (default)
  python cursor_restore_mac.py -r ~/Projects/MyProject/
  
  # Restore files from the last 30 days
  python cursor_restore_mac.py -r ~/Projects/MyProject/ -b 30
  
  # Use custom time range
  python cursor_restore_mac.py -r ~/Projects/MyProject/ -s "2024-01-01 00:00:00" -e "2024-12-31 23:59:59"
  
  # List available workspaces
  python cursor_restore_mac.py --list-workspaces
        """
    )
    
    # Default to macOS Cursor directory
    default_cursor_dir = os.path.expanduser('~/Library/Application Support/Cursor/User')
    default_history_dir = os.path.join(default_cursor_dir, 'History')
    
    parser.add_argument('--cursor-dir',
                       default=default_cursor_dir,
                       help=f'Cursor User directory (default: {default_cursor_dir})')
    
    parser.add_argument('--history-dir', '-d',
                       default=default_history_dir,
                       help=f'Directory containing Cursor history (default: {default_history_dir})')
    
    parser.add_argument('--restore-path', '-r',
                       help='Original directory path to restore (e.g., ~/Projects/MyProject/)')
    
    parser.add_argument('--output-dir', '-o',
                       default='restoredFolder',
                       help='Output directory for restored files (default: restoredFolder)')
    
    parser.add_argument('--start-time', '-s',
                       help='Start timestamp (YYYY-MM-DD HH:MM:SS) - default: calculated from --days-back')
    
    parser.add_argument('--end-time', '-e',
                       help='End timestamp (YYYY-MM-DD HH:MM:SS) - default: now')
    
    parser.add_argument('--days-back', '-b',
                       type=int, default=7,
                       help='Number of days back to search (default: 7, ignored if --start-time provided)')
    
    parser.add_argument('--list-workspaces', '-l',
                       action='store_true',
                       help='List all available workspaces and exit')
    
    parser.add_argument('--quiet', '-q',
                       action='store_true',
                       help='Quiet mode - minimal output')
    
    args = parser.parse_args()
    
    # List workspaces mode
    if args.list_workspaces:
        print("Available Workspaces:")
        print("=" * 80)
        workspaces = list_workspaces(args.cursor_dir)
        if workspaces:
            for ws in workspaces:
                print(f"\nWorkspace ID: {ws['id']}")
                print(f"  Path: {ws['path']}")
                print(f"  Database: {ws['db']}")
        else:
            print("No workspaces found.")
        return 0
    
    # Restore mode requires restore-path
    if not args.restore_path:
        parser.error("--restore-path/-r is required (or use --list-workspaces to list available workspaces)")
    
    # Parse timestamps
    if args.end_time:
        end_time = datetime.strptime(args.end_time, '%Y-%m-%d %H:%M:%S')
    else:
        end_time = datetime.now()
    
    if args.start_time:
        start_time = datetime.strptime(args.start_time, '%Y-%m-%d %H:%M:%S')
    else:
        start_time = end_time - timedelta(days=args.days_back)
    
    verbose = not args.quiet
    
    if verbose:
        print("Cursor History Restore Script for macOS")
        print("=" * 80)
        print(f"History directory: {args.history_dir}")
        print(f"Restore path: {args.restore_path}")
        print(f"Output directory: {args.output_dir}")
        print(f"Time range: {start_time} to {end_time}")
        print()
    
    try:
        # Find the latest files from History folder
        latest_files = find_latest_files_from_history(
            args.history_dir,
            args.restore_path,
            start_time,
            end_time,
            verbose
        )
        
        if not latest_files:
            if verbose:
                print("No files found matching the criteria.")
            return 0
        
        # Restore the files
        restored_count = restore_files(latest_files, args.output_dir, verbose)
        
        if verbose:
            print("\n" + "=" * 80)
            print("Restore complete!")
            print(f"Total files restored: {restored_count}")
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        if not args.quiet:
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())

