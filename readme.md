# Article Scraper and Summarizer

A comprehensive Python application that scrapes articles from various sources, uses Google's Gemini AI to generate summaries, and stores everything in a database. Features async processing, CLI interface, and robust error handling.

## Features

- **Web Scraping**: Support for multiple sources (Quotes to Scrape, Hacker News)
- **AI Summarization**: Uses Google Gemini 2.0 Flash API for intelligent summarization
- **Database Storage**: SQLite database with proper schema design
- **Async Processing**: Efficient async/await implementation
- **CLI Interface**: Easy-to-use command line interface
- **Text Processing**: Comprehensive preprocessing and postprocessing
- **Error Handling**: Robust error handling and logging
- **Rate Limiting**: Built-in rate limiting for API calls

## Installation

### Prerequisites

- Python 3.8 or higher
- Google Gemini API key (using the newer google-genai library)

### Setup

1. **Clone or download the application files**

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   Create a `.env` file in the project root:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   DB_URL=sqlite:///articles.db
   ```

5. **Initialize the database**:
   ```bash
   python main.py init-db
   ```

## Usage

### CLI Commands

#### Scrape Articles
```bash
# Scrape 5 quotes (default)
python main.py scrape --source quotes --limit 5

# Scrape 3 Hacker News stories
python main.py scrape --source hackernews --limit 3
```

#### Get Article Summary
```bash
# Get summary for article with ID 1
python main.py get-summary 1
```

#### List All Articles
```bash
# List all stored articles
python main.py list-articles
```

#### View Database Contents
```bash
# View database with summary info
python main.py view-db

# View database with full content and summaries
python main.py view-db --full

# Limit number of articles shown
python main.py view-db --limit 5
```

#### Search Articles
```bash
# Search articles by any field
python main.py search-db "Einstein"

# Search in database
python main.py search-db "technology"
```

#### Database Statistics
```bash
# Show detailed database statistics
python main.py db-stats
```

#### Advanced Database Viewer
```bash
# Use the dedicated database viewer
python db_viewer.py show-all
python db_viewer.py show-article 1
python db_viewer.py analyze
python db_viewer.py search "keyword"
python db_viewer.py export --output my_export.json
```

#### Initialize Database
```bash
# Initialize/reset the database
python main.py init-db
```

### Programmatic Usage

```python
import asyncio
from main import ArticleProcessor

async def main():
    processor = ArticleProcessor()
    
    # Process articles from quotes.toscrape.com
    article_ids = await processor.process_articles('quotes', limit=3)
    print(f"Processed articles: {article_ids}")

# Run the async function
asyncio.run(main())
```

## Database Viewing and Analysis

The application provides multiple ways to view and analyze your scraped data:

### Quick Database Commands

1. **View Database Contents**:
   ```bash
   # Basic view with summaries
   python main.py view-db
   
   # Full view with complete content
   python main.py view-db --full --limit 5
   ```

2. **Search Articles**:
   ```bash
   # Search across all fields
   python main.py search-db "technology"
   
   # Get specific article
   python main.py get-summary 1
   ```

3. **Database Statistics**:
   ```bash
   # Comprehensive statistics
   python main.py db-stats
   ```

### Advanced Database Viewer

For more detailed analysis, use the dedicated database viewer:

```bash
# Show all articles in formatted table
python db_viewer.py show-all

# Show specific article with full details
python db_viewer.py show-article 1

# Comprehensive database analysis
python db_viewer.py analyze

# Search with field specification
python db_viewer.py search "Einstein" --field author

# Export to JSON
python db_viewer.py export --output articles_backup.json
```

### Sample Database Analysis Output

```
📊 BASIC STATISTICS
Total Articles: 15
Total Summaries: 15
Summary Coverage: 100.0%

📝 CONTENT ANALYSIS
Average Content Length: 284 characters
Shortest Article: 89 characters
Longest Article: 567 characters

🌐 SOURCE DISTRIBUTION
quotes.toscrape.com: 10 articles
news.ycombinator.com: 5 articles

✍️ TOP AUTHORS
Albert Einstein: 3 articles
Steve Jobs: 2 articles
Mark Twain: 2 articles
```

### 1. Quotes to Scrape (quotes.toscrape.com)
- **Source ID**: `quotes`
- **Content**: Famous quotes with authors and tags
- **Fields**: Title, Author, Quote text, Tags, Source URL

### 2. Hacker News
- **Source ID**: `hackernews`
- **Content**: Top stories from Hacker News
- **Fields**: Title, Author, Story content/URL, Source URL

## Example Input/Output

### Input Command
```bash
python main.py scrape --source quotes --limit 2
```

### Expected Output
```
Scraping 2 articles from quotes...
2024-01-15 10:30:15,123 - __main__ - INFO - Scraped 2 quotes from quotes.toscrape.com
2024-01-15 10:30:16,456 - __main__ - INFO - Stored article with ID: 1
2024-01-15 10:30:17,789 - __main__ - INFO - Processed article: Quote by Albert Einstein...
2024-01-15 10:30:18,234 - __main__ - INFO - Stored article with ID: 2
2024-01-15 10:30:19,567 - __main__ - INFO - Processed article: Quote by Steve Jobs...
Successfully processed 2 articles
Article IDs: [1, 2]
```

### Getting Summary
```bash
python main.py get-summary 1
```

### Expected Output
```
Title: Quote by Albert Einstein
Author: Albert Einstein
URL: http://quotes.toscrape.com
Created: 2024-01-15 10:30:15

