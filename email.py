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
        
        # Get related deals
        deals_query = 'SELECT * FROM deals WHERE email_id = ?'
        deals = pd.read_sql_query(deals_query, conn, params=(email_id,))
        
        # Get related sections
        sections_query = 'SELECT * FROM sections WHERE email_id = ?'
        sections = pd.read_sql_query(sections_query, conn, params=(email_id,))
        
        # Get related monetary values
        monetary_query = 'SELECT * FROM monetary_values WHERE email_id = ?'
        monetary_values = pd.read_sql_query(monetary_query, conn, params=(email_id,))
        
        # Get related metadata
        metadata_query = 'SELECT * FROM metadata WHERE email_id = ?'
        metadata = pd.read_sql_query(metadata_query, conn, params=(email_id,))
        
        conn.close()
        
        return {
            'email_info': email_info,
            'deals': deals,
            'sections': sections,
            'monetary_values': monetary_values,
            'metadata': metadata
        }
    
    def delete_email(self, email_id: int) -> bool:
        """Delete an email and all its associated data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Delete associated data first (foreign key constraints)
            cursor.execute('DELETE FROM deals WHERE email_id = ?', (email_id,))
            cursor.execute('DELETE FROM sections WHERE email_id = ?', (email_id,))
            cursor.execute('DELETE FROM monetary_values WHERE email_id = ?', (email_id,))
            cursor.execute('DELETE FROM metadata WHERE email_id = ?', (email_id,))
            
            # Delete the email
            cursor.execute('DELETE FROM emails WHERE id = ?', (email_id,))
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            st.error(f"Error deleting email: {str(e)}")
            return False
        finally:
            conn.close()
    
    def delete_deal(self, deal_id: int) -> bool:
        """Delete a specific deal"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM deals WHERE id = ?', (deal_id,))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            st.error(f"Error deleting deal: {str(e)}")
            return False
        finally:
            conn.close()
    
    def delete_all_data(self) -> bool:
        """Delete all data from the database (nuclear option)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Delete all data from all tables
            cursor.execute('DELETE FROM deals')
            cursor.execute('DELETE FROM sections')
            cursor.execute('DELETE FROM monetary_values')
            cursor.execute('DELETE FROM metadata')
            cursor.execute('DELETE FROM emails')
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            st.error(f"Error deleting all data: {str(e)}")
            return False
        finally:
            conn.close()
    
    def get_database_stats(self) -> Dict[str, int]:
        """Get database statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = {}
        tables = ['emails', 'deals', 'sections', 'monetary_values', 'metadata']
        
        for table in tables:
            cursor.execute(f'SELECT COUNT(*) FROM {table}')
            stats[table] = cursor.fetchone()[0]
        
        conn.close()
        return stats
    
    def get_priority_sector_deals(self, priority_sectors: List[str]) -> pd.DataFrame:
        """Get deals filtered by priority sectors"""
        conn = sqlite3.connect(self.db_path)
        
        # Create placeholders for the IN clause
        placeholders = ','.join(['?'] * len(priority_sectors))
        
        deals_query = f'''
            SELECT 
                d.id,
                d.email_id,
                d.deal_number,
                d.title,
                d.sector,
                d.geography,
                d.value_text,
                d.size_category,
                d.grade,
                d.source,
                d.intelligence_id,
                d.stake_value,
                d.created_at
            FROM deals d
            WHERE d.sector IN ({placeholders})
            ORDER BY d.created_at DESC
        '''
        
        deals = pd.read_sql_query(deals_query, conn, params=priority_sectors)
        conn.close()
        
        return deals

