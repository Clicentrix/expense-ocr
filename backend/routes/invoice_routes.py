from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
import os
import datetime
import mimetypes 

import db 
from services import vision_service # This now contains the Gemini logic

# We might not need google_exceptions if all API calls are within vision_service and handled there
# from google.api_core import exceptions as google_exceptions 

# Define a Blueprint for invoice routes
invoice_bp = Blueprint('invoice_bp', __name__, url_prefix='/api/invoices')

UPLOAD_FOLDER = 'uploads' # Should be a configuration, e.g., app.config['UPLOAD_FOLDER']
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@invoice_bp.route('/upload', methods=['POST'])
def upload_invoice():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    # Assuming user_id is sent in the form data or from session/token in a real app
    user_id = request.form.get('user_id', 1) # Placeholder, replace with actual user auth

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Ensure UPLOAD_FOLDER is absolute or correctly relative to the app root
        upload_folder_abs = os.path.join(current_app.root_path, UPLOAD_FOLDER)
        if not os.path.exists(upload_folder_abs):
            try:
                os.makedirs(upload_folder_abs)
                current_app.logger.info(f"Created upload folder: {upload_folder_abs}")
            except OSError as e:
                current_app.logger.error(f"Error creating upload folder {upload_folder_abs}: {e}")
                return jsonify({'error': 'Could not create upload directory'}), 500
        
        # Create a unique filename to avoid overwrites
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
        unique_filename = f"{timestamp}_{filename}"
        file_path = os.path.join(upload_folder_abs, unique_filename)
        
        try:
            file.save(file_path)
            current_app.logger.info(f"File saved to {file_path}")
        except Exception as e:
            current_app.logger.error(f"Error saving file {file_path}: {e}")
            return jsonify({'error': f'Could not save file: {str(e)}'}), 500

        # At this point, the file is saved. Now, interact with the database.
        conn = db.get_db()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        cursor = conn.cursor()
        invoice_id = None # Initialize invoice_id

        try:
            # Save initial invoice record to database
            sql_insert_invoice = """
            INSERT INTO invoices (user_id, file_name, original_file_path, status, raw_text)
            VALUES (%s, %s, %s, 'uploaded', %s) """ # Add raw_text placeholder initially
            
            # Perform OCR first to get raw_text
            mime_type = mimetypes.guess_type(file_path)[0] or file.mimetype
            with open(file_path, 'rb') as f_content:
                image_content = f_content.read()
            
            ocr_text = "" # Default to empty if OCR fails
            try:
                # Pass file_path and mime_type to handle PDFs differently
                ocr_text = vision_service.get_ocr_text_from_image(
                    image_content=image_content,
                    file_path=file_path,
                    mime_type=mime_type
                )
            except Exception as ocr_error:
                current_app.logger.error(f"OCR step failed for {unique_filename}: {ocr_error}")
                # Decide if you want to proceed without OCR text or mark as error
                # For now, we'll proceed with empty ocr_text but log it.

            cursor.execute(sql_insert_invoice, (user_id, unique_filename, file_path, ocr_text))
            invoice_id = cursor.lastrowid
            # conn.commit() # Commit after OCR and initial insert
            current_app.logger.info(f"Invoice record created with ID: {invoice_id}, OCR text stored (length: {len(ocr_text)}).")

            cursor.execute("UPDATE invoices SET status = 'processing' WHERE id = %s", (invoice_id,))
            # conn.commit() # Commit status update

            # Now, extract structured data using Gemini
            structured_data = vision_service.extract_invoice_data_with_gemini(ocr_text)
            current_app.logger.info(f"Data extracted by Gemini for invoice ID {invoice_id}: {structured_data}")
            
            update_sql = """
            UPDATE invoices 
            SET total_amount = %s, vendor_name = %s, invoice_date = %s, 
                status = 'processed', processed_at = CURRENT_TIMESTAMP,
                raw_text = %s, 
                invoice_number = %s
                /* Note: currency column will be added later */
            WHERE id = %s
            """
            
            db_invoice_date = structured_data.get('invoice_date')
            # The vision_service now attempts to parse to YYYY-MM-DD, or keeps original string
            detected_currency = structured_data.get('detected_currency') # Get the detected currency, will be used when currency column exists

            cursor.execute(update_sql, (
                structured_data.get('total_amount'),
                structured_data.get('vendor_name'),
                db_invoice_date, 
                structured_data.get('raw_text', ocr_text), # Use Gemini's raw_text if it differs, else original OCR
                structured_data.get('invoice_number'),
                # detected_currency, # Commenting out until the column exists in the database
                invoice_id
            ))
            
            # Save line items to invoice_fields table
            if structured_data.get('line_items') and isinstance(structured_data['line_items'], list):
                for idx, item in enumerate(structured_data['line_items']):
                    # Ensure item is a dictionary before trying to get values
                    if not isinstance(item, dict): 
                        current_app.logger.warning(f"Skipping line item as it is not a dictionary: {item}")
                        continue

                    field_sql = "INSERT INTO invoice_fields (invoice_id, field_name, field_value) VALUES (%s, %s, %s)" # Removed confidence and coordinates for now
                    
                    desc = str(item.get('description', '')) # Default to empty string if None
                    amt = str(item.get('item_total', ''))
                    qty = str(item.get('quantity', ''))
                    unit_p = str(item.get('unit_price', ''))

                    if desc: cursor.execute(field_sql, (invoice_id, f"line_item_{idx+1}_description", desc))
                    if amt: cursor.execute(field_sql, (invoice_id, f"line_item_{idx+1}_amount", amt))
                    if qty: cursor.execute(field_sql, (invoice_id, f"line_item_{idx+1}_quantity", qty))
                    if unit_p: cursor.execute(field_sql, (invoice_id, f"line_item_{idx+1}_unit_price", unit_p))
            
            # Save additional_details from Gemini to invoice_fields table
            additional_details = structured_data.get('additional_details', {})
            if isinstance(additional_details, dict):
                for field_name, field_value in additional_details.items():
                    if field_value is not None: # Only save if there's a value
                        field_sql_additional = "INSERT INTO invoice_fields (invoice_id, field_name, field_value) VALUES (%s, %s, %s)" # Removed confidence and coordinates
                        # Ensure field_value is a string for DB insertion
                        cursor.execute(field_sql_additional, (invoice_id, str(field_name), str(field_value)))
                        current_app.logger.info(f"Stored additional detail: {field_name} = {field_value}")

            conn.commit() 
            current_app.logger.info(f"Invoice ID: {invoice_id} fully processed and updated in DB using Gemini data.")

            return jsonify({
                'message': 'File uploaded, OCRed, and parsed with Gemini successfully!',
                'invoice_id': invoice_id,
                'filename': unique_filename,
                'raw_text_preview': structured_data.get('raw_text', ocr_text)[:200] + '...' if structured_data.get('raw_text', ocr_text) else 'No OCR text extracted',
                'extracted_data_gemini': structured_data
            }), 201

        except ValueError as ve: # Catch specific ValueErrors like missing API keys or JSON parsing issues from Gemini service
            current_app.logger.error(f"ValueError during processing for invoice {invoice_id if invoice_id else 'unknown'}: {ve}")
            if invoice_id and cursor and conn: # Ensure cursor and conn are available
                 try:
                    cursor.execute("UPDATE invoices SET status = 'error' WHERE id = %s", (invoice_id,))
                    conn.commit()
                 except Exception as db_err:
                    current_app.logger.error(f"DB error while setting status to error after ValueError: {db_err}")
            return jsonify({'error': f'Configuration or input error: {str(ve)}'}), 500
        except Exception as e: # Catch other general exceptions, including those re-raised from services
            if conn: conn.rollback()
            current_app.logger.error(f"Unexpected error for invoice {invoice_id if invoice_id else 'unknown'}: {e}", exc_info=True)
            if invoice_id and cursor and conn:
                 try:
                    cursor.execute("UPDATE invoices SET status = 'error' WHERE id = %s", (invoice_id,))
                    conn.commit()
                 except Exception as db_err:
                    current_app.logger.error(f"DB error while setting status to error after general Exception: {db_err}")
            return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500
        finally:
            if cursor: cursor.close()
    else:
        return jsonify({'error': 'File type not allowed'}), 400

