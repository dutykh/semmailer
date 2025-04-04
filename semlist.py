#!/usr/bin/env python3
"""
semlist.py - Command-line tool to manage the KU Math Seminar mailing list.

Author: Dr. Denys Dutykh
        Mathematics Department, Khalifa University
        Abu Dhabi, UAE

© 2025 Denys Dutykh. All rights reserved.

Usage:
  python3 semlist.py help                  - Show help information
  python3 semlist.py print all             - Print all emails for copying
  python3 semlist.py print [BATCH_NUMBER]  - Print specific batch
  python3 semlist.py batches               - Show batch info
  python3 semlist.py add 'email@example.com'
  python3 semlist.py new DatabaseName      - Create database
  python3 semlist.py del DatabaseName      - Delete database
  python3 semlist.py activate DatabaseName - Set active database
  python3 semlist.py config                - Show configuration
"""

import os
import sys
import argparse
import re
import json
from pathlib import Path
from datetime import datetime

# Constants
DEFAULT_DATABASE_NAME = "MailingList"
DATABASE_FOLDER = "dbase"
CONFIG_FILE = os.path.join(DATABASE_FOLDER, "config.json")
MAX_EMAILS_PER_BATCH = 58

def ensure_config_exists():
    """Ensure the configuration file exists."""
    if not os.path.exists(DATABASE_FOLDER):
        os.makedirs(DATABASE_FOLDER, exist_ok=True)

    if not os.path.exists(CONFIG_FILE):
        config = {
            "active_database": f"{DEFAULT_DATABASE_NAME}.json"
        }
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        return config
    return get_config()

def get_config():
    """Get the configuration."""
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading configuration: {str(e)}")
        return {"active_database": f"{DEFAULT_DATABASE_NAME}.json"}

