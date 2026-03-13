# database.py
from datetime import datetime
from urllib.parse import quote_plus

from flask import Flask
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# Flask app instance for DB binding
app = Flask(__name__)

# MySQL configuration
DB_USER = "root"
DB_PASSWORD = quote_plus("pankaj1412@2711")
DB_HOST = "TOMAR-PC"
DB_NAME = "CivicAI"

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}?charset=utf8mb4"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "your-secret-key-here-change-in-production"

db = SQLAlchemy(app)

class User(UserMixin, db.Model):
    """Regular citizen user model"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.String(200))
    password_hash = db.Column(db.String(200), nullable=False)
    
    # User status
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(100))
    
    # Profile
    profile_pic = db.Column(db.String(500))
    total_complaints = db.Column(db.Integer, default=0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    complaints = db.relationship('Complaint', backref='citizen', lazy=True, foreign_keys='Complaint.user_id')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Admin(UserMixin, db.Model):
    """Separate Admin model with specific privileges"""
    __tablename__ = 'admins'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    
    # Admin specific fields
    admin_level = db.Column(db.String(50), default='moderator')  # super_admin, department_admin, moderator
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    can_assign_admins = db.Column(db.Boolean, default=False)
    can_delete_complaints = db.Column(db.Boolean, default=False)
    can_manage_departments = db.Column(db.Boolean, default=False)
    can_view_reports = db.Column(db.Boolean, default=True)
    
    # Personal info
    full_name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    employee_id = db.Column(db.String(50), unique=True)
    
    # Status
    is_super_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('admins.id'), nullable=True)
    
    # Relationships
    assigned_complaints = db.relationship('Complaint', backref='assigned_admin', lazy=True, foreign_keys='Complaint.assigned_to')
    status_changes = db.relationship('StatusHistory', backref='changed_by_admin', lazy=True, foreign_keys='StatusHistory.changed_by')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def can_manage(self, resource):
        """Check if admin can manage specific resource"""
        if self.is_super_admin:
            return True
        
        permissions = {
            'complaints': self.can_delete_complaints,
            'departments': self.can_manage_departments,
            'admins': self.can_assign_admins,
            'reports': self.can_view_reports
        }
        return permissions.get(resource, False)
    
    def __repr__(self):
        return f'<Admin {self.username} ({self.admin_level})>'

class Department(db.Model):
    """Department model for categorizing complaints"""
    __tablename__ = 'departments'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    head_office = db.Column(db.String(200))
    
    # Department head (references Admin)
    head_admin_id = db.Column(db.Integer, db.ForeignKey('admins.id'), nullable=True)
    
    # Department stats
    total_complaints = db.Column(db.Integer, default=0)
    resolved_complaints = db.Column(db.Integer, default=0)
    pending_complaints = db.Column(db.Integer, default=0)
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('admins.id'))
    
    # Relationships
    complaints = db.relationship('Complaint', backref='assigned_department', lazy=True)
    admins = db.relationship('Admin', backref='department_ref', lazy=True, foreign_keys='Admin.department_id')
    head_admin = db.relationship('Admin', foreign_keys=[head_admin_id], post_update=True)
    
    def update_stats(self):
        """Update department statistics"""
        self.total_complaints = Complaint.query.filter_by(department_id=self.id).count()
        self.resolved_complaints = Complaint.query.filter_by(department_id=self.id, status='resolved').count()
        self.pending_complaints = Complaint.query.filter_by(department_id=self.id, status='pending').count()
    
    def __repr__(self):
        return f'<Department {self.name}>'

class Complaint(db.Model):
    """Complaint model"""
    __tablename__ = 'complaints'
    
    id = db.Column(db.Integer, primary_key=True)
    complaint_number = db.Column(db.String(50), unique=True, nullable=False)  # Auto-generated like CMP-2024-001
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(200), nullable=False)
    landmark = db.Column(db.String(200))
    pincode = db.Column(db.String(10))
    
    # Media
    image_path = db.Column(db.String(500))
    video_path = db.Column(db.String(500))
    
    # Classification fields
    category = db.Column(db.String(50))  # Predicted by AI
    subcategory = db.Column(db.String(50))
    confidence = db.Column(db.Float)  # Confidence score of prediction
    priority = db.Column(db.String(20), default='medium')  # high, medium, low
    
    # Status tracking
    status = db.Column(db.String(50), default='pending')  # pending, assigned, in_progress, resolved, rejected, closed
    status_updated_at = db.Column(db.DateTime)
    rejection_reason = db.Column(db.Text)  # If rejected
    resolution_notes = db.Column(db.Text)  # Notes when resolved
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    assigned_at = db.Column(db.DateTime)
    resolved_at = db.Column(db.DateTime)
    
    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    assigned_to = db.Column(db.Integer, db.ForeignKey('admins.id'), nullable=True)
    
    # Feedback
    citizen_rating = db.Column(db.Integer)  # 1-5 stars after resolution
    citizen_feedback = db.Column(db.Text)
    
    # Metadata
    ip_address = db.Column(db.String(50))
    source = db.Column(db.String(50), default='web')  # web, mobile, whatsapp
    
    def generate_complaint_number(self):
        """Generate unique complaint number"""
        year = datetime.utcnow().year
        count = Complaint.query.filter(Complaint.created_at >= f'{year}-01-01').count() + 1
        return f'CMP-{year}-{count:04d}'
    
    def __repr__(self):
        return f'<Complaint {self.complaint_number}: {self.title}>'

class StatusHistory(db.Model):
    """Track status changes of complaints"""
    __tablename__ = 'status_history'
    
    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey('complaints.id'), nullable=False)
    complaint_number = db.Column(db.String(50))
    
    old_status = db.Column(db.String(50))
    new_status = db.Column(db.String(50), nullable=False)
    changed_by = db.Column(db.Integer, db.ForeignKey('admins.id'), nullable=True)
    changed_by_user = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    changed_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)
    
    # System metadata
    ip_address = db.Column(db.String(50))
    
    # Relationships
    complaint = db.relationship('Complaint', backref='status_history')
    
    def __repr__(self):
        return f'<StatusChange {self.complaint_number}: {self.old_status} -> {self.new_status}>'

class Notification(db.Model):
    """Notifications for users and admins"""
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('admins.id'), nullable=True)
    
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50))  # complaint_update, system, alert
    reference_id = db.Column(db.Integer)  # ID of related entity (complaint_id, etc.)
    reference_type = db.Column(db.String(50))  # complaint, department
    
    is_read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Notification {self.title}>'

class AuditLog(db.Model):
    """Audit log for all admin actions"""
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('admins.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False)  # CREATE, UPDATE, DELETE, ASSIGN, etc.
    resource_type = db.Column(db.String(50))  # complaint, department, admin, user
    resource_id = db.Column(db.Integer)
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(50))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<AuditLog {self.action} on {self.resource_type}>'

# Initialize database
def init_db():
    """Create all tables"""
    with app.app_context():
        db.create_all()
        print("Database tables created successfully!")

# Create default super admin
def create_super_admin():
    """Create initial super admin"""
    with app.app_context():
        if not Admin.query.filter_by(is_super_admin=True).first():
            super_admin = Admin(
                username='superadmin',
                email='admin@civicai.com',
                full_name='System Administrator',
                employee_id='ADMIN001',
                admin_level='super_admin',
                is_super_admin=True,
                can_assign_admins=True,
                can_delete_complaints=True,
                can_manage_departments=True,
                can_view_reports=True
            )
            super_admin.set_password('Admin@123')  # Change in production!
            
            db.session.add(super_admin)
            db.session.commit()
            print("Super admin created successfully!")

# Create default departments
def create_default_departments():
    """Create default departments"""
    with app.app_context():
        departments = [
            {
                'name': 'Roads and Infrastructure',
                'description': 'Handles road repairs, potholes, street lights, and related infrastructure issues',
                'email': 'roads@civicai.com',
                'phone': '1800-123-ROAD'
            },
            {
                'name': 'Water Supply and Sanitation',
                'description': 'Manages water supply issues, drainage, sewage, and sanitation complaints',
                'email': 'water@civicai.com',
                'phone': '1800-123-WATER'
            },
            {
                'name': 'Waste Management',
                'description': 'Handles garbage collection, waste disposal, and cleanliness issues',
                'email': 'waste@civicai.com',
                'phone': '1800-123-CLEAN'
            },
            {
                'name': 'Public Safety',
                'description': 'Manages street lighting, security concerns, and safety infrastructure',
                'email': 'safety@civicai.com',
                'phone': '1800-123-SAFE'
            },
            {
                'name': 'Parks and Recreation',
                'description': 'Handles parks, gardens, playgrounds, and public space maintenance',
                'email': 'parks@civicai.com',
                'phone': '1800-123-PARK'
            }
        ]
        
        for dept_data in departments:
            if not Department.query.filter_by(name=dept_data['name']).first():
                dept = Department(**dept_data)
                db.session.add(dept)
        
        db.session.commit()
        print("Default departments created successfully!")

if __name__ == '__main__':
    init_db()
    create_super_admin()
    create_default_departments()