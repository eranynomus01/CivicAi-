# app.py
import os
import random
import string
import secrets
from datetime import datetime, timedelta
from PIL import Image
from flask import render_template, redirect, url_for, flash, request, abort, session, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_mail import Mail, Message
# Add this with your other imports at the top of app.py
import re
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_login import login_required, current_user
from database import app, db, User, Admin, Department, Complaint, StatusHistory, Notification, AuditLog
from model import classifier

# =========================================================
# APP CONFIGURATION
# =========================================================

app.config['SECRET_KEY'] = secrets.token_hex(32)

app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# =========================================================
# EMAIL CONFIGURATION - FIXED
# =========================================================

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'civicaicode4bharat@gmail.com'
app.config['MAIL_PASSWORD'] = 'lbfmdxmmgumaoecf'
app.config['MAIL_DEFAULT_SENDER'] = ('CivicAI', 'civicaicode4bharat@gmail.com')
app.config['MAIL_MAX_EMAILS'] = None
app.config['MAIL_ASCII_ATTACHMENTS'] = False
app.config['MAIL_SUPPRESS_SEND'] = False
app.config['MAIL_TIMEOUT'] = 30
# Initialize Mail with proper configuration
mail = Mail(app)

# OTP Storage with expiry
otp_storage = {}

# =========================================================
# LOGIN MANAGER
# =========================================================

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "warning"


@login_manager.user_loader
def load_user(user_id):
    # Check both User and Admin tables
    user = User.query.get(int(user_id))
    if user:
        return user
    return Admin.query.get(int(user_id))


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_image(file):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        name, ext = os.path.splitext(filename)
        filename = f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        try:
            image = Image.open(file)
            image.thumbnail((800, 800))
            image.save(filepath)
            return filename
        except Exception as e:
            print(f"Image save error: {e}")
            return None
    return None


def generate_otp():
    return ''.join(random.choices(string.digits, k=6))


def send_otp_email(email, otp):
    """Improved OTP email sending function"""
    try:
        print(f"📨 Attempting to send OTP email to: {email}")

        # Create message
        msg = Message(
            subject='CivicAI - Email Verification OTP',
            recipients=[email]
        )

        # Plain text version
        msg.html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width">
<title>CivicAI Verification</title>
</head>

<body style="margin:0;padding:0;background:#f4f1de;font-family:Arial,Helvetica,sans-serif;">

<table width="100%" cellpadding="0" cellspacing="0" border="0">
<tr>
<td align="center" style="padding:40px 10px;">

<table width="600" cellpadding="0" cellspacing="0" border="0" style="background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 10px 30px rgba(0,0,0,0.08);">

<tr>
<td style="background:#84a98c;padding:25px;text-align:center;">
<h1 style="margin:0;color:white;font-size:26px;font-weight:700;">
🏙 CivicAI
</h1>
<p style="margin:5px 0 0;color:#e8f0e9;font-size:14px;">
Your Voice • Smarter City
</p>
</td>
</tr>

<tr>
<td style="padding:35px;text-align:center;">

<h2 style="margin:0 0 10px;color:#3d405b;font-size:22px;">
Verify Your Email
</h2>

<p style="margin:0 0 25px;color:#6c757d;font-size:14px;">
Use the verification code below to complete your signup.
</p>

<table align="center" cellpadding="0" cellspacing="0">
<tr>
<td style="background:#f8faf9;border:2px dashed #84a98c;border-radius:12px;padding:18px 35px;font-size:40px;font-weight:700;color:#3d405b;letter-spacing:8px;font-family:monospace;">
{otp}
</td>
</tr>
</table>

<p style="margin:20px 0 0;color:#e07a5f;font-size:13px;font-weight:600;">
This code expires in 10 minutes
</p>

</td>
</tr>

<tr>
<td style="padding:20px 35px;text-align:center;border-top:1px solid #eee;">