def save_config(config):
    """Save the configuration."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving configuration: {str(e)}")
        return False

def get_active_database_path():
    """Get the active database path."""
    config = ensure_config_exists()
    active_db = config.get("active_database", f"{DEFAULT_DATABASE_NAME}.json")

    # Make sure we have the correct path with database folder
    if not active_db.startswith(DATABASE_FOLDER):
        return os.path.join(DATABASE_FOLDER, active_db)
    return active_db

def parse_arguments():
    """Parse command-line arguments."""
    # Manually check for help commands to provide consistent help output
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help', 'help']:
        display_help()
        sys.exit(0)

    parser = argparse.ArgumentParser(add_help=False)  # Disable built-in help
    parser.add_argument("command", help="Command to execute: print, add, new, etc.")
    parser.add_argument("args", nargs="*", help="Arguments for the command")

    return parser.parse_args()

def parse_email_entries(args_list):
    """Parse multiple email entries from arguments."""
    # The input should be a list of arguments which may be a single quoted string with multiple emails
    if not args_list:
        return []

    # First, join all arguments into a single string
    input_str = " ".join(args_list)

    # Split by semicolons if there are multiple entries
    entries = []
    current_entry = ""
    in_angle_brackets = False

    for char in input_str:
        if char == '<':
            in_angle_brackets = True
            current_entry += char
        elif char == '>':
            in_angle_brackets = False
            current_entry += char
        elif char == ';' and not in_angle_brackets:
            if current_entry.strip():
                entries.append(current_entry.strip())
            current_entry = ""
        else:
            current_entry += char

    # Add the last entry if it's not empty
    if current_entry.strip():
        entries.append(current_entry.strip())

    # Process each entry to extract email and name components
    parsed_entries = []
    for entry in entries:
        # Strip any single quotes from the entry
        entry = entry.strip("'")

        # Pattern: Name With Spaces <email@example.com>
        match = re.search(r'(.*?)\s*<([^>]+)>', entry)
        if match:
            full_name = match.group(1).strip()
            email = match.group(2).strip()
            name_components = parse_name(full_name)
            parsed_entries.append({
                "email": email,
                "name": full_name,
                **name_components
            })
            continue

        # Pattern: <email@example.com>
        match = re.search(r'<([^>]+)>', entry)
        if match:
            email = match.group(1).strip()
            parsed_entries.append({
                "email": email,
                "name": "",
                "first_name": "",
                "middle_names": "",
                "last_name": ""
            })
            continue

        # Pattern: Just email@example.com
        match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', entry)
        if match:
            email = match.group(1).strip()
            parsed_entries.append({
                "email": email,
                "name": "",
                "first_name": "",
                "middle_names": "",
                "last_name": ""
            })
            continue

    return parsed_entries

def parse_name(full_name):
    """Parse a full name into first, middle, and last name components."""
    # Remove any quotes
    name = full_name.replace('"', '').strip()
    if not name:
        return {
            "first_name": "",
            "middle_names": "",
            "last_name": ""
        }

    # Split the name into components
    name_parts = name.split()

    if len(name_parts) == 1:
        return {
            "first_name": name_parts[0],
            "middle_names": "",
            "last_name": ""
        }
    elif len(name_parts) == 2:
        return {
            "first_name": name_parts[0],
            "middle_names": "",
            "last_name": name_parts[1]
        }
    else:
        return {
            "first_name": name_parts[0],
            "middle_names": " ".join(name_parts[1:-1]),
            "last_name": name_parts[-1]
        }

def convert_txt_to_json(txt_path, json_path=None):
    """Convert a text-based mailing list to JSON format."""
    if json_path is None:
        json_path = txt_path.replace('.txt', '.json')

    if not os.path.exists(txt_path):
        print(f"Error: Text database file '{txt_path}' does not exist.")
        return False

    batches = []
    current_batch = []

    try:
        with open(txt_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                if line == "%%%":
                    if current_batch:
                        batches.append(current_batch)
                        current_batch = []
                else:
                    email = extract_email_from_line(line)
                    name = extract_name_from_line(line)
                    if email:
                        name_components = parse_name(name)
                        current_batch.append({
                            "email": email,
                            "name": name,
                            "full_entry": line,
                            **name_components
                        })

            # Add the last batch if it's not empty
            if current_batch:
                batches.append(current_batch)

        # Create JSON structure
        json_data = {
            "name": "KU Math Seminar",
            "created": datetime.now().strftime("%Y-%m-%d"),
            "last_modified": datetime.now().strftime("%Y-%m-%d"),
            "batches": []
        }

        for i, batch_emails in enumerate(batches, 1):
            json_data["batches"].append({
                "id": i,
                "emails": batch_emails
            })

        # Write JSON data
        with open(json_path, 'w') as f:
            json.dump(json_data, f, indent=2)

        print(f"Successfully converted '{txt_path}' to JSON format at '{json_path}'.")
        return True

    except Exception as e:
        print(f"Error converting text to JSON: {str(e)}")
        return False

def show_statistics(database_path=None):
    """Show statistics about the mailing list database."""
    if database_path is None:
        database_path = get_active_database_path()

    data = read_mailing_list(database_path)
    if not data:
        return False

    # Calculate statistics
    total_emails = 0
    batch_stats = []

    for batch in data["batches"]:
        batch_count = len(batch["emails"])
        total_emails += batch_count
        batch_stats.append({
            "id": batch["id"],
            "count": batch_count
        })

    # Display statistics
    print(f"Database: {data.get('name', 'Unknown')}")
    print(f"Last modified: {data.get('last_modified', 'Unknown')}")
    print(f"Total number of emails: {total_emails}")
    print(f"Number of batches: {len(data['batches'])}")
    print("\nEmails per batch:")

    for batch in batch_stats:
        print(f"  Batch {batch['id']}: {batch['count']} emails")

    return True

def remove_email(email, database_path=None):
    """Remove an email from the database."""
    if database_path is None:
        database_path = get_active_database_path()

    data = read_mailing_list(database_path)
    if not data:
        return False

    email_found = False
    email = email.lower()  # Convert to lowercase for case-insensitive comparison

    # Search through all batches for the email
    for batch in data["batches"]:
        for i, entry in enumerate(batch["emails"]):
            if entry["email"].lower() == email:
                removed_entry = batch["emails"].pop(i)
                email_found = True
                name = removed_entry.get("name", "")
                if name:
                    print(f"Email '{name} <{email}>' has been removed from the database.")
                else:
                    print(f"Email '{email}' has been removed from the database.")
                break
        if email_found:
            break

    if not email_found:
        print(f"Email '{email}' was not found in the database.")
        return False

    # Remove any empty batches
    data["batches"] = [batch for batch in data["batches"] if batch["emails"]]

    # Renumber batch IDs to ensure they are consecutive
    for i, batch in enumerate(data["batches"], 1):
        batch["id"] = i

    if write_mailing_list(data, database_path):
        return True
    else:
        return False

def extract_email_from_line(line):
    """Extract the email address from a line."""
    match = re.search(r'<([^>]+)>', line)
    if match:
        return match.group(1).strip()

    # If no <> format, try to find an email pattern
    match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', line)
    if match:
        return match.group(1).strip()

    return None

def extract_name_from_line(line):
    """Extract the name from a line."""
    # Check for "Name" <email> format
    match = re.search(r'"([^"]*)"?\s*<', line)
    if match:
        return match.group(1).strip()

    # Check for Name <email> format without quotes
    match = re.search(r'^([^<]+)<', line)
    if match:
        name = match.group(1).strip()
        if name.endswith(';'):
            name = name[:-1].strip()
        return name

    return ""

def read_mailing_list(database_path=None):
    """Read the mailing list from the JSON database file."""
    if database_path is None:
        database_path = get_active_database_path()

    if not os.path.exists(database_path):
        print(f"Error: Database file '{database_path}' does not exist.")
        return None

    try:
        with open(database_path, 'r') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"Error reading database: {str(e)}")
        return None

def write_mailing_list(data, database_path=None):
    """Write the mailing list to the JSON database file."""
    if database_path is None:
        database_path = get_active_database_path()

    try:
        # Update last modified date
        data["last_modified"] = datetime.now().strftime("%Y-%m-%d")

        # Write JSON data
        with open(database_path, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"Error writing to database: {str(e)}")
        return False

def optimize_batches(data, max_per_batch=MAX_EMAILS_PER_BATCH):
    """
    Optimize the batches to minimize the number of batches while
    respecting the max_per_batch limit.
    """
    # Flatten all email entries
    all_emails = []
    for batch in data["batches"]:
        all_emails.extend(batch["emails"])

    # Create new optimized batches
    optimized_batches = []
    current_batch = []

    for email_entry in all_emails:
        if len(current_batch) >= max_per_batch:
            optimized_batches.append({
                "id": len(optimized_batches) + 1,
                "emails": current_batch
            })
            current_batch = []
        current_batch.append(email_entry)

    # Add the last batch if it's not empty
    if current_batch:
        optimized_batches.append({
            "id": len(optimized_batches) + 1,
            "emails": current_batch
        })

    # Update the data with optimized batches
    data["batches"] = optimized_batches
    return data

def print_emails(data, batch_number=None, simple_format=False):
    """Print emails in batches.

    Args:
        data: The database data
        batch_number: If provided, print only this batch number
        simple_format: If True, print only the email addresses in a simple format for copying
    """
    if not data:
        print("No data found in the database.")
        return

    if not data.get("batches"):
        print("No batches found in the database.")
        return

    # If a specific batch is requested
    if batch_number is not None:
        if batch_number == 'all':
            # Print all batches in simple format
            for i, batch in enumerate(data["batches"], 1):
                print(f"\n=== Batch {i} ===\n")
                for entry in batch["emails"]:
                    # Format for Outlook: First name Last name <email>;
                    first = entry.get('first_name', '')
                    last = entry.get('last_name', '')
                    name = f"{first} {last}".strip()
                    if not name:
                        name = entry.get('name', '')
                    print(f"{name} <{entry['email']}>;")
            return

        try:
            batch_num = int(batch_number)
            # Check if the batch exists
            if batch_num < 1 or batch_num > len(data["batches"]):
                print(f"Error: Batch {batch_num} does not exist.")
                print(f"Available batches: 1 to {len(data['batches'])}")
                return

            # Print the requested batch
            batch = data["batches"][batch_num - 1]
            print(f"\n=== Batch {batch_num} ===\n")
            if simple_format:
                for entry in batch["emails"]:
                    # Format for Outlook: First name Last name <email>;
                    first = entry.get('first_name', '')
                    last = entry.get('last_name', '')
                    name = f"{first} {last}".strip()
                    if not name:
                        name = entry.get('name', '')
                    print(f"{name} <{entry['email']}>;")
            else:
                for entry in batch["emails"]:
                    print(f"  {entry.get('full_entry', f'{entry.get('name', '')} <{entry['email']}>').strip()}")

                    # Optionally show name components
                    first = entry.get('first_name', '')
                    middle = entry.get('middle_names', '')
                    last = entry.get('last_name', '')
                    if first or middle or last:
                        print(f"    First: {first}, Middle: {middle}, Last: {last}")
            return

        except ValueError:
            print(f"Error: Invalid batch number '{batch_number}'.")
            return

    # Print summary and all batches in detailed format
    total_entries = sum(len(batch["emails"]) for batch in data["batches"])
    print(f"Database: {data.get('name', 'Unknown')}")
    print(f"Last modified: {data.get('last_modified', 'Unknown')}")
    print(f"Found {total_entries} entries in {len(data['batches'])} batches:")

    for i, batch in enumerate(data["batches"], 1):
        print(f"\n=== Batch {i} ===\n")
        for entry in batch["emails"]:
            # Display name and email
            print(f"  {entry.get('full_entry', f'{entry.get('name', '')} <{entry['email']}>').strip()}")

            # Optionally show name components
            first = entry.get('first_name', '')
            middle = entry.get('middle_names', '')
            last = entry.get('last_name', '')
            if first or middle or last:
                print(f"    First: {first}, Middle: {middle}, Last: {last}")

def is_email_exists(email, data):
    """Check if the email already exists in the database."""
    if not data or not data.get("batches"):
        return False

    for batch in data["batches"]:
        for entry in batch["emails"]:
            if entry["email"].lower() == email.lower():
                return True

    return False

def add_email_entry(entry, data):
    """Add a new email entry to the database if it doesn't exist."""
    if is_email_exists(entry["email"], data):
        print(f"Email '{entry['email']}' already exists in the database.")
        return False

    # Format the new entry
    name = entry.get("name", "")
    email = entry["email"]

    if name:
        full_entry = f'"{name}" <{email}>;'
    else:
        full_entry = f'<{email}>;'

    new_entry = {
        "email": email,
        "name": name,
        "full_entry": full_entry,
        "first_name": entry.get("first_name", ""),
        "middle_names": entry.get("middle_names", ""),
        "last_name": entry.get("last_name", "")
    }

    # Add to the last batch if it exists and has room, otherwise create a new batch
    if data["batches"] and len(data["batches"][-1]["emails"]) < MAX_EMAILS_PER_BATCH:
        data["batches"][-1]["emails"].append(new_entry)
    else:
        data["batches"].append({
            "id": len(data["batches"]) + 1,
            "emails": [new_entry]
        })

    print(f"Successfully added '{email}' to the database.")
    return True

