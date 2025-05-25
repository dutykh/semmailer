#!/usr/bin/env python3
"""
================================================================================
File:       semlist.py

Purpose:
    Command-line utility for managing the KU Math Seminar mailing list.
    Allows adding, removing, searching, printing, and batch-optimizing
    email lists stored in JSON format with Outlook compatibility.

Syntax:
    python3 semlist.py <command> [arguments]

    Example commands:
        python3 semlist.py help
        python3 semlist.py print all
        python3 semlist.py add 'John Doe <john@doe.com>'
        python3 semlist.py check 'pattern'
        python3 semlist.py optimize

Input Arguments:
    command (str): One of the supported commands (help, print, add, rem, check, etc.)
    arguments:     Command-specific arguments (see usage below)

Output:
    Prints results to terminal or saves to file (for print commands).
    Functions return True/False for success/failure, or print results directly.

Dependencies:
    - Python 3.x
    - Standard library only: os, sys, argparse, re, json, pathlib, datetime

Configuration:
    - All mailing list databases are stored in the 'dbase/' directory (JSON files)
    - The active database is tracked in 'dbase/config.json'
    - Maximum emails per batch: 57 (for Microsoft Outlook compatibility)

References:
    - Microsoft Outlook email import format
    - JSON mailing list schema (see README.md)

Author:
    Dr. Denys Dutykh
    Mathematics Department, Khalifa University of Science and Technology
    Abu Dhabi, UAE
    denys.dutykh@ku.ac.ae

Date:       April 21, 2025
Version:    1.1 (with regex search and improved documentation)
License:    GPL-3.0 ([https://www.gnu.org/licenses/gpl-3.0.en.html)](https://www.gnu.org/licenses/gpl-3.0.en.html))
================================================================================

Usage:
  python3 semlist.py help                            - Show this help information
  python3 semlist.py -h                              - Same as help
  python3 semlist.py --help                          - Same as help
  python3 semlist.py print all                       - Print all emails in Outlook format to screen
  python3 semlist.py print [BATCH_NUMBER]            - Print emails from specified batch to screen
  python3 semlist.py print all [FILENAME]            - Save all emails to a file (silent mode)
  python3 semlist.py print [BATCH_NUMBER] [FILENAME] - Save emails from specified batch to a file (silent mode)
  python3 semlist.py batches                         - Print the number of batches and emails in each
  python3 semlist.py stat                            - Show detailed statistics about the database
  python3 semlist.py check 'pattern'                 - Check emails matching a regex pattern
  python3 semlist.py add 'email@example.com'         - Add a single email address
  python3 semlist.py add 'Name <email@example.com>'  - Add an email with a name
  python3 semlist.py add 'Name1 <email1@...>; Name2 <email2@...>' - Add multiple emails
  python3 semlist.py rem email@example.com           - Remove an email address from the database
  python3 semlist.py new DatabaseName                - Create a new database
  python3 semlist.py del DatabaseName                - Delete an existing database (with confirmation)
  python3 semlist.py activate DatabaseName           - Activate an existing database
  python3 semlist.py optimize                        - Optimize batches (minimize number of batches)
  python3 semlist.py config                          - Show current configuration
"""

import os
import sys
import argparse
import re
import json
from datetime import datetime

# Constants
DEFAULT_DATABASE_NAME = "MailingList"
DATABASE_FOLDER = "dbase"
CONFIG_FILE = os.path.join(DATABASE_FOLDER, "config.json")
MAX_EMAILS_PER_BATCH = 57


def ensure_config_exists():
    """Ensure the configuration file exists."""
    if not os.path.exists(DATABASE_FOLDER):
        os.makedirs(DATABASE_FOLDER, exist_ok=True)

    if not os.path.exists(CONFIG_FILE):
        config = {"active_database": f"{DEFAULT_DATABASE_NAME}.json"}
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
        return config
    return get_config()


def get_config():
    """Get the configuration."""
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading configuration: {str(e)}")
        # Ensure we return the default if reading fails
        return {"active_database": f"{DEFAULT_DATABASE_NAME}.json"}


def save_config(config):
    """Save the configuration."""
    try:
        with open(CONFIG_FILE, "w") as f:
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
    # Handle cases where active_db might already contain the folder path
    db_filename = os.path.basename(active_db)
    return os.path.join(DATABASE_FOLDER, db_filename)


def parse_arguments():
    """Parse command-line arguments using argparse.

    Uses a custom approach to handle the 'help' command and its aliases
    ('-h', '--help') *before* involving argparse. This ensures that the
    custom `display_help` function (which prints the main docstring) is called
    for help requests, providing more detailed and formatted help than
    argparse's default.

    For all other commands, it uses argparse to identify the main command
    and collect any subsequent arguments associated with it.

    Returns:
        argparse.Namespace: An object containing the parsed command and its arguments.
                             - command (str): The main command entered by the user
                               (e.g., 'print', 'add', 'check').
                             - args (list): A list of strings representing all
                               arguments that followed the main command.
    """
    # --- Manual Help Check --- Priority handling for help requests.
    # Check if the second argument (index 1) is one of the help flags.
    # sys.argv[0] is the script name itself.
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help", "help"]:
        display_help()  # Call our custom help display function.
        sys.exit(0)  # Exit cleanly after displaying help.

    # --- Argparse for Other Commands ---
    # Initialize ArgumentParser. `add_help=False` disables argparse's automatic
    # -h/--help handling, as we've already handled it manually.
    parser = argparse.ArgumentParser(
        description="Command-line tool to manage the KU Math Seminar mailing list.",
        add_help=False,
    )
    # Define the mandatory 'command' positional argument.
    parser.add_argument(
        "command",
        help="The primary action to perform (e.g., print, add, check, new, etc.)",
    )
    # Define 'args' to capture all remaining positional arguments.
    # `nargs="*"` means it accepts zero or more arguments and collects them into a list.
    parser.add_argument(
        "args", nargs="*", help="Additional arguments required by the specific command."
    )

    # --- Handle No Command Case ---
    # If the script is called with no arguments other than its name.
    if len(sys.argv) == 1:
        display_help()  # Show help if the script is run without commands.
        sys.exit(0)  # Exit cleanly.

    # --- Parse Arguments ---
    try:
        # Let argparse parse the command line arguments based on the definitions above.
        parsed_args = parser.parse_args()
        return parsed_args
    except SystemExit:
        # This block might be reached if argparse encounters an error it can't handle
        # (though less likely with this simple setup). It prevents argparse from
        # exiting the script directly. We display our help and exit with an error code.
        display_help()
        sys.exit(1)  # Exit with a non-zero code indicating an error.


