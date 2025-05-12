from flask import current_app
import os
import json
import re 

import pdfplumber # For PDF text extraction
from google.cloud import vision

# For Gemini API
import google.generativeai as genai
from dateutil import parser as date_parse


def extract_text_from_pdf(file_path):
    """Extracts text from a PDF file using pdfplumber."""
    current_app.logger.info(f"Attempting to extract text from PDF: {file_path}")
    try:
        all_text = []
        with pdfplumber.open(file_path) as pdf:
            current_app.logger.info(f"PDF opened successfully. Contains {len(pdf.pages)} pages.")
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                if text.strip():
                    all_text.append(text)
                current_app.logger.debug(f"Extracted {len(text)} characters from page {i+1}")
        
        combined_text = "\n\n".join(all_text)
        current_app.logger.info(f"Successfully extracted {len(combined_text)} characters from PDF.")
        current_app.logger.debug(f"---BEGIN FULL PDF TEXT FOR GEMINI---\n{combined_text}\n---END FULL PDF TEXT FOR GEMINI---")
        return combined_text
    except Exception as e:
        current_app.logger.error(f"Error extracting text from PDF: {e}")
        raise


def get_ocr_text_from_image(image_content, file_path=None, mime_type=None):
    """
    Extracts text from an image or PDF file.
    For PDFs, uses pdfplumber.
    For images, uses Google Cloud Vision API.
    
    Parameters:
        image_content: The binary content of the file
        file_path: Optional, the path to the file (required for PDFs)
        mime_type: Optional, the MIME type of the file
    """
    # Determine if the file is a PDF
    is_pdf = False
    if mime_type and "pdf" in mime_type.lower():
        is_pdf = True
    elif file_path and file_path.lower().endswith(".pdf"):
        is_pdf = True
    
    # If it's a PDF, use pdfplumber
    if is_pdf:
        if not file_path:
            raise ValueError("File path is required for PDF processing")
        current_app.logger.info(f"Detected PDF file, using pdfplumber for text extraction")
        return extract_text_from_pdf(file_path)
    
    # Otherwise, use Vision API for images
    current_app.logger.info("Attempting OCR with Google Cloud Vision API...")
    try:
        client = vision.ImageAnnotatorClient() # Assumes GOOGLE_APPLICATION_CREDENTIALS is set
        image = vision.Image(content=image_content)
        response = client.text_detection(image=image)

        if response.error.message:
            current_app.logger.error(f'Google Cloud Vision API error: {response.error.message}')
            raise Exception(f'Google Cloud Vision API error: {response.error.message}')

        if response.text_annotations:
            full_text = response.text_annotations[0].description
            current_app.logger.info("OCR successful with Google Cloud Vision API.")
            current_app.logger.debug(f"---BEGIN FULL OCR TEXT FOR GEMINI---\n{full_text}\n---END FULL OCR TEXT FOR GEMINI---")
            return full_text
        else:
            current_app.logger.info("No text found in image by Google Cloud Vision API.")
            return ""
    except Exception as e:
        current_app.logger.error(f"Google Cloud Vision API request failed: {e}")
        raise

