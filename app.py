from flask import Flask, render_template, request, jsonify, send_file
import sqlite3
import pandas as pd
import os
import sys
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)

# مسیرهای پروژه - استفاده از مسیر مطلق
if getattr(sys, 'frozen', False):
    # اگر برنامه executable شده باشد
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # حالت عادی
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'uploads')
app.config['EXPORT_FOLDER'] = os.path.join(BASE_DIR, 'exports')
app.config['DATA_FOLDER'] = os.path.join(BASE_DIR, 'data')
app.config['DATABASE_PATH'] = os.path.join(app.config['DATA_FOLDER'], 'repair_shop.db')

print(f"📁 مسیر پایه: {BASE_DIR}")
print(f"📊 مسیر دیتابیس: {app.config['DATABASE_PATH']}")

# ایجاد پوشه‌های مورد نیاز
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['EXPORT_FOLDER'], exist_ok=True)
os.makedirs(app.config['DATA_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

def init_db():
    """ایجاد دیتابیس و جدول‌ها"""
    try:
        # بررسی وجود فایل دیتابیس
        db_exists = os.path.exists(app.config['DATABASE_PATH'])
        
        conn = sqlite3.connect(app.config['DATABASE_PATH'])
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                phone_number TEXT NOT NULL,
                entry_date TEXT NOT NULL,
                exit_date TEXT,
                device_code TEXT NOT NULL,
                device_type TEXT NOT NULL,
                material_cost INTEGER DEFAULT 0,
                service_cost INTEGER DEFAULT 0,
                total_cost INTEGER DEFAULT 0,
                description TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        
        if db_exists:
            print("✅ دیتابیس موجود بارگیری شد")
        else:
            print("✅ دیتابیس جدید ایجاد شد")
            
        # نمایش اطلاعات دیتابیس
        show_db_info()
        
    except Exception as e:
        print(f"❌ خطا در ایجاد دیتابیس: {e}")

def show_db_info():
    """نمایش اطلاعات دیتابیس"""
    try:
        conn = sqlite3.connect(app.config['DATABASE_PATH'])
        cursor = conn.cursor()
        
        # تعداد رکوردها
        cursor.execute('SELECT COUNT(*) FROM customers')
        count = cursor.fetchone()[0]
        
        # اندازه فایل
        db_size = os.path.getsize(app.config['DATABASE_PATH'])
        
        conn.close()
        
        print(f"📊 تعداد مشتریان در دیتابیس: {count}")
        print(f"💾 اندازه فایل دیتابیس: {db_size} بایت")
        
    except Exception as e:
        print(f"⚠️ خطا در دریافت اطلاعات دیتابیس: {e}")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def safe_int(value, default=0):
    """تبدیل ایمن به integer"""
    try:
        if value is None or value == '':
            return default
        return int(value)
    except (ValueError, TypeError):
        return default

def normalize_persian_date(date_str):
    """نرمال کردن تاریخ به فرمت استاندارد 1403/01/01"""
    if not date_str or date_str.strip() == '':
        return None
    
    # حذف فاصله و کاراکترهای اضافی
    date_str = date_str.strip().replace(' ', '')
    
    # جدا کردن بخش‌های تاریخ
    parts = date_str.split('/')
    if len(parts) != 3:
        return None
    
    year = parts[0]
    month = parts[1].zfill(2)  # اضافه کردن صفر به ماه
    day = parts[2].zfill(2)    # اضافه کردن صفر به روز
    
    return f"{year}/{month}/{day}"

def add_customer(data):
    """افزودن مشتری جدید به دیتابیس"""
    conn = sqlite3.connect(app.config['DATABASE_PATH'])
    cursor = conn.cursor()
    
    # تبدیل مقادیر به integer و مدیریت مقادیر خالی
    material_cost = safe_int(data.get('material_cost', 0))
    service_cost = safe_int(data.get('service_cost', 0))
    total_cost = material_cost + service_cost
    
    cursor.execute('''
        INSERT INTO customers 
        (full_name, phone_number, entry_date, exit_date, 
         device_code, device_type, material_cost, service_cost, total_cost, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data['full_name'], 
        data['phone_number'],
        data['entry_date'], 
        data.get('exit_date', ''), 
        data['device_code'],
        data['device_type'], 
        material_cost, 
        service_cost,
        total_cost, 
        data.get('description', '')
    ))
    
    conn.commit()
    customer_id = cursor.lastrowid
    conn.close()
    
    print(f"➕ مشتری جدید ثبت شد: {data['full_name']} (ID: {customer_id})")
    return customer_id

def get_all_customers():
    """دریافت همه مشتریان"""
    conn = sqlite3.connect(app.config['DATABASE_PATH'])
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM customers ORDER BY created_at DESC')
    customers = cursor.fetchall()
    conn.close()
    return customers

def search_customers(query):
    """جستجوی مشتریان"""
    conn = sqlite3.connect(app.config['DATABASE_PATH'])
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM customers 
        WHERE full_name LIKE ? OR phone_number LIKE ? OR device_code LIKE ? OR device_type LIKE ?
        ORDER BY created_at DESC
    ''', (f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%'))
    customers = cursor.fetchall()
    conn.close()
    return customers

def get_income_by_exit_date_range(start_date, end_date):
    """محاسبه درآمد در بازه زمانی مشخص بر اساس تاریخ خروج"""
    conn = sqlite3.connect(app.config['DATABASE_PATH'])
    cursor = conn.cursor()
    
    # نرمال کردن تاریخ‌های ورودی
    start_normalized = normalize_persian_date(start_date)
    end_normalized = normalize_persian_date(end_date)
    
    if not start_normalized or not end_normalized:
        return 0
    
    # گرفتن همه مشتریان با تاریخ خروج
    cursor.execute('''
        SELECT id, exit_date, total_cost FROM customers 
        WHERE exit_date IS NOT NULL AND exit_date != ''
    ''')
    all_customers = cursor.fetchall()
    
    # فیلتر کردن در پایتون با تاریخ نرمال شده
    total_income = 0
    
    for customer in all_customers:
        customer_exit_normalized = normalize_persian_date(customer[1])
        if customer_exit_normalized:
            # مقایسه تاریخ‌های نرمال شده
            if start_normalized <= customer_exit_normalized <= end_normalized:
                total_income += customer[2] or 0
    
    conn.close()
    return total_income

def get_customers_by_exit_date_range(start_date, end_date):
    """دریافت مشتریان در بازه زمانی مشخص بر اساس تاریخ خروج"""
    conn = sqlite3.connect(app.config['DATABASE_PATH'])
    cursor = conn.cursor()
    
    # نرمال کردن تاریخ‌های ورودی
    start_normalized = normalize_persian_date(start_date)
    end_normalized = normalize_persian_date(end_date)
    
    if not start_normalized or not end_normalized:
        return []
    
    # گرفتن همه مشتریان با تاریخ خروج
    cursor.execute('SELECT * FROM customers WHERE exit_date IS NOT NULL AND exit_date != ""')
    all_customers = cursor.fetchall()
    
    # فیلتر و مرتب‌سازی در پایتون
    matching_customers = []
    for customer in all_customers:
        customer_exit_normalized = normalize_persian_date(customer[4])
        if customer_exit_normalized:
            if start_normalized <= customer_exit_normalized <= end_normalized:
                matching_customers.append(customer)
    
    # مرتب‌سازی بر اساس تاریخ خروج (نرمال شده)
    matching_customers.sort(
        key=lambda x: normalize_persian_date(x[4]) or '', 
        reverse=True
    )
    
    conn.close()
    return matching_customers

def import_from_excel(file_path):
    """ایمپورت از فایل اکسل"""
    try:
        df = pd.read_excel(file_path)
        imported_count = 0
        
        print(f"📥 شروع ایمپورت از فایل: {file_path}")
        print(f"📋 تعداد ردیف‌های پیدا شده: {len(df)}")
        
        for index, row in df.iterrows():
            # تطبیق نام ستون‌ها با فایل اکسل شما
            data = {
                'full_name': str(row.get('نام مشتری', '')) or str(row.get('نام منشری', '')) or 'نامشخص',
                'phone_number': str(row.get('شماره تماس', '')) or 'نامشخص',
                'entry_date': str(row.get('تاریخ ورود', '')) or '1403/10/15',
                'exit_date': str(row.get('تاریخ خروج', '')) or str(row.get('تاریخ حریح', '')) or '',
                'device_code': str(row.get('کد وسیله', '')) or 'نامشخص',
                'device_type': str(row.get('نوع وسیله', '')) or 'نامشخص',
                'material_cost': safe_int(row.get('قیمت جنس', 0)),
                'service_cost': safe_int(row.get('سود فروش و دستمزد', 0) or row.get('سود فروش و مستمره', 0)),
                'description': str(row.get('توضیحات', '')) or ''
            }
            
            add_customer(data)
            imported_count += 1
            
            # نمایش پیشرفت
            if (index + 1) % 10 == 0:
                print(f"📊 در حال پردازش ردیف {index + 1} از {len(df)}")
        
        print(f"✅ ایمپورت کامل شد: {imported_count} رکورد اضافه شد")
        return imported_count
        
    except Exception as e:
        print(f"❌ خطا در ایمپورت فایل: {str(e)}")
        raise Exception(f"خطا در ایمپورت فایل: {str(e)}")

def export_to_excel():
    """اکسپورت به فایل اکسل"""
    customers = get_all_customers()
    
    # ساخت لیست داده‌ها برای DataFrame
    data = []
    for customer in customers:
        data.append({
            'ID': customer[0],
            'نام مشتری': customer[1],
            'شماره تماس': customer[2],
            'تاریخ ورود': customer[3],
            'تاریخ خروج': customer[4] or '',
            'کد وسیله': customer[5],
            'نوع وسیله': customer[6],
            'قیمت جنس': customer[7] or 0,
            'سود فروش و دستمزد': customer[8] or 0,
            'مجموع': customer[9] or 0,
            'توضیحات': customer[10] or '',
            'تاریخ ثبت': customer[11]
        })
    
    df = pd.DataFrame(data)
    
    filename = f"گزارش_تعمیرات_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    filepath = os.path.join(app.config['EXPORT_FOLDER'], filename)
    df.to_excel(filepath, index=False, engine='openpyxl')
    
    print(f"📤 گزارش اکسل ایجاد شد: {filename}")
    return filename

# Routes
@app.route('/')
def index():
    return render_template('index.html')
    
@app.route('/api/update-customer', methods=['POST'])
def update_customer():
    """به‌روزرسانی اطلاعات مشتری"""
    try:
        customer_id = request.form['id']
        data = {
            'full_name': request.form['full_name'],
            'phone_number': request.form['phone_number'],
            'entry_date': request.form['entry_date'],
            'exit_date': request.form.get('exit_date', ''),
            'device_code': request.form['device_code'],
            'device_type': request.form['device_type'],
            'material_cost': safe_int(request.form.get('material_cost', 0)),
            'service_cost': safe_int(request.form.get('service_cost', 0)),
            'description': request.form.get('description', '')
        }
        
        # محاسبه مجموع جدید
        total_cost = data['material_cost'] + data['service_cost']
        
        conn = sqlite3.connect(app.config['DATABASE_PATH'])
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE customers 
            SET full_name = ?, phone_number = ?, entry_date = ?, exit_date = ?,
                device_code = ?, device_type = ?, material_cost = ?, service_cost = ?,
                total_cost = ?, description = ?
            WHERE id = ?
        ''', (
            data['full_name'], data['phone_number'], data['entry_date'], 
            data['exit_date'], data['device_code'], data['device_type'],
            data['material_cost'], data['service_cost'], total_cost,
            data['description'], customer_id
        ))
        
        conn.commit()
        conn.close()
        
        print(f"✏️ مشتری به‌روزرسانی شد: {data['full_name']} (ID: {customer_id})")
        
        return jsonify({
            'success': True,
            'message': 'اطلاعات مشتری با موفقیت به‌روزرسانی شد'
        })
        
    except Exception as e:
        print(f"❌ خطا در به‌روزرسانی مشتری: {e}")
        return jsonify({
            'success': False,
            'message': f'خطا در به‌روزرسانی اطلاعات: {str(e)}'
        })    
    
@app.route('/api/delete-customer/<int:customer_id>', methods=['DELETE'])
def delete_customer(customer_id):
    """حذف یک مشتری"""
    try:
        conn = sqlite3.connect(app.config['DATABASE_PATH'])
        cursor = conn.cursor()
        
        # ابتدا اطلاعات مشتری رو بگیریم برای لاگ
        cursor.execute('SELECT full_name FROM customers WHERE id = ?', (customer_id,))
        customer = cursor.fetchone()
        
        if not customer:
            return jsonify({
                'success': False,
                'message': 'مشتری یافت نشد'
            })
        
        # حذف مشتری
        cursor.execute('DELETE FROM customers WHERE id = ?', (customer_id,))
        conn.commit()
        conn.close()
        
        print(f"🗑️ مشتری حذف شد: {customer[0]} (ID: {customer_id})")
        
        return jsonify({
            'success': True,
            'message': f'مشتری "{customer[0]}" با موفقیت حذف شد'
        })
        
    except Exception as e:
        print(f"❌ خطا در حذف مشتری: {e}")
        return jsonify({
            'success': False,
            'message': f'خطا در حذف مشتری: {str(e)}'
        })

@app.route('/add-customer', methods=['GET', 'POST'])
def add_customer_page():
    if request.method == 'POST':
        try:
            data = {
                'full_name': request.form['full_name'],
                'phone_number': request.form['phone_number'],
                'entry_date': request.form['entry_date'],
                'exit_date': request.form.get('exit_date', ''),
                'device_code': request.form['device_code'],
                'device_type': request.form['device_type'],
                'material_cost': safe_int(request.form.get('material_cost', 0)),
                'service_cost': safe_int(request.form.get('service_cost', 0)),
                'description': request.form.get('description', '')
            }
            
            customer_id = add_customer(data)
            return jsonify({
                'success': True, 
                'message': 'مشتری با موفقیت ثبت شد', 
                'id': customer_id
            })
        
        except Exception as e:
            return jsonify({
                'success': False, 
                'message': f'خطا در ثبت اطلاعات: {str(e)}'
            })
    
    return render_template('add_customer.html')

@app.route('/customers')
def customers_page():
    search_query = request.args.get('search', '')
    if search_query:
        customers = search_customers(search_query)
    else:
        customers = get_all_customers()
    return render_template('customers.html', customers=customers)

@app.route('/reports')
def reports_page():
    """صفحه گزارش‌های پیشرفته"""
    return render_template('reports.html')

@app.route('/import-export')
def import_export_page():
    return render_template('import_export.html')

@app.route('/api/import-excel', methods=['POST'])
def import_excel():
    if 'file' not in request.files:
        return jsonify({
            'success': False, 
            'message': 'فایلی انتخاب نشده است'
        })
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({
            'success': False, 
            'message': 'فایلی انتخاب نشده است'
        })
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        try:
            imported_count = import_from_excel(file_path)
            return jsonify({
                'success': True, 
                'message': f'تعداد {imported_count} رکورد با موفقیت ایمپورت شد'
            })
        except Exception as e:
            return jsonify({
                'success': False, 
                'message': str(e)
            })
    
    return jsonify({
        'success': False, 
        'message': 'فرمت فایل مجاز نیست. فقط فایل‌های xlsx و xls قابل قبول هستند.'
    })

@app.route('/api/export-excel')
def export_excel():
    try:
        filename = export_to_excel()
        return send_file(
            os.path.join(app.config['EXPORT_FOLDER'], filename),
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({
            'success': False, 
            'message': str(e)
        })

@app.route('/api/income-by-date', methods=['POST'])
def get_income_by_date():
    """دریافت درآمد در بازه زمانی - بر اساس تاریخ خروج"""
    try:
        data = request.get_json()
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if not start_date or not end_date:
            return jsonify({
                'success': False,
                'message': 'لطفاً هر دو تاریخ را انتخاب کنید'
            })
        
        print(f"📅 دریافت درخواست گزارش از {start_date} تا {end_date}")
        
        # استفاده از exit_date به جای entry_date
        total_income = get_income_by_exit_date_range(start_date, end_date)
        customers = get_customers_by_exit_date_range(start_date, end_date)
        
        print(f"📊 نتایج: {len(customers)} مشتری، {total_income} درآمد")
        
        return jsonify({
            'success': True,
            'total_income': total_income,
            'customer_count': len(customers),
            'start_date': start_date,
            'end_date': end_date
        })
        
    except Exception as e:
        print(f"❌ خطا در محاسبه درآمد: {e}")
        return jsonify({
            'success': False,
            'message': f'خطا در محاسبه درآمد: {str(e)}'
        })

@app.route('/api/stats')
def get_stats():
    """دریافت آمار سیستم"""
    try:
        conn = sqlite3.connect(app.config['DATABASE_PATH'])
        cursor = conn.cursor()
        
        # تعداد کل مشتریان
        cursor.execute('SELECT COUNT(*) FROM customers')
        total_customers = cursor.fetchone()[0]
        
        # مجموع درآمد
        cursor.execute('SELECT SUM(total_cost) FROM customers WHERE total_cost IS NOT NULL')
        total_income_result = cursor.fetchone()[0]
        total_income = total_income_result if total_income_result is not None else 0
        
        # میانگین درآمد
        cursor.execute('SELECT AVG(total_cost) FROM customers WHERE total_cost IS NOT NULL AND total_cost > 0')
        average_income_result = cursor.fetchone()[0]
        average_income = int(average_income_result) if average_income_result is not None else 0
        
        conn.close()
        
        return jsonify({
            'total_customers': total_customers,
            'total_income': total_income,
            'average_income': average_income
        })
    except Exception as e:
        print(f"Error in get_stats: {e}")
        return jsonify({
            'total_customers': 0,
            'total_income': 0,
            'average_income': 0
        })

@app.route('/api/recent-customers')
def get_recent_customers():
    """دریافت آخرین مشتریان برای داشبورد"""
    try:
        conn = sqlite3.connect(app.config['DATABASE_PATH'])
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, full_name, phone_number, device_type, entry_date, total_cost 
            FROM customers 
            ORDER BY created_at DESC 
            LIMIT 5
        ''')
        customers = cursor.fetchall()
        conn.close()
        
        result = []
        for customer in customers:
            result.append({
                'id': customer[0],
                'full_name': customer[1],
                'phone_number': customer[2],
                'device_type': customer[3],
                'entry_date': customer[4],
                'total_cost': customer[5] or 0
            })
        
        return jsonify(result)
    except Exception as e:
        print(f"Error in get_recent_customers: {e}")
        return jsonify([])

@app.route('/api/customer/<int:customer_id>')
def get_customer_details(customer_id):
    """دریافت اطلاعات کامل یک مشتری"""
    try:
        conn = sqlite3.connect(app.config['DATABASE_PATH'])
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM customers WHERE id = ?', (customer_id,))
        customer = cursor.fetchone()
        conn.close()
        
        if customer:
            customer_data = {
                'id': customer[0],
                'full_name': customer[1],
                'phone_number': customer[2],
                'entry_date': customer[3],
                'exit_date': customer[4],
                'device_code': customer[5],
                'device_type': customer[6],
                'material_cost': customer[7],
                'service_cost': customer[8],
                'total_cost': customer[9],
                'description': customer[10],
                'created_at': customer[11]
            }
            return jsonify({
                'success': True,
                'data': customer_data
            })
        else:
            return jsonify({
                'success': False,
                'message': 'مشتری یافت نشد'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'خطا در دریافت اطلاعات: {str(e)}'
        })

@app.route('/api/db-info')
def get_db_info():
    """دریافت اطلاعات دیتابیس"""
    try:
        db_size = os.path.getsize(app.config['DATABASE_PATH'])
        db_exists = os.path.exists(app.config['DATABASE_PATH'])
        
        conn = sqlite3.connect(app.config['DATABASE_PATH'])
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM customers')
        customer_count = cursor.fetchone()[0]
        conn.close()
        
        return jsonify({
            'success': True,
            'db_path': app.config['DATABASE_PATH'],
            'db_exists': db_exists,
            'db_size': db_size,
            'customer_count': customer_count,
            'data_folder': app.config['DATA_FOLDER']
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 در حال راه‌اندازی سیستم مدیریت تعمیرگاه...")
    print("=" * 60)
    
    # بررسی وجود پوشه‌ها
    print("📂 بررسی پوشه‌ها...")
    for folder_name, folder_path in [
        ('آپلودها', app.config['UPLOAD_FOLDER']),
        ('خروجی‌ها', app.config['EXPORT_FOLDER']),
        ('دیتابیس', app.config['DATA_FOLDER'])
    ]:
        if os.path.exists(folder_path):
            print(f"   ✅ {folder_name}: {folder_path}")
        else:
            print(f"   ❌ {folder_name}: {folder_path} - در حال ایجاد...")
            os.makedirs(folder_path, exist_ok=True)
    
    init_db()
    
    print("🌐 سیستم آماده است!")
    print("📊 آدرس: http://localhost:5000")
    print("💾 داده‌ها در فایل دیتابیس ذخیره می‌شوند")
    print("⏹️  برای توقف، Ctrl+C را فشار دهید")
    print("=" * 60)
    
    app.run(debug=True, host='0.0.0.0', port=5000)