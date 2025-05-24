import sqlite3
import json
from datetime import datetime
from urllib.parse import urlparse
from typing import Dict, List, Any
import click

class DatabaseViewer:
    """Interactive database viewer with analysis capabilities"""
    
    def __init__(self, db_path: str = "articles.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row  # Enable column access by name
    
    def __del__(self):
        if hasattr(self, 'conn'):
            self.conn.close()
    
    def get_table_info(self) -> Dict[str, Any]:
        """Get information about the articles table"""
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA table_info(articles)")
        columns = cursor.fetchall()
        
        cursor.execute("SELECT COUNT(*) FROM articles")
        total_rows = cursor.fetchone()[0]
        
        return {
            'columns': [{'name': col[1], 'type': col[2], 'nullable': not col[3]} for col in columns],
            'total_rows': total_rows
        }
    
    def get_all_articles_detailed(self) -> List[Dict[str, Any]]:
        """Get all articles with detailed information"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, title, author, content, summary, source_url, created_at,
                   LENGTH(content) as content_length,
                   LENGTH(summary) as summary_length
            FROM articles 
            ORDER BY created_at DESC
        """)
        
        articles = []
        for row in cursor.fetchall():
            articles.append(dict(row))
        
        return articles
    
    def get_content_analysis(self) -> Dict[str, Any]:
        """Analyze content patterns and statistics"""
        cursor = self.conn.cursor()
        
        # Content length distribution
        cursor.execute("""
            SELECT 
                MIN(LENGTH(content)) as min_length,
                MAX(LENGTH(content)) as max_length,
                AVG(LENGTH(content)) as avg_length,
                COUNT(*) as total_articles
            FROM articles
        """)
        content_stats = dict(cursor.fetchone())
        
        # Summary statistics
        cursor.execute("""
            SELECT 
                COUNT(*) as total_summaries,
                AVG(LENGTH(summary)) as avg_summary_length,
                MIN(LENGTH(summary)) as min_summary_length,
                MAX(LENGTH(summary)) as max_summary_length
            FROM articles 
            WHERE summary IS NOT NULL AND summary != ''
        """)
        summary_stats = dict(cursor.fetchone())
        
        # Source distribution
        cursor.execute("""
            SELECT source_url, COUNT(*) as count
            FROM articles 
            GROUP BY source_url 
            ORDER BY count DESC
        """)
        source_distribution = [dict(row) for row in cursor.fetchall()]
        
        # Author distribution
        cursor.execute("""
            SELECT author, COUNT(*) as count
            FROM articles 
            WHERE author IS NOT NULL AND author != ''
            GROUP BY author 
            ORDER BY count DESC
            LIMIT 20
        """)
        author_distribution = [dict(row) for row in cursor.fetchall()]
        
        # Timeline analysis
        cursor.execute("""
            SELECT 
                DATE(created_at) as date,
                COUNT(*) as articles_count
            FROM articles 
            GROUP BY DATE(created_at)
            ORDER BY date DESC
            LIMIT 30
        """)
        timeline = [dict(row) for row in cursor.fetchall()]
        
        return {
            'content_stats': content_stats,
            'summary_stats': summary_stats,
            'source_distribution': source_distribution,
            'author_distribution': author_distribution,
            'timeline': timeline
        }
    
    def search_articles(self, query: str, field: str = 'all') -> List[Dict[str, Any]]:
        """Search articles in specific fields"""
        cursor = self.conn.cursor()
        
        if field == 'all':
            sql = """
                SELECT * FROM articles 
                WHERE title LIKE ? OR author LIKE ? OR content LIKE ? OR summary LIKE ?
                ORDER BY created_at DESC
            """
            params = [f'%{query}%'] * 4
        elif field == 'title':
            sql = "SELECT * FROM articles WHERE title LIKE ? ORDER BY created_at DESC"
            params = [f'%{query}%']
        elif field == 'author':
            sql = "SELECT * FROM articles WHERE author LIKE ? ORDER BY created_at DESC"
            params = [f'%{query}%']
        elif field == 'content':
            sql = "SELECT * FROM articles WHERE content LIKE ? ORDER BY created_at DESC"
            params = [f'%{query}%']
        elif field == 'summary':
            sql = "SELECT * FROM articles WHERE summary LIKE ? ORDER BY created_at DESC"
            params = [f'%{query}%']
        else:
            raise ValueError(f"Invalid field: {field}")
        
        cursor.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def get_article_by_id(self, article_id: int) -> Dict[str, Any]:
        """Get a specific article by ID"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM articles WHERE id = ?", (article_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def export_to_json(self, filename: str = None) -> str:
        """Export all data to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"articles_export_{timestamp}.json"
        
        articles = self.get_all_articles_detailed()
        analysis = self.get_content_analysis()
        table_info = self.get_table_info()
        
        export_data = {
            'export_date': datetime.now().isoformat(),
            'table_info': table_info,
            'analysis': analysis,
            'articles': articles
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        return filename
    
    def generate_report(self) -> str:
        """Generate a comprehensive text report"""
        analysis = self.get_content_analysis()
        table_info = self.get_table_info()
        
        report = []
        report.append("=" * 60)
        report.append("ARTICLE DATABASE ANALYSIS REPORT")
        report.append("=" * 60)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Database: {self.db_path}")
        report.append("")
        
        # Basic Stats
        report.append("📊 BASIC STATISTICS")
        report.append("-" * 30)
        report.append(f"Total Articles: {table_info['total_rows']}")
        report.append(f"Total Summaries: {analysis['summary_stats']['total_summaries']}")
        report.append(f"Summary Coverage: {(analysis['summary_stats']['total_summaries']/table_info['total_rows']*100):.1f}%")
        report.append("")
        
        # Content Analysis
        report.append("📝 CONTENT ANALYSIS")
        report.append("-" * 30)
        content_stats = analysis['content_stats']
        report.append(f"Average Content Length: {content_stats['avg_length']:.0f} characters")
        report.append(f"Shortest Article: {content_stats['min_length']} characters")
        report.append(f"Longest Article: {content_stats['max_length']} characters")
        report.append("")
        
        # Summary Analysis
        if analysis['summary_stats']['total_summaries'] > 0:
            report.append("📋 SUMMARY ANALYSIS")
            report.append("-" * 30)
            summary_stats = analysis['summary_stats']
            report.append(f"Average Summary Length: {summary_stats['avg_summary_length']:.0f} characters")
            report.append(f"Shortest Summary: {summary_stats['min_summary_length']} characters")
            report.append(f"Longest Summary: {summary_stats['max_summary_length']} characters")
            report.append("")
        
        # Source Distribution
        report.append("🌐 SOURCE DISTRIBUTION")
        report.append("-" * 30)
        for source in analysis['source_distribution'][:10]:
            domain = urlparse(source['source_url']).netloc or source['source_url']
            report.append(f"{domain}: {source['count']} articles")
        report.append("")
        
        # Top Authors
        if analysis['author_distribution']:
            report.append("✍️  TOP AUTHORS")
            report.append("-" * 30)
            for author in analysis['author_distribution'][:10]:
                report.append(f"{author['author']}: {author['count']} articles")
            report.append("")
        
        # Recent Activity
        report.append("📅 RECENT ACTIVITY")
        report.append("-" * 30)
        for day in analysis['timeline'][:7]:
            report.append(f"{day['date']}: {day['articles_count']} articles")
        
        report.append("")
        report.append("=" * 60)
        
        return "\n".join(report)

# CLI for the database viewer
@click.group()
def viewer_cli():
    """Database Viewer CLI"""
    pass

@viewer_cli.command()
@click.option('--db-path', default='articles.db', help='Path to database file')
def show_all(db_path):
    """Show all articles in a formatted table"""
    viewer = DatabaseViewer(db_path)
    articles = viewer.get_all_articles_detailed()
    
    if not articles:
        click.echo("No articles found in database")
        return
    
    click.echo(f"\n📚 All Articles ({len(articles)} total)")
    click.echo("=" * 100)
    
    for i, article in enumerate(articles, 1):
        click.echo(f"\n#{article['id']} | {article['title'][:60]}{'...' if len(article['title']) > 60 else ''}")
        click.echo(f"Author: {article['author'] or 'Unknown'} | Created: {article['created_at']}")
        click.echo(f"Content: {article['content_length']} chars | Summary: {article['summary_length'] or 0} chars")
        click.echo(f"Source: {urlparse(article['source_url']).netloc}")
        
        if i % 5 == 0 and i < len(articles):
            if not click.confirm(f"\nContinue showing articles? ({len(articles) - i} remaining)"):
                break

@viewer_cli.command()
@click.argument('article_id', type=int)
@click.option('--db-path', default='articles.db', help='Path to database file')
def show_article(article_id, db_path):
    """Show detailed view of a specific article"""
    viewer = DatabaseViewer(db_path)
    article = viewer.get_article_by_id(article_id)
    
    if not article:
        click.echo(f"Article with ID {article_id} not found")
        return
    
    click.echo(f"\n📄 Article #{article['id']}")
    click.echo("=" * 80)
    click.echo(f"Title: {article['title']}")
    click.echo(f"Author: {article['author'] or 'Unknown'}")
    click.echo(f"Source: {article['source_url']}")
    click.echo(f"Created: {article['created_at']}")
    click.echo(f"Content Length: {len(article['content'])} characters")
    click.echo(f"Summary Length: {len(article['summary']) if article['summary'] else 0} characters")
    
    click.echo(f"\n📝 Content:")
    click.echo("-" * 40)
    click.echo(article['content'])
    
    if article['summary']:
        click.echo(f"\n📋 Summary:")
        click.echo("-" * 40)
        click.echo(article['summary'])

@viewer_cli.command()
@click.option('--db-path', default='articles.db', help='Path to database file')
def analyze(db_path):
    """Show comprehensive database analysis"""
    viewer = DatabaseViewer(db_path)
    report = viewer.generate_report()
    click.echo(report)

@viewer_cli.command()
@click.argument('query')
@click.option('--field', default='all', help='Field to search in (all, title, author, content, summary)')
@click.option('--db-path', default='articles.db', help='Path to database file')
def search(query, field, db_path):
    """Search articles"""
    viewer = DatabaseViewer(db_path)
    results = viewer.search_articles(query, field)
    
    if not results:
        click.echo(f"No articles found matching '{query}' in {field}")
        return
    
    click.echo(f"\n🔍 Search Results for '{query}' in {field} ({len(results)} found)")
    click.echo("=" * 80)
    
    for article in results:
        click.echo(f"\n#{article['id']} | {article['title']}")
        click.echo(f"Author: {article['author'] or 'Unknown'}")
        click.echo(f"Created: {article['created_at']}")
        
        # Show snippet of matching content
        if field in ['all', 'content'] and query.lower() in article['content'].lower():
            content = article['content']
            index = content.lower().find(query.lower())
            start = max(0, index - 50)
            end = min(len(content), index + 100)
            snippet = content[start:end]
            click.echo(f"Content snippet: ...{snippet}...")
        
        if field in ['all', 'summary'] and article['summary'] and query.lower() in article['summary'].lower():
            click.echo(f"Summary: {article['summary']}")

@viewer_cli.command()
@click.option('--db-path', default='articles.db', help='Path to database file')
@click.option('--output', help='Output filename (default: auto-generated)')
def export(db_path, output):
    """Export database to JSON"""
    viewer = DatabaseViewer(db_path)
    filename = viewer.export_to_json(output)
    click.echo(f"Database exported to: {filename}")

if __name__ == "__main__":
    viewer_cli()