<p style="margin:0;color:#6c757d;font-size:13px;">
If you did not request this email, you can safely ignore it.
</p>

<p style="margin:10px 0 0;color:#999;font-size:12px;">
© 2026 CivicAI • Secure Verification System
</p>

</td>
</tr>

</table>

</td>
</tr>
</table>

</body>
</html>
"""
        # Send email safely
        with mail.connect() as conn:
            conn.send(msg)

        print(f"✅ OTP email sent successfully to {email}")
        return True, "OTP sent successfully"

    except Exception as e:
        print("❌ Email sending failed")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        return False, f"Failed to send email: {str(e)}"
def create_audit_log(admin_id, action, resource_type, resource_id, details, ip_address):
    """Create an audit log entry"""
    log = AuditLog(
        admin_id=admin_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address
    )
    db.session.add(log)
    db.session.commit()


def create_notification(user_id=None, admin_id=None, title=None, message=None, 
                        type='system', reference_id=None, reference_type=None):
    """Create a notification"""
    notification = Notification(
        user_id=user_id,
        admin_id=admin_id,
        title=title,
        message=message,
        type=type,
        reference_id=reference_id,
        reference_type=reference_type
    )
    db.session.add(notification)
    db.session.commit()


# =========================================================
# PUBLIC ROUTES - UPDATED INDEX
# =========================================================

@app.route('/')
def index():
    """Home page with real stats from database"""
    total_complaints = Complaint.query.count()
    resolved = Complaint.query.filter_by(status='resolved').count()
    pending = Complaint.query.filter_by(status='pending').count()
    user_count = User.query.count()
    
    # Get real testimonials from users with resolved complaints and feedback
    testimonials = db.session.query(Complaint, User).join(
        User, Complaint.user_id == User.id
    ).filter(
        Complaint.status == 'resolved',
        Complaint.citizen_feedback.isnot(None),
        Complaint.citizen_feedback != ''
    ).order_by(
        Complaint.resolved_at.desc()
    ).limit(3).all()
    
    testimonial_list = []
    for complaint, user in testimonials:
        testimonial_list.append({
            'message': complaint.citizen_feedback,
            'user_name': user.username
        })

    return render_template(
        'index.html',
        complaint_count=total_complaints,
        resolved_count=resolved,
        user_count=user_count,
        testimonials=testimonial_list
    )


# =========================================================
# AUTHENTICATION SYSTEM - FIXED OTP
# =========================================================

@app.route("/send-otp", methods=["POST"])
def send_otp():
    print("🚀 /send-otp route triggered")

    try:
        data = request.get_json()
        print("📦 Received data:", data)

        if not data:
            return jsonify({"success": False, "error": "Invalid request data"}), 400

        email = data.get("email", "").strip().lower()
        print("📧 Email received:", email)

        if not email:
            return jsonify({"success": False, "error": "Email is required"}), 400

        if User.query.filter_by(email=email).first():
            return jsonify({"success": False, "error": "Email already registered"}), 400

        otp = generate_otp()
        print("🔢 Generated OTP:", otp)

        otp_storage[email] = {
            'otp': otp,
            'created_at': datetime.now(),
            'attempts': 0
        }

        print("📨 Sending OTP email...")

        success, message = send_otp_email(email, otp)

        print("📬 Email result:", success, message)

        if success:
            return jsonify({"success": True, "message": "OTP sent successfully"})
        else:
            if email in otp_storage:
                del otp_storage[email]
            return jsonify({"success": False, "error": message}), 500

    except Exception as e:
        print("❌ Error in send_otp:", str(e))
        return jsonify({"success": False, "error": "Server error occurred"}), 500

@app.route("/verify-otp", methods=["POST"])
def verify_otp():
    """Verify OTP entered by user"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "Invalid request data"}), 400
            
        email = data.get("email", "").strip().lower()
        entered_otp = data.get("otp", "").strip()

        if not email or not entered_otp:
            return jsonify({"success": False, "error": "Email and OTP are required"}), 400

        # Check if OTP exists
        if email not in otp_storage:
            return jsonify({"success": False, "error": "OTP expired. Please request a new one."}), 400

        otp_data = otp_storage[email]
        
        # Check OTP expiry (10 minutes)
        time_diff = datetime.now() - otp_data['created_at']
        if time_diff.total_seconds() > 600:  # 10 minutes
            del otp_storage[email]
            return jsonify({"success": False, "error": "OTP expired. Please request a new one."}), 400

        # Check attempts
        otp_data['attempts'] = otp_data.get('attempts', 0) + 1
        if otp_data['attempts'] > 3:
            del otp_storage[email]
            return jsonify({"success": False, "error": "Too many failed attempts. Please request new OTP."}), 400

        # Verify OTP
        if otp_data['otp'] == entered_otp:
            # Store verified email in session
            session['verified_email'] = email
            session.permanent = True
            
            return jsonify({
                "success": True,
                "message": "Email verified successfully"
            })

        return jsonify({"success": False, "error": "Invalid OTP"}), 400

    except Exception as e:
        print(f"Error in verify_otp: {str(e)}")
        return jsonify({"success": False, "error": "Server error occurred"}), 500


