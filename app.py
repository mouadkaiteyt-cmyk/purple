import threading
import time
import random
import requests
import os
import uuid
import json
from datetime import datetime, timedelta, date
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, abort, get_flashed_messages, make_response, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import inspect, text

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'super-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    referral_code = db.Column(db.String(20), unique=True, nullable=False)
    referred_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    ccp_account = db.Column(db.String(50), nullable=True) 
    payment_method = db.Column(db.String(20), default='ccp') 
    ccp_last_changed = db.Column(db.DateTime, nullable=True)
    instagram_username = db.Column(db.String(50), nullable=True)
    instagram_last_changed = db.Column(db.DateTime, nullable=True)
    gender = db.Column(db.String(10), default='male') 
    age = db.Column(db.Integer, default=18)
    
    goal_choice = db.Column(db.String(20), default='money') # 'money' or 'followers'
    target_followers_page = db.Column(db.String(200), nullable=True) # Page link/username for followers goal
    target_followers_gender = db.Column(db.String(20), default='all')
    target_followers_age = db.Column(db.String(20), default='all')
    fast_goal_tasks_completed = db.Column(db.Integer, default=0)
    fast_goal_tasks_today = db.Column(db.Integer, default=0)
    fast_goal_last_task_date = db.Column(db.Date, nullable=True)
    fast_goal_claimed = db.Column(db.Boolean, default=False)

    referrals = db.relationship('User', backref=db.backref('referrer', remote_side=[id]))

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    link = db.Column(db.String(500), nullable=True)
    max_completions = db.Column(db.Integer, nullable=True)
    target_gender = db.Column(db.String(10), default='all')
    min_age = db.Column(db.Integer, nullable=True)
    max_age = db.Column(db.Integer, nullable=True)

class CompletedTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)

class WithdrawalRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    ccp_account = db.Column(db.String(50), nullable=False) 
    payment_method = db.Column(db.String(20), default='ccp') 
    status = db.Column(db.String(20), default='pending') # pending, approved, rejected
    rejection_reason = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship('User', backref=db.backref('withdrawals', lazy=True))

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    type = db.Column(db.String(20), default='info') 
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('notifications', lazy=True))

class AppConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    daily_task_limit = db.Column(db.Integer, default=10)
    instagram_agent_link = db.Column(db.String(200), default='https://instagram.com/YourAgent')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not getattr(current_user, 'is_admin', False):
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def model_to_dict(obj):
    d = {}
    for column in obj.__table__.columns:
        val = getattr(obj, column.name)
        if isinstance(val, (datetime, date)):
            d[column.name] = val.isoformat()
        else:
            d[column.name] = val
    return d

with app.app_context():
    db.create_all()
    
    # Simple migration for new columns
    try:
        inspector = inspect(db.engine)
        if 'user' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('user')]
            if 'goal_choice' not in columns:
                db.session.execute(text("ALTER TABLE \"user\" ADD COLUMN goal_choice VARCHAR(20) DEFAULT 'money'"))
                db.session.commit()
            if 'target_followers_page' not in columns:
                db.session.execute(text("ALTER TABLE \"user\" ADD COLUMN target_followers_page VARCHAR(200)"))
                db.session.commit()
            if 'target_followers_gender' not in columns:
                db.session.execute(text("ALTER TABLE \"user\" ADD COLUMN target_followers_gender VARCHAR(20) DEFAULT 'all'"))
                db.session.commit()
            if 'target_followers_age' not in columns:
                db.session.execute(text("ALTER TABLE \"user\" ADD COLUMN target_followers_age VARCHAR(20) DEFAULT 'all'"))
                db.session.commit()
    except Exception as e:
        print(f"Migration error: {e}")
        db.session.rollback()

    if not AppConfig.query.first():
        config = AppConfig(daily_task_limit=10)
        db.session.add(config)
        db.session.commit()

    if not User.query.filter_by(is_admin=True).first():
        admin_user = User(
            username='admin',
            email='admin@admin.com',
            password_hash=generate_password_hash('admin123'),
            is_admin=True,
            referral_code=str(uuid.uuid4())[:8],
            goal_choice='money'
        )
        db.session.add(admin_user)
        db.session.commit()

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/sw.js')
def sw():
    response = make_response(app.send_static_file('sw.js'))
    response.headers['Content-Type'] = 'application/javascript'
    return response

