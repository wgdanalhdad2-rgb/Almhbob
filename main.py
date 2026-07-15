from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import sessionmaker, Session, declarative_base

# ==========================================
# 1. إعداد قاعدة البيانات (SQLite)
# ==========================================
SQLALCHEMY_DATABASE_URL = "sqlite:///./shop_workshop.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ==========================================
# 2. نماذج قاعدة البيانات (جداول البيانات)
# ==========================================
# جدول قطع الغيار
class DBProduct(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)          # اسم القطعة (مثال: كشاف لاندكروزر)
    category = Column(String)                  # التصنيف (كشافات، صدامات، لمبات)
    price = Column(Float)                      # السعر
    stock = Column(Integer)                    # الكمية المتوفرة في المحل

# جدول الورشة (كروت العمل)
class DBJobCard(Base):
    __tablename__ = "job_cards"
    id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String)             # اسم العميل
    car_model = Column(String)                 # نوع السيارة
    issue_description = Column(String)         # وصف المشكلة (مثال: سمكرة صدام أمامي)
    status = Column(String, default="في الانتظار") # حالة السيارة (في الانتظار، جاري العمل، جاهزة)

# إنشاء الجداول في قاعدة البيانات
Base.metadata.create_all(bind=engine)

# ==========================================
# 3. نماذج البيانات (لإرسال واستقبال الطلبات)
# ==========================================
class ProductCreate(BaseModel):
    name: str
    category: str
    price: float
    stock: int

class ProductResponse(ProductCreate):
    id: int
    class Config:
        orm_mode = True

class JobCardCreate(BaseModel):
    customer_name: str
    car_model: str
    issue_description: str

class JobCardResponse(JobCardCreate):
    id: int
    status: str
    class Config:
        orm_mode = True

# ==========================================
# 4. بناء التطبيق (API Endpoints)
# ==========================================
app = FastAPI(title="نظام إدارة المحل والورشة")

# دالة مساعدة لفتح وإغلاق قاعدة البيانات
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- قسم المبيعات والمخزون ---

@app.post("/products/", response_model=ProductResponse, tags=["المخزون"])
def add_product(product: ProductCreate, db: Session = Depends(get_db)):
    """إضافة قطعة غيار جديدة للمخزون"""
    db_product = DBProduct(**product.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@app.get("/products/", response_model=List[ProductResponse], tags=["المخزون"])
def get_all_products(db: Session = Depends(get_db)):
    """عرض جميع قطع الغيار المتوفرة"""
    return db.query(DBProduct).all()

# --- قسم الورشة والسمكرة ---

@app.post("/jobs/", response_model=JobCardResponse, tags=["الورشة"])
def create_job_card(job: JobCardCreate, db: Session = Depends(get_db)):
    """فتح كرت عمل جديد لسيارة في الورشة"""
    db_job = DBJobCard(**job.dict())
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job

@app.get("/jobs/", response_model=List[JobCardResponse], tags=["الورشة"])
def get_all_jobs(db: Session = Depends(get_db)):
    """عرض جميع السيارات الموجودة في الورشة"""
    return db.query(DBJobCard).all()

@app.put("/jobs/{job_id}/status", response_model=JobCardResponse, tags=["الورشة"])
def update_job_status(job_id: int, new_status: str, db: Session = Depends(get_db)):
    """تحديث حالة السيارة (مثلاً: جاهزة للاستلام)"""
    db_job = db.query(DBJobCard).filter(DBJobCard.id == job_id).first()
    if not db_job:
        raise HTTPException(status_code=404, detail="كرت العمل غير موجود")
    db_job.status = new_status
    db.commit()
    db.refresh(db_job)
    return db_job

@app.get("/", response_class=HTMLResponse, tags=["العميل"])
def client_homepage():
    """واجهة العميل الرئيسية"""
    try:
        with open("index.html", "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        return "<h1>ملف الواجهة غير موجود. يرجى التأكد من إنشاء index.html</h1>"

