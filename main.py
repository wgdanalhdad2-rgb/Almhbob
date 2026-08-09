from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
import os
import json
import base64
import firebase_admin
from firebase_admin import credentials, firestore

# ====================== تهيئة Firebase بشكل آمن جداً ======================
db = None

def initialize_firebase():
    global db
    
    if firebase_admin._apps:
        try:
            db = firestore.client()
            return True
        except:
            pass

    try:
        cred = None

        # 1. Base64
        b64_creds = os.getenv("FIREBASE_CREDENTIALS_BASE64")
        if b64_creds:
            print("🔑 محاولة استخدام Base64...")
            try:
                decoded = base64.b64decode(b64_creds.strip()).decode("utf-8")
                cred_dict = json.loads(decoded)
                if "private_key" in cred_dict:
                    cred_dict["private_key"] = cred_dict["private_key"].replace("\\n", "\n")
                cred = credentials.Certificate(cred_dict)
                print("✅ تم تحميل المفتاح من Base64")
            except Exception as e:
                print(f"⚠️ فشل Base64: {e}")

        # 2. متغير عادي
        if not cred:
            raw = os.getenv("FIREBASE_CREDENTIALS")
            if raw:
                print("🔑 محاولة استخدام FIREBASE_CREDENTIALS...")
                try:
                    cred_dict = json.loads(raw.strip())
                    if "private_key" in cred_dict:
                        cred_dict["private_key"] = cred_dict["private_key"].replace("\\n", "\n")
                    cred = credentials.Certificate(cred_dict)
                    print("✅ تم تحميل المفتاح من متغير البيئة")
                except Exception as e:
                    print(f"⚠️ فشل متغير البيئة: {e}")

        # 3. ملف محلي
        if not cred:
            for path in ["serviceAccountKey.json", "firebase-credentials.json", "firebase_key.json"]:
                if os.path.exists(path):
                    print(f"🔑 محاولة استخدام الملف: {path}")
                    try:
                        cred = credentials.Certificate(path)
                        print(f"✅ تم تحميل المفتاح من الملف {path}")
                        break
                    except Exception as e:
                        print(f"⚠️ فشل الملف {path}: {e}")

        if not cred:
            print("❌ لم يتم العثور على أي مفتاح صالح")
            return False

        firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("✅ تم الاتصال بـ Firebase بنجاح")
        return True

    except Exception as e:
        print(f"❌ خطأ عام في تهيئة Firebase: {e}")
        return False


# تشغيل التهيئة
initialize_firebase()

app = FastAPI()

# --- نماذج البيانات ---
class ProductCreate(BaseModel):
    name: str
    category: str
    car_brand: Optional[str] = None
    car_model: Optional[str] = None
    price: float
    stock: int = 0
    image_url: Optional[str] = None

class JobCreate(BaseModel):
    customer_name: str
    whatsapp_number: Optional[str] = None
    car_model: str
    issue_description: str


@app.get("/products/")
def get_products():
    if not db:
        return []
    try:
        products = []
        for doc in db.collection("products").stream():
            data = doc.to_dict()
            data["id"] = doc.id
            products.append(data)
        return products
    except Exception as e:
        print(f"خطأ في جلب المنتجات: {e}")
        return []


@app.post("/products/")
def create_product(product: ProductCreate):
    if not db:
        raise HTTPException(status_code=500, detail="قاعدة البيانات غير متصلة")
    try:
        data = product.model_dump() if hasattr(product, 'model_dump') else product.dict()
        ref = db.collection("products").document()
        ref.set(data)
        data["id"] = ref.id
        return data
    except Exception as e:
        print(f"❌ خطأ إضافة قطعة: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/products/{product_id}")
def delete_product(product_id: str):
    if not db:
        raise HTTPException(status_code=500, detail="Database not connected")
    ref = db.collection("products").document(product_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Product not found")
    ref.delete()
    return {"message": "Deleted successfully"}


@app.get("/jobs/")
def get_jobs():
    if not db:
        return []
    try:
        jobs = []
        for doc in db.collection("jobs").stream():
            data = doc.to_dict()
            data["id"] = doc.id
            jobs.append(data)
        return jobs
    except Exception as e:
        print(f"خطأ في جلب الطلبات: {e}")
        return []


@app.post("/jobs/")
def create_job(job: JobCreate):
    if not db:
        raise HTTPException(status_code=500, detail="Database not connected")
    data = job.model_dump() if hasattr(job, 'model_dump') else job.dict()
    data["status"] = "تحت الصيانة"
    ref = db.collection("jobs").document()
    ref.set(data)
    data["id"] = ref.id
    return data


@app.put("/jobs/{job_id}/status")
def update_job_status(job_id: str, status: str):
    if not db:
        raise HTTPException(status_code=500, detail="Database not connected")
    ref = db.collection("jobs").document(job_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Job not found")
    ref.update({"status": status})
    return {"message": "Status updated", "status": status}


@app.get("/", response_class=HTMLResponse)
def read_root():
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    except:
        return "<h1>index.html غير موجود</h1>"


@app.get("/admin", response_class=HTMLResponse)
def read_admin():
    try:
        with open("admin.html", "r", encoding="utf-8") as f:
            return f.read()
    except:
        return "<h1>admin.html غير موجود</h1>"