@app.before_request
def check_referral():
    ref_code = request.args.get('ref')
    if ref_code:
        request.new_ref_code = ref_code

@app.after_request
def save_referral(response):
    if hasattr(request, 'new_ref_code') and request.new_ref_code:
        expires = datetime.utcnow() + timedelta(hours=48)
        response.set_cookie('ref_code', request.new_ref_code, expires=expires)
    return response

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    ref_code = request.args.get('ref')
    if not ref_code:
        ref_code = request.cookies.get('ref_code', '')

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        gender = request.form.get('gender', 'male')
        age = request.form.get('age', 18, type=int)
        goal_choice = request.form.get('goal_choice', 'money')
        ref_code_post = request.form.get('ref_code', '')

        user_exists = User.query.filter((User.username == username) | (User.email == email)).first()
        if user_exists:
            flash('اسم المستخدم أو البريد الإلكتروني موجود بالفعل.', 'danger')
            return redirect(url_for('register', ref=ref_code_post))

        hashed_password = generate_password_hash(password)
        new_referral_code = str(uuid.uuid4())[:8]

        referred_by_id = None
        if ref_code_post:
            referrer = User.query.filter_by(referral_code=ref_code_post).first()
            if referrer:
                referred_by_id = referrer.id

        new_user = User(
            username=username,
            email=email,
            password_hash=hashed_password,
            gender=gender,
            age=age,
            goal_choice=goal_choice,
            referral_code=new_referral_code,
            referred_by=referred_by_id
        )
        db.session.add(new_user)
        db.session.commit()

        flash('تم التسجيل بنجاح! يمكنك الآن تسجيل الدخول.', 'success')
        resp = make_response(redirect(url_for('login')))
        resp.delete_cookie('ref_code')
        if hasattr(request, 'new_ref_code'):
            delattr(request, 'new_ref_code')
        return resp

    return render_template('register.html', ref_code=ref_code)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('البريد الإلكتروني أو كلمة المرور غير صحيحة.', 'danger')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/notifications/read/<int:notif_id>', methods=['POST'])
