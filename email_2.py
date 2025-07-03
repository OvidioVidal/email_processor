import streamlit as st
import pandas as pd
import re
from typing import List, Dict, Any, Set
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
import sqlite3
import json
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
    
    .database-stats {
        background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

class DatabaseManager:
    def __init__(self, db_path: str = "email_intelligence.db"):
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
                original_content TEXT NOT NULL,
                formatted_content TEXT,
                email_formatted_content TEXT,
                processed_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                total_lines INTEGER,
                section_count INTEGER,
                deal_count INTEGER,
                monetary_value_count INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create sections table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_id INTEGER,
                section_name TEXT,
                section_order INTEGER,
                FOREIGN KEY (email_id) REFERENCES emails (id)
            )
        ''')
        
        # Create deals table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS deals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_id INTEGER,
                deal_number INTEGER,
                deal_title TEXT,
                section_name TEXT,
                deal_content TEXT,
                FOREIGN KEY (email_id) REFERENCES emails (id)
            )
        ''')
        
        # Create monetary_values table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS monetary_values (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_id INTEGER,
                currency TEXT,
                amount_text TEXT,
                extracted_value REAL,
                context TEXT,
                FOREIGN KEY (email_id) REFERENCES emails (id)
            )
        ''')
        
        # Create companies table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_id INTEGER,
                company_name TEXT,
                context TEXT,
                confidence_score REAL,
                FOREIGN KEY (email_id) REFERENCES emails (id)
            )
        ''')
        
        # Create metadata table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_id INTEGER,
                key_name TEXT,
                value_text TEXT,
                FOREIGN KEY (email_id) REFERENCES emails (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_email_data(self, content: str, formatted_content: str, email_formatted_content: str, analysis_data: Dict[str, Any]) -> int:
        """Save email data and return the email ID"""
        # Create content hash for deduplication
        content_hash = hashlib.md5(content.encode()).hexdigest()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Insert main email record
            cursor.execute('''
                INSERT OR REPLACE INTO emails (
                    content_hash, original_content, formatted_content, email_formatted_content,
                    total_lines, section_count, deal_count, monetary_value_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                content_hash, content, formatted_content, email_formatted_content,
                analysis_data['total_lines'], len(analysis_data['sections']),
                len(analysis_data['deals']), len(set(analysis_data['monetary_values']))
            ))
            
            email_id = cursor.lastrowid
            
            # Insert sections
            for i, section in enumerate(analysis_data['sections']):
                cursor.execute('''
                    INSERT INTO sections (email_id, section_name, section_order)
                    VALUES (?, ?, ?)
                ''', (email_id, section, i))
            
            # Insert deals
            for deal in analysis_data['deals']:
                cursor.execute('''
                    INSERT INTO deals (email_id, deal_number, deal_title, section_name, deal_content)
                    VALUES (?, ?, ?, ?, ?)
                ''', (email_id, deal.get('number', 0), deal.get('title', ''), 
                      deal.get('section', ''), deal.get('title', '')))
            
            # Insert monetary values
            for value in analysis_data['monetary_values']:
                # Extract numeric value if possible
                numeric_value = self._extract_numeric_value(value)
                currency = self._extract_currency(value)
                
                cursor.execute('''
                    INSERT INTO monetary_values (email_id, currency, amount_text, extracted_value, context)
                    VALUES (?, ?, ?, ?, ?)
                ''', (email_id, currency, value, numeric_value, value))
            
            # Insert metadata
            for key, value in analysis_data['metadata'].items():
                cursor.execute('''
                    INSERT INTO metadata (email_id, key_name, value_text)
                    VALUES (?, ?, ?)
                ''', (email_id, key, str(value)))
            
            conn.commit()
            return email_id
            
        except Exception as e:
            conn.rollback()
            st.error(f"Database error: {str(e)}")
            return None
        finally:
            conn.close()
    
    def _extract_numeric_value(self, monetary_text: str) -> float:
        """Extract numeric value from monetary text"""
        try:
            # Remove currency symbols and extract numbers
            numbers = re.findall(r'[\d,\.]+', monetary_text)
            if numbers:
                # Take the first number and clean it
                clean_number = numbers[0].replace(',', '')
                base_value = float(clean_number)
                
                # Check for multipliers
                if 'billion' in monetary_text.lower() or 'bn' in monetary_text.lower():
                    return base_value * 1000000000
                elif 'million' in monetary_text.lower() or 'm' in monetary_text.lower():
                    return base_value * 1000000
                else:
                    return base_value
            return 0.0
        except:
            return 0.0
    
    def _extract_currency(self, monetary_text: str) -> str:
        """Extract currency from monetary text"""
        if 'EUR' in monetary_text.upper() or '€' in monetary_text:
            return 'EUR'
        elif 'USD' in monetary_text.upper() or '$' in monetary_text:
            return 'USD'
        elif 'GBP' in monetary_text.upper() or '£' in monetary_text:
            return 'GBP'
        elif 'CNY' in monetary_text.upper():
            return 'CNY'
        return 'UNKNOWN'
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics for dashboard"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = {}
        
        # Total emails
        cursor.execute("SELECT COUNT(*) FROM emails")
        stats['total_emails'] = cursor.fetchone()[0]
        
        # Total deals
        cursor.execute("SELECT COUNT(*) FROM deals")
        stats['total_deals'] = cursor.fetchone()[0]
        
        # Total monetary values
        cursor.execute("SELECT COUNT(*) FROM monetary_values")
        stats['total_monetary_values'] = cursor.fetchone()[0]
        
        # Recent activity (last 7 days)
        cursor.execute("SELECT COUNT(*) FROM emails WHERE created_at >= datetime('now', '-7 days')")
        stats['recent_emails'] = cursor.fetchone()[0]
        
        # Top sections
        cursor.execute('''
            SELECT section_name, COUNT(*) as count 
            FROM sections 
            GROUP BY section_name 
            ORDER BY count DESC 
            LIMIT 5
        ''')
        stats['top_sections'] = cursor.fetchall()
        
        # Currency distribution
        cursor.execute('''
            SELECT currency, COUNT(*) as count, SUM(extracted_value) as total_value
            FROM monetary_values 
            GROUP BY currency 
            ORDER BY count DESC
        ''')
        stats['currency_distribution'] = cursor.fetchall()
        
        # Daily activity over last 30 days
        cursor.execute('''
            SELECT DATE(created_at) as date, COUNT(*) as count
            FROM emails 
            WHERE created_at >= datetime('now', '-30 days')
            GROUP BY DATE(created_at)
            ORDER BY date DESC
        ''')
        stats['daily_activity'] = cursor.fetchall()
        
        conn.close()
        return stats
<<<<<<< HEAD
    
    def search_emails(self, search_term: str, limit: int = 20) -> List[Dict]:
        """Search emails by content"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, original_content, processed_date, section_count, deal_count
            FROM emails 
            WHERE original_content LIKE ? 
            ORDER BY processed_date DESC 
            LIMIT ?
        ''', (f'%{search_term}%', limit))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'id': row[0],
                'content_preview': row[1][:200] + '...' if len(row[1]) > 200 else row[1],
                'date': row[2],
                'sections': row[3],
                'deals': row[4]
            })
        
        conn.close()
        return results

