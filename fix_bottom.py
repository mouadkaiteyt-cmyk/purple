import re

with open('app.py', 'r') as f:
    content = f.read()

# Fix tasks bottom
tasks_bottom_old = """    if all_completed_task_ids:
        completed_tasks = Task.query.filter(Task.id.in_(all_completed_task_ids)).all()
    else:
        completed_tasks = []

    all_tasks_to_show = uncompleted_tasks + completed_tasks

    return render_template('tasks.html',
                           tasks=all_tasks_to_show,
                           completed_task_ids=all_completed_task_ids,
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

if "if all_completed_task_ids:\n        completed_tasks" in content:
    content = content.replace(tasks_bottom_old, tasks_bottom_new)
else:
    # If not already changed to all_completed_task_ids
    tasks_bottom_old_2 = """    if completed_task_ids:
        completed_tasks = Task.query.filter(Task.id.in_(completed_task_ids)).all()
    else:
        completed_tasks = []

    all_tasks_to_show = uncompleted_tasks + completed_tasks

    return render_template('tasks.html',
                           tasks=all_tasks_to_show,
                           completed_task_ids=completed_task_ids,
                           limit=limit,
                           recent_completions=recent_completions)"""
    content = content.replace(tasks_bottom_old_2, tasks_bottom_new)


# Fix fast_goal bottom
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
                           completed_task_ids=all_completed_task_ids)"""

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

if "completed_task_ids=all_completed_task_ids" in fast_goal_bottom_old and fast_goal_bottom_old in content:
    content = content.replace(fast_goal_bottom_old, fast_goal_bottom_new)
else:
    fast_goal_bottom_old_2 = fast_goal_bottom_old.replace("completed_task_ids=all_completed_task_ids", "completed_task_ids=completed_task_ids")
    if fast_goal_bottom_old_2 in content:
        content = content.replace(fast_goal_bottom_old_2, fast_goal_bottom_new)
    else:
        # maybe another variation
        pass

with open('app.py', 'w') as f:
    f.write(content)