@login_required
def read_notification(notif_id):
    notif = Notification.query.get_or_404(notif_id)
    if notif.user_id == current_user.id:
        db.session.delete(notif)
        db.session.commit()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True})
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.fast_goal_last_task_date != datetime.utcnow().date():
        current_user.fast_goal_tasks_today = 0
        current_user.fast_goal_last_task_date = datetime.utcnow().date()
        db.session.commit()

    # Calculate active referrals
    valid_referrals_count = 0
    all_referred = User.query.filter_by(referred_by=current_user.id).all()
    for r in all_referred:
        # A referral is considered active if they completed at least 50 tasks and invited 50 users (active or inactive)
        r_total_invites = User.query.filter_by(referred_by=r.id).count()
        if r.fast_goal_tasks_completed >= 50 and r_total_invites >= 50:
            valid_referrals_count += 1
            
    referrals_count = len(all_referred)
    
    config = AppConfig.query.first()
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    
    # Progress Calculation
    target_tasks = 100
    target_invites = 100 if current_user.goal_choice == 'money' else 200
    
    tasks_completed = min(current_user.fast_goal_tasks_completed, target_tasks)
    invites_completed = min(valid_referrals_count, target_invites)
    
    tasks_progress = (tasks_completed / target_tasks) * 100
    invites_progress = (invites_completed / target_invites) * 100
    total_progress = (tasks_progress + invites_progress) / 2
    
    # Fetch tasks
    all_completed_task_ids = [ct.task_id for ct in CompletedTask.query.filter_by(user_id=current_user.id).all()]
    query = Task.query
    if all_completed_task_ids:
        query = query.filter(~Task.id.in_(all_completed_task_ids))
        
    if current_user.gender:
        query = query.filter((Task.target_gender == 'all') | (Task.target_gender == current_user.gender))
        
    if current_user.age:
        query = query.filter((Task.min_age == None) | (Task.min_age <= current_user.age))
        query = query.filter((Task.max_age == None) | (Task.max_age >= current_user.age))
        
    uncompleted_tasks_raw = query.order_by(Task.id.desc()).all()
    
    available_tasks = []
    for t in uncompleted_tasks_raw:
        if t.max_completions:
            c_count = CompletedTask.query.filter_by(task_id=t.id).count()
            if c_count >= t.max_completions:
                continue
        available_tasks.append(t)
        
    limit = config.daily_task_limit if config else 10
    remaining_slots = max(0, limit - current_user.fast_goal_tasks_today)
    tasks_to_show = available_tasks[:remaining_slots]

    # Include tasks completed today
    today = datetime.utcnow().date()
    today_completions = CompletedTask.query.filter(
        CompletedTask.user_id == current_user.id,
        db.func.date(CompletedTask.completed_at) == today
    ).all()
    today_completed_task_ids = [ct.task_id for ct in today_completions]

    if today_completed_task_ids:
        today_completed_tasks = Task.query.filter(Task.id.in_(today_completed_task_ids)).all()
    else:
        today_completed_tasks = []

    all_tasks_to_show = tasks_to_show + today_completed_tasks
    all_tasks_to_show.sort(key=lambda x: x.id, reverse=True)
    
    latest_withdrawal = WithdrawalRequest.query.filter_by(user_id=current_user.id).order_by(WithdrawalRequest.created_at.desc()).first()
    
    has_missing_info = False
    if current_user.goal_choice == 'money':
        if not current_user.instagram_username or not current_user.ccp_account:
            has_missing_info = True
    else:
        if not current_user.instagram_username or not current_user.target_followers_page:
            has_missing_info = True
            
    inactive_invites = referrals_count - valid_referrals_count
    
    return render_template('dashboard.html', 
                           user=current_user, 
                           referrals_count=referrals_count,
                           valid_referrals_count=valid_referrals_count,
                           inactive_invites=inactive_invites,
                           tasks=all_tasks_to_show,
                           config=config,
                           notifications=notifications,
                           target_tasks=target_tasks,
                           target_invites=target_invites,
                           tasks_completed=tasks_completed,
                           invites_completed=invites_completed,
                           total_progress=total_progress,
                           remaining_slots=remaining_slots,
                           latest_withdrawal=latest_withdrawal,
                           has_missing_info=has_missing_info,
                           completed_task_ids=today_completed_task_ids)