class SmartTextProcessor:
    def __init__(self):
        self.db_manager = DatabaseManager()
        
        # Define allowed categories - only these will be processed
        self.allowed_categories = {
            'automotive',
            'computer software',
            'consumer: foods',
            'consumer: other', 
            'consumer: retail',
            'defense',
            'financial services',
            'industrial automation',
            'industrial products and services',
            'industrial: electronics',
            'services (other)'
        }
        
=======

class SmartTextProcessor:
    def __init__(self):
>>>>>>> parent of 0d84145 (Add sector filtering and priority sector logic)
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

    def _is_allowed_category(self, section_name: str) -> bool:
        """Check if a section category is in the allowed list"""
        if not section_name:
            return False
        
        section_lower = section_name.lower().strip()
        
        # Direct match first
        if section_lower in self.allowed_categories:
            return True
        
        # Check for partial matches (e.g., "industrial automation" should match "industrial: automation")
        for allowed_cat in self.allowed_categories:
            # Remove punctuation and compare
            section_clean = re.sub(r'[^\w\s]', '', section_lower)
            allowed_clean = re.sub(r'[^\w\s]', '', allowed_cat)
            
            if section_clean == allowed_clean:
                return True
        
        return False

    def _extract_numbered_items_by_category(self, content: str) -> Dict[str, List[int]]:
        """Extract which numbered items belong to which categories"""
        lines = content.split('\n')
        category_to_numbers = {}
        current_category = None
        
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue
                
            # Check if this is a section header
            if self._is_section_header(line_stripped):
                current_category = line_stripped
                if current_category not in category_to_numbers:
                    category_to_numbers[current_category] = []
            
            # Check if this is a numbered item
            elif re.match(r'^\d+\.', line_stripped) and current_category:
                # Extract the number
                match = re.match(r'^(\d+)\.', line_stripped)
                if match:
                    item_number = int(match.group(1))
                    category_to_numbers[current_category].append(item_number)
        
        return category_to_numbers

    def _get_allowed_item_numbers(self, content: str) -> Set[int]:
        """Get the numbers of items that belong to allowed categories"""
        category_to_numbers = self._extract_numbered_items_by_category(content)
        allowed_numbers = set()
        
        for category, numbers in category_to_numbers.items():
            if self._is_allowed_category(category):
                allowed_numbers.update(numbers)
        
        return allowed_numbers

    def _filter_content_by_category(self, content: str) -> str:
        """Filter content to only include allowed categories and their corresponding press releases"""
        lines = content.split('\n')
        filtered_lines = []
        
        # First pass: get which numbered items belong to allowed categories
        allowed_numbers = self._get_allowed_item_numbers(content)
        
        current_section = None
        include_current_section = False
        in_detailed_section = False
        current_item_number = None
        
        for line in lines:
            line_stripped = line.strip()
            
            # Empty lines are preserved if we're in an allowed section
            if not line_stripped:
                if include_current_section or (in_detailed_section and current_item_number in allowed_numbers):
                    filtered_lines.append(line)
                continue
            
            # Check if this is a section header
            if self._is_section_header(line_stripped):
                current_section = line_stripped
                include_current_section = self._is_allowed_category(current_section)
                in_detailed_section = False
                current_item_number = None
                
                # Only add the section header if it's allowed
                if include_current_section:
                    # Add some spacing before new sections (except first)
                    if filtered_lines and filtered_lines[-1].strip():
                        filtered_lines.append('')
                    filtered_lines.append(line)
            
            # Check if this is a numbered item (could be title or detailed section)
            elif re.match(r'^\d+\.', line_stripped):
                match = re.match(r'^(\d+)\.', line_stripped)
                if match:
                    item_number = int(match.group(1))
                    current_item_number = item_number
                    
                    # If we're in the initial categorized list
                    if current_section and include_current_section:
                        filtered_lines.append(line)
                        in_detailed_section = False
                    
                    # If this looks like a detailed press release section (longer text after number)
                    elif item_number in allowed_numbers:
                        # This is a detailed section for an allowed item
                        in_detailed_section = True
                        # Add spacing before detailed sections
                        if filtered_lines and filtered_lines[-1].strip():
                            filtered_lines.append('')
                        filtered_lines.append(line)
                        include_current_section = False  # Override section-based logic
            
            # Handle all other content
            else:
                # If we're in an allowed section OR we're in a detailed section for an allowed item
                if include_current_section or (in_detailed_section and current_item_number in allowed_numbers):
                    filtered_lines.append(line)
        
        return '\n'.join(filtered_lines)

    def format_raw_text(self, content: str) -> str:
        """Format raw text into a more readable structure with HTML"""
        if not content.strip():
            return "No content to format."
        
        # First filter content by allowed categories
        filtered_content = self._filter_content_by_category(content)
        
        if not filtered_content.strip():
            return '<div class="section-header">⚠️ NO ALLOWED CATEGORIES FOUND</div><p style="color: #e74c3c; margin: 1rem 0;">The input text does not contain any of the allowed categories. Please check if the section headers match the permitted categories.</p>'
        
        lines = filtered_content.split('\n')
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
        
        # First filter content by allowed categories
        filtered_content = self._filter_content_by_category(content)
        
        if not filtered_content.strip():
            return "NO ALLOWED CATEGORIES FOUND\n\nThe input text does not contain any of the allowed categories.\nPlease check if the section headers match the permitted categories:\n\n" + \
                   "\n".join(f"• {cat.title()}" for cat in sorted(self.allowed_categories))
        
        lines = filtered_content.split('\n')
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

