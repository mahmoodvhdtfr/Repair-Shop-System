import sqlite3
import pandas as pd
from datetime import datetime

def init_db():
    conn = sqlite3.connect('data/repair_shop.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            national_id TEXT,
            phone_number TEXT NOT NULL,
            entry_date TEXT NOT NULL,
            exit_date TEXT,
            device_code TEXT NOT NULL,
            device_type TEXT NOT NULL,
            material_cost INTEGER DEFAULT 0,
            service_cost INTEGER DEFAULT 0,
            total_cost INTEGER,
            description TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def calculate_total_cost(material_cost, service_cost):
    return int(material_cost or 0) + int(service_cost or 0)

def add_customer(data):
    conn = sqlite3.connect('data/repair_shop.db')
    cursor = conn.cursor()
    
    total_cost = calculate_total_cost(data['material_cost'], data['service_cost'])
    
    cursor.execute('''
        INSERT INTO customers 
        (full_name, national_id, phone_number, entry_date, exit_date, 
         device_code, device_type, material_cost, service_cost, total_cost, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data['full_name'], data['national_id'], data['phone_number'],
        data['entry_date'], data['exit_date'], data['device_code'],
        data['device_type'], data['material_cost'], data['service_cost'],
        total_cost, data['description']
    ))
    
    conn.commit()
    customer_id = cursor.lastrowid
    conn.close()
    return customer_id

def get_all_customers():
    conn = sqlite3.connect('data/repair_shop.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM customers ORDER BY created_at DESC')
    customers = cursor.fetchall()
    conn.close()
    return customers

def search_customers(query):
    conn = sqlite3.connect('data/repair_shop.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM customers 
        WHERE full_name LIKE ? OR phone_number LIKE ? OR device_code LIKE ?
        ORDER BY created_at DESC
    ''', (f'%{query}%', f'%{query}%', f'%{query}%'))
    customers = cursor.fetchall()
    conn.close()
    return customers

def import_from_excel(file_path):
    try:
        df = pd.read_excel(file_path)
        imported_count = 0
        
        for _, row in df.iterrows():
            data = {
                'full_name': row.get('نام مشتری', ''),
                'national_id': str(row.get('کد ملی', '')),
                'phone_number': str(row.get('شماره تماس', '')),
                'entry_date': row.get('تاریخ ورود', ''),
                'exit_date': row.get('تاریخ خروج', ''),
                'device_code': row.get('کد وسیله', ''),
                'device_type': row.get('نوع وسیله', ''),
                'material_cost': int(row.get('قیمت جنس', 0) or 0),
                'service_cost': int(row.get('سود فروش و دستمزد', 0) or 0),
                'description': row.get('توضیحات', '')
            }
            
            add_customer(data)
            imported_count += 1
            
        return imported_count
    except Exception as e:
        raise Exception(f"خطا در ایمپورت فایل: {str(e)}")

def export_to_excel():
    customers = get_all_customers()
    df = pd.DataFrame(customers, columns=[
        'ID', 'نام مشتری', 'کد ملی', 'شماره تماس', 'تاریخ ورود', 
        'تاریخ خروج', 'کد وسیله', 'نوع وسیله', 'قیمت جنس', 
        'سود فروش و دستمزد', 'مجموع', 'توضیحات', 'تاریخ ثبت'
    ])
    
    filename = f"گزارش_تعمیرات_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    df.to_excel(f"exports/{filename}", index=False, engine='openpyxl')
    return filename