Summary:
Albert Einstein's quote emphasizes the importance of imagination over knowledge. He suggests that while knowledge is limited to what we know and understand, imagination embraces the entire world and drives progress and evolution. This perspective highlights creativity as a fundamental force for human advancement.
```

## Environment Variables

Create a `.env` file with the following variables:

```env
# Required: Google Gemini API Key
GEMINI_API_KEY=your_gemini_api_key_here

# Optional: Database URL (defaults to SQLite)
DB_URL=sqlite:///articles.db

# For PostgreSQL (optional):
# DB_URL=postgresql://username:password@localhost:5432/articles_db

# Optional: Logging level
LOG_LEVEL=INFO
```

### Getting a Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Create a new API key
4. Copy the key to your `.env` file

## Database Schema

The application uses SQLite by default with the following schema:

```sql
CREATE TABLE articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT,
    content TEXT NOT NULL,
    summary TEXT,
    source_url TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Architecture

### Core Components

1. **DatabaseManager**: Handles all database operations (SQLite)
2. **TextProcessor**: Preprocessing and postprocessing of text content
3. **GeminiSummarizer**: Integration with Google Gemini API (using google-genai library)
4. **WebScraper**: Async web scraping with multiple source support
5. **ArticleProcessor**: Main orchestrator class

### Processing Pipeline

1. **Scraping**: Extract content from web sources
2. **Preprocessing**: Clean HTML, normalize whitespace
3. **Summarization**: Generate summaries using Gemini AI
4. **Postprocessing**: Clean and format summaries
5. **Storage**: Save to database with metadata

## Error Handling

The application includes comprehensive error handling:

- **Network errors**: Retry logic and graceful degradation
- **API errors**: Rate limiting and fallback responses
- **Database errors**: Transaction rollback and logging
- **Content errors**: Skip invalid content with logging

## Logging

Logs are written to both console and `scraper.log` file:

```python
# View recent logs
tail -f scraper.log

# Filter for errors only
grep ERROR scraper.log
```

## Extending the Application

### Adding New Sources

1. Create a new method in `WebScraper` class:
   ```python
   async def scrape_your_source(self, limit: int) -> List[Dict[str, str]]:
       # Implementation here
       pass
   ```

2. Update the `scrape_articles` method to route to your new scraper

3. Add CLI option for the new source

### Custom Summarization

You can extend the `GeminiSummarizer` class or create alternative summarizers:

```python
class CustomSummarizer:
    async def summarize_text(self, text: str) -> str:
        # Your custom summarization logic
        pass
```

## Performance Considerations

- **Rate Limiting**: Built-in delays for API calls
- **Async Processing**: Non-blocking I/O operations
- **Database Indexing**: Proper indexes on frequently queried columns
- **Memory Management**: Streaming for large content processing

## Troubleshooting

### Common Issues

1. **"GEMINI_API_KEY environment variable is required"**
   - Ensure your `.env` file is in the project root
   - Check that the API key is valid

2. **"Database locked" error**
   - Ensure no other processes are using the database
   - Check file permissions

3. **Network timeouts**
   - Check internet connectivity
   - Some sites may block automated requests

4. **Import errors**
   - Ensure all dependencies are installed: `pip install -r requirements.txt`
   - Check Python version compatibility

### Debug Mode

Enable debug logging by setting environment variable:
```bash
export LOG_LEVEL=DEBUG
python main.py scrape --source quotes
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is open source and available under the MIT License.

## API Reference

### Core Functions

#### `scrape_articles(source: str, limit: int) -> List[Dict[str, str]]`
Scrapes articles from specified source.

**Parameters:**
- `source`: Source identifier ('quotes', 'hackernews')
- `limit`: Maximum number of articles to scrape

**Returns:** List of article dictionaries

#### `preprocess_text(text: str) -> str`
Cleans and normalizes text content.

#### `summarize_text(text: str) -> str`
Generates summary using Gemini API.

#### `store_article(data: Dict[str, str]) -> int`
Stores article in database, returns article ID.

#### `get_summary_by_id(article_id: int) -> Dict[str, str]`
Retrieves article by ID from database.

## Version History

- **v1.0.0**: Initial release with basic scraping and summarization
- **v1.1.0**: Added async support and multiple sources
- **v1.2.0**: Enhanced error handling and CLI interface

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the logs in `scraper.log`
3. Open an issue with detailed error information