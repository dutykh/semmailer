# Seminar mailer database utility

A command-line tool to manage the KU Math Seminar mailing list.

## Developer

**Dr. Denys Dutykh**  
Mathematics Department  
Khalifa University of Science and Technology  
Abu Dhabi, UAE

## Overview

Semmailer is a specialized command-line utility developed to efficiently manage email distribution lists for the KU Math Seminar. The tool offers advanced management features including:

- Storing emails in optimized batches (maximum 57 addresses per batch)
- Adding and removing contacts with proper name handling
- Creating and managing multiple mailing list databases
- Printing the full list or individual batches in Outlook-compatible format
- Silent mode for saving output directly to files
- Statistics and optimization features

## Repository Structure

- `semlist.py` - Main Python script for managing mailing lists
- `MailingList.json` - Default database file containing email addresses
- `dbase/` - Directory for storing additional mailing list databases
- `scripts/import_students.py` - Helper for importing student rosters from Excel

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
python3 semlist.py print all             # Print all emails in Outlook format to screen
python3 semlist.py print 1               # Print emails from batch 1 to screen
python3 semlist.py print all output.txt  # Save all emails to output.txt file (silent mode)
python3 semlist.py print 1 output.txt    # Save emails from batch 1 to output.txt file (silent mode)
```

The emails are formatted as `Name <email>;` which works with Microsoft Outlook. When saving to a file, the script operates in silent mode, only showing a success message without displaying the email content on the screen.

### Check for emails

```bash
python3 semlist.py check 'pattern'         # Search for emails matching the regex pattern (case-insensitive)
```

This command allows you to search the active database for email addresses or names matching a given regular expression. It prints any matches found.

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

When adding emails with names, the script parses and stores first, middle, and last name components automatically.

### Database management

```bash
python3 semlist.py new DatabaseName      # Create a new database
python3 semlist.py del DatabaseName      # Delete a database (with confirmation)
python3 semlist.py activate DatabaseName # Set the active database
python3 semlist.py config                # Show current configuration
```

The system supports multiple databases stored in the `dbase/` directory. You can create, delete, and switch between them with these commands.

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

- Each batch contains up to 57 email entries
- Each entry stores the email, name, and original text format
- Name components (first, middle, last) are stored separately for better formatting

## Email Format Handling

The tool has sophisticated handling of various email formats:

- Simple email: `email@example.com`
- Email with name: `Name <email@example.com>`
- Full format: `"First Last" <email@example.com>;`
- Multiple entries: `"Name1" <email1@example.com>; "Name2" <email2@example.com>;`

When printing, emails are formatted according to Microsoft Outlook requirements (Name <email>;).

## Silent Mode

When saving output to a file, the script operates in silent mode:

```bash
python3 semlist.py print 1 output.txt
```

This will save the emails to the file without displaying them on the terminal, showing only a confirmation message. This feature is useful for scripts and automated workflows.

## Importing student rosters from Excel

A helper script is provided to ingest department spreadsheets that contain student IDs and names and append their email addresses to the active database:

```bash
python3 scripts/import_students.py data/CIE-Department-PGStudentList.xls \
    --id-column D --name-column E --dry-run
```

Key options:

- `--id-column` and `--name-column` accept header names, Excel letters (e.g. `D`), or zero-based indices.
- `--dry-run` previews how many entries would be imported without touching the database.
- `--email-domain` (default `ku.ac.ae`) customizes the generated email address suffix.
- `--database` overrides the active database path if needed.

Imports require `pandas` plus the `xlrd` engine for legacy `.xls` files. Install the latter with:

```bash
pip install xlrd
```

After successful import you can refresh the Outlook-ready text file with:

```bash
python3 semlist.py print all MailingList.txt
```

## Requirements

- Python 3.x
- Core `semlist.py` commands rely only on the Python standard library.
- Excel import workflow additionally needs `pandas` (already bundled in most KU environments) and, for `.xls` files, the `xlrd` package.

## License

[GPL-3.0 License](LICENSE)
