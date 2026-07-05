import re

with open('app.py', 'r') as f:
    content = f.read()

# 1. Update CompletedTask model
content = re.sub(
    r"    completed_at = db\.Column\(db\.DateTime, default=datetime\.utcnow\)",
    r"    completed_at = db.Column(db.DateTime, default=datetime.utcnow)\n    completion_type = db.Column(db.String(20), default='normal') # 'normal' or 'fast_goal'",
    content
)

# 2. Add database migration
migration_str = """        if 'completed_task' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('completed_task')]
            if 'completed_at' not in columns:
                db.session.execute(text('ALTER TABLE completed_task ADD COLUMN completed_at TIMESTAMP'))
                db.session.execute(text("UPDATE completed_task SET completed_at = CURRENT_TIMESTAMP WHERE completed_at IS NULL"))
            if 'completion_type' not in columns:
                db.session.execute(text("ALTER TABLE completed_task ADD COLUMN completion_type VARCHAR(20) DEFAULT 'normal'"))"""

content = re.sub(
    r"        if 'completed_task' in inspector\.get_table_names\(\):\n            columns = \[col\['name'\] for col in inspector\.get_columns\('completed_task'\)\]\n            if 'completed_at' not in columns:\n                db\.session\.execute\(text\('ALTER TABLE completed_task ADD COLUMN completed_at TIMESTAMP'\)\)\n                # Update existing records to current time so they don't have NULL\n                db\.session\.execute\(text\(\"UPDATE completed_task SET completed_at = CURRENT_TIMESTAMP WHERE completed_at IS NULL\"\)\)",
    migration_str,
    content
)

# 3. Update tasks route
tasks_func_old = """@app.route('/tasks')
@login_required
def tasks():
    completed_task_ids = [ct.task_id for ct in CompletedTask.query.filter_by(user_id=current_user.id).all()]

    # Get recent completions in last 24 hours
    twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
    recent_completions = CompletedTask.query.filter(
        CompletedTask.user_id == current_user.id,
        CompletedTask.completed_at >= twenty_four_hours_ago
    ).count()"""

tasks_func_new = """@app.route('/tasks')
@login_required
def tasks():
    all_completed_task_ids = [ct.task_id for ct in CompletedTask.query.filter_by(user_id=current_user.id).all()]

    # Get recent completions in last 24 hours
    twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
    recent_completions = CompletedTask.query.filter(
        CompletedTask.user_id == current_user.id,
        CompletedTask.completion_type == 'normal',
        CompletedTask.completed_at >= twenty_four_hours_ago
    ).count()"""

content = content.replace(tasks_func_old, tasks_func_new)

content = content.replace(
    "    if completed_task_ids:\n        query = query.filter(~Task.id.in_(completed_task_ids))",
    "    if all_completed_task_ids:\n        query = query.filter(~Task.id.in_(all_completed_task_ids))"
)

tasks_bottom_old = """    if completed_task_ids:
        completed_tasks = Task.query.filter(Task.id.in_(completed_task_ids)).all()
    else:
        completed_tasks = []

    all_tasks_to_show = uncompleted_tasks + completed_tasks

    return render_template('tasks.html',
                           tasks=all_tasks_to_show,
                           completed_task_ids=completed_task_ids,
                           limit=limit,
                           recent_completions=recent_completions)"""

tasks_bottom_new = """    normal_completed_task_ids = [ct.task_id for ct in CompletedTask.query.filter_by(user_id=current_user.id, completion_type='normal').all()]

    if normal_completed_task_ids:
        completed_tasks = Task.query.filter(Task.id.in_(normal_completed_task_ids)).all()
    else:
        completed_tasks = []

    all_tasks_to_show = uncompleted_tasks + completed_tasks

    return render_template('tasks.html',
                           tasks=all_tasks_to_show,
                           completed_task_ids=normal_completed_task_ids,
                           limit=limit,
                           recent_completions=recent_completions)"""

content = content.replace(tasks_bottom_old, tasks_bottom_new)

# 4. Update complete_task route
content = content.replace(
    """    recent_completions = CompletedTask.query.filter(
        CompletedTask.user_id == current_user.id,
        CompletedTask.completed_at >= twenty_four_hours_ago
    ).count()""",
    """    recent_completions = CompletedTask.query.filter(
        CompletedTask.user_id == current_user.id,
        CompletedTask.completion_type == 'normal',
        CompletedTask.completed_at >= twenty_four_hours_ago
    ).count()"""
)

content = content.replace(
    "    new_completion = CompletedTask(user_id=current_user.id, task_id=task.id)",
    "    new_completion = CompletedTask(user_id=current_user.id, task_id=task.id, completion_type='normal')",
    1 # Only the first occurrence in complete_task
)

# 5. Update fast_goal route
fast_goal_old = """    # Fetch uncompleted tasks for fast goal
    completed_task_ids = [ct.task_id for ct in CompletedTask.query.filter_by(user_id=current_user.id).all()]
    query = Task.query
    if completed_task_ids:
        query = query.filter(~Task.id.in_(completed_task_ids))"""

fast_goal_new = """    # Fetch uncompleted tasks for fast goal
    all_completed_task_ids = [ct.task_id for ct in CompletedTask.query.filter_by(user_id=current_user.id).all()]
    query = Task.query
    if all_completed_task_ids:
        query = query.filter(~Task.id.in_(all_completed_task_ids))"""

content = content.replace(fast_goal_old, fast_goal_new)

fast_goal_bottom_old = """    # Include tasks completed today to show them as completed
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

    all_tasks_to_show = available_tasks + today_completed_tasks

    return render_template('fast_goal.html',
                           user=current_user,
                           valid_referrals_count=valid_referrals_count,
                           inactive_referrals_count=inactive_referrals_count,
                           tasks=all_tasks_to_show,
                           remaining_slots=remaining_slots,
                           completed_task_ids=completed_task_ids)"""

fast_goal_bottom_new = """    # Include tasks completed today to show them as completed
    today = datetime.utcnow().date()
    today_completions = CompletedTask.query.filter(
        CompletedTask.user_id == current_user.id,
        CompletedTask.completion_type == 'fast_goal',
        db.func.date(CompletedTask.completed_at) == today
    ).all()
    today_completed_task_ids = [ct.task_id for ct in today_completions]

    if today_completed_task_ids:
        today_completed_tasks = Task.query.filter(Task.id.in_(today_completed_task_ids)).all()
    else:
        today_completed_tasks = []

    all_tasks_to_show = available_tasks + today_completed_tasks

    return render_template('fast_goal.html',
                           user=current_user,
                           valid_referrals_count=valid_referrals_count,
                           inactive_referrals_count=inactive_referrals_count,
                           tasks=all_tasks_to_show,
                           remaining_slots=remaining_slots,
                           completed_task_ids=today_completed_task_ids)"""

content = content.replace(fast_goal_bottom_old, fast_goal_bottom_new)

# 6. Update complete_fast_goal_task route
content = content.replace(
    "    new_completion = CompletedTask(user_id=current_user.id, task_id=task.id)",
    "    new_completion = CompletedTask(user_id=current_user.id, task_id=task.id, completion_type='fast_goal')"
)

with open('app.py', 'w') as f:
    f.write(content)
