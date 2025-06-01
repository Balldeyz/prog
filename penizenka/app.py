from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
DB_NAME = 'finance.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS family_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            age INTEGER NOT NULL,
            employment TEXT NOT NULL,
            salary REAL NOT NULL,
            contribution REAL NOT NULL,
            last_activity TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'ACTIVE'
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            date TEXT NOT NULL,
            FOREIGN KEY(member_id) REFERENCES family_members(id)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS mortgages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            total_amount REAL NOT NULL,
            interest_rate REAL NOT NULL,
            term INTEGER NOT NULL,
            monthly_payment REAL NOT NULL,
            start_date TEXT NOT NULL,
            primary_borrower INTEGER NOT NULL,
            co_borrower INTEGER,
            remaining_balance REAL NOT NULL,
            payments_made INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(primary_borrower) REFERENCES family_members(id),
            FOREIGN KEY(co_borrower) REFERENCES family_members(id)
        )
    ''')

    conn.commit()
    conn.close()

def get_family_summary():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute("SELECT SUM(salary) FROM family_members WHERE status = 'ACTIVE'")
    total_income = c.fetchone()[0] or 0
    
    expenses = {
        'fixed': {'mortgage': 0, 'utilities': 2500, 'insurance': 1500, 'total': 4000},
        'variable': {'food': 6000, 'transport': 3000, 'education': 2000, 'total': 11000},
        'discretionary': {'entertainment': 1500, 'savings': 3000, 'other': 1000, 'total': 5500}
    }
    
    c.execute("SELECT monthly_payment FROM mortgages LIMIT 1")
    mortgage = c.fetchone()
    if mortgage:
        expenses['fixed']['mortgage'] = mortgage[0]
        expenses['fixed']['total'] += mortgage[0]
    
    total_expenses = expenses['fixed']['total'] + expenses['variable']['total'] + expenses['discretionary']['total']
    net_income = total_income - total_expenses
    savings_rate = (expenses['discretionary']['savings'] / total_income * 100) if total_income > 0 else 0
    
    conn.close()
    
    return {
        'total_income': total_income,
        'total_expenses': total_expenses,
        'net_income': net_income,
        'savings_rate': round(savings_rate, 1)
    }

@app.route('/')
def home():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute("SELECT * FROM family_members")
    members = [{
        'id': row[0], 'name': row[1], 'role': row[2], 'age': row[3],
        'employment': row[4], 'income': row[5], 'contribution': row[6],
        'last_activity': row[7], 'status': row[8]
    } for row in c.fetchall()]
    
    # Initialize mortgage as None by default
    mortgage = None
    
    c.execute("""
        SELECT m.*, p.name as primary_name, c.name as co_name 
        FROM mortgages m
        LEFT JOIN family_members p ON m.primary_borrower = p.id
        LEFT JOIN family_members c ON m.co_borrower = c.id
        LIMIT 1
    """)
    mortgage_row = c.fetchone()
    
    if mortgage_row and len(mortgage_row) >= 13:  # Check if row exists and has enough columns
        mortgage = {
            'id': mortgage_row[0], 'name': mortgage_row[1], 'total_amount': mortgage_row[2],
            'interest_rate': mortgage_row[3], 'term': mortgage_row[4], 'monthly_payment': mortgage_row[5],
            'start_date': mortgage_row[6], 'primary_borrower': mortgage_row[7],
            'co_borrower': mortgage_row[8], 'remaining_balance': mortgage_row[9],
            'payments_made': mortgage_row[10], 'primary_name': mortgage_row[11],
            'co_name': mortgage_row[12] if mortgage_row[12] else None  # Handle NULL co_borrower
        }
    
    # Safely get mortgage payment amount
    mortgage_payment = mortgage['monthly_payment'] if mortgage else 0
    
    expenses = {
        'fixed': {
            'mortgage': mortgage_payment,
            'utilities': 2500,
            'insurance': 1500,
            'total': mortgage_payment + 2500 + 1500
        },
        'variable': {
            'food': 6000,
            'transport': 3000,
            'education': 2000,
            'total': 11000
        },
        'discretionary': {
            'entertainment': 1500,
            'savings': 3000,
            'other': 1000,
            'total': 5500
        }
    }
    
    summary = get_family_summary()
    conn.close()
    
    return render_template('index.html', 
                         family_id=1,
                         members=members,
                         mortgage=mortgage,
                         expenses=expenses,
                         summary=summary)
#бля нахуя ми цим занялися 1,48 я єбуся з перевіркою працевлаштування для створення гіпотеки жбучий банкінг
@app.route('/api/families/<int:family_id>', methods=['GET', 'POST'])
def family_api(family_id):
    if request.method == 'GET':
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        c.execute("SELECT * FROM family_members")
        members = [{
            'id': row[0], 'name': row[1], 'role': row[2], 'age': row[3],
            'employment': row[4], 'income': row[5], 'contribution': row[6],
            'last_activity': row[7], 'status': row[8]
        } for row in c.fetchall()]
        
        c.execute("""
            SELECT m.*, p.name as primary_name, c.name as co_name 
            FROM mortgages m
            LEFT JOIN family_members p ON m.primary_borrower = p.id
            LEFT JOIN family_members c ON m.co_borrower = c.id
            LIMIT 1
        """)
        mortgage_row = c.fetchone()
        mortgage = None
        if mortgage_row:
            mortgage = {
                'id': mortgage_row[0], 'name': mortgage_row[1], 'total_amount': mortgage_row[2],
                'interest_rate': mortgage_row[3], 'term': mortgage_row[4], 'monthly_payment': mortgage_row[5],
                'start_date': mortgage_row[6], 'primary_borrower': mortgage_row[7],
                'co_borrower': mortgage_row[8], 'remaining_balance': mortgage_row[9],
                'payments_made': mortgage_row[10], 'primary_name': mortgage_row[11],
                'co_name': mortgage_row[12]
            }
        
        conn.close()
        
        return jsonify({
            'members': members,
            'mortgage': mortgage,
            'expenses': {
                'fixed': {
                    'mortgage': mortgage['monthly_payment'] if mortgage else 0,
                    'utilities': 2500,
                    'insurance': 1500
                },
                'variable': {
                    'food': 6000,
                    'transport': 3000,
                    'education': 2000
                },
                'discretionary': {
                    'entertainment': 1500,
                    'savings': 3000,
                    'other': 1000
                }
            }
        })
    
    elif request.method == 'POST':
        data = request.json
        return jsonify({'status': 'success', 'message': 'Data received'})

@app.route('/add_member', methods=['GET', 'POST'])
def add_member():
    if request.method == 'POST':
        name = request.form['name']
        role = request.form['role']
        age = int(request.form['age'])
        employment = request.form['employment']
        income = float(request.form['income'])
        contribution = float(request.form['contribution'])
        last_activity = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("""
            INSERT INTO family_members 
            (name, role, age, employment, salary, contribution, last_activity) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (name, role, age, employment, income, contribution, last_activity))
        conn.commit()
        conn.close()
        
        flash('Family member added successfully!', 'success')
        return redirect(url_for('home'))
    
    # For GET request, just render the template
    return render_template('add_member.html', family_id=1)

@app.route('/add_mortgage', methods=['GET', 'POST'])
def add_mortgage():
    if request.method == 'POST':
        try:
            # Отримання даних з форми з перевіркою на наявність
            name = request.form.get('name', '').strip()
            if not name:
                raise ValueError("Mortgage name is required")
            
            # Отримання та перевірка суми
            total_amount_str = request.form.get('total_amount', '0').replace(' ', '')
            try:
                total_amount = float(total_amount_str)
            except ValueError:
                raise ValueError("Invalid total amount")
            
            if total_amount <= 0:
                raise ValueError("Amount must be positive")
            
            # Отримання інших полів
            interest_rate = float(request.form.get('interest_rate', 0))
            term = int(request.form.get('term', 0))
            start_date = request.form.get('start_date', '')
            
            # Обробка опціональних полів
            primary_borrower = request.form.get('primary_borrower', '')
            primary_borrower = int(primary_borrower) if primary_borrower else None
            
            co_borrower = request.form.get('co_borrower', '')
            co_borrower = int(co_borrower) if co_borrower else None
            
            # Перевірка обов'язкових полів
            if not all([name, total_amount > 0, interest_rate > 0, term > 0, start_date]):
                raise ValueError("Please fill all required fields correctly")
            
            # Розрахунок платежів
            monthly_rate = interest_rate / 100 / 12
            payments = term * 12
            monthly_payment = total_amount * (monthly_rate * (1 + monthly_rate)**payments) / ((1 + monthly_rate)**payments - 1)
            
            # Збереження в базу даних
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("""
                INSERT INTO mortgages 
                (name, total_amount, interest_rate, term, monthly_payment, start_date, 
                 primary_borrower, co_borrower, remaining_balance) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (name, total_amount, interest_rate, term, monthly_payment, start_date, 
                  primary_borrower, co_borrower, total_amount))
            conn.commit()
            conn.close()
            
            flash('Hypotéka byla úspěšně přidána!', 'success')
            return redirect(url_for('home'))
            
        except ValueError as e:
            flash(f'Chyba: {str(e)}', 'error')
            return redirect(request.referrer)
        except Exception as e:
            flash('Došlo k neočekávané chybě', 'error')
            return redirect(request.referrer)
    
    # GET request handling...
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, name, salary FROM family_members WHERE employment = 'Employed'")
    members = c.fetchall()
    conn.close()
    
    return render_template('add_mortgage.html', members=members)

@app.route('/update_expenses', methods=['POST'])
def update_expenses():
    category = request.form['category']
    updates = {k: float(v) for k, v in request.form.items() if k != 'category'}
    flash(f'{category.capitalize()} expenses updated successfully!', 'success')
    return redirect(url_for('home'))

@app.route('/delete_member/<int:member_id>', methods=['POST'])
def delete_member(member_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM family_members WHERE id = ?", (member_id,))
    conn.commit()
    conn.close()
    
    flash('Family member removed successfully!', 'success')
    return redirect(url_for('home'))

@app.route('/make_payment/<int:mortgage_id>', methods=['POST'])
def make_payment(mortgage_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    try:
        c.execute("SELECT monthly_payment, remaining_balance FROM mortgages WHERE id = ?", (mortgage_id,))
        mortgage = c.fetchone()
        
        if not mortgage:
            flash('Mortgage not found!', 'error')
            return redirect(url_for('home'))
        
        monthly_payment = mortgage[0]
        new_balance = max(0, mortgage[1] - monthly_payment)
        
        c.execute("""
            UPDATE mortgages 
            SET remaining_balance = ?, payments_made = payments_made + 1 
            WHERE id = ?
        """, (new_balance, mortgage_id))
        conn.commit()
        
        flash(f'Mortgage payment of {monthly_payment} ₴ processed!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error processing payment: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('home'))

@app.route('/delete_mortgage/<int:mortgage_id>', methods=['POST'])
def delete_mortgage(mortgage_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM mortgages WHERE id = ?", (mortgage_id,))
    conn.commit()
    conn.close()
    
    flash('Mortgage removed successfully!', 'success')
    return redirect(url_for('home'))

if __name__ == '__main__':
    init_db()
    app.run(host="0.0.0.0", port=5002)