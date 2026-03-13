# assign_admin.py
import pymysql
from werkzeug.security import generate_password_hash
from getpass import getpass
import re

# Database configuration
DB_CONFIG = {
    'host': 'TOMAR-PC',
    'user': 'root',
    'password': 'pankaj1412@2711',
    'database': 'CivicAI',
    'charset': 'utf8mb4'
}

def connect_db():
    """Connect to MySQL database"""
    try:
        connection = pymysql.connect(**DB_CONFIG)
        return connection
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return None

def validate_email(email):
    """Simple email validation"""
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None

def validate_username(username):
    """Check if username exists"""
    conn = connect_db()
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id FROM admins WHERE username = %s", (username,))
                return cursor.fetchone() is None
        finally:
            conn.close()
    return False

def validate_employee_id(emp_id):
    """Check if employee ID exists"""
    conn = connect_db()
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id FROM admins WHERE employee_id = %s", (emp_id,))
                return cursor.fetchone() is None
        finally:
            conn.close()
    return False

def get_departments():
    """Get list of departments"""
    conn = connect_db()
    departments = []
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id, name FROM departments WHERE is_active = 1")
                departments = cursor.fetchall()
        finally:
            conn.close()
    return departments

def create_admin():
    """Create new admin from terminal input"""
    print("\n" + "="*50)
    print("   CIVICAI - ADMIN ASSIGNMENT TOOL")
    print("="*50 + "\n")

    # Get departments for reference
    departments = get_departments()
    if departments:
        print("Available Departments:")
        for dept_id, dept_name in departments:
            print(f"  {dept_id}. {dept_name}")
        print()

    # Collect admin details
    while True:
        username = input("Username: ").strip()
        if not username:
            print("❌ Username cannot be empty")
            continue
        if not validate_username(username):
            print("❌ Username already exists")
            continue
        break

    while True:
        email = input("Email: ").strip().lower()
        if not validate_email(email):
            print("❌ Invalid email format")
            continue
        break

    while True:
        password = getpass("Password: ")
        if len(password) < 8:
            print("❌ Password must be at least 8 characters")
            continue
        confirm = getpass("Confirm password: ")
        if password != confirm:
            print("❌ Passwords do not match")
            continue
        break

    full_name = input("Full name: ").strip()
    
    while True:
        employee_id = input("Employee ID: ").strip()
        if not employee_id:
            print("❌ Employee ID cannot be empty")
            continue
        if not validate_employee_id(employee_id):
            print("❌ Employee ID already exists")
            continue
        break

    phone = input("Phone (optional): ").strip() or None

    # Admin level selection
    print("\nAdmin Levels:")
    print("  1. super_admin")
    print("  2. department_admin")
    print("  3. moderator")
    level_choice = input("Select level (1-3) [3]: ").strip() or "3"
    
    level_map = {"1": "super_admin", "2": "department_admin", "3": "moderator"}
    admin_level = level_map.get(level_choice, "moderator")

    # Department selection
    dept_id = None
    if departments and admin_level != "super_admin":
        dept_input = input("Department ID (optional): ").strip()
        if dept_input:
            try:
                dept_id = int(dept_input)
            except:
                print("⚠️ Invalid department ID, skipping...")

    # Permissions
    print("\nPermissions:")
    can_assign = input("Can assign admins? (y/n) [n]: ").strip().lower() == 'y'
    can_delete = input("Can delete complaints? (y/n) [n]: ").strip().lower() == 'y'
    can_manage = input("Can manage departments? (y/n) [n]: ").strip().lower() == 'y'
    
    is_super = admin_level == "super_admin"

    # Show summary
    print("\n" + "-"*50)
    print("SUMMARY:")
    print(f"Username:     {username}")
    print(f"Email:        {email}")
    print(f"Full Name:    {full_name}")
    print(f"Employee ID:  {employee_id}")
    print(f"Admin Level:  {admin_level}")
    print(f"Department:   {dept_id if dept_id else 'None'}")
    print(f"Permissions:  Assign={can_assign}, Delete={can_delete}, Manage={can_manage}")
    print("-"*50)

    confirm = input("\nCreate this admin? (y/n): ").strip().lower()
    if confirm != 'y':
        print("❌ Admin creation cancelled")
        return

    # Insert into database
    conn = connect_db()
    if not conn:
        return

    try:
        password_hash = generate_password_hash(password)
        
        with conn.cursor() as cursor:
            sql = """
                INSERT INTO admins (
                    username, email, password_hash, full_name, employee_id,
                    phone, admin_level, department_id, can_assign_admins,
                    can_delete_complaints, can_manage_departments,
                    can_view_reports, is_super_admin, is_active, created_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
                )
            """
            cursor.execute(sql, (
                username, email, password_hash, full_name, employee_id,
                phone, admin_level, dept_id, can_assign, can_delete,
                can_manage, True, is_super, True
            ))
        
        conn.commit()
        print(f"\n✅ Admin '{username}' created successfully!")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error creating admin: {e}")
    finally:
        conn.close()

def list_admins():
    """List all existing admins"""
    conn = connect_db()
    if not conn:
        return

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, username, full_name, admin_level, is_active, created_at 
                FROM admins 
                ORDER BY created_at DESC
            """)
            admins = cursor.fetchall()

        print("\n" + "="*60)
        print("EXISTING ADMINS")
        print("="*60)
        print(f"{'ID':<5} {'Username':<15} {'Name':<20} {'Level':<15} {'Status':<8}")
        print("-"*60)
        
        for admin in admins:
            status = "✅" if admin[4] else "❌"
            print(f"{admin[0]:<5} {admin[1]:<15} {admin[2][:18]:<20} {admin[3]:<15} {status:<8}")
        print("="*60 + "\n")

    except Exception as e:
        print(f"❌ Error fetching admins: {e}")
    finally:
        conn.close()

def delete_admin():
    """Delete an admin"""
    admin_id = input("Enter admin ID to delete: ").strip()
    
    if not admin_id.isdigit():
        print("❌ Invalid ID")
        return

    conn = connect_db()
    if not conn:
        return

    try:
        with conn.cursor() as cursor:
            # Check if admin exists and is not super admin
            cursor.execute("SELECT username, is_super_admin FROM admins WHERE id = %s", (admin_id,))
            admin = cursor.fetchone()
            
            if not admin:
                print("❌ Admin not found")
                return
            
            if admin[1]:  # is_super_admin
                print("❌ Cannot delete super admin")
                return

            confirm = input(f"Delete admin '{admin[0]}'? (y/n): ").strip().lower()
            if confirm != 'y':
                print("❌ Deletion cancelled")
                return

            cursor.execute("DELETE FROM admins WHERE id = %s", (admin_id,))
            conn.commit()
            print(f"✅ Admin deleted successfully")

    except Exception as e:
        conn.rollback()
        print(f"❌ Error deleting admin: {e}")
    finally:
        conn.close()

def main():
    """Main menu"""
    while True:
        print("\n" + "="*50)
        print("CIVICAI - ADMIN MANAGEMENT")
        print("="*50)
        print("1. Create new admin")
        print("2. List all admins")
        print("3. Delete admin")
        print("4. Exit")
        print("-"*50)
        
        choice = input("Select option (1-4): ").strip()
        
        if choice == '1':
            create_admin()
        elif choice == '2':
            list_admins()
        elif choice == '3':
            delete_admin()
        elif choice == '4':
            print("\n👋 Goodbye!")
            break
        else:
            print("❌ Invalid option")

if __name__ == "__main__":
    main()