@app.route('/tasks/complete/<int:task_id>', methods=['POST'])
@login_required
def complete_task(task_id):
    if current_user.fast_goal_last_task_date != datetime.utcnow().date():
        current_user.fast_goal_tasks_today = 0
        current_user.fast_goal_last_task_date = datetime.utcnow().date()
        
    config = AppConfig.query.first()
    limit = config.daily_task_limit if config else 10
    
    if current_user.fast_goal_tasks_today >= limit:
        flash(f'لقد أكملت الحد الأقصى من المهام لهذا اليوم ({limit} مهام).', 'warning')
        return redirect(url_for('dashboard'))
        
    task = Task.query.get_or_404(task_id)
    
    if task.max_completions:
        c_count = CompletedTask.query.filter_by(task_id=task.id).count()
        if c_count >= task.max_completions:
            flash('عذراً، هذه المهمة وصلت للحد الأقصى من الإنجازات ولم تعد متاحة.', 'danger')
            return redirect(url_for('dashboard'))
            
    if task.target_gender != 'all' and task.target_gender != current_user.gender:
        flash('هذه المهمة غير متاحة لك بناءً على متطلبات الاستهداف (الجنس).', 'danger')
        return redirect(url_for('dashboard'))
        
    if current_user.age:
        if task.min_age and current_user.age < task.min_age:
            flash('هذه المهمة غير متاحة لك بناءً على متطلبات الاستهداف (العمر).', 'danger')
            return redirect(url_for('dashboard'))
        if task.max_age and current_user.age > task.max_age:
            flash('هذه المهمة غير متاحة لك بناءً على متطلبات الاستهداف (العمر).', 'danger')
            return redirect(url_for('dashboard'))

    if CompletedTask.query.filter_by(user_id=current_user.id, task_id=task.id).first():
        flash('لقد قمت بإنجاز هذه المهمة مسبقاً.', 'danger')
        return redirect(url_for('dashboard'))
    
    new_completion = CompletedTask(user_id=current_user.id, task_id=task.id)
    db.session.add(new_completion)
    
    current_user.fast_goal_tasks_today += 1
    current_user.fast_goal_tasks_completed += 1
            
    if task.max_completions:
        current_count = CompletedTask.query.filter_by(task_id=task.id).count()
        if current_count >= task.max_completions:
            db.session.delete(task)
            
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/claim_goal', methods=['POST'])
@login_required
def claim_goal():
    if current_user.fast_goal_claimed:
        flash('لقد قمت بسحب مكافأة الهدف مسبقاً.', 'info')
        return redirect(url_for('dashboard'))
        
    valid_referrals_count = 0
    all_referred = User.query.filter_by(referred_by=current_user.id).all()
    for r in all_referred:
        r_total_invites = User.query.filter_by(referred_by=r.id).count()
        if r.fast_goal_tasks_completed >= 50 and r_total_invites >= 50:
            valid_referrals_count += 1
            
    target_tasks = 100
    target_invites = 100 if current_user.goal_choice == 'money' else 200
            
    if valid_referrals_count < target_invites or current_user.fast_goal_tasks_completed < target_tasks:
        flash('لم تكمل شروط الهدف بعد.', 'danger')
        return redirect(url_for('dashboard'))
        
    if current_user.goal_choice == 'money':
        if not current_user.instagram_username or not current_user.ccp_account:
            flash('يرجى إضافة حساب انستغرام وبيانات الدفع في الإعدادات قبل السحب.', 'danger')
            return redirect(url_for('settings'))
    else:
        if not current_user.instagram_username or not current_user.target_followers_page:
            flash('يرجى إضافة حساب انستغرام والصفحة المستهدفة في الإعدادات قبل السحب.', 'danger')
            return redirect(url_for('settings'))
        
    existing_request = WithdrawalRequest.query.filter_by(user_id=current_user.id, status='pending').first()
    if existing_request:
        flash('لديك طلب قيد المعالجة بالفعل.', 'danger')
        return redirect(url_for('dashboard'))
        
    current_user.fast_goal_claimed = True
    
    amount = 80.0 if current_user.goal_choice == 'money' else 0.0
    payment_method = current_user.payment_method if current_user.goal_choice == 'money' else 'followers'
    account_info = current_user.ccp_account if current_user.goal_choice == 'money' else current_user.target_followers_page
    
    new_request = WithdrawalRequest(
        user_id=current_user.id, 
        amount=amount, 
        ccp_account=account_info,
        payment_method=payment_method
    )
    db.session.add(new_request)
    
    msg = 'تهانينا! لقد حققت الهدف وتم إرسال طلبك بقيمة 80$.' if current_user.goal_choice == 'money' else 'تهانينا! لقد حققت الهدف وتم إرسال طلبك للحصول على 10,000 متابع.'
    notif = Notification(user_id=current_user.id, message=msg, type='success')
    db.session.add(notif)
    
    db.session.commit()
    
    flash(msg, 'success')
    return redirect(url_for('dashboard'))

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        ccp_account = request.form.get('ccp_account')
        payment_method = request.form.get('payment_method')
        instagram = request.form.get('instagram_username')
        target_followers_page = request.form.get('target_followers_page')
        target_followers_gender = request.form.get('target_followers_gender')
        target_followers_age = request.form.get('target_followers_age')

        now = datetime.utcnow()
        
        if current_user.goal_choice == 'followers':
            if target_followers_page is not None:
                current_user.target_followers_page = target_followers_page
            if target_followers_gender is not None:
                current_user.target_followers_gender = target_followers_gender
            if target_followers_age is not None:
                current_user.target_followers_age = target_followers_age
        
        if payment_method and payment_method != current_user.payment_method:
            current_user.payment_method = payment_method
            
        if ccp_account and ccp_account != current_user.ccp_account:
            existing_ccp = User.query.filter_by(ccp_account=ccp_account).first()
            if existing_ccp:
                flash('رقم الحساب مستخدم من قبل حساب آخر.', 'danger')
            else:
                if current_user.ccp_last_changed:
                    last_changed_ccp = current_user.ccp_last_changed
                    if last_changed_ccp.tzinfo is not None:
                        last_changed_ccp = last_changed_ccp.replace(tzinfo=None)
                    days_since_ccp = (now - last_changed_ccp).days
                    if days_since_ccp < 60:
                        flash(f'لا يمكنك تغيير حساب الدفع الآن. يرجى الانتظار {60 - days_since_ccp} يوماً.', 'danger')
                    else:
                        current_user.ccp_account = ccp_account
                        current_user.ccp_last_changed = now
                else:
                    current_user.ccp_account = ccp_account
                    current_user.ccp_last_changed = now

        if instagram and instagram != current_user.instagram_username:
            existing_ig = User.query.filter_by(instagram_username=instagram).first()
            if existing_ig:
                flash('حساب انستغرام مستخدم من قبل حساب آخر.', 'danger')
            else:
                if current_user.instagram_last_changed:
                    last_changed = current_user.instagram_last_changed
                    if last_changed.tzinfo is not None:
                        last_changed = last_changed.replace(tzinfo=None)
                    days_since = (now - last_changed).days
                    if days_since < 60:
                        flash(f'لا يمكنك تغيير حساب انستغرام الآن. يرجى الانتظار {60 - days_since} يوماً.', 'danger')
                    else:
                        current_user.instagram_username = instagram
                        current_user.instagram_last_changed = now
                else:
                    current_user.instagram_username = instagram
                    current_user.instagram_last_changed = now

        db.session.commit()
        if not get_flashed_messages(category_filter=['danger']):
            flash('تم حفظ الإعدادات بنجاح.', 'success')
        return redirect(url_for('settings'))

    can_change_ig = True
    ig_days_remaining = 0
    if current_user.instagram_last_changed:
        last_changed = current_user.instagram_last_changed
        if last_changed.tzinfo is not None:
            last_changed = last_changed.replace(tzinfo=None)
        days_since = (datetime.utcnow() - last_changed).days
        if days_since < 60:
            can_change_ig = False
            ig_days_remaining = 60 - days_since

    can_change_ccp = True
    ccp_days_remaining = 0
    if current_user.ccp_last_changed:
        last_changed_ccp = current_user.ccp_last_changed
        if last_changed_ccp.tzinfo is not None:
            last_changed_ccp = last_changed_ccp.replace(tzinfo=None)
        days_since_ccp = (datetime.utcnow() - last_changed_ccp).days
        if days_since_ccp < 60:
            can_change_ccp = False
            ccp_days_remaining = 60 - days_since_ccp

    return render_template('settings.html', 
                           user=current_user, 
                           can_change_ig=can_change_ig, 
                           ig_days_remaining=ig_days_remaining,
                           can_change_ccp=can_change_ccp,
                           ccp_days_remaining=ccp_days_remaining)

