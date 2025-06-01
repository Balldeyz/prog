import base64
import io
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from models import Expense, User
from config import db

def generate_expense_graph(user_id):
    """Generate expense graph by category for user"""
    expenses = Expense.query.filter_by(user_id=user_id).all()
    if not expenses:
        return None

    data = {}
    for exp in expenses:
        data[exp.category] = data.get(exp.category, 0) + exp.amount

    sns.set_theme(style="whitegrid")
    plt.figure(figsize=(8, 5))
    plt.bar(data.keys(), data.values(), color='skyblue')
    plt.xlabel('Kategorie')
    plt.ylabel('Celková částka')
    plt.title('Výdaje podle kategorií')
    plt.xticks(rotation=45)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode()
    plt.close()
    return encoded

def export_to_excel(user_id):
    """Export user financial data to Excel"""
    user = User.query.get(user_id)
    expenses = Expense.query.filter_by(user_id=user_id).all()

    user_df = pd.DataFrame([{
        'Jméno': user.first_name,
        'Příjmení': user.last_name,
        'Pracoviště': user.workplace,
        'Plat': user.salary
    }])

    expenses_df = pd.DataFrame([{
        'Kategorie': e.category,
        'Částka': e.amount,
        'Popis': e.description,
        'Datum': e.date.strftime("%Y-%m-%d %H:%M:%S")
    } for e in expenses])

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        user_df.to_excel(writer, sheet_name='Uživatel', index=False)
        expenses_df.to_excel(writer, sheet_name='Výdaje', index=False)

    output.seek(0)
    return output