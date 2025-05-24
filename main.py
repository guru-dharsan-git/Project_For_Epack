import asyncio
import logging
import re
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse
import aiohttp
import click
from google import genai
from google.genai import types
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class UniversalWebScraper:
    """Universal web scraper that can handle most websites"""
    
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
    
    def _extract_title(self, soup: BeautifulSoup, url: str) -> str:
        """Extract title from various possible locations"""
        title_candidates = [
            soup.find('h1'),
            soup.find('title'),
            soup.find('meta', property='og:title'),
            soup.find('meta', attrs={'name': 'twitter:title'}),
            soup.find('h2'),
        ]
        
        for candidate in title_candidates:
            if candidate:
                if candidate.name == 'meta':
                    title = candidate.get('content', '').strip()
                else:
                    title = candidate.get_text().strip()
                
                if title and len(title) > 3:
                    return title[:200]
        
        parsed_url = urlparse(url)
        return f"Article from {parsed_url.netloc}"
    
    def _extract_author(self, soup: BeautifulSoup) -> str:
        """Extract author from various possible locations - FIXED VERSION"""
        # Try meta tags first
        meta_author = soup.find('meta', attrs={'name': 'author'})
        if meta_author:
            author = meta_author.get('content', '').strip()
            if author and len(author) < 100:
                return author
        
        meta_article_author = soup.find('meta', property='article:author')
        if meta_article_author:
            author = meta_article_author.get('content', '').strip()
            if author and len(author) < 100:
                return author
        
        # Try CSS selectors using select() method instead of find()
        author_selectors = [
            '[class*="author"]',
            '[class*="byline"]', 
            '[class*="writer"]',
            '[rel="author"]',
            '.author-name',
            '.byline',
            '.post-author',
            '.author',
            '.writer',
            '.by-author'
        ]
        
        for selector in author_selectors:
            try:
                elements = soup.select(selector)
                for element in elements:
                    author = element.get_text().strip()
                    # Filter out obviously wrong results
                    if author and len(author) < 100 and len(author) > 2:
                        # Skip if it contains too many special characters or looks like a URL
                        if not re.search(r'[<>@#$%^&*()+=\[\]{}|\\:";\'<>?,./]', author):
                            return author
            except Exception as e:
                logger.debug(f"Error with selector {selector}: {e}")
                continue
        
        return "Unknown"
    
    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """Extract main article content using multiple strategies"""
        # Remove unwanted elements
        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'advertisement']):
            tag.decompose()
        
        content_selectors = [
            'article',
            '[class*="content"]',
            '[class*="post-content"]',
            '[class*="entry-content"]',
            '[class*="article-content"]',
            '[class*="post-body"]',
            '[class*="story-body"]',
            '[class*="article-body"]',
            'main',
            '.content',
            '.post',
            '.article',
            '.story',
        ]
        
        best_content = ""
        max_length = 0
        
        for selector in content_selectors:
            try:
                elements = soup.select(selector)
                for element in elements:
                    text = element.get_text(separator=' ', strip=True)
                    if len(text) > max_length and len(text) > 100:
                        max_length = len(text)
                        best_content = text
            except Exception as e:
                logger.debug(f"Error with content selector {selector}: {e}")
                continue
        
        # Fallback: extract all paragraph text
        if not best_content or len(best_content) < 200:
            try:
                paragraphs = soup.find_all('p')
                paragraph_text = ' '.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
                if len(paragraph_text) > len(best_content):
                    best_content = paragraph_text
            except Exception as e:
                logger.debug(f"Error extracting paragraphs: {e}")
        
        # Final fallback: get all text from body
        if not best_content or len(best_content) < 100:
            try:
                body = soup.find('body')
                if body:
                    best_content = body.get_text(separator=' ', strip=True)
            except Exception as e:
                logger.debug(f"Error extracting body text: {e}")
        
        return best_content[:10000] if best_content else "No content extracted"
    
    def _clean_url(self, url: str) -> str:
        """Clean and validate URL"""
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        return url
    
    async def scrape_url(self, url: str, timeout: int = 30) -> Optional[Dict[str, str]]:
        """Scrape a single URL and extract article data"""
        url = self._clean_url(url)
        
        try:
            timeout_obj = aiohttp.ClientTimeout(total=timeout)
            async with self.session.get(url, headers=self.headers, timeout=timeout_obj) as response:
                if response.status != 200:
                    logger.warning(f"HTTP {response.status} for {url}")
                    return None
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                title = self._extract_title(soup, url)
                author = self._extract_author(soup)
                content = self._extract_main_content(soup)
                
                if not content or len(content) < 50:
                    logger.warning(f"Insufficient content extracted from {url}")
                    return None
                
                return {
                    'title': title,
                    'author': author,
                    'content': content,
                    'source_url': url
                }
                
        except asyncio.TimeoutError:
            logger.error(f"Timeout scraping {url}")
            return None
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            return None
    
    async def scrape_multiple_urls(self, urls: List[str], max_concurrent: int = 5) -> List[Dict[str, str]]:
        """Scrape multiple URLs concurrently"""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def scrape_with_semaphore(url):
            async with semaphore:
                return await self.scrape_url(url)
        
        tasks = [scrape_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        articles = []
        for result in results:
            if isinstance(result, dict) and result is not None:
                articles.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Task failed with exception: {result}")
        
        return articles

class NewsSourceScraper:
    """Specialized scrapers for popular news sources"""
    
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        self.universal_scraper = UniversalWebScraper(session)
    
    async def scrape_reddit_rss(self, subreddit: str = "news", limit: int = 5) -> List[Dict[str, str]]:
        """Scrape Reddit RSS feed"""
        try:
            url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"
            headers = {'User-Agent': 'NewsBot 1.0'}
            
            async with self.session.get(url, headers=headers) as response:
                if response.status != 200:
                    logger.error(f"Reddit API returned status {response.status}")
                    return []
                    
                data = await response.json()
                
                articles = []
                for post in data['data']['children'][:limit]:
                    post_data = post['data']
                    
                    if post_data.get('is_self') and not post_data.get('selftext'):
                        continue
                    
                    content = post_data.get('selftext', '') or f"Reddit post: {post_data['title']}"
                    
                    article = {
                        'title': post_data['title'],
                        'author': f"u/{post_data['author']}",
                        'content': content,
                        'source_url': f"https://reddit.com{post_data['permalink']}"
                    }
                    articles.append(article)
                
                logger.info(f"Scraped {len(articles)} posts from r/{subreddit}")
                return articles
                
        except Exception as e:
            logger.error(f"Error scraping Reddit: {e}")
            return []
    
    async def scrape_hackernews_api(self, limit: int = 5) -> List[Dict[str, str]]:
        """Enhanced Hacker News scraper"""
        articles = []
        
        try:
            async with self.session.get("https://hacker-news.firebaseio.com/v0/topstories.json") as response:
                if response.status != 200:
                    logger.error(f"HackerNews API returned status {response.status}")
                    return []
                story_ids = await response.json()
            
            for story_id in story_ids[:limit]:
                try:
                    async with self.session.get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json") as response:
                        story = await response.json()
                    
                    if story and story.get('title'):
                        content = story.get('text', '') or story['title']
                        
                        # If there's a URL but no text, try to scrape the content
                        if story.get('url') and not story.get('text'):
                            try:
                                scraped = await self.universal_scraper.scrape_url(story['url'])
                                if scraped and scraped.get('content'):
                                    content = scraped['content'][:1000] + "..."
                            except Exception as e:
                                logger.debug(f"Could not scrape HN story URL: {e}")
                        
                        articles.append({
                            'title': story['title'],
                            'author': story.get('by', 'Unknown'),
                            'content': content,
                            'source_url': f"https://news.ycombinator.com/item?id={story_id}"
                        })
                    
                    await asyncio.sleep(0.1)  # Rate limiting
                except Exception as e:
                    logger.debug(f"Error processing HN story {story_id}: {e}")
                    continue
            
            logger.info(f"Scraped {len(articles)} stories from Hacker News")
            return articles
            
        except Exception as e:
            logger.error(f"Error scraping Hacker News: {e}")
            return []

class DatabaseManager:
    """Manages SQLite database operations"""
    
    def __init__(self, db_path: str = None):
        # Use environment variable or default
        self.db_path = db_path or os.getenv('DB_PATH', 'articles.db')
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    author TEXT,
                    content TEXT NOT NULL,
                    summary TEXT,
                    source_url TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info(f"Database initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    def store_article(self, data: Dict[str, str]) -> int:
        """Store article data in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO articles (title, author, content, summary, source_url)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                data['title'],
                data.get('author', ''),
                data['content'],
                data.get('summary', ''),
                data['source_url']
            ))
            
            article_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            logger.info(f"Stored article with ID: {article_id}")
            return article_id
        except Exception as e:
            logger.error(f"Error storing article: {e}")
            raise
    
    def get_summary_by_id(self, article_id: int) -> Optional[Dict[str, str]]:
        """Retrieve article summary by ID"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, title, author, content, summary, source_url, created_at
                FROM articles WHERE id = ?
            ''', (article_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'id': result[0],
                    'title': result[1],
                    'author': result[2],
                    'content': result[3],
                    'summary': result[4],
                    'source_url': result[5],
                    'created_at': result[6]
                }
            return None
        except Exception as e:
            logger.error(f"Error retrieving article {article_id}: {e}")
            return None
    
    def get_all_articles(self) -> List[Dict[str, str]]:
        """Retrieve all articles"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, title, author, summary, source_url, created_at
                FROM articles ORDER BY created_at DESC
            ''')
            
            results = cursor.fetchall()
            conn.close()
            
            return [{
                'id': row[0],
                'title': row[1],
                'author': row[2],
                'summary': row[3],
                'source_url': row[4],
                'created_at': row[5]
            } for row in results]
        except Exception as e:
            logger.error(f"Error retrieving articles: {e}")
            return []

class TextProcessor:
    """Handles text preprocessing and postprocessing"""
    
    @staticmethod
    def preprocess_text(text: str) -> str:
        """Clean and normalize text content"""
        if not text:
            return ""
        
        # Remove HTML tags
        soup = BeautifulSoup(text, 'html.parser')
        text = soup.get_text()
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        # Remove extra newlines
        text = re.sub(r'\n+', '\n', text)
        
        # Convert to lowercase as per requirements
        text = text.lower()
        
        return text
    
    @staticmethod
    def postprocess_summary(summary: str, max_sentences: int = 4) -> str:
        """Clean up and limit summary text to 3-5 sentences"""
        if not summary:
            return ""
        
        # Remove extra whitespace and newlines
        summary = re.sub(r'\s+', ' ', summary).strip()
        summary = re.sub(r'\n+', ' ', summary)
        
        # Split into sentences and limit to 3-5 sentences
        sentences = re.split(r'[.!?]+', summary)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # Limit to max_sentences (3-5 as per requirements)
        if len(sentences) > max_sentences:
            sentences = sentences[:max_sentences]
        
        return '. '.join(sentences) + '.' if sentences else summary

class GeminiSummarizer:
    """Handles Gemini API integration for text summarization"""
    
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("Gemini API key is required")
        
        try:
            self.client = genai.Client(api_key=api_key)
            self.model = "gemini-2.0-flash-exp"
            self.rate_limit_delay = 1  # Rate limiting
            self.last_request_time = 0
        except Exception as e:
            logger.error(f"Error initializing Gemini client: {e}")
            raise
        
    async def summarize_text(self, text: str) -> str:
        """Summarize text using Gemini API with enhanced error handling"""
        try:
            # Rate limiting
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            if time_since_last < self.rate_limit_delay:
                await asyncio.sleep(self.rate_limit_delay - time_since_last)
            
            # Limit text length to avoid API limits
            max_text_length = 8000
            if len(text) > max_text_length:
                text = text[:max_text_length] + "..."
            
            # Enhanced prompt for better summaries
            prompt = f"""
            Please provide a concise summary of the following text in exactly 3-4 sentences. 
            Focus on the main points, key information, and essential details. 
            Make it informative and well-structured:

            {text}
            """
            
            contents = [
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=prompt)],
                ),
            ]
            
            generate_content_config = types.GenerateContentConfig(
                response_mime_type="text/plain",
                temperature=0.3,  # More consistent summaries
            )
            
            response_text = ""
            for chunk in self.client.models.generate_content_stream(
                model=self.model,
                contents=contents,
                config=generate_content_config,
            ):
                if chunk.text:
                    response_text += chunk.text
            
            self.last_request_time = time.time()
            
            if response_text.strip():
                return TextProcessor.postprocess_summary(response_text.strip())
            else:
                logger.warning("Empty response from Gemini API")
                return "Summary could not be generated."
                
        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}")
            return f"Error generating summary: {str(e)}"

