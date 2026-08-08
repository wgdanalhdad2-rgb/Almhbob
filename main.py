from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
import firebase_admin
from firebase_admin import credentials, firestore
import glob
import json

# الاتصال المباشر بقاعدة البيانات وإصلاح المفتاح تلقائياً
if not firebase_admin._apps:
    try:
        key_files = glob.glob("*.json")
        valid_files = [f for f in key_files if "requirements" not in f and "package" not in f]
        
        if valid_files:
            file_path = valid_files[0]
            with open(file_path, "r", encoding="utf-8") as f:
                cred_dict = json.load(f)
            
            if "private_key" in cred_dict:
                cred_dict["private_key"] = cred_dict["private_key"].replace("\\n", "\n")
                
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            print(f"✅ تم الاتصال بنجاح من الملف: {file_path}")
        else:
            print("❌ لم يتم العثور على ملف الـ JSON")
    except Exception as e:
        print(f"❌ خطأ في الاتصال: {e}")

db = firestore.client() if firebase_admin._apps else None
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
    return [{"id": doc.id, **doc.to_dict()} for doc in db.collection("products").stream()]

@app.post("/products/")
def create_product(product: ProductCreate):
    if not db:
        raise HTTPException(status_code=500, detail="قاعدة البيانات غير متصلة")
    try:
        prod_data = product.model_dump() if hasattr(product, 'model_dump') else product.dict()
        new_doc_ref = db.collection("products").document()
        new_doc_ref.set(prod_data)
        prod_data["id"] = new_doc_ref.id
        return prod_data
    except Exception as e:
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
    return [{"id": doc.id, **doc.to_dict()} for doc in db.collection("jobs").stream()]

@app.post("/jobs/")
def create_job(job: JobCreate):
    if not db:
        raise HTTPException(status_code=500, detail="Database not connected")
    job_data = job.model_dump() if hasattr(job, 'model_dump') else job.dict()
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

