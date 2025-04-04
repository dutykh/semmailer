### Show current configuration

```bash
python3 semlist.py config
```

Displays the current active database and checks if it exists.# Semmailer

A command-line tool to manage the KU Math Seminar mailing list.

## Developer
Dr. Denys Dutykh
Mathematics Department, Khalifa University

## Overview

Semmailer helps you organize and manage email distribution lists, with specific support for:
- Storing emails in optimized batches (maximum 58 addresses per batch)
- Adding new contacts
- Creating new mailing list databases
- Printing the full list or individual batches

## Repository Structure

- `semlist.py` - Main Python script for managing mailing lists
- `MailingList.json` - Default database file containing email addresses (JSON format)
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
```

### Print emails

```bash
python3 semlist.py print all             # Print all emails in simple format for copying
python3 semlist.py print 1               # Print emails from batch 1
```

### Display batch information

```bash
python3 semlist.py batches               # Show the number of batches
```

### Add a new email address

```bash
python3 semlist.py add 'email@example.com'
python3 semlist.py add 'Name <email@example.com>'
python3 semlist.py add 'Name <email@example.com>;'
```

You can add multiple emails at once:

```bash
python3 semlist.py add 'Name1 <email1@example.com>; Name2 <email2@example.com>'
```

First, middle, and last name handling:

```bash
python3 semlist.py add 'First Last <email@example.com>'
python3 semlist.py add 'First Middle Last <email@example.com>'
```

### Create a new database

```bash
python3 semlist.py new KUMathSeminar
```

This creates a new empty database file in the `dbase/` folder.

### Optimize batches

```bash
python3 semlist.py optimize
```

This reorganizes the entries to minimize the number of batches while respecting the maximum of 58 emails per batch.

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