<<<<<<< HEAD
=======
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

>>>>>>> parent of 0d84145 (Add sector filtering and priority sector logic)
    def _is_section_header(self, line: str) -> bool:
        """Check if line is likely a section header"""
        if not line.strip():
            return False
            
        words = line.split()
        line_clean = line.strip()
        
        # Exclude common press release patterns that shouldn't be treated as section headers
        press_release_patterns = [
            r'press release',
            r'announces',
            r'reports',
            r'declares',
            r'completes',
            r'enters into',
            r'signs',
            r'agrees to',
            r'launches',
            r'unveils',
            r'introduces',
            r'expands',
            r'acquires',
            r'merges with',
            r'partners with'
        ]
        
        # Check if line contains press release language
        for pattern in press_release_patterns:
            if re.search(pattern, line_clean, re.IGNORECASE):
                return False
        
        # Exclude lines that are clearly content, not headers
        if (re.search(r'\b(said|stated|reported|according to|sources|today|yesterday|this week|last month)\b', line_clean, re.IGNORECASE) or
            re.search(r'\b(the company|the firm|the group|executives|management|ceo|cfo)\b', line_clean, re.IGNORECASE) or
            re.search(r'\b(will|would|could|should|may|might|is expected|plans to)\b', line_clean, re.IGNORECASE)):
            return False
        
        # More strict criteria for section headers
        return (len(words) <= 4 and  # Allow up to 4 words for headers like "Industrial: Electronics"
                len(line_clean) < 60 and    # Reasonable length limit
                not line_clean.startswith('*') and
                not line_clean.startswith('-') and 
                not line_clean.startswith('•') and
                not re.match(r'^\d+\.', line_clean) and  # Not a numbered item
                not any(char in line_clean for char in ['(', ')', '€', '$', '£']) and  # No monetary symbols
                not line_clean.lower().startswith('source:') and  # Not metadata
                not line_clean.lower().startswith('size:') and
                not line_clean.lower().startswith('grade:') and
                not line_clean.lower().startswith('intelligence') and
                not line_clean.lower().startswith('alert:') and
                (':' not in line_clean.lower() or line_clean.count(':') == 1) and  # Allow one colon for "Consumer: Foods" format
                not re.search(r'\d{4}', line_clean) and  # No years
                not re.search(r'[A-Z]{2,}\s+\d', line_clean))  # No currency codes with numbers

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
        # First filter content by allowed categories
        filtered_content = self._filter_content_by_category(content)
        lines = filtered_content.split('\n')
        
        info = {
            'total_lines': len([l for l in lines if l.strip()]),
            'sections': [],
            'deals': [],
            'monetary_values': [],
            'companies': [],
            'metadata': {},
            'filtered_categories': []  # Track which categories were included
        }
        
        current_section = None
        deal_count = 0
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Track sections (only allowed ones will be here after filtering)
            if self._is_section_header(line):
                current_section = line
                info['sections'].append(line)
                if self._is_allowed_category(line):
                    info['filtered_categories'].append(line.lower().strip())
            
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

    def _detect_press_releases(self, content: str) -> List[str]:
        """Detect press release content within the text"""
        lines = content.split('\n')
        press_releases = []
        
        press_release_patterns = [
            r'announces',
            r'reports',
            r'declares',
            r'completes',
            r'enters into',
            r'signs',
            r'launches',
            r'unveils',
            r'introduces',
            r'secures'
        ]
        
        for line in lines:
            line_stripped = line.strip()
            if line_stripped and not self._is_section_header(line_stripped):
                for pattern in press_release_patterns:
                    if re.search(pattern, line_stripped, re.IGNORECASE):
                        # Extract a meaningful preview of the press release
                        preview = line_stripped[:80] + "..." if len(line_stripped) > 80 else line_stripped
                        press_releases.append(preview)
                        break
        
        return press_releases

    def _get_filtering_report(self, content: str) -> Dict[str, Any]:
        """Generate a report of what was filtered during processing"""
        lines = content.split('\n')
        all_sections = []
        allowed_sections = []
        filtered_sections = []
        
        # Get category mappings
        category_to_numbers = self._extract_numbered_items_by_category(content)
        allowed_numbers = self._get_allowed_item_numbers(content)
        
        # Count total and allowed numbered items
        total_numbered_items = sum(len(numbers) for numbers in category_to_numbers.values())
        allowed_numbered_items = len(allowed_numbers)
        
        # Detect press releases in original content
        original_press_releases = self._detect_press_releases(content)
        
        # Detect press releases in filtered content
        filtered_content = self._filter_content_by_category(content)
        preserved_press_releases = self._detect_press_releases(filtered_content)
        
        for line in lines:
            line_stripped = line.strip()
            if self._is_section_header(line_stripped):
                all_sections.append(line_stripped)
                if self._is_allowed_category(line_stripped):
                    allowed_sections.append(line_stripped)
                else:
                    filtered_sections.append(line_stripped)
        
        return {
            'total_sections': len(all_sections),
            'allowed_sections': allowed_sections,
            'filtered_sections': filtered_sections,
            'sections_kept': len(allowed_sections),
            'sections_removed': len(filtered_sections),
            'total_numbered_items': total_numbered_items,
            'allowed_numbered_items': allowed_numbered_items,
            'filtered_numbered_items': total_numbered_items - allowed_numbered_items,
            'original_press_releases': len(original_press_releases),
            'preserved_press_releases': len(preserved_press_releases),
            'press_release_examples': preserved_press_releases[:3],  # Show first 3 as examples
            'allowed_item_numbers': sorted(list(allowed_numbers)) if allowed_numbers else []
        }

    def process_and_save(self, content: str) -> Dict[str, Any]:
        """Process text and save to database"""
        # Generate filtering report first
        filtering_report = self._get_filtering_report(content)
        
        # Format the content
        formatted_text = self.format_raw_text(content)
        email_formatted_text = self.format_for_email(content)
        
        # Extract key information
        analysis_data = self.extract_key_information(content)
        
        # Add filtering report to analysis data
        analysis_data['filtering_report'] = filtering_report
        
        # Save to database
        email_id = self.db_manager.save_email_data(
            content, formatted_text, email_formatted_text, analysis_data
        )
        
        return {
            'email_id': email_id,
            'formatted_text': formatted_text,
            'email_formatted_text': email_formatted_text,
            'analysis_data': analysis_data,
            'filtering_report': filtering_report
        }

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

