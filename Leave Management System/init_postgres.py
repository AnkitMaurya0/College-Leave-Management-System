import os
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash

def init_postgresql_database():
    """Initialize PostgreSQL database with tables and sample data"""
    
    DATABASE_URL = os.environ.get('DATABASE_URL')
    
    if not DATABASE_URL:
        print("Error: DATABASE_URL environment variable not found")
        return
    
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cursor = conn.cursor()
    
    # Drop existing tables if they exist
    cursor.execute('DROP TABLE IF EXISTS leaves CASCADE')
    cursor.execute('DROP TABLE IF EXISTS users CASCADE')
    
    # Create users table
    cursor.execute('''
        CREATE TABLE users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(255) UNIQUE NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(50) NOT NULL DEFAULT 'student',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create leaves table
    cursor.execute('''
        CREATE TABLE leaves (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            from_date DATE NOT NULL,
            to_date DATE NOT NULL,
            reason TEXT NOT NULL,
            status VARCHAR(50) DEFAULT 'pending',
            admin_comments TEXT,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')
    
    # Create admin user
    admin_password = generate_password_hash('admin123')
    cursor.execute('''
        INSERT INTO users (username, email, password_hash, role)
        VALUES (%s, %s, %s, %s)
    ''', ('admin', 'admin@college.edu', admin_password, 'admin'))
    
    # Create sample student users
    student_password = generate_password_hash('student123')
    cursor.execute('''
        INSERT INTO users (username, email, password_hash, role)
        VALUES (%s, %s, %s, %s)
    ''', ('student1', 'student1@college.edu', student_password, 'student'))
    
    cursor.execute('''
        INSERT INTO users (username, email, password_hash, role)
        VALUES (%s, %s, %s, %s)
    ''', ('student2', 'student2@college.edu', student_password, 'student'))
    
    # Create sample leave applications
    cursor.execute('''
        INSERT INTO leaves (user_id, from_date, to_date, reason, status)
        VALUES (%s, %s, %s, %s, %s)
    ''', (2, '2024-01-15', '2024-01-17', 'Medical appointment', 'approved'))
    
    cursor.execute('''
        INSERT INTO leaves (user_id, from_date, to_date, reason, status, admin_comments)
        VALUES (%s, %s, %s, %s, %s, %s)
    ''', (2, '2024-01-20', '2024-01-22', 'Family emergency', 'rejected', 'Need more documentation'))
    
    cursor.execute('''
        INSERT INTO leaves (user_id, from_date, to_date, reason)
        VALUES (%s, %s, %s, %s)
    ''', (3, '2024-01-25', '2024-01-27', 'Personal work'))
    
    conn.close()
    
    print("PostgreSQL database initialized successfully!")
    print("Admin credentials - Username: admin, Password: admin123")
    print("Student credentials - Username: student1, Password: student123")
    print("Student credentials - Username: student2, Password: student123")
    print("Sample leave applications have been created.")

if __name__ == '__main__':
    init_postgresql_database()