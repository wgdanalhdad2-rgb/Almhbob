from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
import firebase_admin
from firebase_admin import credentials, firestore
import glob
import json

# تهيئة اتصال Firebase مع التصحيح التلقائي لمفتاح التوثيق لمنع خطأ JWT Signature
if not firebase_admin._apps:
    try:
        key_files = glob.glob("*firebase-adminsdk*.json") + glob.glob("*.json")
        valid_files = [f for f in key_files if "requirements" not in f and "package" not in f]
        
        if valid_files:
            file_path = valid_files[0]
            with open(file_path, "r", encoding="utf-8") as f:
                cred_dict = json.load(f)
            
            # إصلاح رموز الأسطر في المفتاح الخاص تلقائياً
            if "private_key" in cred_dict:
                cred_dict["private_key"] = cred_dict["private_key"].replace("\\n", "\n")
                
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            print(f"✅ تم الاتصال بقاعدة البيانات وتصحيح المفتاح بنجاح من الملف: {file_path}")
        else:
            print("❌ خطأ: لم يتم العثور على ملف المفاتيح في المجلد!")
    except Exception as e:
        print(f"❌ خطأ أثناء تهيئة Firebase: {e}")

# استدعاء قاعدة البيانات Firestore
db = firestore.client() if firebase_admin._apps else None

app = FastAPI()

# --- نماذج البيانات (Pydantic Models) ---
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

# --- مسارات قطع الغيار (Products) ---
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
    try:
        if not db:
            raise HTTPException(status_code=500, detail="قاعدة البيانات غير متصلة")
        
        prod_data = product.model_dump() if hasattr(product, 'model_dump') else product.dict()
        
        new_doc_ref = db.collection("products").document()
        new_doc_ref.set(prod_data)
        
        result = prod_data
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

# --- مسارات كروت العمل والطلبات (Jobs) ---
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
    
    job_data = job.dict()
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

# --- الصفحات الرئيسية ---
@app.get("/", response_class=HTMLResponse)
def read_root():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/admin", response_class=HTMLResponse)
def read_admin():
    with open("admin.html", "r", encoding="utf-8") as f:
        return f.read()