def create_analytics_dashboard(db_manager: DatabaseManager):
    """Create analytics dashboard for market insights"""
    st.markdown("### 📊 Market Intelligence Dashboard")
    
    # Get database stats
    stats = db_manager.get_database_stats()
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📧 Total Emails", stats['total_emails'])
    
    with col2:
        st.metric("🎯 Total Deals", stats['total_deals'])
    
    with col3:
        st.metric("💰 Monetary Values", stats['total_monetary_values'])
    
    with col4:
        st.metric("🔄 Recent (7 days)", stats['recent_emails'])
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        if stats['top_sections']:
            st.markdown("#### 📈 Top Sectors")
            sections_df = pd.DataFrame(stats['top_sections'], columns=['Section', 'Count'])
            fig = px.bar(sections_df, x='Section', y='Count', title="Deal Distribution by Sector")
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        if stats['currency_distribution']:
            st.markdown("#### 💱 Currency Distribution")
            currency_df = pd.DataFrame(stats['currency_distribution'], columns=['Currency', 'Count', 'Total_Value'])
            fig = px.pie(currency_df, values='Count', names='Currency', title="Currency Distribution")
            st.plotly_chart(fig, use_container_width=True)
    
    # Daily activity chart
    if stats['daily_activity']:
        st.markdown("#### 📅 Daily Activity (Last 30 Days)")
        activity_df = pd.DataFrame(stats['daily_activity'], columns=['Date', 'Count'])
        activity_df['Date'] = pd.to_datetime(activity_df['Date'])
        fig = px.line(activity_df, x='Date', y='Count', title="Daily Email Processing Activity")
        st.plotly_chart(fig, use_container_width=True)