def add_emails(entries_str, database_path=None):
    """Add one or more emails to the database."""
    if database_path is None:
        database_path = get_active_database_path()

    data = read_mailing_list(database_path)
    if not data:
        return False

    parsed_entries = parse_email_entries(entries_str)
    if not parsed_entries:
        print("No valid email entries found.")
        return False

    added_count = 0
    for entry in parsed_entries:
        if add_email_entry(entry, data):
            added_count += 1

    if added_count > 0:
        if write_mailing_list(data, database_path):
            print(f"Successfully added {added_count} email(s) to the database.")
            return True

    return False

def create_new_database(name):
    """Create a new database in the dbase folder."""
    # Create the dbase folder if it doesn't exist
    dbase_path = Path(DATABASE_FOLDER)
    dbase_path.mkdir(exist_ok=True)

    # Create a new empty database file
    db_name = name if name.endswith('.json') else f"{name}.json"
    new_db_path = dbase_path / db_name

    if new_db_path.exists():
        print(f"Error: Database '{name}' already exists.")
        return False

    try:
        # Create initial JSON structure
        data = {
            "name": name,
            "created": datetime.now().strftime("%Y-%m-%d"),
            "last_modified": datetime.now().strftime("%Y-%m-%d"),
            "batches": []
        }

        # Write JSON data
        with open(new_db_path, 'w') as f:
            json.dump(data, f, indent=2)

        # Update config to set this as active database - store just the filename
        config = ensure_config_exists()
        config["active_database"] = db_name
        save_config(config)

        print(f"Successfully created new database '{name}' in {DATABASE_FOLDER}/ folder.")
        print(f"'{name}' is now the active database.")
        return True
    except Exception as e:
        print(f"Error creating new database: {str(e)}")
        return False