@invoice_bp.route('/<int:invoice_id>', methods=['GET'])
def get_invoice(invoice_id):
    conn = db.get_db()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    # Use a dictionary cursor to get column names
    cursor = conn.cursor(dictionary=True) 
    try:
        cursor.execute("SELECT * FROM invoices WHERE id = %s", (invoice_id,))
        invoice = cursor.fetchone()
        if invoice:
            # Convert datetime objects to string for JSON serialization
            if invoice.get('uploaded_at'):
                invoice['uploaded_at'] = invoice['uploaded_at'].isoformat()
            if invoice.get('processed_at'):
                invoice['processed_at'] = invoice['processed_at'].isoformat()
            if invoice.get('invoice_date') and isinstance(invoice['invoice_date'], datetime.date):
                 invoice['invoice_date'] = invoice['invoice_date'].isoformat()

            return jsonify(invoice), 200
        else:
            return jsonify({'error': 'Invoice not found'}), 404
    except Exception as e:
        current_app.logger.error(f"Error fetching invoice {invoice_id}: {e}")
        return jsonify({'error': f'Could not fetch invoice: {str(e)}'}), 500
    finally:
        cursor.close()

@invoice_bp.route('/', methods=['GET'])
def list_invoices():
    # Add user_id filtering in a real app
    # user_id = ... 
    conn = db.get_db()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    cursor = conn.cursor(dictionary=True)
    try:
        # Add pagination later
        cursor.execute("SELECT id, user_id, file_name, uploaded_at, status, total_amount, vendor_name, invoice_date FROM invoices ORDER BY uploaded_at DESC LIMIT 100")
        invoices = cursor.fetchall()
        for invoice in invoices:
            if invoice.get('uploaded_at'):
                invoice['uploaded_at'] = invoice['uploaded_at'].isoformat()
            if invoice.get('invoice_date') and isinstance(invoice['invoice_date'], datetime.date):
                 invoice['invoice_date'] = invoice['invoice_date'].isoformat()

        return jsonify(invoices), 200
    except Exception as e:
        current_app.logger.error(f"Error listing invoices: {e}")
        return jsonify({'error': f'Could not list invoices: {str(e)}'}), 500
    finally:
        cursor.close()

# You would add more routes here for updating, deleting invoices, etc. 