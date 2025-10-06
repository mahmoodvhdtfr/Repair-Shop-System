import sqlite3
import os

def check_database():
    """بررسی وضعیت دیتابیس"""
    
    # مسیر دیتابیس
    db_path = os.path.join('data', 'repair_shop.db')
    
    print("🔍 بررسی وضعیت دیتابیس...")
    print(f"📁 مسیر دیتابیس: {db_path}")
    
    # بررسی وجود فایل
    if os.path.exists(db_path):
        print("✅ فایل دیتابیس وجود دارد")
        
        # بررسی اندازه فایل
        file_size = os.path.getsize(db_path)
        print(f"💾 اندازه فایل: {file_size} بایت")
        
        # اتصال به دیتابیس
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # بررسی وجود جدول
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='customers'")
            table_exists = cursor.fetchone()
            
            if table_exists:
                print("✅ جدول customers وجود دارد")
                
                # تعداد رکوردها
                cursor.execute("SELECT COUNT(*) FROM customers")
                count = cursor.fetchone()[0]
                print(f"📊 تعداد مشتریان: {count}")
                
                # نمایش چند رکورد نمونه
                if count > 0:
                    cursor.execute("SELECT id, full_name, phone_number FROM customers ORDER BY id DESC LIMIT 3")
                    recent_customers = cursor.fetchall()
                    print("📝 آخرین مشتریان:")
                    for customer in recent_customers:
                        print(f"   - ID: {customer[0]}, نام: {customer[1]}, تلفن: {customer[2]}")
            else:
                print("❌ جدول customers وجود ندارد")
                
            conn.close()
            
        except Exception as e:
            print(f"❌ خطا در اتصال به دیتابیس: {e}")
            
    else:
        print("❌ فایل دیتابیس وجود ندارد")
        print("💡 راه حل: سیستم را یکبار اجرا کنید تا دیتابیس ایجاد شود")

if __name__ == '__main__':
    check_database()
    input("\n↵ برای خروج Enter بزنید...")