def delete_database(name):
    """Delete a database from the dbase folder."""
    # Ensure the database exists
    db_name = name if name.endswith('.json') else f"{name}.json"
    db_path = os.path.join(DATABASE_FOLDER, db_name)

    if not os.path.exists(db_path):
        print(f"Error: Database '{name}' does not exist.")
        return False

    # Ask for confirmation
    confirm = input(f"Are you sure you want to delete the database '{name}'? (yes/no): ")
    if confirm.lower() not in ['yes', 'y']:
        print("Database deletion cancelled.")
        return False

    try:
        # Check if it's the active database
        config = ensure_config_exists()
        active_db = config.get("active_database", "")

        # Delete the database file
        os.remove(db_path)
        print(f"Database '{name}' has been deleted.")

        # If it was the active database, reset the active database
        if db_name == active_db or os.path.join(DATABASE_FOLDER, active_db) == db_path:
            print(f"Warning: The deleted database was the active database.")

            # Find another database to set as active, if any
            existing_dbs = [f for f in os.listdir(DATABASE_FOLDER) if f.endswith('.json') and f != 'config.json']
            if existing_dbs:
                new_active = existing_dbs[0]
                config["active_database"] = new_active
                save_config(config)
                print(f"'{new_active}' is now set as the active database.")
            else:
                config["active_database"] = ""
                save_config(config)
                print("No active database is set. Create a new database with 'python3 semlist.py new DatabaseName'.")

        return True
    except Exception as e:
        print(f"Error deleting database: {str(e)}")
        return False

