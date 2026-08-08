from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
import os
import json
import firebase_admin
from firebase_admin import credentials, firestore

# ====================== تهيئة Firebase (من البيئة أو من ملف) ======================
def initialize_firebase():
    if firebase_admin._apps:
        return True

    try:
        cred = None

        # 1. محاولة القراءة من متغير البيئة (Railway / Production)
        cred_json_str = os.getenv("FIREBASE_CREDENTIALS")
        
        if cred_json_str:
            print("🔑 جاري استخدام مفتاح Firebase من متغير البيئة...")
            cred_json_str = cred_json_str.strip()
            cred_dict = json.loads(cred_json_str)

            # إصلاح private_key
            if "private_key" in cred_dict:
                private_key = cred_dict["private_key"].replace("\\n", "\n").strip()
                cred_dict["private_key"] = private_key

            cred = credentials.Certificate(cred_dict)

        else:
            # 2. محاولة القراءة من ملف داخل المشروع (Local Development)
            possible_files = [
                "serviceAccountKey.json",
                "firebase-credentials.json",
                "firebase_key.json",
                "secrets/serviceAccountKey.json",
                "credentials/firebase.json"
            ]

            for file_path in possible_files:
                if os.path.exists(file_path):
                    print(f"🔑 جاري استخدام مفتاح Firebase من الملف: {file_path}")
                    cred = credentials.Certificate(file_path)
                    break

        if not cred:
            print("❌ لم يتم العثور على مفتاح Firebase لا في متغير البيئة ولا في الملفات")
            return False

        firebase_admin.initialize_app(cred)
        print("✅ تم الاتصال بـ Firebase بنجاح!")
        return True

    except json.JSONDecodeError as e:
        print(f"❌ خطأ في تحليل JSON من متغير البيئة: {e}")
        return False
    except Exception as e:
        print(f"❌ خطأ أثناء تهيئة Firebase: {e}")
        return False


# تهيئة Firebase
firebase_ready = initialize_firebase()
db = firestore.client() if firebase_ready else None

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
    products_ref = db.collection("products").stream()
    products = []
    for doc in products_ref:
        p_data = doc.to_dict()
        p_data["id"] = doc.id
        products.append(p_data)
    return products


@app.post("/products/")
def create_product(product: ProductCreate):
    if not db:
        raise HTTPException(status_code=500, detail="قاعدة البيانات غير متصلة - تحقق من مفتاح Firebase")
    
    try:
        prod_data = product.model_dump()
        
        new_doc_ref = db.collection("products").document()
        new_doc_ref.set(prod_data)
        
        result = prod_data.copy()
        result["id"] = new_doc_ref.id
        return result
    except Exception as e:
        print(f"❌ خطأ أثناء إضافة القطعة: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/products/{product_id}")
def delete_product(product_id: str):
    if not db:
        raise HTTPException(status_code=500, detail="Database not connected")
    
    doc_ref = db.collection("products").document(product_id)
    if not doc_ref.get().exists:
        raise HTTPException(status_code=404, detail="Product not found")
    
    doc_ref.delete()
    return {"message": "Deleted successfully"}


# --- مسارات كروت العمل ---
@app.get("/jobs/")
def get_jobs():
    if not db:
        return []
    jobs_ref = db.collection("jobs").stream()
    jobs = []
    for doc in jobs_ref:
        j_data = doc.to_dict()
        j_data["id"] = doc.id
        jobs.append(j_data)
    return jobs


@app.post("/jobs/")
def create_job(job: JobCreate):
    if not db:
        raise HTTPException(status_code=500, detail="Database not connected")
    
    job_data = job.model_dump()
    job_data["status"] = "تحت الصيانة"
    
    new_doc_ref = db.collection("jobs").document()
    new_doc_ref.set(job_data)
    
    job_data["id"] = new_doc_ref.id
    return job_data


@app.put("/jobs/{job_id}/status")
def update_job_status(job_id: str, status: str):
    if not db:
        raise HTTPException(status_code=500, detail="Database not connected")
    
    doc_ref = db.collection("jobs").document(job_id)
    if not doc_ref.get().exists:
        raise HTTPException(status_code=404, detail="Job not found")
    
    doc_ref.update({"status": status})
    return {"message": "Status updated successfully", "status": status}


# --- الصفحات ---
@app.get("/", response_class=HTMLResponse)
def read_root():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()


@app.get("/admin", response_class=HTMLResponse)
def read_admin():
    with open("admin.html", "r", encoding="utf-8") as f:
        return f.read()