def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🎯 Smart Text Formatter & M&A Intelligence Processor</h1>
        <p>Transform raw text and M&A data into professionally formatted, readable content with market intelligence</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize processor
    if 'processor' not in st.session_state:
        st.session_state.processor = SmartTextProcessor()
    
<<<<<<< HEAD
    # Sidebar for navigation
    with st.sidebar:
        st.markdown("### 🗂️ Navigation")
        page = st.selectbox("Choose Function:", 
                           ["📝 Text Formatter", "📊 Analytics Dashboard", "🔍 Search History"])
        
        # Add allowed categories display
        st.markdown("### 🏷️ Allowed Categories")
        st.markdown("**Only these categories will be processed:**")
        
        allowed_cats = [
    "Automotive",
    "Computer software",
    "Consumer: Foods",
    "Consumer: Other",
    "Consumer: Retail",
    "Defense",
    "Financial Services",
    "Industrial automation",
    "Industrial products and services",
    "Industrial: Electronics",
    "Services (other)"
]

        for cat in allowed_cats:
            st.markdown(f"✅ {cat}")
        
=======
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
>>>>>>> parent of 0d84145 (Add sector filtering and priority sector logic)
        st.markdown("---")
        st.markdown("*Content from other categories will be automatically filtered out.*")
        
        st.markdown("### 📰 Press Release Handling")
        st.markdown("✅ **Press releases within allowed categories are preserved**")
        st.markdown("🚫 **Press releases in filtered categories are removed**")
        st.markdown("📊 **System tracks and reports press release retention**")
    
    if page == "📝 Text Formatter":
        # Main layout
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("📝 Raw Text Input")
            
            # Sample data for demonstration
            sample_data = """Automotive

1. Daimler Truck, Volvo launch software JV Coretura

2. VivoPower secures USD 121m investment led by Abdulaziz bin Turki

Chemicals and materials

3. Socomore in exclusive talks to raise over EUR 100m (translated)

Computer software

4. Aya Healthcare acquires Locum's Nest

5. TTC Group acquires Think Eleven

Consumer: Foods

6. Moyca attracts interest from industrial, financial groups - report (translated)

Consumer: Other

7. Eurmoda poised to close two acquisitions this year, double turnover – sponsor

Energy

8. Solar power company seeks strategic investor

9. Naturgy voluntary takeover bid gets 86.37% acceptance

Financial Services

10. Metro Bank majority owner Gilinski considers sale of stake – report

11. Athora in talks to acquire PIC for up to GBP 5bn – report

1. Daimler Truck, Volvo launch software JV Coretura

* Focus on software development for commercial vehicles
* 50% held by each parent
* Volume of investments depends on milestones, technical progress

Daimler Truck, a German vehicle maker, and Swedish auto group Volvo have announced the launch of a software joint venture named Coretura.

Source: Company Press Release(s)
Size: 1bn-5bn (EUR)
Grade: Confirmed

2. VivoPower secures USD 121m investment led by Abdulaziz bin Turki

* First phase is equal to gross proceeds of USD 60.5m
* Remaining 50% of private placement expected to close shortly
* Funds to support VivoPower's Ripple, XRP-focused treasury, DeFi solutions

VivoPower International PLC today announced that it has closed the first phase of the previously announced US$121 million investment round led by His Royal Highness Prince Abdulaziz bin Turki bin Talal Al Saud.

Source: Company Press Release(s)
Size: 60m-300m (GBP)
Grade: Confirmed

3. Socomore in exclusive talks to raise over EUR 100m (translated)

* Transaction led by new investor Three Hills
* President to retain majority, existing backers to reinvest
* Socomore has 450 staff, EUR 120m turnover, EUR 20m+ EBITDA

Socomore, a French surface treatment company specializing in high-tech chemical products, has entered into exclusive negotiations with a group of investors led by Three Hills.

Source: Atlantique Presse Information
Size: 60m-300m (GBP)
Grade: Confirmed

4. Aya Healthcare acquires Locum's Nest

* Combination enhances value for clients
* Locum's Nest streamlines NHS hospital shift filling
* Aya operates world's largest digital staffing platform for healthcare labor services

Aya Healthcare, the largest healthcare talent software and staffing company in the United States, today announced the acquisition of Locum's Nest, a leading workforce solutions provider in the United Kingdom.

Source: Company Press Release(s)
Size: < 60m (GBP)
Grade: Confirmed

5. TTC Group acquires Think Eleven

* TTC's third acquisition in 18 months
* TTC owned by Pricoa Private Capital

TTC Group, a UK-based provider of people risk management solutions, has acquired Think Eleven, a Seaham, UK-based specialist international provider of competency management software and services.

Source: Company Press Release(s)
Size: < 60m (GBP)
Grade: Confirmed

6. Moyca attracts interest from industrial, financial groups - report (translated)

* No formal bids for Moyca, despite interest from multiple parties
* Moyca's 2024 revenues EUR 190m, EBITDA EUR 29m, potential sale at 6-7 times EBITDA
* Deutsche Bank exploring sale of Moyca, acquired by ProA Capital in 2016

Moyca, a Spanish agricultural company owned by private equity firm ProA Capital, has attracted interest from both industrial and financial groups.

Source: El Economista
Size: 60m-300m (GBP)
Grade: Strong evidence

7. Eurmoda poised to close two acquisitions this year, double turnover – sponsor

* Expects turnover to reach EUR 90m post acquisitions
* Aurora maintains 'rich' pipeline of potential targets

Italian manufacturer Eurmoda is set to double its turnover with two strategic acquisitions expected to close this year, according to Piero Migliorini, partner at its sponsor Aurora Growth Capital.

Source: Proprietary Intelligence
Size: < 30m (GBP)
Grade: Confirmed

8. Solar power company seeks strategic investor

* Renewable energy expansion in Asia
* Funding requirement USD 300m
* IPO alternative being considered

A solar power company is seeking strategic investment for expansion in Asian markets with a funding requirement of USD 300 million.

Source: Wall Street Journal
Size: 200m-500m (USD)
Grade: Confirmed

9. Naturgy voluntary takeover bid gets 86.37% acceptance

* Takeover bid successful with high acceptance rate
* Strong shareholder support for the transaction

Naturgy's voluntary takeover bid has achieved an 86.37% acceptance rate from shareholders, marking a successful transaction.

Source: Company Announcement
Size: > 1bn (EUR)
Grade: Confirmed

10. Metro Bank majority owner Gilinski considers sale of stake – report

* Potential divestment by major shareholder
* Strategic review of ownership structure

Metro Bank's majority owner Gilinski is reportedly considering the sale of his stake in the British challenger bank.

Source: Financial media reports
Size: 300m-1bn (GBP)
Grade: Strong evidence

11. Athora in talks to acquire PIC for up to GBP 5bn – report

* Major acquisition in insurance sector
* Deal valued at up to GBP 5 billion

Insurance group Athora is reportedly in talks to acquire Pension Insurance Corporation (PIC) in a deal that could be worth up to GBP 5 billion.

Source: Financial media reports
Size: > 1bn (GBP)
Grade: Strong evidence"""
            
            text_input = st.text_area(
                "Paste your raw text here:",
                value=sample_data,
                height=500,
                help="Paste any raw text content. The system will automatically format it and save to database for analysis."
            )
            
            col_a, col_b = st.columns(2)
            
            with col_a:
                format_button = st.button("🚀 Process & Save", type="primary", use_container_width=True)
            
            with col_b:
                clear_button = st.button("🗑️ Clear", use_container_width=True)
            
            if clear_button:
                st.rerun()
        
        with col2:
            st.subheader("📊 Formatted Output")
            