def activate_database(name):
    """Activate a database."""
    # Ensure the database exists
    db_name = name if name.endswith('.json') else f"{name}.json"
    db_path = os.path.join(DATABASE_FOLDER, db_name)

    if not os.path.exists(db_path):
        print(f"Error: Database '{name}' does not exist.")
        print(f"Looking for file at: {db_path}")

        # Check if any databases exist and list them
        existing_dbs = [f for f in os.listdir(DATABASE_FOLDER) if f.endswith('.json') and f != 'config.json']
        if existing_dbs:
            print("\nAvailable databases:")
            for db in existing_dbs:
                print(f"  {db}")
            print("\nUse 'python3 semlist.py activate <database_name>' to activate one of these.")
        return False

    # Update the configuration - store just the filename, not the full path
    config = ensure_config_exists()
    config["active_database"] = db_name

    if save_config(config):
        print(f"Successfully activated database '{name}'.")
        return True
    else:
        return False

def optimize_command(database_path=None):
    """Optimize the database to minimize the number of batches.

    This command reorganizes all emails to use the minimum number of batches
    possible while respecting the maximum of 58 emails per batch.

    When adding emails one at a time, you might end up with partially filled
    batches. This command consolidates all emails to maximize batch usage.
    """
    if database_path is None:
        database_path = get_active_database_path()

    data = read_mailing_list(database_path)
    if not data:
        return False

    original_batch_count = len(data["batches"])
    optimized_data = optimize_batches(data)

    if write_mailing_list(optimized_data, database_path):
        print(f"Successfully optimized the database from {original_batch_count} to {len(optimized_data['batches'])} batches.")
        return True
    else:
        return False