# Add this to your app.py
# In app.py - Update your register route to handle both GET and POST

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_profile_picture(file):
    """Save profile picture and return filename"""
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Add timestamp to avoid duplicate filenames
        name, ext = os.path.splitext(filename)
        filename = f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        return filename
    return None

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Handle user registration - supports both GET and POST with file upload"""
    
    if request.method == 'GET':
        return render_template('register.html')
    
    # POST request - handle registration with file upload
    try:
        # Get form data
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password')
        phone = request.form.get('phone')
        address = request.form.get('address')
        
        # Validate required fields
        if not all([username, email, password]):
            return jsonify({"success": False, "error": "Missing required fields"}), 400
        
        # Check if user exists
        if User.query.filter_by(username=username).first():
            return jsonify({"success": False, "error": "Username already taken"}), 400
        
        if User.query.filter_by(email=email).first():
            return jsonify({"success": False, "error": "Email already registered"}), 400
        
        # Validate password strength
        if len(password) < 8:
            return jsonify({"success": False, "error": "Password must be at least 8 characters"}), 400
        
        if not re.search(r'[A-Z]', password):
            return jsonify({"success": False, "error": "Password must contain at least 1 uppercase letter"}), 400
        
        if not re.search(r'[a-z]', password):
            return jsonify({"success": False, "error": "Password must contain at least 1 lowercase letter"}), 400
        
        if not re.search(r'[0-9]', password):
            return jsonify({"success": False, "error": "Password must contain at least 1 number"}), 400
        
        # Handle profile picture upload
        profile_pic_filename = None
        if 'profile_pic' in request.files:
            file = request.files['profile_pic']
            if file and file.filename:
                profile_pic_filename = save_profile_picture(file)
        
        # Create new user
        new_user = User(
            username=username,
            email=email,
            phone=phone,
            address=address,
            profile_pic=profile_pic_filename,
            is_verified=True,
            is_active=True
        )
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Account created successfully",
            "user_id": new_user.id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        if not username or not password:
            flash("Username and password are required", "danger")
            return render_template("login.html", user=None)

        # Check regular users
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user, remember=remember)
            user.last_login = datetime.now()
            user.total_complaints = Complaint.query.filter_by(user_id=user.id).count()
            db.session.commit()
            
            flash(f"Welcome back, {user.username}!", "success")
            return redirect(url_for('dashboard'))
            
        flash("Invalid username or password", "danger")
        
        return render_template("login.html", user=None)

    return render_template("login.html", user=None)
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        admin = Admin.query.filter_by(username=username).first()
        
        if admin and admin.is_active and check_password_hash(admin.password_hash, password):
            login_user(admin, remember=remember)
            admin.last_login = datetime.now()  # This line uses datetime
            db.session.commit()
            
            create_audit_log(
                admin_id=admin.id,
                action='LOGIN',
                resource_type='admin',
                resource_id=admin.id,
                details=f"Admin {admin.username} logged in",
                ip_address=request.remote_addr
            )
            
            flash(f"Welcome back, {admin.full_name or admin.username}!", "success")
            return redirect(url_for('admin_dashboard'))
            
        flash("Invalid admin credentials", "danger")
    
    # Get real stats for dashboard preview
    total_complaints = Complaint.query.count()
    total_users = User.query.count()
    resolved_count = Complaint.query.filter_by(status='resolved').count()
    pending_count = Complaint.query.filter_by(status='pending').count()
    verified_count = User.query.filter_by(is_verified=True).count()
    
    recent_complaints = Complaint.query.order_by(
        Complaint.created_at.desc()
    ).limit(5).all()
    
    recent_count = Complaint.query.filter(
        Complaint.created_at >= datetime.now().replace(hour=0, minute=0, second=0)  # This line also uses datetime
    ).count()
    
    current_time = datetime.now().strftime('%H:%M')  # This line uses datetime
    today_date = datetime.now().strftime('%B %d, %Y')  # This line uses datetime
    
    return render_template(
        "admin/login.html",
        total_complaints=total_complaints,
        total_users=total_users,
        resolved_count=resolved_count,
        pending_count=pending_count,
        verified_count=verified_count,
        recent_complaints=recent_complaints,
        recent_count=recent_count,
        current_time=current_time,
        today_date=today_date
    )

@app.route('/logout')
@login_required
def logout():
    """Logout user or admin"""
    if isinstance(current_user, Admin):
        create_audit_log(
            admin_id=current_user.id,
            action='LOGOUT',
            resource_type='admin',
            resource_id=current_user.id,
            details=f"Admin {current_user.username} logged out",
            ip_address=request.remote_addr
        )
    
    logout_user()
    flash("Logged out successfully", "success")
    return redirect(url_for('index'))


# =========================================================
# USER FEATURES (CITIZEN)
# =========================================================

@app.route('/dashboard')
@login_required
def dashboard():

    user = current_user

    total_complaints = Complaint.query.filter_by(user_id=user.id).count()
    resolved = Complaint.query.filter_by(user_id=user.id, status='resolved').count()
    pending = Complaint.query.filter_by(user_id=user.id, status='pending').count()
    in_progress = Complaint.query.filter_by(user_id=user.id, status='in_progress').count()

    recent_complaints = Complaint.query.filter_by(user_id=user.id)\
        .order_by(Complaint.created_at.desc()).limit(5).all()

    active_complaint = Complaint.query.filter(
        Complaint.user_id == user.id,
        Complaint.status != 'resolved'
    ).order_by(Complaint.created_at.desc()).first()

    chart_labels = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    chart_data = [2,1,3,0,2,1,4]   # temporary example

    return render_template(
        "dashboard.html",
        user=user,                     # 🔴 THIS FIXES YOUR ERROR
        total_complaints=total_complaints,
        resolved=resolved,
        pending=pending,
        in_progress=in_progress,
        recent_complaints=recent_complaints,
        active_complaint=active_complaint,
        chart_labels=chart_labels,
        chart_data=chart_data
    )

@app.route('/submit-complaint', methods=['GET', 'POST'])
@login_required
def submit_complaint():
    """Submit a new complaint"""
    if isinstance(current_user, Admin):
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        location = request.form.get('location', '').strip()
        category = request.form.get('category', '').strip()

        if not all([title, description, location]):
            flash("Please fill in all required fields", "danger")
            return redirect(url_for('submit_complaint'))

        image_filename = None
        if 'image' in request.files and request.files['image'].filename:
            image_filename = save_image(request.files['image'])

        # AI Classification
        if not category or category == '':
            complaint_text = f"{title} {description}"
            category, confidence = classifier.predict(complaint_text)
            
            # Map category to department
            department_map = {
                'Roads': 'Roads and Infrastructure',
                'Infrastructure': 'Roads and Infrastructure',
                'Pothole': 'Roads and Infrastructure',
                'Street Light': 'Public Safety',
                'Water': 'Water Supply and Sanitation',
                'Sanitation': 'Waste Management',
                'Garbage': 'Waste Management',
                'Waste': 'Waste Management',
                'Public Safety': 'Public Safety',
                'Safety': 'Public Safety',
                'Park': 'Parks and Recreation',
                'Garden': 'Parks and Recreation',
                'Electricity': 'Electricity Board'
            }
            
            department_name = department_map.get(category, 'General')
        else:
            confidence = 1.0
            department_name = request.form.get('department', 'General')

        department = Department.query.filter_by(
            name=department_name).first()

        try:
            complaint = Complaint(
                title=title,
                description=description,
                location=location,
                image_path=image_filename,
                category=category,
                confidence=confidence,
                status='pending',
                user_id=current_user.id,
                department_id=department.id if department else None,
                ip_address=request.remote_addr,
                source='web'
            )

            db.session.add(complaint)
            db.session.commit()
            
            # Update user's complaint count
            current_user.total_complaints = Complaint.query.filter_by(user_id=current_user.id).count()
            db.session.commit()
            
            # Create notification for user
            create_notification(
                user_id=current_user.id,
                title="Complaint Submitted",
                message=f"Your complaint #{complaint.complaint_number} has been submitted successfully.",
                type='complaint_update',
                reference_id=complaint.id,
                reference_type='complaint'
            )

            flash(f"Complaint #{complaint.complaint_number} submitted successfully!", "success")
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            db.session.rollback()
            flash("Failed to submit complaint. Please try again.", "danger")
            return redirect(url_for('submit_complaint'))

    # Get departments for dropdown
    departments = Department.query.filter_by(is_active=True).all()
    return render_template("submit_complaint.html", departments=departments)


@app.route('/complaint/<int:complaint_id>')
@login_required
def view_complaint(complaint_id):
    """View complaint details"""
    complaint = Complaint.query.get_or_404(complaint_id)
    
    # Check if user owns this complaint or is admin
    if not (complaint.user_id == current_user.id or isinstance(current_user, Admin)):
        abort(403)
    
    status_history = StatusHistory.query.filter_by(
        complaint_id=complaint.id
    ).order_by(StatusHistory.changed_at.desc()).all()
    
    return render_template("view_complaint.html", 
                         complaint=complaint, 
                         status_history=status_history)


@app.route('/complaint/<int:complaint_id>/feedback', methods=['POST'])
@login_required
def submit_feedback(complaint_id):
    """Submit feedback for resolved complaint"""
    complaint = Complaint.query.get_or_404(complaint_id)
    
    if complaint.user_id != current_user.id:
        abort(403)
    
    if complaint.status != 'resolved':
        flash("You can only provide feedback for resolved complaints", "danger")
        return redirect(url_for('view_complaint', complaint_id=complaint.id))
    
    rating = request.form.get('rating')
    feedback = request.form.get('feedback', '').strip()
    
    if rating:
        complaint.citizen_rating = int(rating)
        complaint.citizen_feedback = feedback
        db.session.commit()
        
        flash("Thank you for your feedback!", "success")
    
    return redirect(url_for('view_complaint', complaint_id=complaint.id))


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile"""
    if isinstance(current_user, Admin):
        return redirect(url_for('admin_profile'))
    
    if request.method == 'POST':
        current_user.phone = request.form.get('phone', current_user.phone)
        current_user.address = request.form.get('address', current_user.address)
        
        if 'profile_pic' in request.files and request.files['profile_pic'].filename:
            filename = save_image(request.files['profile_pic'])
            if filename:
                current_user.profile_pic = filename
        
        db.session.commit()
        flash("Profile updated successfully", "success")
        return redirect(url_for('profile'))
    
    return render_template("profile.html", user=current_user)
