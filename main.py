from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
import os
import json
import firebase_admin
from firebase_admin import credentials, firestore

# ====================== تهيئة Firebase الذكية والإصلاح التلقائي للمفتاح ======================
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
        cred_dict = None

        # 1. محاولة القراءة من متغير البيئة FIREBASE_CREDENTIALS
        raw = os.getenv("FIREBASE_CREDENTIALS")
        if raw:
            try:
                cred_dict = json.loads(raw.strip())
            except Exception as e:
                print(f"⚠️ فشل قراءة JSON من المتغير: {e}")

        # 2. إذا لم يوجد في المتغير، نبحث عن أي ملف JSON محلي في المجلد
        if not cred_dict:
            import glob
            json_files = glob.glob("*.json")
            valid_files = [f for f in json_files if "requirements" not in f and "package" not in f]
            if valid_files:
                path = valid_files[0]
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        cred_dict = json.load(f)
                    print(f"📂 تم العثور على ملف محلي: {path}")
                except Exception as e:
                    print(f"⚠️ فشل قراءة الملف المحلي: {e}")

        if not cred_dict:
            print("❌ لم يتم العثور على أي بيانات اعتماد لـ Firebase!")
            return False

        # --- تصحيح تلقائي وجذري لصيغة المفتاح السري لضمان عدم حدوث خطأ JWT Signature ---
        if "private_key" in cred_dict:
            pk = cred_dict["private_key"]
            # إزالة أي ترميز خاطئ للأسطر الجديدة وتحويلها لأسطر حقيقية
            pk = pk.replace("\\\\n", "\n").replace("\\n", "\n").replace("\r", "")
            
            # إعادة بناء هيكل المفتاح البرمجي بدقة تامة
            if "BEGIN PRIVATE KEY" in pk and "END PRIVATE KEY" in pk:
                lines = pk.split("\n")
                body_lines = [l.strip() for l in lines if l.strip() and not l.startswith("-----")]
                body = "".join(body_lines)
                chunks = [body[i:i+64] for i in range(0, len(body), 64)]
                cred_dict["private_key"] = "-----BEGIN PRIVATE KEY-----\n" + "\n".join(chunks) + "\n-----END PRIVATE KEY-----\n"

        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("✅ تم الاتصال بقاعدة بيانات Firebase وتصحيح التوقيع بنجاح تام!")
        return True

    except Exception as e:
        print(f"❌ خطأ عام أثناء تهيئة Firebase: {e}")
        return False

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


# --- مسارات قطع الغيار ---
@app.get("/products/")
def get_products():
    if not db:
        return []
    try:
        return [{"id": doc.id, **doc.to_dict()} for doc in db.collection("products").stream()]
    except Exception as e:
        print(f"خطأ في جلب القطع: {e}")
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


# --- مسارات كروت العمل (الصيانة) ---
@app.get("/jobs/")
def get_jobs():
    if not db:
        return []
    try:
        return [{"id": doc.id, **doc.to_dict()} for doc in db.collection("jobs").stream()]
    except Exception as e:
        print(f"خطأ في جلب الطلبات: {e}")
        return []

@app.post("/jobs/")
def create_job(job: JobCreate):
    if not db:
        raise HTTPException(status_code=500, detail="Database not connected")
    try:
        data = job.model_dump() if hasattr(job, 'model_dump') else job.dict()
        data["status"] = "تحت الصيانة"
        ref = db.collection("jobs").document()
        ref.set(data)
        data["id"] = ref.id
        return data
    except Exception as e:
        print(f"❌ خطأ إضافة طلب: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/jobs/{job_id}/status")
def update_job_status(job_id: str, status: str):
    if not db:
        raise HTTPException(status_code=500, detail="Database not connected")
    ref = db.collection("jobs").document(job_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Job not found")
    ref.update({"status": status})
    return {"message": "Status updated", "status": status}


# --- مسارات الواجهات ---
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
