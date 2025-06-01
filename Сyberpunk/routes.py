from flask import render_template, request, redirect, url_for, send_file, jsonify, flash
from config import app, db
from models import User, Expense
from receipt_processing import (allowed_file, extract_text, parse_receipt, 
                              save_receipt_to_db, get_all_receipts_from_db, 
                              get_receipt_details_from_db)
from financial_helpers import generate_expense_graph, export_to_excel
import os
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
import os
import pandas as pd
from models import db, User
@app.route('/')
def main_menu():
    users = User.query.all()
    return render_template('main_menu.html', users=users)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        workplace = request.form.get('workplace', '')
        salary = float(request.form['salary'])

        new_user = User(first_name=first_name, last_name=last_name, workplace=workplace, salary=salary)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('main_menu'))
    return render_template('register.html')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SECRET_KEY'] = 'tajny-klic'

# дозволені типи файлів
ALLOWED_EXTENSIONS = {'xlsx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/import_form', methods=['POST'])
def import_form():
    file = request.files['file']
    if file and file.filename.endswith('.xlsx'):
        filename = secure_filename(file.filename)
        filepath = os.path.join(os.getcwd(), filename)  # 💡 файл у корінь проєкту
        file.save(filepath)

        # читаємо Excel
        try:
            df = pd.read_excel(filepath)

            # 👇 Твоє збереження у БД або логіка тут
            for _, row in df.iterrows():
                user = User(
                    first_name=row.get('first_name', ''),
                    last_name=row.get('last_name', ''),
                    workplace=row.get('workplace', ''),
                    salary=row.get('salary', 0.0)
                )
                db.session.add(user)
            db.session.commit()

            os.remove(filepath)  # 🧹 опціонально видаляємо файл після імпорту

            return redirect(url_for('main_menu'))

        except Exception as e:
            return f"Chyba při čtení souboru: {e}", 500

    return "Chybný soubor", 400

@app.route('/user/<int:user_id>', methods=['GET', 'POST'])
def user_detail(user_id):
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        category = request.form['category']
        amount = float(request.form['amount'])
        description = request.form.get('description', '')
        
        new_exp = Expense(category=category, amount=amount, description=description, user_id=user_id)
        db.session.add(new_exp)
        db.session.commit()
        return redirect(url_for('user_detail', user_id=user_id))

    expenses = Expense.query.filter_by(user_id=user_id).order_by(Expense.date.desc()).all()
    chart = generate_expense_graph(user_id)
    return render_template('user_detail.html', user=user, expenses=expenses, chart=chart)

@app.route('/user/<int:user_id>/export')
def export_data(user_id):
    user = User.query.get(user_id)
    file = export_to_excel(user_id)
    filename = f"{user.first_name}_{user.last_name}_financni_data.xlsx"
    return send_file(file, as_attachment=True, download_name=filename, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.route('/user/<int:user_id>/delete', methods=['GET'])
def delete_user(user_id):
    user = User.query.get(user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
    return redirect(url_for('main_menu'))

@app.route('/family_wallet')
def family_wallet():
    return render_template('family_wallet.html')

@app.route('/ai_advisor')
def ai_advisor():
    return render_template('ai_advisor.html')

@app.route('/import_export.html')
def import_export():
    return render_template('import_export.html')

@app.route('/portfolio')
def portfolio():
    return render_template('portfolio.html')

@app.route('/scanner')
def scanner():
    return render_template('scanner.html')

@app.route('/scanner/upload', methods=['POST'])
def scanner_upload():
    if 'file' not in request.files:
        return jsonify({'error': 'Nebyl vybrán žádný soubor'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Nebyl vybrán žádný soubor'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Nepodporovaný formát souboru'}), 400

    try:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        text = extract_text(filepath)
        data = parse_receipt(text)
        save_receipt_to_db(data, filename)

        os.remove(filepath)

        return jsonify({
            'success': 'Účtenka byla úspěšně zpracována',
            'data': data
        })
    except Exception as e:
        if os.path.exists(filepath):
            os.remove(filepath)
        return jsonify({'error': str(e)}), 500

@app.route('/scanner/receipts')
def scanner_receipts():
    try:
        receipts = get_all_receipts_from_db()
        return render_template('receipts_list.html', receipts=receipts)
    except Exception as e:
        return render_template('error.html', error=str(e))

@app.route('/scanner/receipt/<int:receipt_id>')
def scanner_receipt_detail(receipt_id):
    receipt = get_receipt_details_from_db(receipt_id)
    if not receipt:
        return render_template('error.html', error="Účtenka nebyla nalezena"), 404
    return render_template('receipt_detail.html', receipt=receipt)