def display_help():
    """Display help information."""
    print("KU Math Seminar Mailing List Manager")
    print("\nUsage: python3 semlist.py [command] [arguments]")
    print("\nCommands:")
    print("  help, -h, --help                     Show this help information")
    print("  print all                            Print all emails in Outlook format for copying")
    print("  print [BATCH_NUMBER]                 Print emails from the specified batch")
    print("  batches                              Print the number of batches")
    print("  stat                                 Show statistics about the database")
    print("  add 'email@example.com'              Add a single email address")
    print("  add 'Name <email@example.com>'       Add an email with a name")
    print("  add 'Name1 <email1@...>; Name2 <email2@...>'  Add multiple emails")
    print("  rem email@example.com                Remove an email address from the database")
    print("  new DatabaseName                     Create a new database")
    print("  del DatabaseName                     Delete an existing database")
    print("  activate DatabaseName                Activate an existing database")
    print("  optimize                             Optimize batches (minimize number of batches)")
    print("  config                               Show current configuration")
    print("\nExample of batch optimization:")
    print("  If you have 3 batches with 30 emails each, running 'optimize'")
    print("  will consolidate them into 2 batches (58 emails in first batch,")
    print("  32 emails in second batch).")
    print("\nEmail format for Outlook:")
    print("  Emails are printed in the format: 'Name <email>;' which is compatible")
    print("  with Microsoft Outlook's expected format for recipients.")

def main():
    """Main entry point of the script."""
    args = parse_arguments()
    command = args.command.lower()

    if command == "print":
        if not args.args:
            print("Error: The 'print' command requires either 'all' or a batch number.")
            print("Use 'python3 semlist.py print all' to print all emails.")
            print("Use 'python3 semlist.py print [BATCH_NUMBER]' to print a specific batch.")
            return

        data = read_mailing_list()
        if data:
            print_emails(data, args.args[0], simple_format=True)

    elif command == "batches":
        data = read_mailing_list()
        if data and data.get("batches"):
            print(f"Number of batches: {len(data['batches'])}")
            for i, batch in enumerate(data["batches"], 1):
                print(f"  Batch {i}: {len(batch['emails'])} emails")
        else:
            print("No batches found in the database.")

    elif command == "help":
        display_help()

    elif command == "stat":
        show_statistics()

    elif command == "add" and len(args.args) > 0:
        # Check if the default database exists, if not, inform user to create one
        active_db = get_active_database_path()
        if not os.path.exists(active_db):
            print(f"Error: Active database file '{active_db}' does not exist.")

            # Check if there are any databases available
            existing_dbs = [f for f in os.listdir(DATABASE_FOLDER) if f.endswith('.json') and f != 'config.json']
            if existing_dbs:
                print("\nAvailable databases:")
                for db in existing_dbs:
                    print(f"  {db}")
                print("\nUse 'python3 semlist.py activate <database_name>' to activate one of these.")
            else:
                print("Use 'python3 semlist.py new DatabaseName' to create a new database.")
            return
        add_emails(args.args)

    elif command == "rem" and len(args.args) > 0:
        email = args.args[0]
        remove_email(email)

    elif command == "new" and len(args.args) > 0:
        name = args.args[0]
        create_new_database(name)

    elif command == "del" and len(args.args) > 0:
        name = args.args[0]
        delete_database(name)

    elif command == "activate" and len(args.args) > 0:
        name = args.args[0]
        activate_database(name)

    elif command == "optimize":
        optimize_command()

    elif command == "config":
        # Display current configuration
        config = ensure_config_exists()
        active_db_config = config.get('active_database', 'None')
        print("Current configuration:")
        print(f"Active database (in config): {active_db_config}")

        active_db_path = get_active_database_path()
        print(f"Full path being used: {active_db_path}")

        if os.path.exists(active_db_path):
            print("Database exists: Yes")
        else:
            print("Database exists: No - File not found")

            # List available databases
            existing_dbs = [f for f in os.listdir(DATABASE_FOLDER) if f.endswith('.json') and f != 'config.json']
            if existing_dbs:
                print("\nAvailable databases:")
                for db in existing_dbs:
                    print(f"  {db}")
                print("\nUse 'python3 semlist.py activate <database_name>' to activate one of these.")

    else:
        print("Invalid command or missing arguments.")
        print("Use 'python3 semlist.py help' for usage information.")

if __name__ == "__main__":
    main()