def display_help():
    """Display the detailed help message from the module's main docstring."""
    # Access the main docstring (__doc__) of the current module (this file)
    # and print it after removing leading/trailing whitespace.
    # This ensures the help message is always consistent with the documentation
    # at the top of the file.
    print(__doc__.strip())


def parse_email_entries(args_list):
    """Parse one or more email entries from a list of command-line arguments.

    This function is designed to be flexible and handle various common ways users
    might input email addresses and names, including multiple entries separated
    by semicolons. It robustly handles quotes and spacing.

    Supported Input Formats:
    - Plain email: 'email@example.com'
    - Name and email: '"First Last" <email@example.com>'
    - Simpler name and email: 'Name <email@example.com>'
    - Multiple entries in one string: '"Name1" <e1@ex.com>; Name2 <e2@ex.com>; e3@ex.com'
    - Multiple entries across arguments: `add "Name1 <e1@ex.com>;" "Name2 <e2@ex.com>"`

    Args:
        args_list (list): A list of strings received as arguments for the 'add' command.
                          These are typically the elements from `parsed_args.args`.

    Returns:
        list: A list of dictionaries, where each dictionary represents a successfully
              parsed email entry. Each dictionary contains:
                - 'email' (str): The extracted email address.
                - 'name' (str): The extracted full name (can be empty).
                - 'full_entry' (str): The reconstructed entry in a standardized format
                  (e.g., '"Name" <email@addr.com>;' or '<email@addr.com>;').
                - 'first_name' (str): Parsed first name.
                - 'middle_names' (str): Parsed middle name(s).
                - 'last_name' (str): Parsed last name.
              Returns an empty list if `args_list` is empty or if no valid entries
              could be parsed from the input.
    """
    # If no arguments were provided for the 'add' command, return an empty list.
    if not args_list:
        return []

    # --- Step 1: Combine and Split Entries ---
    # Join all arguments into a single string. This handles cases where a single
    # quoted argument might contain multiple semicolon-separated entries, or where
    # entries are spread across multiple arguments.
    input_str = " ".join(args_list)

    # Split the combined string by semicolons (;), but only if the semicolon is
    # *outside* of angle brackets (<...>). This prevents splitting email addresses
    # like '<local-part;@domain.com>'.
    entries = []
    current_entry = ""
    in_angle_brackets = False  # Flag to track if we are inside angle brackets.
    for char in input_str:
        if char == "<":
            in_angle_brackets = True
        elif char == ">":
            in_angle_brackets = False

        # Check for semicolon separator only when not inside angle brackets.
        if char == ";" and not in_angle_brackets:
            # If a semicolon separator is found, add the accumulated entry
            # (if not empty after stripping whitespace) to the list.
            if current_entry.strip():
                entries.append(current_entry.strip())
            current_entry = ""  # Reset to start accumulating the next entry.
        else:
            # Append the character to the current entry being built.
            current_entry += char

    # After the loop, add the last accumulated entry (if any).
    if current_entry.strip():
        entries.append(current_entry.strip())

    # --- Step 2: Parse Individual Entries ---
    parsed_entries = []
    # Define regular expressions for matching different email formats.
    # Basic email pattern (simplified, but covers common cases).
    email_pattern_core = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    # Pattern 1: Matches 'Optional Name <email@addr.com>'. Captures name and email.
    # - `^`: Start of string.
    # - `(.*?)`: Capture group 1: Any characters non-greedily (for the name).
    # - `\s*`: Zero or more whitespace characters.
    # - `<(` + email_pattern_core + `)>`: Capture group 2: The email address inside angle brackets.
    # - `$`: End of string.
    name_email_pattern = re.compile(r"^(.*?)\s*<(" + email_pattern_core + ")>$")
    # Pattern 2: Matches '<email@addr.com>'. Captures email.
    angle_email_pattern = re.compile(r"^<(" + email_pattern_core + ")>$")
    # Pattern 3: Matches 'email@addr.com'. Captures email.
    plain_email_pattern = re.compile(r"^(" + email_pattern_core + ")$")

    # Iterate through the strings extracted in Step 1.
    for entry_text in entries:
        # Store the original text for potential warning messages.
        original_entry = entry_text
        # Remove leading/trailing whitespace and potential surrounding quotes.
        entry = entry_text.strip(" '\"")

        # Attempt to match each pattern in order of complexity.
        # 1. Check for 'Name <email>' format.
        match = name_email_pattern.match(entry)
        if match:
            # Group 1 is the name part, group 2 is the email.
            full_name = match.group(1).strip(" '\"")  # Clean quotes/spaces from name.
            email = match.group(2).strip()  # Email part.
            # Parse the extracted name into components.
            name_components = parse_name(full_name)
            # Construct the standardized entry string.
            standard_entry = f'"{full_name}" <{email}>;' if full_name else f"<{email}>;"
            parsed_entries.append(
                {
                    "email": email,
                    "name": full_name,
                    "full_entry": standard_entry,  # Store the standardized format.
                    **name_components,  # Merge first/middle/last name dict.
                }
            )
            continue  # Successfully parsed, move to the next entry string.

        # 2. Check for '<email>' format.
        match = angle_email_pattern.match(entry)
        if match:
            # Group 1 is the email.
            email = match.group(1).strip()
            # No name present.
            parsed_entries.append(
                {
                    "email": email,
                    "name": "",
                    "full_entry": f"<{email}>;",  # Standardized format.
                    "first_name": "",
                    "middle_names": "",
                    "last_name": "",
                }
            )
            continue  # Parsed successfully.

        # 3. Check for plain 'email' format.
        match = plain_email_pattern.match(entry)
        if match:
            # Group 1 is the email.
            email = match.group(1).strip()
            # No name present.
            parsed_entries.append(
                {
                    "email": email,
                    "name": "",
                    "full_entry": f"<{email}>;",  # Store in standard format internally.
                    "first_name": "",
                    "middle_names": "",
                    "last_name": "",
                }
            )
            continue  # Parsed successfully.

        # --- Handle Unparseable Entries ---
        # If none of the patterns matched the current entry string.
        print(
            f"Warning: Could not parse entry format: '{original_entry}' - Skipping this entry."
        )

    # Return the list of successfully parsed email dictionaries.
    return parsed_entries