# Add this to app.py - Forgot password route

# Add these fields to your User and Admin models first:

# In User model:
reset_token = db.Column(db.String(100), unique=True, nullable=True)
reset_token_expiry = db.Column(db.DateTime, nullable=True)

# In Admin model:
reset_token = db.Column(db.String(100), unique=True, nullable=True)
reset_token_expiry = db.Column(db.DateTime, nullable=True)

# Then add these routes:

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Handle password reset for both users and admins"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        account_type = request.form.get('account_type', 'user')
        
        if not email:
            flash("Please enter your email address", "error")
            return render_template("forgot_password.html")
        
        # Check based on account type
        user = None
        if account_type == 'user':
            user = User.query.filter_by(email=email).first()
        else:
            user = Admin.query.filter_by(email=email).first()
        
        if user:
            # Generate reset token
            reset_token = secrets.token_urlsafe(32)
            
            # Store token with expiry (1 hour)
            user.reset_token = reset_token
            user.reset_token_expiry = datetime.now() + timedelta(hours=1)
            db.session.commit()
            
            # Create reset link with account type
            reset_link = url_for('reset_password', token=reset_token, _external=True)
            
            # Send email
            try:
                msg = Message(
                    subject=f'Reset Your CivicAI {account_type.title()} Password',
                    recipients=[email],
                    sender=('CivicAI', 'noreply@civicai.com')
                )
                
                account_display = "Citizen" if account_type == 'user' else "Admin"
                
                msg.body = f"""
                Password Reset Request
                
                Hello {user.username},
                
                You requested to reset your {account_display} password.
                
                Click the link below:
                {reset_link}
                
                This link is valid for 1 hour.
                
                If you didn't request this, please ignore this email.
                
                - CivicAI Team
                """
                
                msg.html = f"""
                <h2>Password Reset Request</h2>
                <p>Hello {user.username},</p>
                <p>You requested to reset your <strong>{account_display}</strong> password.</p>
                <p>Click the button below:</p>
                <a href="{reset_link}" style="display:inline-block; padding:12px 24px; background:#2d5a4b; color:white; text-decoration:none; border-radius:8px; margin:20px 0;">Reset Password</a>
                <p>Link valid for 1 hour.</p>
                """
                
                mail.send(msg)
                flash(f"Password reset link sent to your email", "success")
            except Exception as e:
                flash("Error sending email. Please try again.", "error")
                print(f"Email error: {e}")
        else:
            # Don't reveal if email exists
            flash("If your email is registered, you will receive a reset link", "info")
        
        return redirect(url_for('forgot_password'))
    
    return render_template("forgot_password.html")


