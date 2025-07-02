import re
import sqlite3
import hashlib
from typing import Dict, List, Any, Optional
from datetime import datetime
import json


class MergerMarketProcessor:
    """
    Advanced M&A email processor for extracting and analyzing deal intelligence
    from MergerMarket email alerts and similar structured content.
    """
    
    def __init__(self, db_path: str = "email_intelligence.db"):
        self.db_path = db_path
        self.industries = [
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
        
    def process_mergermarket_content(self, raw_text: str) -> Dict[str, Any]:
        """
        Process raw MergerMarket email content and extract structured deal data.
        
        Args:
            raw_text (str): Raw M&A alert text content
            
        Returns:
            Dict containing extracted data, statistics, and metadata
        """
        if not raw_text or not raw_text.strip():
            return {"error": "Empty or invalid content provided"}
            
        try:
            # Extract structured data by industry
            extracted_data = self._extract_industry_data(raw_text)
            
            # Generate analytics and statistics
            analytics = self._generate_analytics(extracted_data, raw_text)
            
            # Create content hash for deduplication
            content_hash = hashlib.md5(raw_text.encode()).hexdigest()
            
            result = {
                "content_hash": content_hash,
                "extracted_data": extracted_data,
                "analytics": analytics,
                "processed_at": datetime.now().isoformat(),
                "total_industries": len([k for k, v in extracted_data.items() if v]),
                "total_deals": sum(len(items) for items in extracted_data.values()),
                "processing_status": "success"
            }
            
            return result
            
        except Exception as e:
            return {
                "error": f"Processing failed: {str(e)}",
                "processing_status": "error"
            }
    
    def _extract_industry_data(self, raw_text: str) -> Dict[str, List[Dict]]:
        """Extract data organized by industry categories."""
        extracted_data = {}
        
        for industry in self.industries:
            # Pattern to match the entire industry section
            pattern = rf"### \*\*{re.escape(industry)}\*\*([\s\S]*?)(?=\n### |\Z)"
            matches = re.findall(pattern, raw_text)
            
            if matches:
                extracted_items = []
                for match in matches:
                    # Split into numbered items
                    item_pattern = r"(\d+\..*?)(?=\n\d+\.|\Z)"
                    items = re.findall(item_pattern, match, re.DOTALL)
                    
                    for item in items:
                        # Extract press releases
                        press_release_pattern = r"(Press release.*?)(?=\n[A-Z]|\Z)"
                        press_releases = re.findall(press_release_pattern, item, re.DOTALL | re.IGNORECASE)
                        
                        # Extract deal information
                        deal_info = self._parse_deal_item(item)
                        deal_info.update({
                            "content": item.strip(),
                            "press_release": press_releases[0].strip() if press_releases else None,
                            "industry": industry
                        })
                        
                        extracted_items.append(deal_info)
                        
                extracted_data[industry] = extracted_items
            else:
                extracted_data[industry] = []
                
        return extracted_data
    
    def _parse_deal_item(self, item_text: str) -> Dict[str, Any]:
        """Parse individual deal item to extract structured information."""
        deal_info = {
            "companies": [],
            "deal_value": None,
            "currency": None,
            "deal_type": None,
            "geography": [],
            "key_terms": []
        }
        
        # Extract company names (typically in bold or at start of sentences)
        company_pattern = r'\*\*([^*]+)\*\*|([A-Z][a-z]+ (?:[A-Z][a-z]+ )*(?:Inc|Corp|Ltd|LLC|SA|AG|GmbH|plc))'
        companies = re.findall(company_pattern, item_text)
        deal_info["companies"] = [comp[0] or comp[1] for comp in companies if comp[0] or comp[1]]
        
        # Extract monetary values
        money_pattern = r'(USD|EUR|GBP|£|\$|€)\s*([0-9,]+(?:\.[0-9]+)?)\s*(million|billion|m|bn)?'
        money_matches = re.findall(money_pattern, item_text, re.IGNORECASE)
        if money_matches:
            currency, amount, unit = money_matches[0]
            deal_info["currency"] = currency
            deal_info["deal_value"] = f"{amount} {unit}" if unit else amount
            
        # Extract deal types
        deal_type_pattern = r'\b(acquisition|merger|buyout|investment|stake|divestiture|IPO|sale)\b'
        deal_types = re.findall(deal_type_pattern, item_text, re.IGNORECASE)
        deal_info["deal_type"] = list(set(deal_types))
        
        # Extract geography/countries
        geography_pattern = r'\b(UK|US|USA|Germany|France|Italy|Spain|Netherlands|Belgium|Switzerland|Canada)\b'
        geographies = re.findall(geography_pattern, item_text, re.IGNORECASE)
        deal_info["geography"] = list(set(geographies))
        
        return deal_info
    
    def _generate_analytics(self, extracted_data: Dict[str, List], raw_text: str) -> Dict[str, Any]:
        """Generate analytics and insights from extracted data."""
        analytics = {
            "industry_breakdown": {},
            "deal_value_summary": {},
            "geography_distribution": {},
            "deal_type_distribution": {},
            "key_metrics": {}
        }
        
        # Industry breakdown
        for industry, items in extracted_data.items():
            analytics["industry_breakdown"][industry] = len(items)
            
        # Deal value analysis
        all_values = []
        currencies = []
        
        for industry_items in extracted_data.values():
            for item in industry_items:
                if item.get("deal_value"):
                    all_values.append(item["deal_value"])
                if item.get("currency"):
                    currencies.append(item["currency"])
                    
        analytics["deal_value_summary"] = {
            "total_valued_deals": len(all_values),
            "currency_breakdown": {curr: currencies.count(curr) for curr in set(currencies)}
        }
        
        # Geography distribution
        all_geographies = []
        for industry_items in extracted_data.values():
            for item in industry_items:
                all_geographies.extend(item.get("geography", []))
                
        analytics["geography_distribution"] = {
            geo: all_geographies.count(geo) for geo in set(all_geographies)
        }
        
        # Deal type distribution
        all_deal_types = []
        for industry_items in extracted_data.values():
            for item in industry_items:
                all_deal_types.extend(item.get("deal_type", []))
                
        analytics["deal_type_distribution"] = {
            dtype: all_deal_types.count(dtype) for dtype in set(all_deal_types)
        }
        
        # Key metrics
        total_deals = sum(len(items) for items in extracted_data.values())
        analytics["key_metrics"] = {
            "total_deals": total_deals,
            "active_industries": len([k for k, v in extracted_data.items() if v]),
            "deals_with_press_releases": sum(
                1 for industry_items in extracted_data.values()
                for item in industry_items if item.get("press_release")
            ),
            "content_length": len(raw_text),
            "avg_deals_per_industry": total_deals / len(self.industries) if total_deals > 0 else 0
        }
        
        return analytics
    
    def save_to_database(self, processed_data: Dict[str, Any], original_content: str) -> Optional[int]:
        """Save processed data to database and return email ID."""
        if processed_data.get("processing_status") != "success":
            return None
            
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Insert main email record
            cursor.execute('''
                INSERT OR REPLACE INTO emails 
                (content_hash, original_content, formatted_content, processed_date, 
                 deal_count, section_count, total_lines) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                processed_data["content_hash"],
                original_content,
                json.dumps(processed_data["extracted_data"]),
                datetime.now(),
                processed_data["total_deals"],
                processed_data["total_industries"],
                len(original_content.split('\n'))
            ))
            
            email_id = cursor.lastrowid
            
            # Insert deal details
            for industry, items in processed_data["extracted_data"].items():
                for idx, item in enumerate(items):
                    cursor.execute('''
                        INSERT INTO deals 
                        (email_id, deal_number, deal_title, section_name, deal_content)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        email_id,
                        idx + 1,
                        ' '.join(item.get("companies", []))[:200],  # Truncate if too long
                        industry,
                        item["content"]
                    ))
                    
                    # Insert company information
                    for company in item.get("companies", []):
                        cursor.execute('''
                            INSERT INTO companies
                            (email_id, company_name, context, confidence_score)
                            VALUES (?, ?, ?, ?)
                        ''', (email_id, company, industry, 0.8))
            
            # Insert analytics as metadata
            for key, value in processed_data["analytics"]["key_metrics"].items():
                cursor.execute('''
                    INSERT INTO metadata (email_id, key_name, value_text)
                    VALUES (?, ?, ?)
                ''', (email_id, f"analytics_{key}", str(value)))
            
            conn.commit()
            conn.close()
            
            return email_id
            
        except Exception as e:
            print(f"Database save error: {str(e)}")
            return None
    
    def format_for_display(self, processed_data: Dict[str, Any]) -> str:
        """Format processed data for display or export."""
        if processed_data.get("processing_status") != "success":
            return f"Error: {processed_data.get('error', 'Unknown error')}"
            
        output_lines = []
        output_lines.append("=== M&A INTELLIGENCE REPORT ===")
        output_lines.append(f"Processed: {processed_data['processed_at']}")
        output_lines.append(f"Total Deals: {processed_data['total_deals']}")
        output_lines.append(f"Active Industries: {processed_data['total_industries']}")
        output_lines.append("")
        
        # Industry sections
        for industry, items in processed_data["extracted_data"].items():
            if items:  # Only show industries with deals
                output_lines.append(f"=== {industry.upper()} ===")
                for idx, item in enumerate(items, 1):
                    output_lines.append(f"{idx}. {item['content']}")
                    if item.get("press_release"):
                        output_lines.append("   PRESS RELEASE:")
                        output_lines.append(f"   {item['press_release']}")
                    output_lines.append("---")
                output_lines.append("")
        
        # Analytics summary
        analytics = processed_data.get("analytics", {})
        if analytics.get("key_metrics"):
            output_lines.append("=== ANALYTICS SUMMARY ===")
            for key, value in analytics["key_metrics"].items():
                output_lines.append(f"{key.replace('_', ' ').title()}: {value}")
                
        return "\n".join(output_lines)


# Standalone usage example
if __name__ == "__main__":
    # Example usage
    processor = MergerMarketProcessor()
    
    # Sample input (replace with actual content)
    sample_text = """
    ### **Automotive**
    1. **Tesla Inc** announced acquisition of battery manufacturer for $2.5 billion...
    Press release: Tesla confirms strategic acquisition to enhance battery technology capabilities.
    
    ### **Financial Services**
    2. **JPMorgan Chase** to acquire fintech startup for undisclosed amount...
    """
    
    # Process content
    result = processor.process_mergermarket_content(sample_text)
    
    # Display results
    if result.get("processing_status") == "success":
        print(processor.format_for_display(result))
        
        # Save to database
        email_id = processor.save_to_database(result, sample_text)
        if email_id:
            print(f"\nData saved to database with ID: {email_id}")
    else:
        print(f"Processing failed: {result.get('error')}")