def parse_name(full_name):
    """Parse a full name string into first, middle, and last name components.

    Assumes names are separated by spaces. Handles single names (as first name),
    two-part names (as first and last), and names with three or more parts
    (as first, middle(s), and last).

    Args:
        full_name (str): The full name string (e.g., "Denys Dutykh",
                         "John Fitzgerald Kennedy", "Cher").

    Returns:
        dict: A dictionary containing the parsed components:
              - 'first_name' (str)
              - 'middle_names' (str): Contains all middle parts joined by space, or empty.
              - 'last_name' (str)
    """
    # Clean the input name: remove leading/trailing whitespace and quotes.
    name = full_name.strip(" '\"")
    # If the name is empty after cleaning, return empty components.
    if not name:
        return {"first_name": "", "middle_names": "", "last_name": ""}

    # Split the cleaned name into parts based on spaces.
    name_parts = name.split()
    num_parts = len(name_parts)

    # Determine components based on the number of parts.
    if num_parts == 1:
        # Assume a single part is the first name.
        return {"first_name": name_parts[0], "middle_names": "", "last_name": ""}
    elif num_parts == 2:
        # Assume two parts are first and last name.
        return {
            "first_name": name_parts[0],
            "middle_names": "",
            "last_name": name_parts[1],
        }
    else:  # 3 or more parts
        # Assume the first part is the first name,
        # the last part is the last name,
        # and everything in between constitutes the middle name(s).
        return {
            "first_name": name_parts[0],
            "middle_names": " ".join(name_parts[1:-1]),  # Join middle parts with space.
            "last_name": name_parts[-1],
        }