def extract_invoice_data_with_gemini(ocr_text):
    """Extracts invoice data from OCR text using Gemini API."""
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        current_app.logger.error("GEMINI_API_KEY not found in environment variables.")
        raise ValueError("GEMINI_API_KEY is not set.")

    # Define core fields we expect and want to structure specifically
    core_fields_schema = {
        "vendor_name": None,
        "invoice_number": None,
        "invoice_date": None, 
        "total_amount": None,
        "line_items": [],
        "detected_currency": None, # Added for currency detection
        # Add other core fields you always want structured here, e.g., subtotal, tax_amount
    }

    if not ocr_text.strip():
        current_app.logger.warning("OCR text is empty. Skipping Gemini processing.")
        # Ensure the new field is included in the empty response
        return {**core_fields_schema, "raw_text": ocr_text, "additional_details": {}}

    genai.configure(api_key=api_key)
    # Using gemini-1.5-flash-latest for potentially faster responses and good capability.
    # You can switch to 'gemini-pro' or other models based on your needs/testing.
    model = genai.GenerativeModel('gemini-1.5-flash-latest') 

    prompt = f"""
    You are an expert AI assistant for extracting structured data from OCR text of invoices.
    Analyze the provided OCR text and extract the specified information.
    You MUST return ONLY a single, valid JSON object.
    Do NOT include any explanations, apologies, introductory text, or markdown formatting (like ```json ... ```) around the JSON object.
    The JSON object should be the sole content of your response.

    Core Fields to Extract (ensure these keys are in the root of the JSON object):
    - vendor_name: (string) The supplier or company name. If not found, use null.
    - invoice_number: (string) The invoice ID or bill number. If not found, use null.
    - invoice_date: (string) The main date of the invoice, formatted as YYYY-MM-DD. If a date is found but cannot be reliably converted, return the date string as found. If not found, use null.
    - total_amount: (float) The final total amount due. Extract as a numeric float (e.g., 123.45). Remove currency symbols. If not found, use null.
    - detected_currency: (string) The primary currency symbol (e.g., "₹", "$") or currency code (e.g., "INR", "USD") found on the invoice. If multiple are present, choose the most prominent one associated with the total amounts. If not found, use null.
    - line_items: (array of objects) Each object for a line item. If no clear line items, return an empty array []. Each line item object should contain:
        - description: (string) Item/service description. If not found, use null.
        - quantity: (number) Quantity. Convert to a number if possible. If not numeric or not found, use null.
        - unit_price: (float) Price per unit. Convert to a float. If not found, use null.
        - item_total: (float) Total for that line item. Convert to a float. If not found, use null.
    
    Additional Information:
    - Also include any other relevant key-value pairs you can identify from the invoice text as top-level keys in the JSON object.
    - For example, if you find "Subtotal: $100.00", you might include "subtotal": 100.00.
    - If you find "Payment Terms: Net 30", include "payment_terms": "Net 30".
    - Prioritize the core fields above, but also include these other identified details if present.

    JSON Output Rules:
    1. ONLY output the JSON object.
    2. For any of the CORE fields listed above that are not found, their value in the JSON MUST be null (or an empty array for line_items).
    3. Monetary values (total_amount, unit_price, item_total, and other detected monetary fields) MUST be numbers (floats), not strings with currency symbols. The `detected_currency` field is for the symbol/code itself.
    4. Quantity should be a number if possible.

    OCR Text:
    ---BEGIN OCR TEXT---
    {ocr_text}
    ---END OCR TEXT---

    JSON Output:
    """

    current_app.logger.info("Sending request to Gemini API for invoice parsing...")
    # Log only a part of the prompt for brevity, excluding the potentially long OCR text
    prompt_parts = prompt.split("---BEGIN OCR TEXT---")
    log_prompt = prompt_parts[0] + "---BEGIN OCR TEXT---...[OCR TEXT OMITTED FOR LOG]...---END OCR TEXT---" + prompt_parts[1].split("---END OCR TEXT---")[-1]
    current_app.logger.debug(f"Gemini Prompt structure:\n{log_prompt}")

    try:
        # Increased timeout, consider making this configurable
        generation_config = genai.types.GenerationConfig(temperature=0.1, top_p=0.95, top_k=40) # Adjusted for potentially more structured output
        response = model.generate_content(prompt, generation_config=generation_config, request_options={'timeout': 120}) # 120 seconds timeout
        gemini_response_text = response.text
        current_app.logger.info("Received response from Gemini API.")
        current_app.logger.debug(f"Gemini raw response text:\n{gemini_response_text}")

        # Attempt to clean and extract JSON from the response
        # Remove markdown backticks if present
        cleaned_response_text = re.sub(r"^```json\n?|\n?```$", "", gemini_response_text.strip(), flags=re.MULTILINE)
        
        # Try to find the JSON object using regex as LLMs can sometimes include extra text
        match = re.search(r'\{.*\}', cleaned_response_text, re.DOTALL)
        json_str = match.group(0) if match else cleaned_response_text
        current_app.logger.debug(f"Attempting to parse JSON from Gemini: \n{json_str}")

        try:
            raw_extracted_data = json.loads(json_str)
        except json.JSONDecodeError as je:
            current_app.logger.error(f"Failed to parse Gemini response as JSON: {je}. Response: {json_str[:1000]}")
            raise ValueError(f"Gemini response was not valid JSON. Response: {json_str[:500]}...")

        current_app.logger.info(f"Successfully parsed structured data from Gemini.")
        current_app.logger.debug(f"Raw Parsed Gemini Data: {raw_extracted_data}")
        
        # Initialize with core fields schema to ensure all expected keys are present
        structured_data = {**core_fields_schema} 
        structured_data["raw_text"] = ocr_text
        structured_data["additional_details"] = {}

        for key, value in raw_extracted_data.items():
            if key in core_fields_schema:
                structured_data[key] = value
            else:
                # This is an additional field detected by Gemini
                structured_data["additional_details"][key] = value
        
        # Type conversion and validation for core fields
        if structured_data.get('total_amount') is not None:
            try: structured_data['total_amount'] = float(structured_data['total_amount'])
            except (ValueError, TypeError): 
                current_app.logger.warning(f"Could not convert total_amount '{structured_data['total_amount']}' to float. Setting to None.")
                structured_data['total_amount'] = None
        
        if structured_data.get('invoice_date') and isinstance(structured_data['invoice_date'], str):
            try:
                # Try to parse and reformat to YYYY-MM-DD
                parsed_date = date_parse.parse(structured_data['invoice_date'])
                structured_data['invoice_date'] = parsed_date.strftime('%Y-%m-%d')
            except (ValueError, TypeError, OverflowError):
                current_app.logger.warning(f"Could not parse invoice_date '{structured_data['invoice_date']}' to YYYY-MM-DD. Keeping original string.")
                # Keep the original string if parsing fails, as per prompt instructions
        
        if isinstance(structured_data.get('line_items'), list):
            processed_line_items = []
            for item in structured_data['line_items']:
                if not isinstance(item, dict): continue # Skip if item is not a dict
                processed_item = {}
                processed_item['description'] = item.get('description')
                try: processed_item['quantity'] = float(item['quantity']) if item.get('quantity') is not None else None
                except (ValueError, TypeError): processed_item['quantity'] = item.get('quantity') # Keep as string if not floatable
                try: processed_item['unit_price'] = float(item['unit_price']) if item.get('unit_price') is not None else None
                except (ValueError, TypeError): processed_item['unit_price'] = None
                try: processed_item['item_total'] = float(item['item_total']) if item.get('item_total') is not None else None
                except (ValueError, TypeError): processed_item['item_total'] = None
                processed_line_items.append(processed_item)
            structured_data['line_items'] = processed_line_items
        else:
            structured_data['line_items'] = []

        current_app.logger.info(f"Final Processed Structured Data: {structured_data}")
        return structured_data

    except Exception as e:
        current_app.logger.error(f"Error during Gemini API call or processing: {e}", exc_info=True)
        raise

# Commenting out the old Document AI processor as we are shifting to Gemini for parsing
"""
from google.cloud import documentai_v1 as documentai
# ... (old Document AI code was here) ...
""" 