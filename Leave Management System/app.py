import os
import logging
from datetime import datetime, date
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
from psycopg2.extras import RealDictCursor

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "your-secret-key-change-this")

# Database configuration
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    """Get database connection"""
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    return conn

def init_db():
    """Initialize database with tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
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
        CREATE TABLE IF NOT EXISTS leaves (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            from_date DATE NOT NULL,
            to_date DATE NOT NULL,
            reason TEXT NOT NULL,
            status VARCHAR(50) DEFAULT 'pending',
            admin_comments TEXT,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.close()

# Initialize database on startup
init_db()

# Template filter for calculating days between dates
@app.template_filter('days_between')
def days_between_filter(from_date, to_date):
    """Calculate days between two dates"""
    try:
        if isinstance(from_date, str):
            from_date = datetime.strptime(from_date, '%Y-%m-%d').date()
        if isinstance(to_date, str):
            to_date = datetime.strptime(to_date, '%Y-%m-%d').date()
        
        if isinstance(from_date, date) and isinstance(to_date, date):
            return (to_date - from_date).days + 1
        else:
            return 1
    except:
        return 1

@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            'SELECT * FROM users WHERE username = %s', (username,)
        )
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('student_dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        # Validation
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long', 'error')
            return render_template('register.html')
        
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check if user already exists
        cursor.execute(
            'SELECT id FROM users WHERE username = %s OR email = %s', 
            (username, email)
        )
        existing_user = cursor.fetchone()
        
        if existing_user:
            flash('Username or email already exists', 'error')
            conn.close()
            return render_template('register.html')
        
        # Create new user
        password_hash = generate_password_hash(password)
        cursor.execute(
            'INSERT INTO users (username, email, password_hash, role) VALUES (%s, %s, %s, %s)',
            (username, email, password_hash, 'student')
        )
        conn.close()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    """User logout"""
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

@app.route('/student_dashboard')
def student_dashboard():
    """Student dashboard"""
    if 'user_id' not in session or session.get('role') != 'student':
        flash('Please login as a student', 'error')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute(
        'SELECT * FROM leaves WHERE user_id = %s ORDER BY applied_at DESC LIMIT 5',
        (session['user_id'],)
    )
    leaves = cursor.fetchall()
    conn.close()
    
    return render_template('student_dashboard.html', leaves=leaves)

@app.route('/admin_dashboard')
def admin_dashboard():
    """Admin dashboard"""
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Please login as an admin', 'error')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute('''
        SELECT l.*, u.username, u.email 
        FROM leaves l 
        JOIN users u ON l.user_id = u.id 
        ORDER BY l.applied_at DESC
    ''')
    leaves = cursor.fetchall()
    conn.close()
    
    return render_template('admin_dashboard.html', leaves=leaves)

@app.route('/apply_leave', methods=['GET', 'POST'])
def apply_leave():
    """Apply for leave"""
    if 'user_id' not in session or session.get('role') != 'student':
        flash('Please login as a student', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        from_date = request.form['from_date']
        to_date = request.form['to_date']
        reason = request.form['reason']
        
        # Validation
        try:
            from_date_obj = datetime.strptime(from_date, '%Y-%m-%d')
            to_date_obj = datetime.strptime(to_date, '%Y-%m-%d')
            
            if from_date_obj > to_date_obj:
                flash('From date cannot be later than to date', 'error')
                return render_template('apply_leave.html')
            
            if from_date_obj < datetime.now():
                flash('From date cannot be in the past', 'error')
                return render_template('apply_leave.html')
                
        except ValueError:
            flash('Invalid date format', 'error')
            return render_template('apply_leave.html')
        
        if not reason.strip():
            flash('Reason is required', 'error')
            return render_template('apply_leave.html')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO leaves (user_id, from_date, to_date, reason) VALUES (%s, %s, %s, %s)',
            (session['user_id'], from_date, to_date, reason)
        )
        conn.close()
        
        flash('Leave application submitted successfully', 'success')
        return redirect(url_for('student_dashboard'))
    
    return render_template('apply_leave.html')

@app.route('/leave_history')
def leave_history():
    """View leave history"""
    if 'user_id' not in session or session.get('role') != 'student':
        flash('Please login as a student', 'error')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute(
        'SELECT * FROM leaves WHERE user_id = %s ORDER BY applied_at DESC',
        (session['user_id'],)
    )
    leaves = cursor.fetchall()
    conn.close()
    
    return render_template('leave_history.html', leaves=leaves)

@app.route('/approve_leave/<int:leave_id>', methods=['POST'])
def approve_leave(leave_id):
    """Approve leave request"""
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Unauthorized access', 'error')
        return redirect(url_for('login'))
    
    action = request.form['action']
    comments = request.form.get('comments', '')
    
    if action not in ['approve', 'reject']:
        flash('Invalid action', 'error')
        return redirect(url_for('admin_dashboard'))
    
    status = 'approved' if action == 'approve' else 'rejected'
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE leaves SET status = %s, admin_comments = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s',
        (status, comments, leave_id)
    )
    conn.close()
    
    flash(f'Leave request {status} successfully', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/create_admin')
def create_admin():
    """Create admin user - for initial setup"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Check if admin already exists
    cursor.execute(
        'SELECT id FROM users WHERE role = %s', ('admin',)
    )
    admin = cursor.fetchone()
    
    if admin:
        conn.close()
        flash('Admin user already exists', 'info')
        return redirect(url_for('index'))
    
    # Create admin user
    password_hash = generate_password_hash('admin123')
    cursor.execute(
        'INSERT INTO users (username, email, password_hash, role) VALUES (%s, %s, %s, %s)',
        ('admin', 'admin@college.edu', password_hash, 'admin')
    )
    conn.close()
    
    flash('Admin user created successfully! Username: admin, Password: admin123', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
