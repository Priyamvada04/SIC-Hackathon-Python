from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)

import secrets

# Generate a random token
token = secrets.token_hex(16)  # Generates a 32-character random hexadecimal token

# Configuration
app.config['SECRET_KEY'] = secrets.token_hex(16)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'grievances.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database
db = SQLAlchemy(app)
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    department = db.Column(db.String(50), nullable=True)
    grievances = db.relationship('Grievance', backref='user', lazy=True)

class Grievance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='Pending')
    department = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    response = db.Column(db.Text, nullable=True)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    departments = ['Health', 'Public Works', 'Water Supply', 'Electricity', 'Revenue', 'Education']
    return render_template('index.html', departments=departments)

@app.route('/department/<department_name>', methods=['GET', 'POST'])
@login_required
def department(department_name):
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        new_grievance = Grievance(title=title, description=description, department=department_name, user_id=current_user.id)
        db.session.add(new_grievance)
        db.session.commit()
        flash('Your grievance has been submitted successfully!', 'success')
        return redirect(url_for('department', department_name=department_name))

    grievances = Grievance.query.filter_by(user_id=current_user.id, department=department_name).all()
    return render_template('department.html', department_name=department_name, grievances=grievances)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Login failed. Please check your username and password.', 'danger')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        admin = User.query.filter_by(username=username, is_admin=True).first()
        if admin and check_password_hash(admin.password, password):
            login_user(admin)
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Admin login failed. Please check your username and password.', 'danger')

    return render_template('admin_login.html')

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    grievances = Grievance.query.filter_by(department=current_user.department).all()
    return render_template('admin_dashboard.html', grievances=grievances)

@app.route('/admin/respond/<int:grievance_id>', methods=['GET', 'POST'])
@login_required
def respond_grievance(grievance_id):
    if not current_user.is_admin:
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    grievance = Grievance.query.get_or_404(grievance_id)
    if request.method == 'POST':
        response = request.form['response']
        grievance.response = response
        grievance.status = 'Responded'
        db.session.commit()
        flash('Response submitted successfully!', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('respond_grievance.html', grievance=grievance)

@app.route('/create_test_user')
def create_test_user():
    user1 = User(
        username='user',
        email='user@example.com',
        password=generate_password_hash('user123', method='pbkdf2:sha256'),
        is_admin=False,
        department=None
    )
    admin1 = User(
        username='admin_health',
        email='admin_health@example.com',
        password=generate_password_hash('admin123', method='pbkdf2:sha256'),
        is_admin=True,
        department='Health'
    )
    admin2 = User(
        username='admin_public_works',
        email='admin_public_works@example.com',
        password=generate_password_hash('admin123', method='pbkdf2:sha256'),
        is_admin=True,
        department='Public Works'
    )

    db.session.add(user1)
    db.session.add(admin1)
    db.session.add(admin2)
    db.session.commit()
    return 'Test user and admins created!'

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
