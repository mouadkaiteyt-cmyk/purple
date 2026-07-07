from app import app, db, User, Task, CompletedTask, WithdrawalRequest
from werkzeug.security import generate_password_hash
import uuid

def create_accounts():
    with app.app_context():
        # Check if 1@1.1 exists
        u1 = User.query.filter_by(email='1@1.1').first()
        if not u1:
            u1 = User(
                username='user1',
                email='1@1.1',
                password_hash=generate_password_hash('1'),
                referral_code=str(uuid.uuid4())[:8],
                goal_choice='money',
                fast_goal_tasks_completed=100,
                fast_goal_tasks_today=10,
                ccp_account='000011112222',
                payment_method='ccp',
                instagram_username='user1_ig'
            )
            db.session.add(u1)
            db.session.commit()
            print("Created User 1")

        # Give User 1 some tasks
        tasks = Task.query.limit(10).all()
        if not tasks:
            print("No tasks found in DB. You might want to seed some.")
        else:
            for t in tasks:
                ct = CompletedTask.query.filter_by(user_id=u1.id, task_id=t.id).first()
                if not ct:
                    ct = CompletedTask(user_id=u1.id, task_id=t.id)
                    db.session.add(ct)
            db.session.commit()
            print("Added completed tasks for User 1")

        # Create withdrawal requests for User 1 to show different states
        # 1 pending
        if not WithdrawalRequest.query.filter_by(user_id=u1.id, status='pending').first():
            w_pending = WithdrawalRequest(user_id=u1.id, amount=80.0, ccp_account='000011112222', status='pending')
            db.session.add(w_pending)

        # 1 approved
        if not WithdrawalRequest.query.filter_by(user_id=u1.id, status='approved').first():
            w_approved = WithdrawalRequest(user_id=u1.id, amount=80.0, ccp_account='000011112222', status='approved')
            db.session.add(w_approved)

        # 1 rejected
        if not WithdrawalRequest.query.filter_by(user_id=u1.id, status='rejected').first():
            w_rejected = WithdrawalRequest(user_id=u1.id, amount=80.0, ccp_account='000011112222', status='rejected', rejection_reason='معلومات الحساب غير صحيحة')
            db.session.add(w_rejected)

        db.session.commit()
        print("Added withdrawal requests for User 1")

        # Check if 2@2.2 exists
        u2 = User.query.filter_by(email='2@2.2').first()
        if not u2:
            u2 = User(
                username='user2',
                email='2@2.2',
                password_hash=generate_password_hash('2'),
                referral_code=str(uuid.uuid4())[:8],
                goal_choice='followers', # For account upgrade / followers
                fast_goal_tasks_completed=10,
                fast_goal_tasks_today=2,
                instagram_username='user2_ig'
            )
            db.session.add(u2)
            db.session.commit()
            print("Created User 2")

if __name__ == '__main__':
    create_accounts()