# Admin Routes
@app.route('/admin')
@admin_required
def admin_dashboard():
    search_query = request.args.get('q', '')
    if search_query:
        users = User.query.filter(User.username.ilike(f'%{search_query}%') | User.email.ilike(f'%{search_query}%') | User.instagram_username.ilike(f'%{search_query}%') | User.ccp_account.ilike(f'%{search_query}%')).all()
    else:
        users = User.query.all()
        
    for u in users:
        u.completed_tasks_count = CompletedTask.query.filter_by(user_id=u.id).count()
        referrals = User.query.filter_by(referred_by=u.id).all()
        u.total_invites = len(referrals)
        
        u.active_invites = 0
        for r in referrals:
            r_total_invites = User.query.filter_by(referred_by=r.id).count()
            if r.fast_goal_tasks_completed >= 50 and r_total_invites >= 50:
                u.active_invites += 1
                
    task_query = request.args.get('tq', '')
    if task_query:
        tasks = Task.query.filter(Task.title.ilike(f'%{task_query}%') | Task.link.ilike(f'%{task_query}%')).order_by(Task.id.desc()).all()
    else:
        tasks = Task.query.order_by(Task.id.desc()).all()
        
    for task in tasks:
        task.completions_count = CompletedTask.query.filter_by(task_id=task.id).count()
        
    config = AppConfig.query.first()
    
    pending_withdrawals = WithdrawalRequest.query.filter_by(status='pending').order_by(WithdrawalRequest.created_at.desc()).all()
    completed_withdrawals = WithdrawalRequest.query.filter(WithdrawalRequest.status.in_(['approved', 'rejected'])).order_by(WithdrawalRequest.processed_at.desc()).limit(15).all()
    
    total_users = User.query.count()
    
    return render_template('admin_dashboard.html', 
                           users=users, 
                           tasks=tasks, 
                           config=config,
                           pending_withdrawals=pending_withdrawals,
                           completed_withdrawals=completed_withdrawals,
                           total_users=total_users)

