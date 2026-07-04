from app import app, db, Task

with app.app_context():
    # Delete the ones with negative IDs if they exist
    Task.query.filter(Task.id < 0).delete()
    db.session.commit()
    print("Cleaned up any negative ID tasks.")