class SmartTextProcessor:
    def __init__(self):
        # Priority sectors that are important to the user
        self.priority_sectors = [
            'Computer software',
            'Consumer: Foods',
            'Consumer: Other', 
            'Consumer: Retail',
            'Defense',
            'Financial Services',
            'Industrial automation',
            'Industrial products and services',
            'Industrial: Electronics',
            'Services (other)'
        ]
        
        self.sector_keywords = {
            'Computer software': ['software', 'tech', 'AI', 'digital', 'data', 'cyber', 'SaaS', 'IT', 'cloud', 'app', 'platform', 'programming', 'coding', 'database', 'analytics'],
            'Consumer: Foods': ['food', 'beverage', 'restaurant', 'cafe', 'catering', 'nutrition', 'organic', 'dairy', 'meat', 'snack', 'drink', 'culinary', 'grocery'],
            'Consumer: Other': ['consumer', 'lifestyle', 'personal', 'household', 'beauty', 'cosmetic', 'fashion', 'apparel', 'entertainment', 'media', 'leisure'],
            'Consumer: Retail': ['retail', 'store', 'shop', 'e-commerce', 'marketplace', 'outlet', 'chain', 'brand', 'merchandise', 'commerce', 'sales'],
            'Defense': ['defense', 'defence', 'military', 'aerospace', 'security', 'surveillance', 'weapons', 'armament', 'naval', 'aviation', 'tactical'],
            'Financial Services': ['bank', 'finance', 'financial', 'capital', 'investment', 'insurance', 'fund', 'fintech', 'trading', 'lending', 'credit', 'wealth', 'asset'],
            'Industrial automation': ['automation', 'robotics', 'control', 'process', 'manufacturing', 'assembly', 'conveyor', 'sensor', 'plc', 'scada', 'industrial control'],
            'Industrial products and services': ['industrial', 'manufacturing', 'engineering', 'construction', 'machinery', 'equipment', 'tools', 'materials', 'components', 'fabrication'],
            'Industrial: Electronics': ['electronics', 'semiconductor', 'circuit', 'chip', 'component', 'pcb', 'embedded', 'microprocessor', 'sensor', 'electronic'],
            'Services (other)': ['services', 'consulting', 'professional', 'advisory', 'support', 'maintenance', 'repair', 'logistics', 'transportation', 'outsourcing']
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
        """Format raw text for email-friendly plain text with clickable links preserved"""
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
            
            # Process line to ensure URLs are clickable
            processed_line = self._make_links_clickable(line)
            
            # Check if line is a section header (clean, simple format)
            if self._is_section_header(line):
                # Add spacing before section headers
                if formatted_lines and formatted_lines[-1] != '':
                    formatted_lines.append('')
                formatted_lines.append(processed_line)
                formatted_lines.append('')
            
            # Check if line is a numbered item (deal/topic)
            elif re.match(r'^\d+\.', line):
                formatted_lines.append(processed_line)
                formatted_lines.append('')  # Add blank line after numbered items
            
            # Check if line is a bullet point
            elif line.startswith('*') or line.startswith('-') or line.startswith('•'):
                bullet_text = line[1:].strip()
                processed_bullet = self._make_links_clickable(bullet_text)
                formatted_lines.append(f'* {processed_bullet}')
            
            # Check if line contains key metadata (Source:, Size:, etc.)
            elif ':' in line and self._is_metadata_line(line):
                formatted_lines.append(processed_line)
            
            # Regular paragraph text
            else:
                formatted_lines.append(processed_line)
        
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
    
    def _make_links_clickable(self, text: str) -> str:
        """Make URLs in text clickable for email clients"""
        # Pattern to match URLs (http, https, www, or domain.com patterns)
        url_patterns = [
            r'https?://[^\s<>"]+[^\s<>"\.,\?\!]',  # http/https URLs
            r'www\.[^\s<>"]+[^\s<>"\.,\?\!]',       # www URLs
            r'[a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9]*\.[a-zA-Z]{2,}(?:/[^\s<>"]*)?'  # domain.com URLs
        ]
        
        processed_text = text
        
        for pattern in url_patterns:
            # Find all URLs in the text
            urls = re.findall(pattern, processed_text)
            
            for url in urls:
                # Ensure URL has protocol for clickability
                if url.startswith('www.'):
                    clickable_url = f'https://{url}'
                elif not url.startswith(('http://', 'https://')):
                    clickable_url = f'https://{url}'
                else:
                    clickable_url = url
                
                # Replace in text - keep original format but ensure it's a complete URL
                if url != clickable_url:
                    processed_text = processed_text.replace(url, clickable_url)
        
        return processed_text

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
                    'original_text': title,
                    'identified_sector': '',  # Will be filled after collecting all text
                    'is_priority': False
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
            # Identify sector based on full content
            current_deal['identified_sector'] = self.identify_sector(current_deal['original_text'])
            current_deal['is_priority'] = self.is_priority_sector(current_deal['identified_sector'])
            deals.append(current_deal)
        
        # Process all deals to identify sectors and priority status
        for deal in deals:
            if not deal.get('identified_sector'):
                deal['identified_sector'] = self.identify_sector(deal['original_text'])
                deal['is_priority'] = self.is_priority_sector(deal['identified_sector'])
        
        return deals

    def extract_geography(self, title: str) -> str:
        """Extract geography from deal title"""
        lower_title = title.lower()
        for geo, keywords in self.geo_keywords.items():
            if any(keyword in lower_title for keyword in keywords):
                return geo.upper()
        return 'Global'
    
    def identify_sector(self, text: str) -> str:
        """Identify sector based on content using priority sectors first"""
        lower_text = text.lower()
        
        # Check priority sectors first
        sector_scores = {}
        for sector, keywords in self.sector_keywords.items():
            score = sum(1 for keyword in keywords if keyword in lower_text)
            if score > 0:
                sector_scores[sector] = score
        
        if sector_scores:
            # Return the sector with the highest keyword match score
            best_sector = max(sector_scores, key=sector_scores.get)
            return best_sector
        
        return 'Other'
    
    def is_priority_sector(self, sector: str) -> bool:
        """Check if a sector is in the priority list"""
        return sector in self.priority_sectors
    
    def filter_deals_by_priority_sectors(self, deals: List[Dict]) -> List[Dict]:
        """Filter deals to only include priority sectors"""
        return [deal for deal in deals if self.is_priority_sector(deal.get('sector', 'Other'))]

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
    
    # Sidebar for filtering
    with st.sidebar:
        st.header("🎯 Sector Filtering")
        st.markdown("### Priority Sectors")
        
        # Show priority sectors
        priority_sectors = st.session_state.processor.priority_sectors
        
        # Sector filter options
        filter_mode = st.radio(
            "Filter Mode:",
            ["Show All Sectors", "Priority Sectors Only", "Custom Selection"],
            index=1,  # Default to priority sectors only
            help="Choose how to filter deals and insights by sector"
        )
        
        if filter_mode == "Custom Selection":
            # Allow custom selection of sectors
            all_sectors = priority_sectors + ['Other']
            selected_sectors = st.multiselect(
                "Select Sectors:",
                all_sectors,
                default=priority_sectors,
                help="Choose which sectors to focus on"
            )
        elif filter_mode == "Priority Sectors Only":
            selected_sectors = priority_sectors
        else:
            selected_sectors = None  # Show all
        
        # Store filter settings in session state
        st.session_state.filter_mode = filter_mode
        st.session_state.selected_sectors = selected_sectors
        
        # Display current filter status
        if filter_mode == "Show All Sectors":
            st.info("📊 Showing all sectors")
        elif filter_mode == "Priority Sectors Only":
            st.success(f"🎯 Filtering to {len(priority_sectors)} priority sectors")
        else:
            st.info(f"✅ Custom filter: {len(selected_sectors) if selected_sectors else 0} sectors")
        
        # Priority sectors list
        st.markdown("### 🎯 Your Priority Sectors:")
        for i, sector in enumerate(priority_sectors, 1):
            st.markdown(f"{i}. **{sector}**")
    
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
        
        # Database saving option - more prominent placement
        st.markdown("---")
        col_save, col_info = st.columns([2, 1])
        
        with col_save:
            save_to_db = st.checkbox(
                "💾 Save to database for market insights", 
                value=True, 
                help="Save processed data to database for trend analysis and historical tracking"
            )
        
        with col_info:
            if save_to_db:
                st.success("✅ Will save to DB")
            else:
                st.warning("❌ Won't save to DB")
        
        st.markdown("---")
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            format_button = st.button("🚀 Format Text", type="primary", use_container_width=True)
        
        with col_b:
            clear_button = st.button("🗑️ Clear", use_container_width=True)
        
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
                        st.success(f"✅ Data saved to database! Email ID: {email_id} | Deals: {len(key_info['deals'])} | Sections: {len(key_info['sections'])}")
                    else:
                        st.error("❌ Failed to save to database. Please check your data.")
                else:
                    st.info("ℹ️ Data processed but not saved to database (checkbox was unchecked).")
        
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
                col_info1, col_info2 = st.columns(2)
                with col_info1:
                    st.info("💡 Clean format with no decorative separators - perfect for email.")
                with col_info2:
                    st.success("🔗 URLs are automatically made clickable when copied!")
                
                # Display email-formatted text in a copyable text area
                st.text_area(
                    "Copy this text for email:",
                    value=st.session_state.email_formatted_text,
                    height=600,
                    help="Select all (Ctrl+A / Cmd+A) and copy (Ctrl+C / Cmd+C) to paste into your email. URLs will be clickable!",
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
                            help="Download as a text file with clickable URLs - perfect for emails or attachments.",
                            use_container_width=True
                        )
        else:
            st.info("Ready to format your text. Paste content and click 'Format Text'")
    
    # Additional features
    if 'formatted_text' in st.session_state:
        st.markdown("---")
        
        # Tabs for additional features
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Content Analysis", "📋 Professional Summary", "💾 Export Options", "📈 Market Insights", "🗃️ Database Viewer"])
        
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
                
                # Analyze deal priorities
                deals_data = st.session_state.deals_data
                priority_deals = [deal for deal in deals_data if deal.get('is_priority', False)]
                
                # Show priority deal summary
                if priority_deals:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Deals", len(deals_data))
                    with col2:
                        st.metric("Priority Deals", len(priority_deals), delta=f"{len(priority_deals)/len(deals_data)*100:.1f}%")
                    with col3:
                        priority_sectors_found = set(deal.get('identified_sector', 'Other') for deal in priority_deals)
                        st.metric("Priority Sectors Found", len(priority_sectors_found))
                
                # Filter deals based on current filter setting
                filter_mode = st.session_state.get('filter_mode', 'Priority Sectors Only')
                selected_sectors = st.session_state.get('selected_sectors', st.session_state.processor.priority_sectors)
                
                if filter_mode == "Show All Sectors":
                    filtered_deals = deals_data
                elif filter_mode == "Priority Sectors Only":
                    filtered_deals = priority_deals
                else:  # Custom selection
                    filtered_deals = [deal for deal in deals_data if deal.get('identified_sector', 'Other') in (selected_sectors or [])]
                
                if filtered_deals:
                    st.success(f"🎯 Showing {len(filtered_deals)} deals matching your filter")
                    
                    # Enhanced deals dataframe with priority indicators
                    enhanced_deals = []
                    for deal in filtered_deals:
                        enhanced_deal = {
                            'Priority': '🎯' if deal.get('is_priority', False) else '📄',
                            'Deal #': deal.get('id', ''),
                            'Title': deal.get('title', '')[:80] + '...' if len(deal.get('title', '')) > 80 else deal.get('title', ''),
                            'Section': deal.get('sector', 'Unknown'),
                            'Identified Sector': deal.get('identified_sector', 'Other'),
                            'Geography': deal.get('geography', 'Unknown'),
                            'Value': deal.get('value', 'TBD')
                        }
                        enhanced_deals.append(enhanced_deal)
                    
                    enhanced_df = pd.DataFrame(enhanced_deals)
                    st.dataframe(enhanced_df, use_container_width=True, hide_index=True)
                    
                    # Show sector breakdown for filtered deals
                    if len(filtered_deals) > 1:
                        sector_counts = pd.DataFrame(filtered_deals)['identified_sector'].value_counts()
                        st.markdown("#### Sector Breakdown (Filtered)")
                        fig = px.bar(
                            x=sector_counts.values, 
                            y=sector_counts.index,
                            orientation='h',
                            title="Deals by Identified Sector"
                        )
                        st.plotly_chart(fig, use_container_width=True)
                
                else:
                    st.warning("No deals found matching your current filter settings")
                
                # Original deals table (unfiltered)
                if filter_mode != "Show All Sectors":
                    with st.expander("📋 View All Deals (Unfiltered)"):
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
                        # Apply filtering based on sidebar settings
                        filter_mode = st.session_state.get('filter_mode', 'Priority Sectors Only')
                        selected_sectors = st.session_state.get('selected_sectors', st.session_state.processor.priority_sectors)
                        
                        # Filter deals based on sector
                        all_deals = db_contents['deals']
                        
                        if filter_mode == "Show All Sectors":
                            filtered_deals_db = all_deals
                        elif filter_mode == "Priority Sectors Only":
                            filtered_deals_db = all_deals[all_deals['sector'].isin(st.session_state.processor.priority_sectors)]
                        else:  # Custom selection
                            if selected_sectors:
                                filtered_deals_db = all_deals[all_deals['sector'].isin(selected_sectors)]
                            else:
                                filtered_deals_db = pd.DataFrame()  # Empty if no sectors selected
                        
                        # Show filtering info
                        if len(filtered_deals_db) != len(all_deals):
                            st.info(f"🎯 Filtered view: {len(filtered_deals_db)} of {len(all_deals)} deals shown (based on sidebar filter)")
                        
                        if not filtered_deals_db.empty:
                            # Add priority indicators
                            display_deals = filtered_deals_db.copy()
                            display_deals['Priority'] = display_deals['sector'].apply(
                                lambda x: '🎯' if x in st.session_state.processor.priority_sectors else '📄'
                            )
                            
                            # Reorder columns to show priority first
                            cols = ['Priority'] + [col for col in display_deals.columns if col != 'Priority']
                            display_deals = display_deals[cols]
                            
                            st.dataframe(display_deals, use_container_width=True, hide_index=True)
                            
                            # Quick stats for filtered deals
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("Filtered Deals", len(filtered_deals_db))
                            with col2:
                                priority_count = len(filtered_deals_db[filtered_deals_db['sector'].isin(st.session_state.processor.priority_sectors)])
                                st.metric("Priority Deals", priority_count)
                            with col3:
                                top_sector = filtered_deals_db['sector'].mode().iloc[0] if len(filtered_deals_db) > 0 else 'N/A'
                                st.metric("Top Sector", top_sector)
                            with col4:
                                top_geo = filtered_deals_db['geography'].mode().iloc[0] if len(filtered_deals_db) > 0 else 'N/A'
                                st.metric("Top Geography", top_geo)
                            
                            # Priority sector breakdown
                            priority_deals_in_view = filtered_deals_db[filtered_deals_db['sector'].isin(st.session_state.processor.priority_sectors)]
                            if not priority_deals_in_view.empty:
                                st.markdown("#### 🎯 Priority Sector Breakdown")
                                sector_counts = priority_deals_in_view['sector'].value_counts()
                                fig = px.bar(
                                    x=sector_counts.values,
                                    y=sector_counts.index,
                                    orientation='h',
                                    title="Priority Deals by Sector",
                                    color_discrete_sequence=['#2E8B57']  # Green color for priority
                                )
                                st.plotly_chart(fig, use_container_width=True)
                        
                        else:
                            st.warning("No deals found matching your current filter settings")
                            
                        # Show unfiltered data in expander if filtering is active
                        if filter_mode != "Show All Sectors":
                            with st.expander("📋 View All Deals (Unfiltered)"):
                                st.dataframe(all_deals, use_container_width=True, hide_index=True)
                        
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
                    
                    # Double confirmation for nuclear option
                    confirm_nuclear_1 = st.checkbox("I understand this will delete ALL emails and data", key="nuclear_confirm_1")
                    confirm_nuclear_2 = st.checkbox("I really want to delete everything", key="nuclear_confirm_2")
                    
                    nuclear_enabled = confirm_nuclear_1 and confirm_nuclear_2
                    
                    if st.button("🚨 DELETE ALL DATA", type="secondary", disabled=not nuclear_enabled, key="nuclear_delete_btn"):
                        if st.session_state.db_manager.delete_all_data():
                            st.success("✅ All database data has been deleted!")
                            # Clear session state
                            if 'db_contents' in st.session_state:
                                del st.session_state.db_contents
                            st.rerun()
                        else:
                            st.error("❌ Failed to delete all data")
            
            else:
                st.info("Click 'Load Database Contents' to view stored data")

if __name__ == "__main__":
    main()