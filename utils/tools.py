import json
from langchain.tools import tool
from models import DataGovScraper,load_model,predict_image,model_path,device,classes,load_model_wheat,predict_image_wheat,wheat_model_path,class_names
import os
import pandas as pd



scraper = DataGovScraper()

@tool("get_market_price")
def getMarketPrice(crop: str = "tomato", location: str = "") -> str:
    """Get current market price from Data.gov.in government database.
    
    Args:
        crop: Name of the crop (tomato, wheat, rice, maize, cotton, etc.)
        location: State/location (optional - will find best available match)
    
    Returns:
        Current government market price with location and market details
    """
    return scraper.get_market_price(crop, location)

@tool("get_crop_locations")  
def getCropLocations(crop: str = "tomato") -> str:
    """Find which states have data for a specific crop"""
    
    try:
        params = {
            'api-key': scraper.api_key,
            'format': 'json',
            'limit': '200'
        }
        
        response = scraper.session.get(scraper.api_url, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            records = data.get('records', [])
            
            # Find states with this crop
            states_with_crop = set()
            for record in records:
                commodity = str(record.get('commodity', '')).lower()
                state = record.get('state', '')
                
                if crop.lower() in commodity:
                    states_with_crop.add(state)
            
            if states_with_crop:
                states_list = ', '.join(sorted(states_with_crop))
                return f"📍 {crop.title()} price data available in: {states_list}"
            else:
                return f"❌ No {crop} data found in current dataset"
        
        return f"❌ Error fetching location data"
        
    except Exception as e:
        return f"❌ Error: {str(e)}"


@tool(description="Disease detection for {classes}")
def disease_Detect():
    image_path = r"test\test\AppleCedarRust1.JPG"
    model = load_model(model_path, num_classes=len(classes), device=device)
    prediction = predict_image(model, image_path, device=device)
    return prediction


@tool(description="Disease detection for wheat")
def Wheat_disease_detection():
    img_path = r"aphid_33.png"
    model = load_model_wheat(wheat_model_path, num_classes=len(class_names), device=device)
    label = predict_image_wheat(str(img_path), model, class_names, device)
    return label

@tool(description="Fetch all available schemes with description and link")
def Find_scheme():
    json_file_path  ="scheme.json"
    file = pd.read_json(json_file_path)
    des= file["description"]
    link = file["link"]
    output_json = []
    for i in range(len(file)):
        output_json.append({"description":des[i],"link":link[i]})
    return output_json

@tool(description="Get the full details of a scheme using its link")
def Scheme_detials(correct_link:str):
    json_file_path  ="scheme.json"
    file = pd.read_json(json_file_path)
    link = file["link"]
    for i in range(len(file)):
        if link[i] == correct_link:
            break
    output = {
        "title": file["title"][i],
        "ministry": file["ministry"][i],
        "description": file["description"][i],
        "details":file["details"][i],
        "eligibility":file["eligibility"][i],
        "application_process": file["application_process"][i],
        "documents_required": file["documents_required"][i]
    }
    return output

tools = [getCropLocations,getMarketPrice,disease_Detect,Wheat_disease_detection,Scheme_detials,Find_scheme]