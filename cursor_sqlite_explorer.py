#!/usr/bin/env python3
"""
Cursor SQLite Database Explorer

This script explores Cursor's SQLite databases to extract code snippets,
chat history, and other useful information for recovery purposes.
"""

import os
import json
import sqlite3
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional


class CursorDatabaseExplorer:
    """Explores Cursor's SQLite databases."""
    
    def __init__(self, db_path: str):
        """Initialize the explorer with a database path."""
        self.db_path = db_path
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Database not found: {db_path}")
    
    def _connect(self) -> sqlite3.Connection:
        """Create a database connection."""
        return sqlite3.connect(self.db_path)
    
    def list_tables(self) -> List[str]:
        """List all tables in the database."""
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        return tables
    
    def get_table_schema(self, table_name: str) -> str:
        """Get the schema of a specific table."""
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name=?;", (table_name,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else ""
    
    def get_all_keys(self, table_name: str = 'cursorDiskKV', limit: Optional[int] = None) -> List[str]:
        """Get all keys from a key-value table."""
        conn = self._connect()
        cursor = conn.cursor()
        
        query = f"SELECT key FROM {table_name} ORDER BY key"
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query)
        keys = [row[0] for row in cursor.fetchall()]
        conn.close()
        return keys
    
    def get_value(self, key: str, table_name: str = 'cursorDiskKV') -> Optional[bytes]:
        """Get a value by key from a key-value table."""
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute(f"SELECT value FROM {table_name} WHERE key=?", (key,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    
    def search_keys(self, pattern: str, table_name: str = 'cursorDiskKV') -> List[str]:
        """Search for keys matching a pattern."""
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute(f"SELECT key FROM {table_name} WHERE key LIKE ? ORDER BY key", (pattern,))
        keys = [row[0] for row in cursor.fetchall()]
        conn.close()
        return keys
    
    def get_chat_conversations(self) -> List[Dict[str, Any]]:
        """Extract chat conversation metadata."""
        bubble_keys = self.search_keys('bubbleId:%')
        conversations = []
        
        for key in bubble_keys:
            value = self.get_value(key)
            if value:
                try:
                    # Try to decode as JSON
                    data = json.loads(value.decode('utf-8'))
                    conversations.append({
                        'key': key,
                        'data': data
                    })
                except (json.JSONDecodeError, UnicodeDecodeError):
                    # Skip non-JSON or non-UTF8 data
                    pass
        
        return conversations
    
    def extract_code_from_conversations(self, output_dir: str = 'extracted_code',
                                       filter_text: Optional[str] = None) -> int:
        """
        Extract code snippets from chat conversations.
        
        Args:
            output_dir: Directory to save extracted code
            filter_text: Optional text to filter conversations
        
        Returns:
            Number of code snippets extracted
        """
        conversations = self.get_chat_conversations()
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        extracted_count = 0
        
        for i, conv in enumerate(conversations):
            try:
                data = conv['data']
                
                # Skip if filter doesn't match
                if filter_text:
                    data_str = json.dumps(data, default=str).lower()
                    if filter_text.lower() not in data_str:
                        continue
                
                # Look for messages with code blocks or file content
                if isinstance(data, dict):
                    messages = []
                    
                    # Try different structures
                    if 'messages' in data:
                        messages = data['messages']
                    elif 'bubbleContent' in data and isinstance(data['bubbleContent'], dict):
                        if 'messages' in data['bubbleContent']:
                            messages = data['bubbleContent']['messages']
                    
                    # Extract code from messages
                    for msg_idx, msg in enumerate(messages):
                        if not isinstance(msg, dict):
                            continue
                        
                        text = msg.get('text', '') or msg.get('content', '')
                        if not text:
                            continue
                        
                        # Save if it looks like code (contains code blocks or specific patterns)
                        if '```' in text or 'def ' in text or 'function ' in text or 'class ' in text:
                            filename = f"conversation_{i}_message_{msg_idx}.txt"
                            filepath = output_path / filename
                            
                            with open(filepath, 'w', encoding='utf-8') as f:
                                f.write(f"# Extracted from conversation: {conv['key']}\n")
                                f.write(f"# Message index: {msg_idx}\n")
                                f.write(f"# Timestamp: {datetime.now()}\n\n")
                                f.write(text)
                            
                            extracted_count += 1
                            print(f"Extracted: {filename}")
            
            except Exception as e:
                print(f"Warning: Error processing conversation {i}: {e}")
                continue
        
        return extracted_count


def main():
    parser = argparse.ArgumentParser(
        description='Explore Cursor SQLite databases to extract code and chat history',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all tables in the global database
  python cursor_sqlite_explorer.py --list-tables
  
  # List all keys in cursorDiskKV table
  python cursor_sqlite_explorer.py --list-keys
  
  # Search for specific keys
  python cursor_sqlite_explorer.py --search "bubbleId:%"
  
  # Extract code from chat conversations
  python cursor_sqlite_explorer.py --extract-code
  
  # Extract code matching a specific project
  python cursor_sqlite_explorer.py --extract-code --filter "MyProject"
  
  # Use a workspace-specific database
  python cursor_sqlite_explorer.py --db ~/Library/Application\\ Support/Cursor/User/workspaceStorage/xxx/state.vscdb --extract-code
        """
    )
    
    default_db = os.path.expanduser('~/Library/Application Support/Cursor/User/globalStorage/state.vscdb')
    
    parser.add_argument('--db', '-d',
                       default=default_db,
                       help=f'Path to SQLite database (default: global state.vscdb)')
    
    parser.add_argument('--list-tables', '-t',
                       action='store_true',
                       help='List all tables in the database')
    
    parser.add_argument('--list-keys', '-k',
                       action='store_true',
                       help='List all keys in cursorDiskKV table')
    
    parser.add_argument('--search', '-s',
                       help='Search for keys matching a pattern (SQL LIKE syntax)')
    
    parser.add_argument('--get-value', '-g',
                       help='Get value for a specific key')
    
    parser.add_argument('--extract-code', '-e',
                       action='store_true',
                       help='Extract code snippets from chat conversations')
    
    parser.add_argument('--filter', '-f',
                       help='Filter conversations by text content')
    
    parser.add_argument('--output-dir', '-o',
                       default='extracted_code',
                       help='Output directory for extracted code (default: extracted_code)')
    
    parser.add_argument('--limit', '-l',
                       type=int,
                       help='Limit number of results')
    
    args = parser.parse_args()
    
    try:
        explorer = CursorDatabaseExplorer(args.db)
        
        print(f"Exploring database: {args.db}\n")
        
        # List tables
        if args.list_tables:
            print("Tables in database:")
            print("=" * 50)
            tables = explorer.list_tables()
            for table in tables:
                schema = explorer.get_table_schema(table)
                print(f"\n{table}:")
                print(f"  {schema}")
            return 0
        
        # List keys
        if args.list_keys:
            print("Keys in cursorDiskKV table:")
            print("=" * 50)
            keys = explorer.get_all_keys(limit=args.limit)
            for key in keys:
                print(key)
            print(f"\nTotal: {len(keys)} keys")
            return 0
        
        # Search keys
        if args.search:
            print(f"Searching for keys matching: {args.search}")
            print("=" * 50)
            keys = explorer.search_keys(args.search)
            for key in keys[:args.limit] if args.limit else keys:
                print(key)
            print(f"\nTotal: {len(keys)} matching keys")
            return 0
        
        # Get value
        if args.get_value:
            print(f"Value for key: {args.get_value}")
            print("=" * 50)
            value = explorer.get_value(args.get_value)
            if value:
                try:
                    # Try to decode as JSON
                    decoded = value.decode('utf-8')
                    try:
                        parsed = json.loads(decoded)
                        print(json.dumps(parsed, indent=2))
                    except json.JSONDecodeError:
                        print(decoded)
                except UnicodeDecodeError:
                    print(f"Binary data ({len(value)} bytes)")
                    print(value[:200])  # Print first 200 bytes
            else:
                print("Key not found")
            return 0
        
        # Extract code
        if args.extract_code:
            print("Extracting code from chat conversations...")
            print("=" * 50)
            count = explorer.extract_code_from_conversations(
                args.output_dir,
                args.filter
            )
            print(f"\nExtracted {count} code snippets to: {args.output_dir}")
            return 0
        
        # Default: show summary
        print("Database Summary:")
        print("=" * 50)
        tables = explorer.list_tables()
        print(f"Tables: {', '.join(tables)}")
        
        for table in tables:
            keys = explorer.get_all_keys(table)
            print(f"\n{table}: {len(keys)} entries")
            
            # Show sample keys
            if keys:
                print("  Sample keys:")
                for key in keys[:5]:
                    print(f"    - {key}")
                if len(keys) > 5:
                    print(f"    ... and {len(keys) - 5} more")
        
        print("\nUse --help to see available options")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())