@app.route('/admin/withdrawals/<int:req_id>/<action>', methods=['POST'])
@admin_required
def admin_process_withdrawal(req_id, action):
    req = WithdrawalRequest.query.get_or_404(req_id)
    if req.status != 'pending':
        flash('هذا الطلب تمت معالجته مسبقاً.', 'warning')
        return redirect(url_for('admin_dashboard'))
        
    if action == 'approve':
        req.status = 'approved'
        req.processed_at = datetime.utcnow()
        notif = Notification(user_id=req.user_id, message=f'تمت الموافقة على طلبك.', type='success')
        db.session.add(notif)
        flash(f'تمت الموافقة للمستخدم {req.user.username}.', 'success')
    elif action == 'reject':
        reason = request.form.get('reason', 'سبب غير محدد')
        req.status = 'rejected'
        req.rejection_reason = reason
        req.processed_at = datetime.utcnow()
        req.user.fast_goal_claimed = False
        notif = Notification(user_id=req.user_id, message=f'تم رفض طلبك بسبب: {reason}. يمكنك المحاولة مجدداً.', type='danger')
        db.session.add(notif)
        flash(f'تم رفض الطلب للمستخدم {req.user.username}.', 'info')
        
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/task/<int:task_id>/completions')
@admin_required
def admin_task_completions(task_id):
    task = Task.query.get_or_404(task_id)
    search_query = request.args.get('q', '')
    
    query = CompletedTask.query.filter_by(task_id=task.id).join(User)
    if search_query:
        query = query.filter(User.username.ilike(f'%{search_query}%') | User.instagram_username.ilike(f'%{search_query}%') | User.ccp_account.ilike(f'%{search_query}%'))
        
    completions = query.order_by(CompletedTask.completed_at.desc()).all()
    return render_template('task_completions.html', task=task, completions=completions)