class WebScraper:
    """Enhanced web scraper with universal capabilities"""
    
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        self.universal_scraper = UniversalWebScraper(session)
        self.news_scraper = NewsSourceScraper(session)
    
    async def scrape_quotes_toscrape(self, limit: int = 5) -> List[Dict[str, str]]:
        """Original quotes scraper"""
        url = "http://quotes.toscrape.com"
        articles = []
        
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            async with self.session.get(url, headers=headers) as response:
                if response.status != 200:
                    logger.error(f"quotes.toscrape.com returned status {response.status}")
                    return []
                    
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                quotes = soup.find_all('div', class_='quote')[:limit]
                
                for quote in quotes:
                    text_elem = quote.find('span', class_='text')
                    author_elem = quote.find('small', class_='author')
                    tag_elems = quote.find_all('a', class_='tag')
                    
                    if text_elem and author_elem:
                        text = text_elem.get_text()
                        author = author_elem.get_text()
                        tags = [tag.get_text() for tag in tag_elems]
                        
                        articles.append({
                            'title': f"Quote by {author}",
                            'author': author,
                            'content': f"{text}\n\nTags: {', '.join(tags)}",
                            'source_url': url
                        })
                    
                logger.info(f"Scraped {len(articles)} quotes from quotes.toscrape.com")
                return articles
                
        except Exception as e:
            logger.error(f"Error scraping quotes.toscrape.com: {e}")
            return []
    
    async def scrape_articles(self, source: str, limit: int = 5) -> List[Dict[str, str]]:
        """Enhanced scraping function that handles multiple source types"""
        source_lower = source.lower()
        
        try:
            if source_lower == 'quotes':
                return await self.scrape_quotes_toscrape(limit)
            elif source_lower == 'hackernews':
                return await self.news_scraper.scrape_hackernews_api(limit)
            elif source_lower.startswith('reddit:'):
                subreddit = source_lower.split(':', 1)[1] if ':' in source_lower else 'news'
                return await self.news_scraper.scrape_reddit_rss(subreddit, limit)
            elif source_lower.startswith(('http://', 'https://')) or '.' in source:
                if ',' in source:
                    urls = [url.strip() for url in source.split(',')]
                    return await self.universal_scraper.scrape_multiple_urls(urls[:limit])
                else:
                    result = await self.universal_scraper.scrape_url(source)
                    return [result] if result else []
            else:
                logger.error(f"Unknown source: {source}")
                return []
        except Exception as e:
            logger.error(f"Error in scrape_articles: {e}")
            return []

