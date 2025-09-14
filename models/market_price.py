import requests
from datetime import datetime
from langchain_core.tools import tool
import os

class DataGovScraper:
    """Production-ready Data.gov.in scraper with 1,868 records"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        self.api_key = os.getenv("DATA_GOV_API")
        self.api_url = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"

    def get_market_price(self, crop: str, location: str = "") -> str:
        """Get real market prices from Data.gov.in with flexible matching"""
        
        try:
            params = {
                'api-key': self.api_key,
                'format': 'json',
                'limit': '10000000000',  # Get more records for better matching
                'offset': '0'
            }
            
            response = self.session.get(self.api_url, params=params, timeout=15)
            
            if response.status_code != 200:
                return f"API Error: HTTP {response.status_code}"
            
            data = response.json()
            records = data.get('records', [])
            
            if not records:
                return f"No data available from Data.gov.in"
            
            # Smart matching logic
            crop_matches = []
            
            for record in records:
                commodity = str(record.get('commodity', '')).lower()
                state = str(record.get('state', '')).lower()
                
                # Flexible crop matching
                crop_match = (
                    crop.lower() in commodity or 
                    commodity.startswith(crop.lower()[:3]) or
                    crop.lower() == 'rice' and 'paddy' in commodity
                )
                
                # Flexible location matching (if specified)
                location_match = (
                    not location or  # No location specified
                    location.lower() in state or
                    state.startswith(location.lower()[:3])
                )
                
                if crop_match and location_match:
                    crop_matches.append(record)
            
            if not crop_matches:
                return f"❌ No data found for '{crop}' in Data.gov.in database"
            
            # Use best match with modal_price
            for record in crop_matches:
                modal_price = record.get('modal_price')
                if modal_price and str(modal_price).replace('.', '').isdigit():
                    
                    commodity = record.get('commodity', crop)
                    state = record.get('state', 'Unknown State')
                    market = record.get('market', 'Unknown Market')
                    date = record.get('arrival_date', datetime.now().strftime('%d/%m/%Y'))
                    variety = record.get('variety', '')
                    
                    variety_info = f" ({variety})" if variety and variety != commodity else ""
                    
                    return f"✅ Current {commodity}{variety_info} price in {state}: ₹{modal_price}/quintal (Market: {market}, Date: {date}, Source: Data.gov.in)"
            
            return f"❌ Price data incomplete for '{crop}'"
            
        except Exception as e:
            return f"❌ Error: {str(e)}"