@app.route('/admin/config/update', methods=['POST'])
@admin_required
def admin_update_config():
    config = AppConfig.query.first()
    daily_task_limit = request.form.get('daily_task_limit')
    instagram_agent_link = request.form.get('instagram_agent_link')
    
    if daily_task_limit:
        config.daily_task_limit = int(daily_task_limit)
        
    if instagram_agent_link:
        config.instagram_agent_link = instagram_agent_link
        
    db.session.commit()
    flash('تم تحديث الإعدادات بنجاح.', 'success')
    return redirect(url_for('admin_dashboard') + '?tab=tasks')

@app.route('/admin/tasks/add', methods=['POST'])
@admin_required
def admin_add_task():
    task_type = request.form.get('task_type', 'normal')
    
    if task_type == 'follow':
        username = request.form.get('target_username')
        title = 'متابعة حساب انستغرام'
        description = 'قم بمتابعة هذا الحساب على انستغرام'
        link = f'https://instagram.com/{username}'
    elif task_type == 'comment':
        post_link = request.form.get('target_link')
        title = 'إعجاب وتعليق على بوست انستغرام'
        description = 'إعجاب وتعليق ايجابي'
        link = post_link
    else:
        title = request.form.get('title')
        description = request.form.get('description')
        link = request.form.get('link')
        
    max_completions = request.form.get('max_completions')
    max_completions = int(max_completions) if max_completions else None
    target_gender = request.form.get('target_gender', 'all')
    min_age = request.form.get('min_age')
    min_age = int(min_age) if min_age else None
    max_age = request.form.get('max_age')
    max_age = int(max_age) if max_age else None
    
    new_task = Task(
        title=title, 
        description=description, 
        link=link,
        max_completions=max_completions,
        target_gender=target_gender,
        min_age=min_age,
        max_age=max_age
    )
    db.session.add(new_task)
    db.session.commit()
    
    flash('تمت إضافة المهمة بنجاح.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/tasks/update/<int:task_id>', methods=['POST'])
@admin_required
def admin_update_task(task_id):
    task = Task.query.get_or_404(task_id)
    
    title = request.form.get('title')
    if title:
        task.title = title
        
    description = request.form.get('description')
    if description:
        task.description = description
        
    link = request.form.get('link')
    if link is not None:
        task.link = link
        
    max_completions = request.form.get('max_completions')
    task.max_completions = int(max_completions) if max_completions else None
        
    task.target_gender = request.form.get('target_gender', 'all')
    
    min_age = request.form.get('min_age')
    task.min_age = int(min_age) if min_age else None
    
    max_age = request.form.get('max_age')
    task.max_age = int(max_age) if max_age else None
    
    db.session.commit()
    flash('تم تحديث المهمة بنجاح.', 'success')
    return redirect(url_for('admin_dashboard') + '?tab=tasks')

