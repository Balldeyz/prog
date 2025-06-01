import os
import re
import pytesseract
import cv2
import sqlite3
from flask import Flask, request, render_template, jsonify
from datetime import datetime
from werkzeug.utils import secure_filename

# Initialize Flask app
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'temp'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'bmp'}
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB limit

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize database
def init_db():
    conn = sqlite3.connect('receipts.db')
    cursor = conn.cursor()
    
    # Check if table exists and has the correct structure
    cursor.execute("PRAGMA table_info(receipts)")
    columns = [column[1] for column in cursor.fetchall()]
    
    required_columns = [
        'id', 'date', 'time', 'total', 'cash_register', 
        'payment_method', 'change', 'receipt_number', 
        'items', 'vat', 'filename', 'timestamp'
    ]
    
    # If table doesn't exist or is missing columns, recreate it
    if not columns or not all(col in columns for col in required_columns):
        cursor.execute('''DROP TABLE IF EXISTS receipts''')
        cursor.execute('''CREATE TABLE receipts (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            date TEXT,
                            time TEXT,
                            total REAL,
                            cash_register TEXT,
                            payment_method TEXT,
                            change REAL,
                            receipt_number TEXT,
                            items TEXT,
                            vat TEXT,
                            filename TEXT,
                            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    conn.commit()
    conn.close()

# Check if file extension is allowed
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Extract text from image using OCR
def extract_text(image_path):
    try:
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError("Failed to load image")
        
        # Preprocess image for better OCR results
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.medianBlur(gray, 3)
        gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
        
        # Configure Tesseract for Czech language
        custom_config = r'--oem 3 --psm 6 -l ces'
        text = pytesseract.image_to_string(gray, config=custom_config)
        return text
    except Exception as e:
        raise RuntimeError(f"Image processing error: {str(e)}")

# Parse Czech receipt text into structured data
def parse_receipt(text):
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    data = {
        'date': None,
        'time': None,
        'total': None,
        'cash_register': None,
        'payment_method': None,
        'vat': [],
        'items': [],
        'change': None,
        'receipt_number': None,
        'store_info': None
    }
    
    # Patterns for different receipt elements
    item_pattern = re.compile(r'^(.+?)\s+(\d+[,.]\d{2})\s*(\d+)?\s*$')
    date_pattern = re.compile(r'\b\d{1,2}\.\d{1,2}\.\d{4}\b')
    time_pattern = re.compile(r'\b\d{1,2}:\d{2}\b')
    receipt_num_pattern = re.compile(r'\b\d{5,}\b')
    price_pattern = re.compile(r'(\d+[,.]\d{2})')
    store_pattern = re.compile(r'^([A-Za-z0-9].+?)\s+(s\.r\.o|a\.s|v\.o\.s)\.?$', re.IGNORECASE)
    
    store_info = []
    processing_items = True
    
    for line in lines:
        line_lower = line.lower()
        
        # Extract store information (first few lines usually) багнута хуйня 
        if not data['store_info'] and len(store_info) < 3:
            if store_pattern.match(line):
                store_info.append(line)
            elif line.replace('.','').replace(',','').replace(' ','').isalnum():
                store_info.append(line)
            if len(store_info) >= 3:
                data['store_info'] = '\n'.join(store_info)
        
        # Extract date and time together (common format: DD.MM.YYYY HH:MM)
        datetime_match = re.search(r'(\d{1,2}\.\d{1,2}\.\d{4})\s+(\d{1,2}:\d{2})', line)
        if datetime_match:
            data['date'] = datetime_match.group(1)
            data['time'] = datetime_match.group(2)
        
        # Extract receipt number (typically at the end)
        receipt_num_match = receipt_num_pattern.search(line)
        if receipt_num_match and not data['receipt_number']:
            data['receipt_number'] = receipt_num_match.group()
        
        # Extract total amount
        if ('celkem' in line_lower or 'součet' in line_lower or 'k placeni' in line_lower) and not data['total']:
            price_match = price_pattern.search(line.replace(',', '.'))
            if price_match:
                data['total'] = float(price_match.group(1).replace(',', '.'))
        
        # Extract payment method and change
        if 'zaplaceno' in line_lower and not data['payment_method']:
            method = 'hotovost' if 'hotovost' in line_lower else 'karta'
            data['payment_method'] = method.capitalize()
            
            paid_match = price_pattern.search(line.replace(',', '.'))
            if paid_match:
                data['paid_amount'] = float(paid_match.group(1).replace(',', '.'))
        
        if ('vrácen' in line_lower or 'zpět' in line_lower) and not data['change']:
            price_match = price_pattern.search(line.replace(',', '.'))
            if price_match:
                data['change'] = float(price_match.group(1).replace(',', '.'))
        
        # Extract VAT information
        if 'dph' in line_lower:
            parts = line.split()
            for i, part in enumerate(parts):
                if part.lower() == 'dph' and i+3 < len(parts):
                    try:
                        rate = parts[i+1].replace('%', '').replace(',', '.')
                        amount = parts[i+3].replace(',', '.').replace('czk', '').replace('kč', '')
                        if rate.replace('.', '', 1).isdigit() and amount.replace('.', '', 1).isdigit():
                            data['vat'].append({
                                'rate': float(rate),
                                'amount': float(amount)
                            })
                    except (ValueError, IndexError):
                        pass
        
        # Extract items - more precise matching
        if processing_items:
            item_match = item_pattern.match(line)
            if item_match:
                item_name = item_match.group(1).strip()
                item_price = item_match.group(2).replace(',', '.')
                
                # Skip lines that aren't actual items
                if not any(x in item_name.lower() for x in ['dph', 'celkem', 'součet', 'zaokrouhlení', 
                                                          'zaplaceno', 'vrácen', 'k placeni', 'netto']):
                    data['items'].append({
                        'name': item_name,
                        'price': float(item_price),
                        'quantity': int(item_match.group(3)) if item_match.group(3) else 1
                    })
            elif any(x in line_lower for x in ['součet', 'celkem', 'dph', 'zaokrouhlení']):
                processing_items = False
    
    # Clean up extracted data
    if data['items'] and not data['total']:
        # Calculate total from items if not found in text
        data['total'] = sum(item['price'] for item in data['items'])
    
    # Fix common Penny Market specific issues
    if data.get('receipt_number') and len(data['receipt_number']) > 8:
        # Sometimes the receipt number includes store code
        data['receipt_number'] = data['receipt_number'][-8:]
    
    return data

# Save receipt data to database
def save_to_db(data, filename):
    conn = sqlite3.connect('receipts.db')
    cursor = conn.cursor()
    
    cursor.execute('''INSERT INTO receipts 
                  (date, time, total, cash_register, payment_method, 
                   change, receipt_number, items, vat, filename) 
                  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
               (data.get('date'),
                data.get('time'),
                data.get('total'),
                data.get('cash_register'),
                data.get('payment_method'),
                data.get('change'),
                data.get('receipt_number'),
                str(data.get('items', [])),
                str(data.get('vat', [])),
                filename))
    
    conn.commit()
    conn.close()

