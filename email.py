import streamlit as st
import pandas as pd
import re
from typing import List, Dict, Any
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
import sqlite3
import hashlib

# Page configuration
st.set_page_config(
    page_title="Smart Text Formatter & M&A Intelligence Processor",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
        color: white;
        padding: 2rem;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .formatted-text {
        background: white;
        padding: 2rem;
        border-radius: 10px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        border-left: 4px solid #3498db;
        margin-bottom: 1rem;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        line-height: 1.6;
    }
    
    .email-formatted {
        background: #f8f9fa;
        padding: 2rem;
        border-radius: 10px;
        border: 2px solid #e9ecef;
        margin-bottom: 1rem;
        font-family: 'Courier New', monospace;
        font-size: 0.9rem;
        line-height: 1.5;
        white-space: pre-wrap;
    }
    
    .copy-button {
        background: #27ae60;
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 5px;
        cursor: pointer;
    }
    
    .section-header {
        background: linear-gradient(135deg, #34495e 0%, #2c3e50 100%);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        font-weight: 600;
        font-size: 1.1rem;
        margin: 1.5rem 0 1rem 0;
    }
    
    .bullet-point {
        color: #2c3e50;
        margin: 0.5rem 0;
        padding-left: 1rem;
        border-left: 3px solid #3498db;
    }
    
    .highlight-text {
        background: linear-gradient(135deg, #f39c12 0%, #e67e22 100%);
        color: white;
        padding: 0.3rem 0.6rem;
        border-radius: 4px;
        font-weight: 600;
    }
    
    .database-info {
        background: #e8f5e8;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #27ae60;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

class DatabaseManager:
    def __init__(self, db_path="ma_intelligence.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create emails table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_hash TEXT UNIQUE,
                raw_content TEXT,
                formatted_content TEXT,
                processed_date DATETIME,
                total_deals INTEGER,
                total_sections INTEGER,
                total_monetary_values INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create deals table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS deals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_id INTEGER,
                deal_number INTEGER,
                title TEXT,
                sector TEXT,
                geography TEXT,
                value_text TEXT,
                size_category TEXT,
                grade TEXT,
                source TEXT,
                intelligence_id TEXT,
                stake_value TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (email_id) REFERENCES emails (id)
            )
        ''')
        
        # Create sections table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_id INTEGER,
                section_name TEXT,
                deal_count INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (email_id) REFERENCES emails (id)
            )
        ''')
        
        # Create monetary_values table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS monetary_values (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_id INTEGER,
                value_text TEXT,
                currency TEXT,
                amount REAL,
                unit TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (email_id) REFERENCES emails (id)
            )
        ''')
        
        # Create metadata table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_id INTEGER,
                key TEXT,
                value TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (email_id) REFERENCES emails (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_content_hash(self, content: str) -> str:
        """Generate a hash for the content to avoid duplicates"""
        return hashlib.md5(content.encode()).hexdigest()
    
    def save_email_data(self, raw_content: str, formatted_content: str, deals_data: List[Dict], key_info: Dict) -> int:
        """Save email and all extracted data to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        content_hash = self.get_content_hash(raw_content)
        
        try:
            # Check if email already exists
            cursor.execute('SELECT id FROM emails WHERE content_hash = ?', (content_hash,))
            existing = cursor.fetchone()
            
            if existing:
                st.warning("This email content has already been processed and saved.")
                return existing[0]
            
            # Insert email record
            cursor.execute('''
                INSERT INTO emails (content_hash, raw_content, formatted_content, processed_date, 
                                  total_deals, total_sections, total_monetary_values)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                content_hash,
                raw_content,
                formatted_content,
                datetime.now().isoformat(),
                len(key_info['deals']),
                len(key_info['sections']),
                len(set(key_info['monetary_values']))
            ))
            
            email_id = cursor.lastrowid
            
            # Insert deals data
            for deal in key_info['deals']:
                # Extract additional info from deals_data if available
                deal_info = next((d for d in deals_data if d.get('id') == str(deal['number'])), {})
                
                cursor.execute('''
                    INSERT INTO deals (email_id, deal_number, title, sector, geography, 
                                     value_text, size_category, grade, source, intelligence_id, stake_value)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    email_id,
                    deal['number'],
                    deal['title'],
                    deal.get('section', 'Unknown'),
                    deal_info.get('geography', 'Unknown'),
                    deal_info.get('value', ''),
                    deal_info.get('size', ''),
                    deal_info.get('grade', ''),
                    deal_info.get('source', ''),
                    deal_info.get('intelligence_id', ''),
                    deal_info.get('stake_value', '')
                ))
            
            # Insert sections
            section_counts = {}
            for deal in key_info['deals']:
                section = deal.get('section', 'Unknown')
                section_counts[section] = section_counts.get(section, 0) + 1
            
            for section, count in section_counts.items():
                cursor.execute('''
                    INSERT INTO sections (email_id, section_name, deal_count)
                    VALUES (?, ?, ?)
                ''', (email_id, section, count))
            
            # Insert monetary values
            for value in set(key_info['monetary_values']):
                # Parse currency and amount
                currency, amount, unit = self.parse_monetary_value(value)
                cursor.execute('''
                    INSERT INTO monetary_values (email_id, value_text, currency, amount, unit)
                    VALUES (?, ?, ?, ?, ?)
                ''', (email_id, value, currency, amount, unit))
            
            # Insert metadata
            for key, value in key_info['metadata'].items():
                cursor.execute('''
                    INSERT INTO metadata (email_id, key, value)
                    VALUES (?, ?, ?)
                ''', (email_id, key, value))
            
            conn.commit()
            st.success(f"✅ Email data saved to database! Email ID: {email_id}")
            return email_id
            
        except Exception as e:
            conn.rollback()
            st.error(f"Error saving to database: {str(e)}")
            return None
        finally:
            conn.close()
    
    def parse_monetary_value(self, value_text: str) -> tuple:
        """Parse monetary value to extract currency, amount, and unit"""
        # Extract currency
        currency_match = re.search(r'(EUR|USD|GBP|CNY|\$|£|€)', value_text, re.IGNORECASE)
        currency = currency_match.group(1) if currency_match else ''
        
        # Extract amount
        amount_match = re.search(r'([\d,\.]+)', value_text)
        amount = float(amount_match.group(1).replace(',', '')) if amount_match else 0.0
        
        # Extract unit
        unit_match = re.search(r'(million|billion|bn|m|k)\b', value_text, re.IGNORECASE)
        unit = unit_match.group(1) if unit_match else ''
        
        return currency, amount, unit
    
    def get_market_insights(self) -> Dict[str, Any]:
        """Get market insights from stored data"""
        conn = sqlite3.connect(self.db_path)
        
        # Get overview stats
        overview_query = '''
            SELECT 
                COUNT(*) as total_emails,
                SUM(total_deals) as total_deals,
                AVG(total_deals) as avg_deals_per_email,
                COUNT(DISTINCT DATE(created_at)) as active_days
            FROM emails
        '''
        overview = pd.read_sql_query(overview_query, conn)
        
        # Get sector trends
        sector_query = '''
            SELECT 
                sector,
                COUNT(*) as deal_count,
                DATE(created_at) as date
            FROM deals
            WHERE sector != 'Unknown'
            GROUP BY sector, DATE(created_at)
            ORDER BY date DESC
        '''
        sector_trends = pd.read_sql_query(sector_query, conn)
        
        # Get top sectors
        top_sectors_query = '''
            SELECT 
                sector,
                COUNT(*) as deal_count
            FROM deals
            WHERE sector != 'Unknown'
            GROUP BY sector
            ORDER BY deal_count DESC
            LIMIT 10
        '''
        top_sectors = pd.read_sql_query(top_sectors_query, conn)
        
        # Get recent activity
        recent_query = '''
            SELECT 
                e.processed_date,
                e.total_deals,
                e.total_sections
            FROM emails e
            ORDER BY e.created_at DESC
            LIMIT 30
        '''
        recent_activity = pd.read_sql_query(recent_query, conn)
        
        # Get value distribution
        value_query = '''
            SELECT 
                currency,
                AVG(amount) as avg_amount,
                COUNT(*) as count,
                unit
            FROM monetary_values
            WHERE amount > 0
            GROUP BY currency, unit
        '''
        value_distribution = pd.read_sql_query(value_query, conn)
        
        conn.close()
        
        return {
            'overview': overview,
            'sector_trends': sector_trends,
            'top_sectors': top_sectors,
            'recent_activity': recent_activity,
            'value_distribution': value_distribution
        }

class SmartTextProcessor:
    def __init__(self):
        self.sector_keywords = {
            'automotive': ['auto', 'car', 'vehicle', 'motor', 'automotive', 'tesla', 'ford', 'bmw'],
            'technology': ['tech', 'software', 'AI', 'digital', 'data', 'cyber', 'SaaS', 'IT', 'cloud', 'app'],
            'financial': ['bank', 'finance', 'capital', 'investment', 'insurance', 'fund', 'fintech'],
            'industrial': ['construction', 'industrial', 'manufacturing', 'engineering', 'chemical', 'steel'],
            'energy': ['energy', 'oil', 'gas', 'renewable', 'power', 'solar', 'wind', 'nuclear'],
            'healthcare': ['health', 'medical', 'pharma', 'biotech', 'hospital', 'drug', 'medicine'],
            'consumer': ['retail', 'consumer', 'food', 'beauty', 'fashion', 'beverage', 'brand'],
            'real_estate': ['real estate', 'property', 'reit', 'building', 'development'],
            'agriculture': ['agriculture', 'farming', 'food', 'crop', 'livestock']
        }
        
        self.geo_keywords = {
            'uk': ['uk', 'britain', 'london', 'england', 'scotland', 'wales', 'british'],
            'germany': ['german', 'germany', 'berlin', 'munich', 'deutsche'],
            'france': ['france', 'french', 'paris'],
            'europe': ['europe', 'european', 'eu'],
            'usa': ['us', 'usa', 'america', 'american', 'new york', 'california'],
            'china': ['china', 'chinese', 'beijing', 'shanghai'],
            'asia': ['asia', 'asian', 'japan', 'singapore', 'hong kong']
        }

    def format_raw_text(self, content: str) -> str:
        """Format raw text into a more readable structure with HTML"""
        if not content.strip():
            return "No content to format."
        
        lines = content.split('\n')
        formatted_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                formatted_lines.append('')
                continue
            
            # Check if line is a section header (single word/short phrase, all caps or title case)
            if self._is_section_header(line):
                formatted_lines.append(f'<div class="section-header">📊 {line.upper()}</div>')
            
            # Check if line is a numbered item (deal/topic)
            elif re.match(r'^\d+\.', line):
                formatted_lines.append(f'<h3 style="color: #2c3e50; margin-top: 2rem; margin-bottom: 1rem;">🔸 {line}</h3>')
            
            # Check if line is a bullet point
            elif line.startswith('*') or line.startswith('-') or line.startswith('•'):
                bullet_text = line[1:].strip()
                formatted_lines.append(f'<div class="bullet-point">• {bullet_text}</div>')
            
            # Check if line contains monetary values
            elif self._contains_monetary_value(line):
                highlighted_line = self._highlight_monetary_values(line)
                formatted_lines.append(f'<p style="margin: 1rem 0; color: #2c3e50;"><strong>{highlighted_line}</strong></p>')
            
            # Check if line contains key metadata (Source:, Size:, etc.)
            elif ':' in line and self._is_metadata_line(line):
                key, value = line.split(':', 1)
                formatted_lines.append(f'<p style="margin: 0.5rem 0; color: #7f8c8d;"><span style="font-weight: 600;">{key.strip()}:</span> {value.strip()}</p>')
            
            # Regular paragraph text
            else:
                # Highlight important terms
                highlighted_text = self._highlight_important_terms(line)
                formatted_lines.append(f'<p style="margin: 1rem 0; color: #2c3e50; line-height: 1.6;">{highlighted_text}</p>')
        
        return '\n'.join(formatted_lines)

    def format_for_email(self, content: str) -> str:
        """Format raw text for email-friendly plain text matching the specific format"""
        if not content.strip():
            return "No content to format."
        
        lines = content.split('\n')
        formatted_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                formatted_lines.append('')
                continue
            
            # Check if line is a section header (clean, simple format)
            if self._is_section_header(line):
                # Add spacing before section headers
                if formatted_lines and formatted_lines[-1] != '':
                    formatted_lines.append('')
                formatted_lines.append(line)
                formatted_lines.append('')
            
            # Check if line is a numbered item (deal/topic)
            elif re.match(r'^\d+\.', line):
                formatted_lines.append(line)
                formatted_lines.append('')  # Add blank line after numbered items
            
            # Check if line is a bullet point
            elif line.startswith('*') or line.startswith('-') or line.startswith('•'):
                bullet_text = line[1:].strip()
                formatted_lines.append(f'* {bullet_text}')
            
            # Check if line contains key metadata (Source:, Size:, etc.)
            elif ':' in line and self._is_metadata_line(line):
                formatted_lines.append(line)
            
            # Regular paragraph text
            else:
                formatted_lines.append(line)
        
        # Clean up multiple consecutive blank lines
        cleaned_lines = []
        prev_was_blank = False
        
        for line in formatted_lines:
            if line == '':
                if not prev_was_blank:
                    cleaned_lines.append(line)
                prev_was_blank = True
            else:
                cleaned_lines.append(line)
                prev_was_blank = False
        
        # Remove trailing blank lines
        while cleaned_lines and cleaned_lines[-1] == '':
            cleaned_lines.pop()
        
        return '\n'.join(cleaned_lines)

    def parse_deals_from_content(self, content: str) -> List[Dict[str, Any]]:
        """Parse deals with enhanced information extraction"""
        deals = []
        lines = content.split('\n')
        current_deal = None
        current_sector = "Other"
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # Check for sector header
            if self._is_section_header(line):
                current_sector = line.title()
                continue
                
            # Check for deal header (numbered item)
            deal_match = re.match(r'^(\d+)\.\s*(.+)', line)
            if deal_match:
                # Save previous deal
                if current_deal:
                    deals.append(current_deal)
                
                # Start new deal
                deal_id = deal_match.group(1)
                title = deal_match.group(2)
                
                current_deal = {
                    'id': deal_id,
                    'title': title,
                    'sector': current_sector,
                    'geography': self.extract_geography(title),
                    'details': [],
                    'value': self.extract_value(title),
                    'grade': '',
                    'size': '',
                    'source': '',
                    'intelligence_id': '',
                    'stake_value': 'N/A',
                    'original_text': title
                }
                
                # Collect subsequent lines for this deal
                j = i + 1
                while j < len(lines):
                    next_line = lines[j].strip()
                    if not next_line:
                        j += 1
                        continue
                    
                    # Stop if we hit the next numbered deal or sector
                    if re.match(r'^\d+\.', next_line) or self._is_section_header(next_line):
                        break
                    
                    current_deal['original_text'] += '\n' + next_line
                    
                    if next_line.startswith('*'):
                        current_deal['details'].append(next_line[1:].strip())
                    elif 'Size:' in next_line:
                        current_deal['size'] = next_line.split('Size:')[1].strip()
                    elif 'Grade:' in next_line:
                        current_deal['grade'] = next_line.split('Grade:')[1].strip()
                    elif 'Source:' in next_line:
                        current_deal['source'] = next_line.split('Source:')[1].strip()
                    elif 'Intelligence ID:' in next_line:
                        current_deal['intelligence_id'] = next_line.split('Intelligence ID:')[1].strip()
                    elif 'Stake Value:' in next_line:
                        current_deal['stake_value'] = next_line.split('Stake Value:')[1].strip()
                    elif self._contains_monetary_value(next_line):
                        if not current_deal['value'] or current_deal['value'] == 'TBD':
                            current_deal['value'] = self.extract_value(next_line)
                    
                    j += 1
        
        # Don't forget the last deal
        if current_deal:
            deals.append(current_deal)
        
        return deals

    def extract_geography(self, title: str) -> str:
        """Extract geography from deal title"""
        lower_title = title.lower()
        for geo, keywords in self.geo_keywords.items():
            if any(keyword in lower_title for keyword in keywords):
                return geo.upper()
        return 'Global'

    def extract_value(self, text: str) -> str:
        """Extract monetary value from text"""
        value_patterns = [
            r'(EUR|USD|GBP|CNY)\s*([\d,\.]+)\s*([bmk]?)',
            r'([\d,\.]+)\s*(EUR|USD|GBP|million|billion)',
            r'\$\s*([\d,\.]+)\s*([bmk]?)',
            r'£\s*([\d,\.]+)\s*([bmk]?)',
            r'€\s*([\d,\.]+)\s*([bmk]?)'
        ]
        
        for pattern in value_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return 'TBD'

    def _is_section_header(self, line: str) -> bool:
        """Check if line is likely a section header"""
        words = line.split()
        return (len(words) <= 3 and 
                len(line) < 50 and
                (line.isupper() or line.istitle()) and
                not line.startswith('*') and
                not re.match(r'^\d+\.', line) and
                not any(char in line for char in ['(', ')', '€', '$', '£', ':']))
    
    def _contains_monetary_value(self, line: str) -> bool:
        """Check if line contains monetary values"""
        return bool(re.search(r'(EUR|USD|GBP|CNY|\$|£|€)\s*[\d,\.]+', line, re.IGNORECASE) or
                   re.search(r'[\d,\.]+\s*(million|billion|bn|m)\b', line, re.IGNORECASE))
    
    def _highlight_monetary_values(self, line: str) -> str:
        """Highlight monetary values in text"""
        # Pattern for currency values
        currency_pattern = r'((?:EUR|USD|GBP|CNY|\$|£|€)\s*[\d,\.]+(?:\s*(?:million|billion|bn|m))?)'
        line = re.sub(currency_pattern, r'<span class="highlight-text">\1</span>', line, flags=re.IGNORECASE)
        
        # Pattern for standalone monetary amounts
        amount_pattern = r'([\d,\.]+\s*(?:million|billion|bn|m)\b)'
        line = re.sub(amount_pattern, r'<span class="highlight-text">\1</span>', line, flags=re.IGNORECASE)
        
        return line
    
    def _is_metadata_line(self, line: str) -> bool:
        """Check if line contains metadata (Source:, Size:, etc.)"""
        metadata_keys = ['source', 'size', 'grade', 'intelligence id', 'stake value', 'alert']
        key_part = line.split(':', 1)[0].lower().strip()
        return any(meta_key in key_part for meta_key in metadata_keys)
    
    def _highlight_important_terms(self, line: str) -> str:
        """Highlight important business terms"""
        important_terms = [
            'acquisition', 'merger', 'joint venture', 'investment', 'funding',
            'ipo', 'listing', 'talks', 'discussions', 'announced', 'completed',
            'signed', 'agreement', 'deal', 'transaction', 'partnership'
        ]
        
        for term in important_terms:
            pattern = r'\b(' + re.escape(term) + r')\b'
            line = re.sub(pattern, r'<strong>\1</strong>', line, flags=re.IGNORECASE)
        
        return line

    def extract_key_information(self, content: str) -> Dict[str, Any]:
        """Extract key information from the text"""
        lines = content.split('\n')
        
        info = {
            'total_lines': len([l for l in lines if l.strip()]),
            'sections': [],
            'deals': [],
            'monetary_values': [],
            'companies': [],
            'metadata': {}
        }
        
        current_section = None
        deal_count = 0
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Track sections
            if self._is_section_header(line):
                current_section = line
                info['sections'].append(line)
            
            # Track numbered deals
            if re.match(r'^\d+\.', line):
                deal_count += 1
                info['deals'].append({
                    'number': deal_count,
                    'title': line,
                    'section': current_section
                })
            
            # Extract monetary values
            monetary_matches = re.findall(r'((?:EUR|USD|GBP|CNY|\$|£|€)\s*[\d,\.]+(?:\s*(?:million|billion|bn|m))?)', line, re.IGNORECASE)
            info['monetary_values'].extend(monetary_matches)
            
            # Extract metadata
            if ':' in line and self._is_metadata_line(line):
                key, value = line.split(':', 1)
                info['metadata'][key.strip()] = value.strip()
        
        return info

    def create_summary(self, content: str) -> str:
        """Create a clean professional summary without decorative separators"""
        info = self.extract_key_information(content)
        
        summary_parts = []
        
        summary_parts.append(f"DOCUMENT ANALYSIS SUMMARY")
        summary_parts.append(f"Generated: {datetime.now().strftime('%B %d, %Y')}")
        summary_parts.append("")
        
        summary_parts.append("CONTENT OVERVIEW")
        summary_parts.append("")
        summary_parts.append(f"• Total Content Lines: {info['total_lines']}")
        summary_parts.append(f"• Identified Sections: {len(info['sections'])}")
        summary_parts.append(f"• Numbered Items/Deals: {len(info['deals'])}")
        summary_parts.append(f"• Monetary References: {len(set(info['monetary_values']))}")
        summary_parts.append("")
        
        if info['sections']:
            summary_parts.append("SECTIONS IDENTIFIED")
            summary_parts.append("")
            for section in info['sections']:
                summary_parts.append(f"• {section}")
            summary_parts.append("")
        
        if info['deals']:
            summary_parts.append("KEY ITEMS")
            summary_parts.append("")
            for deal in info['deals'][:10]:
                title = deal["title"][:100] + "..." if len(deal["title"]) > 100 else deal["title"]
                summary_parts.append(f"• {title}")
            summary_parts.append("")
        
        if info['monetary_values']:
            summary_parts.append("MONETARY VALUES DETECTED")
            summary_parts.append("")
            unique_values = list(set(info['monetary_values']))[:10]
            for value in unique_values:
                summary_parts.append(f"• {value}")
            summary_parts.append("")
        
        summary_parts.append("Generated by Smart Text Formatter")
        
        return '\n'.join(summary_parts)

def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🎯 Smart Text Formatter & M&A Intelligence Processor</h1>
        <p>Transform raw text and M&A data into professionally formatted, readable content</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize processor and database
    if 'processor' not in st.session_state:
        st.session_state.processor = SmartTextProcessor()
    if 'db_manager' not in st.session_state:
        st.session_state.db_manager = DatabaseManager()
    
    # Main layout
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📝 Raw Text Input")
        
        # Sample data for demonstration
        sample_data = """Automotive

2. Magirus could expand outside of Germany through acquisitions - report (translated)

* Subsidiaries planned in Switzerland, Spain, Poland, and UAE
* Aims to set up production sites in Romania, Croatia through acquisitions
* Aims to double sales to EUR 750m by 2030

Magirus, the German fire protection group, could acquire to expand its business outside of Germany, Schwäbische Zeitung reported.

Without citing a specific source, the German daily said Magirus wants to establish subsidiaries in Switzerland, Spain, Poland and the United Arab Emirates.

Source: Schwäbische Zeitung
Size: 60m-300m (GBP)
Grade: Rumoured
Intelligence ID: intelcms-2bxt7z

Technology

3. Adarga seeks GBP 6m-GBP 8m in new funding – report

* Previous USD 20m investment round led by BOKA Group

Adarga is engaged in extensive discussions with a potential investor regarding a capital infusion ranging from GBP 6m to GBP 8m, Sky News reported.

The company specializes in artificial intelligence solutions for defense applications and has been growing rapidly in the UK market.

Source: Sky News
Size: 5m-30m (GBP)
Grade: Strong evidence
Intelligence ID: intelcms-k9mrqp"""
        
        text_input = st.text_area(
            "Paste your raw text here:",
            value=sample_data,
            height=400,
            help="Paste any raw text content. The system will automatically format it for better readability."
        )
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            format_button = st.button("🚀 Format Text", type="primary", use_container_width=True)
        
        with col_b:
            clear_button = st.button("🗑️ Clear", use_container_width=True)
        
        # Save to database option
        save_to_db = st.checkbox("💾 Save to database for market insights", value=True, help="Save processed data to database for trend analysis")
        
        if clear_button:
            st.rerun()
    
    with col2:
        st.subheader("📊 Formatted Output")
        
        if format_button and text_input:
            with st.spinner("Formatting your text..."):
                # Format the text for both web and email
                formatted_text = st.session_state.processor.format_raw_text(text_input)
                email_formatted_text = st.session_state.processor.format_for_email(text_input)
                
                # Extract key information and deals
                key_info = st.session_state.processor.extract_key_information(text_input)
                deals_data = st.session_state.processor.parse_deals_from_content(text_input)
                
                # Store in session state
                st.session_state.formatted_text = formatted_text
                st.session_state.email_formatted_text = email_formatted_text
                st.session_state.raw_input = text_input
                st.session_state.key_info = key_info
                st.session_state.deals_data = deals_data
                
                # Save to database if option is checked
                if save_to_db:
                    email_id = st.session_state.db_manager.save_email_data(
                        text_input, 
                        email_formatted_text, 
                        deals_data, 
                        key_info
                    )
                    
                    if email_id:
                        st.markdown(f"""
                        <div class="database-info">
                            <strong>✅ Data Saved to Database</strong><br>
                            Email ID: {email_id} | Date: {datetime.now().strftime('%Y-%m-%d %H:%M')} | 
                            Deals: {len(key_info['deals'])} | Sections: {len(key_info['sections'])}
                        </div>
                        """, unsafe_allow_html=True)
        
        # Display formatted text if available
        if 'formatted_text' in st.session_state:
            # Tabs for different viewing options
            tab1, tab2 = st.tabs(["🖥️ Web View", "📧 Email Ready"])
            
            with tab1:
                st.markdown(f"""
                <div class="formatted-text">
                    {st.session_state.formatted_text}
                </div>
                """, unsafe_allow_html=True)
            
            with tab2:
                st.markdown("### 📧 Email-Ready Format")
                st.info("💡 Clean format with no decorative separators - perfect for email.")
                
                # Display email-formatted text in a copyable text area
                st.text_area(
                    "Copy this text for email:",
                    value=st.session_state.email_formatted_text,
                    height=600,
                    help="Select all (Ctrl+A / Cmd+A) and copy (Ctrl+C / Cmd+C) to paste into your email.",
                    key="email_text_area"
                )
                
                col_copy, col_download = st.columns(2) 
                
                with col_copy:
                    if st.button("📋 Copy to Clipboard", use_container_width=True):
                        st.success("Select the text above and use Ctrl+C (or Cmd+C) to copy!")
                
                with col_download:
                    # Download button for email format
                    st.download_button(
                        label="📧 Download Email Format",
                        data=st.session_state.email_formatted_text,
                        file_name=f"email_ready_text_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                        mime="text/plain",
                        help="Download as a text file that you can copy from or attach to emails.",
                        use_container_width=True
                    )
        else:
            st.info("Ready to format your text. Paste content and click 'Format Text'")
    
    # Additional features
    if 'formatted_text' in st.session_state:
        st.markdown("---")
        
        # Tabs for additional features
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Content Analysis", "📋 Professional Summary", "💾 Export Options", "📈 Market Insights"])
        
        with tab1:
            st.subheader("📊 Content Analysis")
            
            # Extract and display key information
            key_info = st.session_state.key_info
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Lines", key_info['total_lines'])
            
            with col2:
                st.metric("Sections", len(key_info['sections']))
            
            with col3:
                st.metric("Key Items", len(key_info['deals']))
            
            with col4:
                st.metric("Monetary Values", len(set(key_info['monetary_values'])))
            
            if key_info['sections']:
                st.markdown("### 📁 Sections Identified")
                for i, section in enumerate(key_info['sections'], 1):
                    st.markdown(f"{i}. **{section}**")
            
            if key_info['deals']:
                st.markdown("### 🎯 Key Items/Deals")
                deals_df = pd.DataFrame(key_info['deals'])
                st.dataframe(deals_df, use_container_width=True, hide_index=True)
            
            if key_info['monetary_values']:
                st.markdown("### 💰 Monetary Values Found")
                unique_values = list(set(key_info['monetary_values']))
                for value in unique_values:
                    st.markdown(f"• {value}")
        
        with tab2:
            st.subheader("📋 Professional Summary")
            
            summary = st.session_state.processor.create_summary(st.session_state.raw_input)
            
            st.markdown("""
            <div style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); 
                        padding: 2rem; border-radius: 15px; 
                        border-left: 5px solid #2c3e50; margin: 1rem 0;">
            """, unsafe_allow_html=True)
            
            st.text_area("Clean Professional Summary:", summary, height=400, key="summary_text_area")
            
            st.markdown("</div>", unsafe_allow_html=True)
        
        with tab3:
            st.subheader("💾 Export Options")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # Export formatted HTML
                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Formatted Document</title>
                    <style>
                    body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 2rem; line-height: 1.6; }}
                    .section-header {{ background: #2c3e50; color: white; padding: 1rem; border-radius: 8px; margin: 1.5rem 0 1rem 0; }}
                    .bullet-point {{ color: #2c3e50; margin: 0.5rem 0; padding-left: 1rem; border-left: 3px solid #3498db; }}
                    .highlight-text {{ background: #f39c12; color: white; padding: 0.3rem 0.6rem; border-radius: 4px; }}
                    </style>
                </head>
                <body>
                    <h1>Formatted Document</h1>
                    <div class="formatted-text">
                        {st.session_state.formatted_text}
                    </div>
                </body>
                </html>
                """
                
                st.download_button(
                    label="📄 Download HTML",
                    data=html_content,
                    file_name=f"formatted_text_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
                    mime="text/html",
                    use_container_width=True
                )
            
            with col2:
                # Export email format
                st.download_button(
                    label="📧 Download Email Format",
                    data=st.session_state.email_formatted_text,
                    file_name=f"email_format_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain",
                    use_container_width=True
                )
            
            with col3:
                # Export summary
                summary = st.session_state.processor.create_summary(st.session_state.raw_input)
                st.download_button(
                    label="📊 Download Summary",
                    data=summary,
                    file_name=f"content_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain",
                    use_container_width=True
                )
        
        with tab4:
            st.subheader("📈 Market Insights")
            
            if st.button("🔄 Load Market Insights", use_container_width=True):
                with st.spinner("Analyzing market data..."):
                    insights = st.session_state.db_manager.get_market_insights()
                    
                    if not insights['overview'].empty:
                        # Overview metrics
                        overview = insights['overview'].iloc[0]
                        
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Total Emails", int(overview['total_emails']))
                        with col2:
                            st.metric("Total Deals", int(overview['total_deals']))
                        with col3:
                            st.metric("Avg Deals/Email", f"{overview['avg_deals_per_email']:.1f}")
                        with col4:
                            st.metric("Active Days", int(overview['active_days']))
                        
                        # Sector insights
                        if not insights['top_sectors'].empty:
                            st.markdown("### 🏭 Top Sectors by Deal Volume")
                            
                            fig = px.bar(
                                insights['top_sectors'].head(8), 
                                x='deal_count', 
                                y='sector',
                                orientation='h',
                                title="Most Active Sectors"
                            )
                            fig.update_layout(height=400)
                            st.plotly_chart(fig, use_container_width=True)
                        
                        # Recent activity
                        if not insights['recent_activity'].empty:
                            st.markdown("### 📅 Recent Activity Trends")
                            insights['recent_activity']['processed_date'] = pd.to_datetime(insights['recent_activity']['processed_date'])
                            
                            fig = px.line(
                                insights['recent_activity'].sort_values('processed_date'),
                                x='processed_date',
                                y='total_deals',
                                title="Daily Deal Volume"
                            )
                            st.plotly_chart(fig, use_container_width=True)
                        
                        # Value distribution
                        if not insights['value_distribution'].empty:
                            st.markdown("### 💰 Value Distribution by Currency")
                            st.dataframe(insights['value_distribution'], use_container_width=True)
                    
                    else:
                        st.info("No historical data available yet. Process some emails first!")

if __name__ == "__main__":
    main()