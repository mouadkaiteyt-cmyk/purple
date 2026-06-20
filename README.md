# ReVerse

موقع ويب مبني باستخدام لغة Python وإطار عمل Flask للربح من خلال نظام الإحالات.

## المميزات:
- تسجيل مستخدمين مجاني
- نظام إحالة:
  - الحساب العادي يكسب 0.01 دولار لكل إحالة
  - الحساب المطور يكسب 0.1 دولار لكل إحالة
- ترقية الحساب (محاكاة دفع 10 دولار)
- واجهة مستخدم حديثة ومتجاوبة باستخدام Tailwind CSS

## خطوات التشغيل محلياً:
1. قم بإنشاء بيئة عمل افتراضية (اختياري):
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```
2. قم بتثبيت المتطلبات:
   ```bash
   pip install -r requirements.txt
   ```
3. قم بتشغيل التطبيق:
   ```bash
   python app.py
   ```
   أو باستخدام Gunicorn:
   ```bash
   gunicorn app:app
   ```

## تعليمات الرفع على Render:
1. قم برفع هذا المشروع إلى مستودع على GitHub.
2. في لوحة تحكم Render، اختر **New Web Service** وقم بربط المستودع.
3. الإعدادات المطلوبة:
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
4. انقر على **Create Web Service**. سيتم رفع الموقع وتجهيزه للعمل تلقائياً.
