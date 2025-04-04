# Seminar mailer database utility

A command-line tool to manage the KU Math Seminar mailing list.

## Developer
Dr. Denys Dutykh (Mathematics Department, Khalifa University)

## Overview

Semmailer is a specialized command-line utility developed to efficiently manage email distribution lists for the KU Math Seminar. The tool offers advanced management features including:

- Storing emails in optimized batches (maximum 58 addresses per batch)
- Adding and removing contacts with proper name handling
- Creating and managing multiple mailing list databases
- Printing the full list or individual batches in Outlook-compatible format
- Statistics and optimization features

## Repository Structure

- `semlist.py` - Main Python script for managing mailing lists
- `MailingList.json` - Default database file containing email addresses
- `dbase/` - Directory for storing additional mailing list databases

## Installation

No special installation is required. Simply download the script and ensure you have Python 3.x installed.

```bash
git clone https://github.com/dutykh/semmailer.git
cd semmailer
```

## Usage Examples

### Get help

```bash
python3 semlist.py help                  # Display usage information
python3 semlist.py -h                    # Same as help
python3 semlist.py --help                # Same as help
python3 semlist.py print all             # Print all emails in Outlook format
python3 semlist.py print 1               # Print emails from batch 1
python3 semlist.py batches               # Show the number of batches
python3 semlist.py stat                  # Show statistics about the database
python3 semlist.py add 'email@example.com'   # Add a single email
python3 semlist.py rem email@example.com     # Remove an email
python3 semlist.py new DatabaseName      # Create a new database
python3 semlist.py del DatabaseName      # Delete a database
python3 semlist.py activate DatabaseName # Set active database
python3 semlist.py optimize              # Minimize number of batches
python3 semlist.py config                # Show configuration
```

### Print emails

```bash
python3 semlist.py print all             # Print all emails in Outlook format
python3 semlist.py print 1               # Print emails from batch 1
```

The emails are formatted as `Name <email>;` which works with Microsoft Outlook.

### Display database information

```bash
python3 semlist.py batches               # Show the number of batches and emails in each
python3 semlist.py stat                  # Show detailed statistics about the database
```

### Managing emails

```bash
python3 semlist.py add 'email@example.com'                     # Add a single email
python3 semlist.py add 'Name <email@example.com>'              # Add with name
python3 semlist.py add 'Name1 <email1@...>; Name2 <email2@...>' # Add multiple emails
python3 semlist.py rem email@example.com                       # Remove an email
```

### Database management

```bash
python3 semlist.py new DatabaseName      # Create a new database
python3 semlist.py del DatabaseName      # Delete a database (with confirmation)
python3 semlist.py activate DatabaseName # Set the active database
python3 semlist.py config                # Show current configuration
```

### Optimize batches

```bash
python3 semlist.py optimize
```

This reorganizes the entries to minimize the number of batches while respecting the maximum of 58 emails per batch. For example, if you have 3 batches with 30 emails each, running optimize will consolidate them into 2 batches (58 emails in first batch, 32 emails in second batch).

## Database Format

The mailing list is stored in JSON format with the following structure:

```json
{
  "name": "KU Math Seminar",
  "created": "2024-04-04",
  "last_modified": "2024-04-04",
  "batches": [
    {
      "id": 1,
      "emails": [
        {
          "email": "example@ku.ac.ae",
          "name": "Example Name",
          "full_entry": "Example Name <example@ku.ac.ae>;",
          "first_name": "Example",
          "middle_names": "",
          "last_name": "Name"
        }
      ]
    }
  ]
}
```

- Each batch contains up to 58 email entries
- Each entry stores the email, name, and original text format

## Requirements

- Python 3.x
- No external dependencies required

## License

[MIT License](LICENSE)