# Get all receipts from database
def get_receipts():
    conn = sqlite3.connect('receipts.db')
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    cursor = conn.cursor()
    cursor.execute('''SELECT id, date, time, total, cash_register, 
                     payment_method, change, receipt_number, items, 
                     vat, timestamp FROM receipts ORDER BY timestamp DESC''')
    receipts = cursor.fetchall()
    conn.close()
    
    # Convert to list of dictionaries
    result = []
    for row in receipts:
        receipt = dict(row)
        # Convert string fields back to Python objects
        receipt['items'] = eval(receipt['items']) if receipt['items'] else []
        receipt['vat'] = eval(receipt['vat']) if receipt['vat'] else []
        result.append(receipt)
    
    return result

# Get receipt details by ID
def get_receipt_details(receipt_id):
    conn = sqlite3.connect('receipts.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''SELECT * FROM receipts WHERE id = ?''', (receipt_id,))
    receipt = cursor.fetchone()
    conn.close()
    
    if receipt:
        receipt = dict(receipt)
        receipt['items'] = eval(receipt['items']) if receipt['items'] else []
        receipt['vat'] = eval(receipt['vat']) if receipt['vat'] else []
        return receipt
    return None

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/receipts', methods=['GET'])
def get_all_receipts():
    try:
        receipts = get_receipts()
        return jsonify(receipts)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file selected'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Unsupported file format'}), 400
    
    try:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        text = extract_text(filepath)
        data = parse_receipt(text)
        save_to_db(data, filename)
        
        os.remove(filepath)
        
        return jsonify({
            'success': 'Receipt processed successfully',
            'data': data
        })
    except Exception as e:
        if os.path.exists(filepath):
            os.remove(filepath)
        return jsonify({'error': str(e)}), 500

# Run the application
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)

