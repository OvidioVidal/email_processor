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
        self.sector_keywords = {
            'automotive': ['auto', 'car', 'vehicle', 'motor', 'automotive', 'tesla', 'ford', 'bmw'],
            'computer software': ['software', 'app', 'platform', 'SaaS', 'cloud', 'AI', 'digital', 'tech'],
            'consumer: foods': ['food', 'beverage', 'restaurant', 'dining', 'nutrition', 'snack', 'drink'],
            'consumer: other': ['consumer', 'retail', 'brand', 'lifestyle', 'beauty', 'personal care'],
            'consumer: retail': ['retail', 'store', 'shopping', 'ecommerce', 'fashion', 'apparel', 'goods'],
            'defense': ['defense', 'military', 'aerospace', 'security', 'weapons', 'defense contractor'],
            'financial services': ['bank', 'finance', 'capital', 'investment', 'insurance', 'fund', 'fintech', 'payment'],
            'industrial automation': ['automation', 'robotics', 'manufacturing', 'industrial', 'machinery'],
            'industrial products and services': ['industrial', 'manufacturing', 'engineering', 'equipment', 'machinery'],
            'industrial: electronics': ['electronics', 'semiconductor', 'components', 'circuits', 'hardware'],
            'services (other)': ['services', 'consulting', 'professional', 'outsourcing', 'support']
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
    
    def _extract_numeric_value(self, text: str) -> float:
        """Extract numeric value from monetary text and convert to millions"""
        if not text:
            return 0.0
            
        try:
            # Remove currency symbols and clean the text
            cleaned = re.sub(r'[€$£¥₹]', '', text)
            cleaned = re.sub(r'[^\d\.,bmk]', ' ', cleaned, flags=re.IGNORECASE)
            
            # Look for numeric values
            numeric_match = re.search(r'([\d,\.]+)', cleaned)
            if not numeric_match:
                return 0.0
                
            # Extract the base number
            num_str = numeric_match.group(1).replace(',', '')
            base_value = float(num_str)
            
            # Handle multipliers (normalize to millions)
            text_lower = text.lower()
            if 'billion' in text_lower or 'bn' in text_lower or 'b' in text_lower:
                return base_value * 1000  # Convert billions to millions
            elif 'million' in text_lower or 'mn' in text_lower or 'm' in text_lower:
                return base_value  # Already in millions
            elif 'thousand' in text_lower or 'k' in text_lower:
                return base_value / 1000  # Convert thousands to millions
            else:
                # Assume raw numbers are in currency units, convert to millions
                return base_value / 1000000
                
        except (ValueError, AttributeError) as e:
            # Return 0 for invalid inputs rather than raising an exception
            return 0.0

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
        
    if page == "📝 Text Formatter":
        # Main layout
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("📝 Raw Text Input")
            
            # Sample data for demonstration
            sample_data = """Automotive

1. Daimler Truck, Volvo launch software JV Coretura

Computer software

2. Aya Healthcare acquires Locum's Nest

3. TTC Group acquires Think Eleven

Consumer: Foods

4. Moyca attracts interest from industrial, financial groups - report (translated)

Consumer: Other

5. Beauty brand seeks strategic investor for expansion

Defense

6. Aerospace company announces defense contract acquisition

Financial Services

7. Metro Bank majority owner Gilinski considers sale of stake – report

8. Athora in talks to acquire PIC for up to GBP 5bn – report

Industrial automation

9. Robotics firm secures EUR 150m funding round

Services (other)

10. Consulting firm announces merger with rival

1. Daimler Truck, Volvo launch software JV Coretura

* Focus on software development for commercial vehicles
* 50% held by each parent
* Volume of investments depends on milestones, technical progress

Daimler Truck, a German vehicle maker, and Swedish auto group Volvo have announced the launch of a software joint venture named Coretura.

Source: Company Press Release(s)
Size: 1bn-5bn (EUR)
Grade: Confirmed"""
            
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