@app.route('/admin/tasks/delete/<int:task_id>', methods=['POST'])
@admin_required
def admin_delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    CompletedTask.query.filter_by(task_id=task.id).delete()
    db.session.delete(task)
    db.session.commit()
    flash('تم حذف المهمة بنجاح.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@admin_required
def admin_delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        flash('لا يمكن حذف حساب المسؤول.', 'danger')
        return redirect(url_for('admin_dashboard'))
        
    User.query.filter_by(referred_by=user.id).update({User.referred_by: None})
    CompletedTask.query.filter_by(user_id=user.id).delete()
    WithdrawalRequest.query.filter_by(user_id=user.id).delete()
    
    db.session.delete(user)
    db.session.commit()
    flash(f'تم حذف المستخدم {user.username} بنجاح.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/users/reset_password/<int:user_id>', methods=['POST'])
@admin_required
def admin_reset_password(user_id):
    user = User.query.get_or_404(user_id)
    new_password = request.form.get('new_password')
    
    if new_password and len(new_password) >= 6:
        user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        flash(f'تم تعيين كلمة مرور جديدة للمستخدم {user.username} بنجاح.', 'success')
    else:
        flash('كلمة المرور يجب أن تكون 6 أحرف على الأقل.', 'danger')
        
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/backup/export')
@admin_required
def export_backup():
    data = {
        'users': [model_to_dict(u) for u in User.query.all()],
        'tasks': [model_to_dict(t) for t in Task.query.all()],
        'completed_tasks': [model_to_dict(c) for c in CompletedTask.query.all()],
        'withdrawals': [model_to_dict(w) for w in WithdrawalRequest.query.all()],
        'config': [model_to_dict(c) for c in AppConfig.query.all()]
    }
    
    response = app.response_class(
        response=json.dumps(data, ensure_ascii=False, indent=2),
        status=200,
        mimetype='application/json'
    )
    filename = f'backup_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.json'
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response

@app.route('/admin/backup/import', methods=['POST'])
@admin_required
def import_backup():
    if 'backup_file' not in request.files:
        flash('لم يتم تحديد ملف.', 'danger')
        return redirect(url_for('admin_dashboard') + '?tab=tasks')
        
    file = request.files['backup_file']
    if file.filename == '':
        flash('لم يتم تحديد ملف.', 'danger')
        return redirect(url_for('admin_dashboard') + '?tab=tasks')
        
    if not file.filename.endswith('.json'):
        flash('يجب أن يكون الملف بصيغة JSON.', 'danger')
        return redirect(url_for('admin_dashboard') + '?tab=tasks')
        
    try:
        data = json.load(file)
        
        WithdrawalRequest.query.delete()
        CompletedTask.query.delete()
        Task.query.delete()
        AppConfig.query.delete()
        
        User.query.update({User.referred_by: None})
        User.query.delete()
        
        db.session.commit()
        
        def parse_dt(val):
            return datetime.fromisoformat(val) if val else None

        def parse_date(val):
            return date.fromisoformat(val) if val else None

        for u_data in data.get('users', []):
            u = User(**{k: v for k, v in u_data.items() if k not in ['created_at', 'ccp_last_changed', 'instagram_last_changed', 'fast_goal_last_task_date']})
            u.ccp_last_changed = parse_dt(u_data.get('ccp_last_changed'))
            u.instagram_last_changed = parse_dt(u_data.get('instagram_last_changed'))
            u.fast_goal_last_task_date = parse_date(u_data.get('fast_goal_last_task_date'))
            db.session.add(u)
        db.session.commit()
        
        for t_data in data.get('tasks', []):
            t = Task(**{k: v for k, v in t_data.items()})
            db.session.add(t)
            
        for c_data in data.get('config', []):
            c = AppConfig(**{k: v for k, v in c_data.items()})
            db.session.add(c)
            
        for ct_data in data.get('completed_tasks', []):
            ct = CompletedTask(**{k: v for k, v in ct_data.items() if k != 'completed_at'})
            ct.completed_at = parse_dt(ct_data.get('completed_at'))
            db.session.add(ct)
            
        for w_data in data.get('withdrawals', []):
            w = WithdrawalRequest(**{k: v for k, v in w_data.items() if k not in ['created_at', 'processed_at']})
            w.created_at = parse_dt(w_data.get('created_at'))
            w.processed_at = parse_dt(w_data.get('processed_at'))
            db.session.add(w)
            
        db.session.commit()
        flash('تم استعادة النسخة الاحتياطية بنجاح! يرجى تسجيل الدخول مجدداً.', 'success')
        
        try:
            logout_user()
        except Exception:
            pass
            
        return redirect(url_for('login'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'حدث خطأ أثناء الاستعادة: {str(e)}', 'danger')
        return redirect(url_for('admin_dashboard') + '?tab=tasks')

def ping_server():
    url = os.environ.get('RENDER_EXTERNAL_URL', 'https://purple-oxtp.onrender.com')
    while True:
        try:
            time.sleep(random.randint(30, 40))
            requests.get(url)
        except Exception as e:
            pass

ping_thread = threading.Thread(target=ping_server, daemon=True)
ping_thread.start()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)
