# Database Viewer (db_viewer.py)

A command-line tool for viewing and analyzing SQLite article databases.

## Installation

```bash
pip install click
```

## Commands

### View Articles
```bash
# Show all articles (paginated)
python db_viewer.py show-all

# Show specific article by ID
python db_viewer.py show-article 5
```

### Search & Analysis
```bash
# Search all fields
python db_viewer.py search "keyword"

# Search specific field
python db_viewer.py search "author name" --field author

# Generate analysis report
python db_viewer.py analyze
```

### Export Data
```bash
# Export to JSON
python db_viewer.py export --output backup.json
```

## Features

- 📊 **Analytics**: Content stats, author distribution, source analysis
- 🔍 **Search**: Search by title, author, content, or summary
- 📄 **Detailed Views**: Full article content with metadata
- 📤 **Export**: JSON export with complete data
- 🎯 **Flexible**: Works with any `articles.db` SQLite database

## Database Structure Expected

Table: `articles`
- `id`, `title`, `author`, `content`, `summary`, `source_url`, `created_at`

## Usage Examples

```bash
# Quick overview
python db_viewer.py analyze

# Find articles by author
python db_viewer.py search "John Doe" --field author

# Export everything
python db_viewer.py export
```