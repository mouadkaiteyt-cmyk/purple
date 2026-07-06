import re

with open('/workspace/app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update User model
content = re.sub(
    r'class User\(UserMixin, db.Model\):.*?def is_upgraded\(self\):.*?return False',
    '''class User(UserMixin, db.Model):
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
    fast_goal_tasks_completed = db.Column(db.Integer, default=0)
    fast_goal_tasks_today = db.Column(db.Integer, default=0)
    fast_goal_last_task_date = db.Column(db.Date, nullable=True)
    fast_goal_claimed = db.Column(db.Boolean, default=False)

    referrals = db.relationship('User', backref=db.backref('referrer', remote_side=[id]))''',
    content, flags=re.DOTALL
)

# 2. Update Task Model
content = re.sub(
    r'class Task\(db.Model\):.*?is_boosted = db.Column\(db.Boolean, default=False\)',
    '''class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    link = db.Column(db.String(500), nullable=True)
    max_completions = db.Column(db.Integer, nullable=True)
    target_gender = db.Column(db.String(10), default='all')
    min_age = db.Column(db.Integer, nullable=True)
    max_age = db.Column(db.Integer, nullable=True)''',
    content, flags=re.DOTALL
)

# 3. Update CompletedTask Model
content = re.sub(
    r'class CompletedTask\(db.Model\):.*?completion_type = db.Column\(db.String\(20\), default=\'normal\'\).*?# \'normal\' or \'fast_goal\'',
    '''class CompletedTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)''',
    content, flags=re.DOTALL
)

# 4. Remove Models: Advertisement, Product, Purchase
content = re.sub(r'class Advertisement\(db.Model\):.*?created_at = db.Column\(db.DateTime, default=datetime.utcnow\)', '', content, flags=re.DOTALL)
content = re.sub(r'class Product\(db.Model\):.*?created_at = db.Column\(db.DateTime, default=datetime.utcnow\)', '', content, flags=re.DOTALL)
content = re.sub(r'class Purchase\(db.Model\):.*?product = db.relationship\(\'Product\', backref=db.backref\(\'purchases\', lazy=True\)\)', '', content, flags=re.DOTALL)

# 5. Update AppConfig Model
content = re.sub(
    r'class AppConfig\(db.Model\):.*?total_revenue = db.Column\(db.Float, default=0.0\)',
    '''class AppConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    daily_task_limit = db.Column(db.Integer, default=10)
    instagram_agent_link = db.Column(db.String(200), default='https://instagram.com/YourAgent')''',
    content, flags=re.DOTALL
)

# Replace 'with open("new_app.py", "w") as f: f.write(content)'
with open('/workspace/app2.py', 'w', encoding='utf-8') as f:
    f.write(content)

