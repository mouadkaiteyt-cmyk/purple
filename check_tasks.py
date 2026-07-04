from app import app, db, Task

with app.app_context():
    count = Task.query.count()
    print(f"Total tasks in database: {count}")
    
    tasks = Task.query.order_by(Task.id.asc()).limit(5).all()
    print("\nFirst 5 tasks:")
    for t in tasks:
        print(f"ID: {t.id}, Title: {t.title}, Link: {t.link}")