@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Reset password for both users and admins"""
    # Check both tables
    user = User.query.filter_by(reset_token=token).first()
    admin = Admin.query.filter_by(reset_token=token).first()
    
    account = user or admin
    account_type = 'user' if user else 'admin' if admin else None
    
    # Check if token exists and is not expired
    if not account or account.reset_token_expiry < datetime.now():
        flash("Invalid or expired reset link. Please request a new one.", "error")
        return redirect(url_for('forgot_password'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        confirm = request.form.get('confirm_password')
        
        # Validate password
        if not password or len(password) < 8:
            flash("Password must be at least 8 characters", "error")
            return render_template("reset_password.html", token=token)
        
        if not re.search(r'[A-Z]', password):
            flash("Password must contain at least 1 uppercase letter", "error")
            return render_template("reset_password.html", token=token)
        
        if not re.search(r'[a-z]', password):
            flash("Password must contain at least 1 lowercase letter", "error")
            return render_template("reset_password.html", token=token)
        
        if not re.search(r'[0-9]', password):
            flash("Password must contain at least 1 number", "error")
            return render_template("reset_password.html", token=token)
        
        if password != confirm:
            flash("Passwords do not match", "error")
            return render_template("reset_password.html", token=token)
        
        # Update password
        account.password_hash = generate_password_hash(password)
        account.reset_token = None
        account.reset_token_expiry = None
        db.session.commit()
        
        flash(f"Password reset successful! Please login with your new password.", "success")
        return redirect(url_for('login'))
    
    return render_template("reset_password.html", token=token)

@app.route('/admin')
@login_required
def admin_dashboard():
    """Admin dashboard"""
    if not isinstance(current_user, Admin):
        abort(403)
    
    # Real stats from database
    total_complaints = Complaint.query.count()
    pending_complaints = Complaint.query.filter_by(status='pending').count()
    in_progress_complaints = Complaint.query.filter(
        Complaint.status.in_(['assigned', 'in_progress'])
    ).count()
    resolved_complaints = Complaint.query.filter_by(status='resolved').count()
    total_users = User.query.count()
    total_admins = Admin.query.count()
    
    recent_complaints = Complaint.query.order_by(
        Complaint.created_at.desc()
    ).limit(10).all()
    
    # Get notifications
    notifications = Notification.query.filter_by(
        admin_id=current_user.id, 
        is_read=False
    ).order_by(Notification.created_at.desc()).limit(5).all()

    return render_template(
        "admin/dashboard.html",
        total_complaints=total_complaints,
        pending_complaints=pending_complaints,
        in_progress_complaints=in_progress_complaints,
        resolved_complaints=resolved_complaints,
        total_users=total_users,
        total_admins=total_admins,
        recent_complaints=recent_complaints,
        notifications=notifications
    )


# =========================================================
# TEST EMAIL ROUTE
# =========================================================

@app.route('/test-email')
def test_email():
    """Route to test email configuration"""
    try:
        msg = Message(
            subject='Test Email from CivicAI',
            recipients=['civicaicode4bharat@gmail.com'],
            body='This is a test email to verify SMTP configuration.'
        )
        mail.send(msg)
        return "✅ Test email sent successfully!"
    except Exception as e:
        return f"❌ Error: {str(e)}"


# =========================================================
# ERROR HANDLERS
# =========================================================

@app.errorhandler(404)
def not_found(e):
    if request.path.startswith('/admin'):
        return render_template('admin/404.html'), 404
    return "<h1>404 - Page Not Found</h1><p>The page you're looking for doesn't exist.</p><a href='/'>Go Home</a>", 404


@app.errorhandler(403)
def forbidden(e):
    if request.path.startswith('/admin'):
        return render_template('admin/403.html'), 403
    return "<h1>403 - Access Denied</h1><p>You don't have permission to access this page.</p><a href='/'>Go Home</a>", 403


@app.errorhandler(500)
def server_error(e):
    db.session.rollback()
    if request.path.startswith('/admin'):
        return render_template('admin/500.html'), 500
    return "<h1>500 - Server Error</h1><p>Something went wrong. Please try again later.</p><a href='/'>Go Home</a>", 500


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

with app.app_context():
    db.create_all()
    
    # Create default departments if they don't exist (only if empty)
    if Department.query.count() == 0:
        departments = [
            'Roads and Infrastructure',
            'Water Supply and Sanitation',
            'Waste Management',
            'Public Safety',
            'Parks and Recreation',
            'Electricity Board',
            'General'
        ]
        
        for dept_name in departments:
            dept = Department(name=dept_name)
            db.session.add(dept)
        
        db.session.commit()
        print("✅ Default departments created")
    
    print("✅ Database initialized successfully")

# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":
    print("\n" + "="*50)
    print("📧 EMAIL CONFIGURATION:")
    print(f"Server: {app.config['MAIL_SERVER']}")
    print(f"Port: {app.config['MAIL_PORT']}")
    print(f"Username: {app.config['MAIL_USERNAME']}")
    print(f"TLS: {app.config['MAIL_USE_TLS']}")
    print("="*50 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)