class ArticleProcessor:
    """Main application class that orchestrates the entire workflow"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.text_processor = TextProcessor()
        
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            logger.warning("GEMINI_API_KEY not found. Summaries will not be generated.")
            self.summarizer = None
        else:
            try:
                self.summarizer = GeminiSummarizer(api_key)
            except Exception as e:
                logger.error(f"Error initializing Gemini summarizer: {e}")
                self.summarizer = None
    
    async def process_articles(self, source: str, limit: int = 5) -> List[int]:
        """Complete workflow: scrape, summarize, and store articles"""
        article_ids = []
        
        try:
            async with aiohttp.ClientSession() as session:
                scraper = WebScraper(session)
                articles = await scraper.scrape_articles(source, limit)
                
                logger.info(f"Scraped {len(articles)} articles from {source}")
                
                for article in articles:
                    try:
                        # Preprocess content (now includes lowercasing)
                        clean_content = self.text_processor.preprocess_text(article['content'])
                        article['content'] = clean_content
                        
                        # Generate summary with better error handling
                        if clean_content and self.summarizer:
                            try:
                                summary = await self.summarizer.summarize_text(clean_content)
                                article['summary'] = summary
                            except Exception as e:
                                logger.error(f"Error generating summary: {e}")
                                article['summary'] = "Summary generation failed"
                        else:
                            article['summary'] = "No summary available"
                        
                        # Store in database
                        article_id = self.db.store_article(article)
                        article_ids.append(article_id)
                        
                        logger.info(f"Processed article: {article['title'][:50]}...")
                        
                    except Exception as e:
                        logger.error(f"Error processing article '{article.get('title', 'Unknown')}': {e}")
                        continue
        except Exception as e:
            logger.error(f"Error in process_articles: {e}")
        
        return article_ids

# CLI Interface
@click.group()
def cli():
    """Article Scraper and Summarizer CLI"""
    pass

@cli.command()
@click.option('--source', default='quotes', help='Source to scrape (quotes, hackernews, reddit:subreddit, URL, or comma-separated URLs)')
@click.option('--limit', default=5, help='Number of articles to scrape')
def scrape(source, limit):
    """Scrape and process articles from various sources"""
    click.echo(f"Scraping {limit} articles from {source}...")
    
    try:
        processor = ArticleProcessor()
        article_ids = asyncio.run(processor.process_articles(source, limit))
        
        click.echo(f"Successfully processed {len(article_ids)} articles")
        click.echo(f"Article IDs: {article_ids}")
        
        if len(article_ids) == 0:
            click.echo("No articles were successfully processed. Check the logs for details.")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        logger.error(f"CLI scrape command failed: {e}")

@cli.command()
@click.argument('url')
def test_scrape(url):
    """Test scraping a single URL"""
    async def test():
        try:
            async with aiohttp.ClientSession() as session:
                scraper = UniversalWebScraper(session)
                result = await scraper.scrape_url(url)
                return result
        except Exception as e:
            logger.error(f"Error in test scrape: {e}")
            return None
    
    try:
        result = asyncio.run(test())
        if result:
            click.echo(f"\n✅ Successfully scraped: {url}")
            click.echo(f"Title: {result['title']}")
            click.echo(f"Author: {result['author']}")
            click.echo(f"Content length: {len(result['content'])} characters")
            click.echo(f"Content preview: {result['content'][:200]}...")
        else:
            click.echo(f"❌ Failed to scrape: {url}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        
@cli.command()
@click.argument('article_id', type=int)
def get_summary(article_id):
    """Get summary by article ID"""
    try:
        db = DatabaseManager()
        article = db.get_summary_by_id(article_id)
        
        if article:
            click.echo(f"\nTitle: {article['title']}")
            click.echo(f"Author: {article['author']}")
            click.echo(f"URL: {article['source_url']}")
            click.echo(f"Created: {article['created_at']}")
            click.echo(f"\nSummary:\n{article['summary']}")
        else:
            click.echo(f"Article with ID {article_id} not found")
            
    except Exception as e:
        click.echo(f"Error: {e}", err=True)

@cli.command()
def list_articles():
    """List all articles"""
    try:
        db = DatabaseManager()
        articles = db.get_all_articles()
        
        if articles:
            click.echo(f"\nFound {len(articles)} articles:\n")
            for article in articles:
                click.echo(f"ID: {article['id']}")
                click.echo(f"Title: {article['title']}")
                click.echo(f"Author: {article['author']}")
                click.echo(f"Created: {article['created_at']}")
                click.echo("-" * 50)
        else:
            click.echo("No articles found")
            
    except Exception as e:
        click.echo(f"Error: {e}", err=True)

@cli.command()
def init_db():
    """Initialize the database"""
    try:
        db = DatabaseManager()
        click.echo("Database initialized successfully")
    except Exception as e:
        click.echo(f"Error initializing database: {e}", err=True)

@cli.command()
@click.option('--full', is_flag=True, help='Show full content and summary')
@click.option('--limit', default=10, help='Number of articles to show')
def view_db(full, limit):
    """View database contents with detailed information"""
    try:
        db = DatabaseManager()
        articles = db.get_all_articles()
        
        if not articles:
            click.echo("No articles found in database")
            return
        
        articles = articles[:limit]
        
        click.echo(f"\n📊 Database Contents ({len(articles)} articles shown)")
        click.echo("=" * 80)
        
        for i, article in enumerate(articles, 1):
            click.echo(f"\n🔹 Article #{article['id']} ({i}/{len(articles)})")
            click.echo(f"Title: {article['title']}")
            click.echo(f"Author: {article['author'] or 'Unknown'}")
            click.echo(f"Source: {article['source_url']}")
            click.echo(f"Created: {article['created_at']}")
            
            if full:
                full_article = db.get_summary_by_id(article['id'])
                if full_article:
                    click.echo(f"\n📝 Content:")
                    content = full_article['content'][:500] + "..." if len(full_article['content']) > 500 else full_article['content']
                    click.echo(content)
                    
                    click.echo(f"\n📋 Summary:")
                    click.echo(full_article['summary'] or 'No summary available')
            else:
                summary_preview = article['summary'][:150] + "..." if article['summary'] and len(article['summary']) > 150 else article['summary'] or 'No summary'
                click.echo(f"Summary: {summary_preview}")
            
            click.echo("-" * 80)
            
    except Exception as e:
        click.echo(f"Error viewing database: {e}", err=True)

if __name__ == "__main__":
    cli()