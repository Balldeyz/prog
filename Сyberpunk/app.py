from config import app, db
from models import User, Expense
import receipt_processing
from routes import *
import financial_helpers

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        receipt_processing.init_receipts_db()
    app.run(host="0.0.0.0",port=5000)