def convert_txt_to_json(txt_path, json_path=None):
    """Convert a text-based mailing list to JSON format."""
    if json_path is None:
        json_path = txt_path.replace(".txt", ".json")

    if not os.path.exists(txt_path):
        print(f"Error: Text database file '{txt_path}' does not exist.")
        return False

    batches = []
    current_batch = []

    try:
        with open(txt_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
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
                        current_batch.append(
                            {
                                "email": email,
                                "name": name,
                                "full_entry": line,
                                **name_components,
                            }
                        )

            # Add the last batch if it's not empty
            if current_batch:
                batches.append(current_batch)

        # Create JSON structure
        json_data = {
            "name": "KU Math Seminar",
            "created": datetime.now().strftime("%Y-%m-%d"),
            "last_modified": datetime.now().strftime("%Y-%m-%d"),
            "batches": [],
        }

        for i, batch_emails in enumerate(batches, 1):
            json_data["batches"].append({"id": i, "emails": batch_emails})

        # Write JSON data
        with open(json_path, "w") as f:
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
        batch_stats.append({"id": batch["id"], "count": batch_count})

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
                    print(
                        f"Email '{name} <{email}>' has been removed from the database."
                    )
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
    match = re.search(r"<([^>]+)>", line)
    if match:
        return match.group(1).strip()

    # If no <> format, try to find an email pattern
    match = re.search(r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", line)
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
    match = re.search(r"^([^<]+)<", line)
    if match:
        name = match.group(1).strip()
        if name.endswith(";"):
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
        with open(database_path, "r") as f:
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
        with open(database_path, "w") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"Error writing to database: {str(e)}")
        return False


def optimize_batches(data, max_per_batch=57):
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
            optimized_batches.append(
                {"id": len(optimized_batches) + 1, "emails": current_batch}
            )
            current_batch = []
        current_batch.append(email_entry)

    # Add the last batch if it's not empty
    if current_batch:
        optimized_batches.append(
            {"id": len(optimized_batches) + 1, "emails": current_batch}
        )

    # Update the data with optimized batches
    data["batches"] = optimized_batches
    return data


def print_emails(data, batch_number=None, simple_format=False, output_file=None):
    """Print emails in batches.

    Args:
        data: The database data
        batch_number: If provided, print only this batch number
        simple_format: If True, print only the email addresses in a simple format for copying
        output_file: If provided, write output to this file instead of the console
    """
    # If we're writing to a file, we don't want any console output
    if output_file:
        try:
            with open(output_file, "w") as f:
                # Process the requested batch
                if batch_number == "all":
                    # Write all batches to file
                    for i, batch in enumerate(data["batches"], 1):
                        if i == 1:
                            f.write(f"=== Batch {i} ===\n\n")
                        else:
                            f.write(f"\n=== Batch {i} ===\n\n")
                        for j, entry in enumerate(batch["emails"]):
                            # Format for Outlook: First name Last name <email>;
                            first = entry.get("first_name", "")
                            last = entry.get("last_name", "")
                            name = f"{first} {last}".strip()
                            if not name:
                                name = entry.get("name", "")

                            # Don't add semicolon to the last email in the batch
                            if j == len(batch["emails"]) - 1:
                                f.write(f"{name} <{entry['email']}>")
                            else:
                                f.write(f"{name} <{entry['email']}>;")
                            f.write("\n")

                elif batch_number is not None:
                    try:
                        batch_num = int(batch_number)
                        # Check if the batch exists
                        if batch_num < 1 or batch_num > len(data["batches"]):
                            print(f"Error: Batch {batch_num} does not exist.")
                            print(f"Available batches: 1 to {len(data['batches'])}")
                            return

                        # Write the requested batch to file
                        batch = data["batches"][batch_num - 1]
                        f.write(f"=== Batch {batch_num} ===\n\n")
                        for j, entry in enumerate(batch["emails"]):
                            # Format for Outlook: First name Last name <email>;
                            first = entry.get("first_name", "")
                            last = entry.get("last_name", "")
                            name = f"{first} {last}".strip()
                            if not name:
                                name = entry.get("name", "")

                            # Don't add semicolon to the last email in the batch
                            if j == len(batch["emails"]) - 1:
                                f.write(f"{name} <{entry['email']}>")
                            else:
                                f.write(f"{name} <{entry['email']}>;")
                            f.write("\n")

                    except ValueError:
                        print(f"Error: Invalid batch number '{batch_number}'.")
                        return

                else:
                    # Write summary and all batches in detailed format
                    total_entries = sum(
                        len(batch["emails"]) for batch in data["batches"]
                    )
                    f.write(f"Database: {data.get('name', 'Unknown')}\n")
                    f.write(f"Last modified: {data.get('last_modified', 'Unknown')}\n")
                    f.write(
                        f"Found {total_entries} entries in {len(data['batches'])} batches:\n"
                    )

                    for i, batch in enumerate(data["batches"], 1):
                        if i == 1:
                            f.write(f"\n=== Batch {i} ===\n\n")
                        else:
                            f.write(f"\n=== Batch {i} ===\n\n")
                        for j, entry in enumerate(batch["emails"]):
                            # Don't add semicolon to the last email in the batch
                            full_entry = entry.get(
                                "full_entry",
                                f"{entry.get('name', '')} <{entry['email']}>",
                            )
                            if ";" in full_entry and j == len(batch["emails"]) - 1:
                                full_entry = full_entry.replace(";", "")

                            f.write(f"  {full_entry.strip()}\n")

                            # Optionally show name components
                            first = entry.get("first_name", "")
                            middle = entry.get("middle_names", "")
                            last = entry.get("last_name", "")
                            if first or middle or last:
                                f.write(
                                    f"    First: {first}, Middle: {middle}, Last: {last}\n"
                                )

            # Only print success message after closing the file
            print(f"Successfully wrote to '{output_file}'.")
            return

        except Exception as e:
            print(f"Error opening file '{output_file}' for writing: {str(e)}")
            return

    # Console output (only when no output_file is specified)
    if not data:
        print("No data found in the database.")
        return

    if not data.get("batches"):
        print("No batches found in the database.")
        return

    # If a specific batch is requested
    if batch_number is not None:
        if batch_number == "all":
            # Print all batches in simple format
            for i, batch in enumerate(data["batches"], 1):
                print(f"\n=== Batch {i} ===\n")
                for j, entry in enumerate(batch["emails"]):
                    # Format for Outlook: First name Last name <email>;
                    first = entry.get("first_name", "")
                    last = entry.get("last_name", "")
                    name = f"{first} {last}".strip()
                    if not name:
                        name = entry.get("name", "")

                    # Don't add semicolon to the last email in the batch
                    if j == len(batch["emails"]) - 1:
                        print(f"{name} <{entry['email']}>")
                    else:
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
                for j, entry in enumerate(batch["emails"]):
                    # Format for Outlook: First name Last name <email>;
                    first = entry.get("first_name", "")
                    last = entry.get("last_name", "")
                    name = f"{first} {last}".strip()
                    if not name:
                        name = entry.get("name", "")

                    # Don't add semicolon to the last email in the batch
                    if j == len(batch["emails"]) - 1:
                        print(f"{name} <{entry['email']}>")
                    else:
                        print(f"{name} <{entry['email']}>;")
            else:
                for j, entry in enumerate(batch["emails"]):
                    # Don't add semicolon to the last email in the batch
                    full_entry = entry.get(
                        "full_entry", f"{entry.get('name', '')} <{entry['email']}>"
                    )
                    if ";" in full_entry and j == len(batch["emails"]) - 1:
                        full_entry = full_entry.replace(";", "")

                    print(f"  {full_entry.strip()}")

                    # Optionally show name components
                    first = entry.get("first_name", "")
                    middle = entry.get("middle_names", "")
                    last = entry.get("last_name", "")
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
        if i == 1:
            print(f"\n=== Batch {i} ===\n")
        else:
            print(f"\n=== Batch {i} ===\n")
        for j, entry in enumerate(batch["emails"]):
            # Don't add semicolon to the last email in the batch
            full_entry = entry.get(
                "full_entry", f"{entry.get('name', '')} <{entry['email']}>"
            )
            if ";" in full_entry and j == len(batch["emails"]) - 1:
                full_entry = full_entry.replace(";", "")

            print(f"  {full_entry.strip()}")

            # Optionally show name components
            first = entry.get("first_name", "")
            middle = entry.get("middle_names", "")
            last = entry.get("last_name", "")
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
        full_entry = f"<{email}>;"

    new_entry = {
        "email": email,
        "name": name,
        "full_entry": full_entry,
        "first_name": entry.get("first_name", ""),
        "middle_names": entry.get("middle_names", ""),
        "last_name": entry.get("last_name", ""),
    }

    # Add to the last batch if it exists and has room, otherwise create a new batch
    if data["batches"] and len(data["batches"][-1]["emails"]) < MAX_EMAILS_PER_BATCH:
        data["batches"][-1]["emails"].append(new_entry)
    else:
        data["batches"].append({"id": len(data["batches"]) + 1, "emails": [new_entry]})

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


def optimize_command(database_path=None):
    """Reorganize emails to use the minimum number of batches.

    This command reorganizes all emails to use the minimum number of batches
    possible while respecting the maximum of 57 emails per batch.

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
        print(
            f"Successfully optimized the database from {original_batch_count} to {len(optimized_data['batches'])} batches."
        )
        return True
    else:
        return False


def load_database(db_path):
    """Load the database from the specified JSON file."""
    if not os.path.exists(db_path):
        print(f"Error: Database file '{db_path}' not found.")
        return None
    try:
        with open(db_path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading database: {str(e)}")
        return None


def get_all_emails(db_path):
    """Get all emails from the database."""
    data = load_database(db_path)
    if not data:
        return []

    all_emails = []
    for batch in data["batches"]:
        all_emails.extend(batch["emails"])
    return all_emails


def check_emails(pattern):
    """Check emails in the active database matching the regex pattern."""
    db_path = get_active_database_path()
    db_data = load_database(db_path)
    if db_data is None:
        return

    all_emails = get_all_emails(db_path)  # Reuse existing function to get flat list
    found_matches = False

    print(
        f"Checking for pattern '{pattern}' in database '{os.path.basename(db_path)}':"
    )

    try:
        regex = re.compile(pattern, re.IGNORECASE)  # Case-insensitive search
    except re.error as e:
        print(f"Error: Invalid regular expression: {e}")
        return

    for entry in all_emails:
        # Check against the email address and the full entry string
        if regex.search(entry.get("email", "")) or regex.search(
            entry.get("full_entry", "")
        ):
            print(f"  Match found: {entry.get('full_entry', entry.get('email'))}")
            found_matches = True

    if not found_matches:
        print("  No matches found.")


def create_new_database(db_name):
    """Create a new, empty database file with basic structure and metadata.

    Ensures the database directory exists, prevents overwriting existing files,
    and initializes the JSON with name, creation/modification dates, and an
    empty batches list.

    Args:
        db_name (str): The desired base name for the database (e.g., "MyList").
                       The '.json' extension will be added automatically if missing.
                       Should not contain path separators.

    Returns:
        bool: True if the database file was created successfully, False otherwise.
    """
    # Sanitize the provided name: remove leading/trailing whitespace and path components.
    safe_db_name = os.path.basename(db_name.strip())
    if not safe_db_name:
        print("Error: Invalid or empty database name provided.")
        return False

    # Ensure the filename ends with '.json'.
    if not safe_db_name.endswith(".json"):
        db_filename = f"{safe_db_name}.json"
    else:
        db_filename = safe_db_name

    # Construct the full path within the designated DATABASE_FOLDER.
    db_path = os.path.join(DATABASE_FOLDER, db_filename)

    # --- Prevent Overwriting --- Check if a file with this name already exists.
    if os.path.exists(db_path):
        print(
            f"Error: Database '{db_filename}' already exists in '{DATABASE_FOLDER}'. Use a different name or delete the existing file first."
        )
        return False

    # --- Initial Database Structure ---
    # Define the content for the new JSON database file.
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # More precise timestamp
    new_db_content = {
        "name": safe_db_name,  # Use the cleaned base name.
        "created": now_str,
        "last_modified": now_str,
        "batches": [],  # Initialize with an empty list of batches.
    }

    # --- Write to File ---
    try:
        # Ensure the DATABASE_FOLDER directory exists before writing the file.
        os.makedirs(DATABASE_FOLDER, exist_ok=True)
        # Write the initial structure to the new file using UTF-8 encoding.
        with open(db_path, "w", encoding="utf-8") as f:
            json.dump(new_db_content, f, indent=2)  # Use indent for readability.
        print(f"Database '{db_filename}' created successfully in '{DATABASE_FOLDER}'.")
        return True
    except IOError as e:
        # Handle potential file system errors during writing.
        print(f"Error creating database file '{db_path}': {e}")
        return False
    except Exception as e:
        # Catch any other unexpected errors.
        print(f"An unexpected error occurred during database creation: {e}")
        return False


def delete_database(db_name):
    """Delete an existing database file after explicit user confirmation.

    Prompts the user for confirmation before proceeding. If the deleted database
    was the currently active one, it resets the active database in the config
    to the default and ensures the default database file exists.

    Args:
        db_name (str): The name of the database to delete (e.g., "MyList" or
                       "MyList.json").

    Returns:
        bool: True if deletion was confirmed and successful, False otherwise
              (including cancellation by the user or errors).
    """
    # Sanitize the input name.
    safe_db_name = os.path.basename(db_name.strip())
    if not safe_db_name:
        print("Error: Invalid or empty database name provided.")
        return False

    # Ensure the filename ends with '.json'.
    if not safe_db_name.endswith(".json"):
        db_filename = f"{safe_db_name}.json"
    else:
        db_filename = safe_db_name

    # Construct the full path.
    db_path = os.path.join(DATABASE_FOLDER, db_filename)

    # --- Check Existence --- Ensure the file to be deleted actually exists.
    if not os.path.exists(db_path):
        print(
            f"Error: Database '{db_filename}' not found in '{DATABASE_FOLDER}'. Cannot delete."
        )
        return False

    # --- Critical Safety Check: User Confirmation ---
    # Prevent accidental deletion by requiring explicit confirmation.
    try:
        # Use a clear prompt.
        confirm = input(
            f"!!! WARNING !!!\nAre you sure you want to PERMANENTLY delete the database '{db_filename}'? \nThis action cannot be undone. (Type 'yes' to confirm): "
        )
        # Only proceed if the user types exactly 'yes'.
        if confirm.strip().lower() != "yes":
            print("Deletion cancelled by user.")
            return False
    except EOFError:  # Handle potential script interruption during input.
        print("\nDeletion cancelled (input interrupted).")
        return False

    # --- Proceed with Deletion ---
    try:
        os.remove(db_path)
        print(f"Database '{db_filename}' deleted successfully.")

        # --- Update Config if Active DB was Deleted ---
        config = get_config()
        # Check if the deleted database filename matches the active one in config.
        if config.get("active_database") == db_filename:
            default_db_filename = f"{DEFAULT_DATABASE_NAME}.json"
            print("Warning: The deleted database was the active one.")
            print(f"Resetting active database to default: '{default_db_filename}'.")
            config["active_database"] = default_db_filename
            # Ensure the default database file actually exists; create if not.
            default_db_path = os.path.join(DATABASE_FOLDER, default_db_filename)
            if not os.path.exists(default_db_path):
                print(
                    f"Default database '{default_db_filename}' not found. Creating it."
                )
                # Reuse the create function; ignore return value here as we prioritize saving config.
                create_new_database(DEFAULT_DATABASE_NAME)
            # Save the updated configuration pointing to the default DB.
            save_config(config)

        return True
    except OSError as e:
        # Handle errors during file removal (e.g., permissions).
        print(f"Error deleting database file '{db_path}': {e}")
        return False
    except Exception as e:
        # Catch other unexpected errors.
        print(f"An unexpected error occurred during database deletion: {e}")
        return False


def activate_database(db_name):
    """Set the specified database as the active one in the configuration file.

    Verifies that the target database file exists before updating the config.

    Args:
        db_name (str): The name of the database to activate (e.g., "MyList" or
                       "MyList.json").

    Returns:
        bool: True if the database exists and the configuration was successfully
              updated, False otherwise.
    """
    # Sanitize the input name.
    safe_db_name = os.path.basename(db_name.strip())
    if not safe_db_name:
        print("Error: Invalid or empty database name provided.")
        return False

    # Ensure the filename ends with '.json'.
    if not safe_db_name.endswith(".json"):
        db_filename = f"{safe_db_name}.json"
    else:
        db_filename = safe_db_name

    # Construct the full path.
    db_path = os.path.join(DATABASE_FOLDER, db_filename)

    # --- Check Existence --- Crucial: Only activate a database that actually exists.
    if not os.path.exists(db_path):
        print(
            f"Error: Database '{db_filename}' not found in '{DATABASE_FOLDER}'. Cannot activate."
        )
        print(f"Available databases can be found in the '{DATABASE_FOLDER}' directory.")
        return False

    # --- Update Configuration ---
    # Load current config (ensure_config_exists handles creation if needed).
    config = ensure_config_exists()
    # Update the 'active_database' key with the validated filename.
    config["active_database"] = db_filename

    # Attempt to save the updated configuration.
    if save_config(config):
        print(f"Database '{db_filename}' is now the active database.")
        return True
    else:
        # `save_config` will print a specific error message.
        print(f"Failed to update configuration to activate database '{db_filename}'.")
        return False


def add_emails_to_database(emails_to_add):
    """Add a list of parsed email entries to the currently active database.

    Handles adding emails efficiently:
    - Checks for duplicates (case-insensitive) against existing emails.
    - Adds new emails to the first available batch with space.
    - Creates new batches if all existing ones are full.
    - Updates the 'last_modified' timestamp in the database.
    - Handles cases where the active database doesn't exist (tries to create default).

    Args:
        emails_to_add (list): A list of email dictionaries, typically the output
                              of `parse_email_entries`.

    Returns:
        bool: True if the database was successfully loaded, modified (if needed),
              and saved. False if any critical error occurred (e.g., cannot load,
              cannot create default, cannot save).
    """
    # If the input list is empty, there's nothing to add.
    if not emails_to_add:
        print("No valid email entries provided to add.")
        # Return True as it's not an error state, just no action taken.
        return True

    # --- Load Active Database ---
    db_path = get_active_database_path()
    db_data = load_database(db_path)

    # --- Handle Missing/Invalid Database --- Special case for default DB.
    if db_data is None:
        active_db_filename = os.path.basename(db_path)
        default_db_filename = f"{DEFAULT_DATABASE_NAME}.json"
        # If the *default* database is the active one but is missing/invalid,
        # attempt to create it automatically.
        if active_db_filename == default_db_filename:
            print(
                f"Default database '{default_db_filename}' not found or invalid. Attempting to create it."
            )
            if create_new_database(DEFAULT_DATABASE_NAME):
                db_data = load_database(db_path)  # Try loading again after creation.
                if db_data is None:
                    # If it still fails after creation, something is wrong.
                    print("Error: Failed to load the newly created default database.")
                    return False
            else:
                # If creation itself failed.
                print(
                    "Error: Failed to create the default database. Cannot add emails."
                )
                return False
        else:
            # If a *non-default* active database is missing/invalid, guide the user.
            print(
                f"Error: Active database '{active_db_filename}' not found or is invalid."
            )
            print(
                f"Cannot add emails. Please check the file in '{DATABASE_FOLDER}' or activate/create a valid database:"
            )
            print(
                f"  - Create: python3 semlist.py new {active_db_filename[:-5]}  (if it should be new)"
            )
            print("  - Activate: python3 semlist.py activate <ExistingDBName>")
            return False

    # --- Prepare for Duplicate Checking ---
    # Create a set of existing email addresses (lowercase for case-insensitivity)
    # for efficient duplicate checking.
    existing_emails_lower = set()
    for batch in db_data.get("batches", []):
        for email_entry in batch.get("emails", []):
            email = email_entry.get("email")
            if email:
                existing_emails_lower.add(email.lower())

    # --- Filter New Emails --- Separate actual new entries from duplicates/invalid.
    newly_added_entries = []  # List to hold only the entries that will be added.
    added_count = 0
    skipped_count = 0
    for new_entry in emails_to_add:
        email_addr = new_entry.get("email")
        # Check if the email exists and if its lowercase version is not in the set.
        if email_addr and email_addr.lower() not in existing_emails_lower:
            newly_added_entries.append(new_entry)
            # Add to the set immediately to handle duplicates *within* the input list itself.
            existing_emails_lower.add(email_addr.lower())
            added_count += 1
        elif email_addr:  # Email exists but is a duplicate.
            print(f"Skipping duplicate: {email_addr}")
            skipped_count += 1
        else:  # Entry lacks an email address (shouldn't happen with proper parsing).
            print(
                f"Warning: Skipping entry with missing email address: {new_entry.get('full_entry', 'Invalid Entry')}"
            )
            skipped_count += 1

    # If, after filtering, there are no new emails to add, report and exit.
    if not newly_added_entries:
        print(
            "No new emails to add."
            + (
                f" Skipped {skipped_count} duplicate/invalid entries."
                if skipped_count > 0
                else ""
            )
        )
        return True  # Still considered a successful operation (no changes needed).

    # --- Add Filtered Emails to Batches ---
    # Ensure 'batches' list exists in the database dictionary.
    batches = db_data.setdefault("batches", [])

    for email_to_add in newly_added_entries:
        added_to_existing_batch = False
        # Iterate through existing batches to find one with space.
        for batch in batches:
            # Ensure the 'emails' list exists within the batch dictionary.
            batch_emails = batch.setdefault("emails", [])
            # Check if the current batch is below the maximum size limit.
            if len(batch_emails) < MAX_EMAILS_PER_BATCH:
                batch_emails.append(email_to_add)
                added_to_existing_batch = True
                break  # Email added, move to the next email_to_add.

        # If the email wasn't added to any existing batch (all were full),
        # create a new batch for it.
        if not added_to_existing_batch:
            # Determine the ID for the new batch. Find the max existing ID and add 1.
            # Handle the case of no existing batches ([0] ensures max works).
            new_batch_id = max([b.get("id", 0) for b in batches] + [0]) + 1
            new_batch = {
                "id": new_batch_id,
                "emails": [email_to_add],  # Start the new batch with this email.
            }
            batches.append(new_batch)
            print(
                f"Created new batch (ID: {new_batch_id}) for {email_to_add.get('email')}."
            )

    # --- Finalize and Save --- Update timestamp and write back to the file.
    db_data["last_modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        with open(db_path, "w", encoding="utf-8") as f:
            json.dump(db_data, f, indent=2)
        print(
            f"Successfully added {added_count} new email(s) to '{os.path.basename(db_path)}'."
        )
        if skipped_count > 0:
            print(f"(Skipped {skipped_count} duplicate/invalid entries.)")
        return True
    except IOError as e:
        print(f"Error writing updated database file '{db_path}': {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred while saving the database: {e}")
        return False


def remove_email_from_database(email_to_remove):
    """Remove an email address (case-insensitive) from the active database.

    Searches all batches for the specified email address. If found, removes the
    entire email entry dictionary. If removing an email results in an empty batch,
    that batch is also removed. Updates the 'last_modified' timestamp.

    Args:
        email_to_remove (str): The email address to search for and remove.

    Returns:
        bool: True if the email was found and removed, and the database was saved
              successfully. False if the email was not found, or if any error
              occurred during loading or saving.
    """
    # Basic validation of the input email.
    if not email_to_remove or "@" not in email_to_remove:
        print("Error: Invalid or empty email address provided for removal.")
        return False

    # --- Load Database ---
    db_path = get_active_database_path()
    db_data = load_database(db_path)

    if db_data is None:
        # If loading failed, load_database already printed an error.
        print(
            f"Error: Cannot remove email. Active database '{os.path.basename(db_path)}' could not be loaded."
        )
        return False

    # --- Search and Remove ---
    found_and_removed = False
    email_to_remove_lower = email_to_remove.lower()  # For case-insensitive comparison.
    batches = db_data.get("batches", [])
    # Keep track of batches that become empty after removal.
    indices_of_empty_batches = []

    # Iterate through each batch using index for potential removal.
    for i, batch in enumerate(batches):
        emails_in_batch = batch.get("emails", [])
        initial_count = len(emails_in_batch)

        # Create a new list containing only the emails that *don't* match the one to remove.
        updated_emails = [
            entry
            for entry in emails_in_batch
            if entry.get("email", "").lower() != email_to_remove_lower
        ]

        # Check if the length changed, indicating a removal occurred.
        if len(updated_emails) < initial_count:
            batch["emails"] = updated_emails  # Update the batch with the filtered list.
            found_and_removed = True
            print(f"Removed '{email_to_remove}' from batch {batch.get('id', 'N/A')}.")
            # If the batch is now empty, mark its index for removal later.
            if not updated_emails:
                indices_of_empty_batches.append(i)
            # Optimization: If we only expect one instance, we could break here.
            # Assuming duplicates are possible or we want to remove all instances,
            # we continue searching other batches.

    # --- Handle Email Not Found ---
    if not found_and_removed:
        print(f"Email '{email_to_remove}' not found in the database.")
        return False  # Return False as no change was made.

    # --- Remove Empty Batches ---
    # Remove empty batches by rebuilding the list, excluding the marked indices.
    # Iterating backwards by index or rebuilding is safer than removing while iterating.
    if indices_of_empty_batches:
        print(f"Removing {len(indices_of_empty_batches)} batch(es) that became empty.")
        # Create a new list containing only non-empty batches.
        updated_batches = [
            batch
            for idx, batch in enumerate(batches)
            if idx not in indices_of_empty_batches
        ]
        db_data["batches"] = updated_batches
        # Optional: Re-assign batch IDs sequentially after removing empty ones?
        # For simplicity, we currently keep original IDs.

    # --- Finalize and Save ---
    db_data["last_modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        with open(db_path, "w", encoding="utf-8") as f:
            json.dump(db_data, f, indent=2)
        print(f"Database '{os.path.basename(db_path)}' updated successfully.")
        return True
    except IOError as e:
        print(f"Error writing updated database file '{db_path}': {e}")
        return False
    except Exception as e:
        print(
            f"An unexpected error occurred while saving the database after removal: {e}"
        )
        return False


def main():
    """Main entry point of the script."""
    args = parse_arguments()
    command = args.command.lower()

    if command == "print":
        if not args.args:
            print("Error: The 'print' command requires either 'all' or a batch number.")
            print("Use 'python3 semlist.py print all' to print all emails.")
            print(
                "Use 'python3 semlist.py print [BATCH_NUMBER]' to print a specific batch."
            )
            return

        # Check if we have an output file specified
        batch_number = args.args[0]
        output_file = None
        if len(args.args) > 1:
            output_file = args.args[1]

        data = read_mailing_list()
        if data:
            print_emails(
                data, batch_number, simple_format=True, output_file=output_file
            )

    elif command == "batches":
        data = read_mailing_list()
        if data and data.get("batches"):
            print(f"Number of batches: {len(data['batches'])}")
            for i, batch in enumerate(data["batches"], 1):
                print(f"  Batch {i}: {len(batch['emails'])} emails")
        else:
            print("No batches found in the database.")

    elif command == "stat":
        show_statistics()

    elif command == "check":
        if not args.args:
            print("Error: 'check' command requires a regex pattern.")
            display_help()
            sys.exit(1)
        pattern = " ".join(args.args)  # Join args in case pattern has spaces
        check_emails(pattern)

    elif command == "add" and len(args.args) > 0:
        # Check if the default database exists, if not, inform user to create one
        active_db = get_active_database_path()
        if not os.path.exists(active_db):
            print(f"Error: Active database file '{active_db}' does not exist.")

            # Check if there are any databases available
            existing_dbs = [
                f
                for f in os.listdir(DATABASE_FOLDER)
                if f.endswith(".json") and f != "config.json"
            ]
            if existing_dbs:
                print("\nAvailable databases:")
                for db in existing_dbs:
                    print(f"  {db}")
                print(
                    "\nUse 'python3 semlist.py activate <database_name>' to activate one of these."
                )
            else:
                print(
                    "Use 'python3 semlist.py new DatabaseName' to create a new database."
                )
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
        active_db_config = config.get("active_database", "None")
        print("Current configuration:")
        print(f"Active database (in config): {active_db_config}")

        active_db_path = get_active_database_path()
        print(f"Full path being used: {active_db_path}")

        if os.path.exists(active_db_path):
            print("Database exists: Yes")
        else:
            print("Database exists: No - File not found")

            # List available databases
            existing_dbs = [
                f
                for f in os.listdir(DATABASE_FOLDER)
                if f.endswith(".json") and f != "config.json"
            ]
            if existing_dbs:
                print("\nAvailable databases:")
                for db in existing_dbs:
                    print(f"  {db}")
                print(
                    "\nUse 'python3 semlist.py activate <database_name>' to activate one of these."
                )

    else:
        print("Invalid command or missing arguments.")
        print("Use 'python3 semlist.py help' for usage information.")


if __name__ == "__main__":
    main()