<<<<<<< HEAD
            if format_button and text_input:
                with st.spinner("Processing and saving to database..."):
                    # Process and save to database
                    result = st.session_state.processor.process_and_save(text_input)
                    
                    # Store in session state
                    st.session_state.formatted_text = result['formatted_text']
                    st.session_state.email_formatted_text = result['email_formatted_text']
                    st.session_state.analysis_data = result['analysis_data']
                    st.session_state.email_id = result['email_id']
                    
                    # Show success message with filtering info
                    if result['email_id']:
                        st.success(f"✅ Email saved to database with ID: {result['email_id']}")
                        
                        # Display detailed filtering statistics
                        filtering_report = result['filtering_report']
                        
                        col_stats1, col_stats2 = st.columns(2)
                        
                        with col_stats1:
                            if filtering_report['allowed_sections']:
                                st.info(f"✅ **{filtering_report['sections_kept']} Categories Processed:**")
                                for section in filtering_report['allowed_sections']:
                                    st.write(f"  • {section}")
                            else:
                                st.warning("⚠️ **No allowed categories found in the input text.**")
                        
                        with col_stats2:
                            if filtering_report['filtered_sections']:
                                st.warning(f"🚫 **{filtering_report['sections_removed']} Categories Filtered Out:**")
                                for section in filtering_report['filtered_sections']:
                                    st.write(f"  • {section}")
                            else:
                                st.success("✨ **All sections were in allowed categories!**")
                        
                        # Numbered items information
                        if filtering_report.get('total_numbered_items', 0) > 0:
                            st.info(f"🔢 **Numbered Items**: {filtering_report['allowed_numbered_items']} of {filtering_report['total_numbered_items']} items preserved (Numbers: {', '.join(map(str, filtering_report['allowed_item_numbers'][:10]))})")
                        
                        # Press release information
                        if filtering_report.get('original_press_releases', 0) > 0:
                            st.info(f"📰 **Press Releases**: {filtering_report['preserved_press_releases']} of {filtering_report['original_press_releases']} preserved under allowed categories")
                            
                            if filtering_report.get('press_release_examples'):
                                with st.expander("View Press Release Examples"):
                                    for example in filtering_report['press_release_examples']:
                                        st.write(f"• {example}")
                        
                        # Summary
                        if filtering_report['total_sections'] > 0:
                            retention_rate = (filtering_report['sections_kept'] / filtering_report['total_sections']) * 100
                            st.metric("📊 Content Retention Rate", f"{retention_rate:.1f}%")
                        
                    else:
                        st.error("❌ Failed to save to database")
            
            # Display formatted text if available
            if 'formatted_text' in st.session_state:
                # Tabs for different viewing options
                tab1, tab2 = st.tabs(["🖥️ Web View", "📧 Email Ready"])
                
                with tab1:
                    st.markdown(f"""
=======
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
>>>>>>> parent of 0d84145 (Add sector filtering and priority sector logic)
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
                    
<<<<<<< HEAD
                    col_copy, col_download = st.columns(2) 
=======
                    else:
                        st.info("No historical data available yet. Process some emails first!")
        
        with tab5:
            st.subheader("🗃️ Database Viewer")
            st.info("View all data stored in the database from processed emails")
            
            # Load database contents
            if st.button("🔄 Load Database Contents", use_container_width=True):
                with st.spinner("Loading database contents..."):
                    db_contents = st.session_state.db_manager.get_all_database_contents()
                    st.session_state.db_contents = db_contents
            
            if 'db_contents' in st.session_state:
                db_contents = st.session_state.db_contents
                
                # Create sub-tabs for different tables
                db_tab1, db_tab2, db_tab3, db_tab4, db_tab5 = st.tabs(["📧 Emails", "🤝 Deals", "📁 Sections", "💰 Values", "📋 Metadata"])
                
                with db_tab1:
                    st.markdown("### 📧 Processed Emails")
                    if not db_contents['emails'].empty:
                        st.dataframe(db_contents['emails'], use_container_width=True, hide_index=True)
                        
                        # Email management controls
                        st.markdown("#### 🔧 Email Management")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("##### 🔍 View Email Details")
                            email_ids = db_contents['emails']['id'].tolist()
                            selected_email_id = st.selectbox("Select Email ID to view details:", email_ids, key="view_email_select")
                            
                            if st.button("📖 View Full Email Details", key="view_email_btn"):
                                email_details = st.session_state.db_manager.get_email_details(selected_email_id)
                                
                                st.markdown("##### Email Information")
                                st.dataframe(email_details['email_info'], use_container_width=True, hide_index=True)
                                
                                if not email_details['deals'].empty:
                                    st.markdown("##### Associated Deals")
                                    st.dataframe(email_details['deals'], use_container_width=True, hide_index=True)
                                
                                if not email_details['sections'].empty:
                                    st.markdown("##### Associated Sections")  
                                    st.dataframe(email_details['sections'], use_container_width=True, hide_index=True)
                                
                                if not email_details['monetary_values'].empty:
                                    st.markdown("##### Associated Monetary Values")
                                    st.dataframe(email_details['monetary_values'], use_container_width=True, hide_index=True)
                                
                                if not email_details['metadata'].empty:
                                    st.markdown("##### Associated Metadata")
                                    st.dataframe(email_details['metadata'], use_container_width=True, hide_index=True)
                        
                        with col2:
                            st.markdown("##### 🗑️ Delete Email")
                            st.warning("⚠️ This will delete the email and ALL associated data!")
                            
                            delete_email_id = st.selectbox("Select Email ID to delete:", email_ids, key="delete_email_select")
                            
                            # Confirmation checkbox
                            confirm_delete = st.checkbox("I confirm I want to delete this email and all its data", key="confirm_delete_email")
                            
                            if st.button("🗑️ Delete Email", type="secondary", disabled=not confirm_delete, key="delete_email_btn"):
                                if st.session_state.db_manager.delete_email(delete_email_id):
                                    st.success(f"✅ Email {delete_email_id} and all associated data deleted successfully!")
                                    # Refresh the data
                                    st.session_state.db_contents = st.session_state.db_manager.get_all_database_contents()
                                    st.rerun()
                                else:
                                    st.error("❌ Failed to delete email")
                    else:
                        st.info("No emails found in database")
                
                with db_tab2:
                    st.markdown("### 🤝 All Deals")
                    if not db_contents['deals'].empty:
                        st.dataframe(db_contents['deals'], use_container_width=True, hide_index=True)
                        
                        # Quick stats
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Total Deals", len(db_contents['deals']))
                        with col2:
                            top_sector = db_contents['deals']['sector'].mode().iloc[0] if len(db_contents['deals']) > 0 else 'N/A'
                            st.metric("Top Sector", top_sector)
                        with col3:
                            top_geo = db_contents['deals']['geography'].mode().iloc[0] if len(db_contents['deals']) > 0 else 'N/A'
                            st.metric("Top Geography", top_geo)
                        
                        # Deal deletion
                        st.markdown("#### 🗑️ Delete Individual Deal")
                        st.warning("⚠️ This will delete the selected deal only!")
                        
                        deal_ids = db_contents['deals']['id'].tolist()
                        deal_titles = db_contents['deals']['title'].tolist()
                        deal_options = [f"ID {deal_id}: {title[:50]}..." if len(title) > 50 else f"ID {deal_id}: {title}" 
                                      for deal_id, title in zip(deal_ids, deal_titles)]
                        
                        selected_deal_option = st.selectbox("Select Deal to delete:", deal_options, key="delete_deal_select")
                        selected_deal_id = int(selected_deal_option.split(":")[0].replace("ID ", ""))
                        
                        confirm_delete_deal = st.checkbox("I confirm I want to delete this deal", key="confirm_delete_deal")
                        
                        if st.button("🗑️ Delete Deal", type="secondary", disabled=not confirm_delete_deal, key="delete_deal_btn"):
                            if st.session_state.db_manager.delete_deal(selected_deal_id):
                                st.success(f"✅ Deal {selected_deal_id} deleted successfully!")
                                # Refresh the data
                                st.session_state.db_contents = st.session_state.db_manager.get_all_database_contents()
                                st.rerun()
                            else:
                                st.error("❌ Failed to delete deal")
                    else:
                        st.info("No deals found in database")
                
                with db_tab3:
                    st.markdown("### 📁 Sections")
                    if not db_contents['sections'].empty:
                        st.dataframe(db_contents['sections'], use_container_width=True, hide_index=True)
                        
                        # Section summary
                        section_summary = db_contents['sections'].groupby('section_name')['deal_count'].sum().reset_index()
                        section_summary = section_summary.sort_values('deal_count', ascending=False)
                        
                        st.markdown("#### Section Deal Counts")
                        fig = px.bar(section_summary, x='section_name', y='deal_count', 
                                   title="Total Deals by Section")
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No sections found in database")
                
                with db_tab4:
                    st.markdown("### 💰 Monetary Values")
                    if not db_contents['monetary_values'].empty:
                        st.dataframe(db_contents['monetary_values'], use_container_width=True, hide_index=True)
                        
                        # Currency distribution
                        currency_dist = db_contents['monetary_values']['currency'].value_counts().reset_index()
                        currency_dist.columns = ['currency', 'count']
                        
                        if not currency_dist.empty:
                            st.markdown("#### Currency Distribution")
                            fig = px.pie(currency_dist, values='count', names='currency', 
                                       title="Distribution of Currencies")
                            st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No monetary values found in database")
                
                with db_tab5:
                    st.markdown("### 📋 Metadata")
                    if not db_contents['metadata'].empty:
                        st.dataframe(db_contents['metadata'], use_container_width=True, hide_index=True)
                        
                        # Metadata keys distribution
                        key_dist = db_contents['metadata']['key'].value_counts().reset_index()
                        key_dist.columns = ['key', 'count']
                        
                        if not key_dist.empty:
                            st.markdown("#### Metadata Keys Distribution")
                            fig = px.bar(key_dist, x='key', y='count', 
                                       title="Frequency of Metadata Keys")
                            st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No metadata found in database")
                
                # Database statistics
                st.markdown("---")
                st.markdown("### 📊 Database Statistics")
                
                col1, col2, col3, col4, col5 = st.columns(5)
                
                with col1:
                    st.metric("Total Emails", len(db_contents['emails']))
                with col2:
                    st.metric("Total Deals", len(db_contents['deals']))
                with col3:
                    st.metric("Total Sections", len(db_contents['sections']))
                with col4:
                    st.metric("Total Values", len(db_contents['monetary_values']))
                with col5:
                    st.metric("Total Metadata", len(db_contents['metadata']))
                
                # Database Management
                st.markdown("---")
                st.markdown("### ⚙️ Database Management")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("#### 🔄 Refresh Database")
                    if st.button("🔄 Refresh All Data", use_container_width=True):
                        with st.spinner("Refreshing database contents..."):
                            st.session_state.db_contents = st.session_state.db_manager.get_all_database_contents()
                            st.success("✅ Database contents refreshed!")
                            st.rerun()
                
                with col2:
                    st.markdown("#### 🚨 Clear All Data")
                    st.error("⚠️ DANGER ZONE: This will delete ALL data from the database!")
>>>>>>> parent of 0d84145 (Add sector filtering and priority sector logic)
                    
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
                st.info("Ready to format your text. Paste content and click 'Process & Save'")
    
    elif page == "📊 Analytics Dashboard":
        create_analytics_dashboard(st.session_state.processor.db_manager)
    
    elif page == "🔍 Search History":
        st.markdown("### 🔍 Search Email History")
        
        search_term = st.text_input("Search in saved emails:", placeholder="Enter keywords to search...")
        
        if search_term:
            results = st.session_state.processor.db_manager.search_emails(search_term)
            
            if results:
                st.markdown(f"**Found {len(results)} emails matching '{search_term}':**")
                
                for result in results:
                    with st.expander(f"Email ID: {result['id']} - {result['date']} ({result['sections']} sections, {result['deals']} deals)"):
                        st.markdown(result['content_preview'])
            else:
                st.info("No emails found matching your search term.")

if __name__ == "__main__":
    main()