from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import create_engine, Column, Integer, String, Float, desc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from typing import List, Optional

# ====================== 1. إعداد قاعدة البيانات ======================
SQLALCHEMY_DATABASE_URL = "sqlite:///./workshop.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ====================== 2. جداول قاعدة البيانات ======================
class DBProduct(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    category = Column(String)
    car_brand = Column(String, nullable=True)
    car_model = Column(String, nullable=True)
    price = Column(Float)
    stock = Column(Integer, default=0)

class DBJobCard(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String, index=True)
    phone = Column(String, nullable=True)
    car_brand = Column(String, nullable=True)
    car_model = Column(String)
    plate_number = Column(String, nullable=True)
    year = Column(String, nullable=True)
    issue_description = Column(String)
    status = Column(String, default="في الانتظار")

class DBEmployee(Base):
    __tablename__ = "employees"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    role = Column(String)
    phone = Column(String, nullable=True)

# إنشاء الجداول تلقائياً إذا لم تكن موجودة
Base.metadata.create_all(bind=engine)


# ====================== 3. نماذج Pydantic للتحقق ======================
class ProductCreate(BaseModel):
    name: str
    category: str
    car_brand: Optional[str] = None
    car_model: Optional[str] = None
    price: float
    stock: int = 0

class ProductResponse(ProductCreate):
    id: int
    class Config:
        orm_mode = True

class JobCardCreate(BaseModel):
    customer_name: str
    phone: Optional[str] = None
    car_brand: Optional[str] = None
    car_model: str
    plate_number: Optional[str] = None
    year: Optional[str] = None
    issue_description: str

class JobCardResponse(JobCardCreate):
    id: int
    status: str
    class Config:
        orm_mode = True

class EmployeeCreate(BaseModel):
    name: str
    role: str
    phone: Optional[str] = None

class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    phone: Optional[str] = None

class EmployeeResponse(EmployeeCreate):
    id: int
    class Config:
        orm_mode = True


# ====================== 4. تهيئة FastAPI ======================
app = FastAPI(title="ورشة المحبوب API")

# دالة مساعدة للحصول على جلسة الاتصال بقاعدة البيانات
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ====================== 5. مسارات صفحات الـ HTML ======================
@app.get("/", tags=["الصفحات الرئيسية"])
def get_home_page():
    # تأكد أن ملف index.html في نفس المجلد
    return FileResponse("index.html")

@app.get("/admin", tags=["الصفحات الرئيسية"])
def get_admin_page():
    # تأكد أن ملف admin.html في نفس المجلد
    return FileResponse("admin.html")


# ====================== 6. مسارات المنتجات ======================
@app.post("/products/", response_model=ProductResponse, tags=["المنتجات"])
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    db_product = DBProduct(**product.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@app.get("/products/", response_model=List[ProductResponse], tags=["المنتجات"])
def get_products(db: Session = Depends(get_db)):
    return db.query(DBProduct).all()

@app.get("/products/{prod_id}", response_model=ProductResponse, tags=["المنتجات"])
def get_product(prod_id: int, db: Session = Depends(get_db)):
    db_prod = db.query(DBProduct).filter(DBProduct.id == prod_id).first()
    if not db_prod:
        raise HTTPException(status_code=404, detail="المنتج غير موجود")
    return db_prod

@app.put("/products/{prod_id}", response_model=ProductResponse, tags=["المنتجات"])
def update_product(prod_id: int, updates: ProductCreate, db: Session = Depends(get_db)):
    db_prod = db.query(DBProduct).filter(DBProduct.id == prod_id).first()
    if not db_prod:
        raise HTTPException(status_code=404, detail="المنتج غير موجود")
    
    for key, value in updates.dict().items():
        setattr(db_prod, key, value)
    
    db.commit()
    db.refresh(db_prod)
    return db_prod

@app.delete("/products/{prod_id}", tags=["المنتجات"])
def delete_product(prod_id: int, db: Session = Depends(get_db)):
    db_prod = db.query(DBProduct).filter(DBProduct.id == prod_id).first()
    if not db_prod:
        raise HTTPException(status_code=404, detail="المنتج غير موجود")
    db.delete(db_prod)
    db.commit()
    return {"msg": "تم حذف المنتج بنجاح"}


# ====================== 7. مسارات كروت الورشة ======================
@app.post("/jobs/", response_model=JobCardResponse, tags=["الورشة"])
def create_job(job: JobCardCreate, db: Session = Depends(get_db)):
    db_job = DBJobCard(**job.dict())
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job

@app.get("/jobs/", response_model=List[JobCardResponse], tags=["الورشة"])
def get_all_jobs(status: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(DBJobCard)
    if status:
        query = query.filter(DBJobCard.status == status)
    return query.order_by(desc(DBJobCard.id)).all()

@app.put("/jobs/{job_id}/status", tags=["الورشة"])
def update_job_status(job_id: int, status: str, db: Session = Depends(get_db)):
    db_job = db.query(DBJobCard).filter(DBJobCard.id == job_id).first()
    if not db_job:
        raise HTTPException(status_code=404, detail="بطاقة العمل غير موجودة")
    db_job.status = status
    db.commit()
    return {"msg": "تم تحديث الحالة بنجاح", "status": status}

@app.delete("/jobs/{job_id}", tags=["الورشة"])
def delete_job(job_id: int, db: Session = Depends(get_db)):
    db_job = db.query(DBJobCard).filter(DBJobCard.id == job_id).first()
    if not db_job:
        raise HTTPException(status_code=404, detail="بطاقة العمل غير موجودة")
    db.delete(db_job)
    db.commit()
    return {"msg": "تم حذف بطاقة العمل"}


# ====================== 8. مسارات الموظفين ======================
@app.post("/employees/", response_model=EmployeeResponse, tags=["الموظفين"])
def add_employee(emp: EmployeeCreate, db: Session = Depends(get_db)):
    db_emp = DBEmployee(**emp.dict())
    db.add(db_emp)
    db.commit()
    db.refresh(db_emp)
    return db_emp

@app.get("/employees/", response_model=List[EmployeeResponse], tags=["الموظفين"])
def get_employees(db: Session = Depends(get_db)):
    return db.query(DBEmployee).all()

@app.put("/employees/{emp_id}", response_model=EmployeeResponse, tags=["الموظفين"])
def update_employee(emp_id: int, updates: EmployeeUpdate, db: Session = Depends(get_db)):
    db_emp = db.query(DBEmployee).filter(DBEmployee.id == emp_id).first()
    if not db_emp:
        raise HTTPException(status_code=404, detail="الموظف غير موجود")
    
    for key, value in updates.dict(exclude_unset=True).items():
        setattr(db_emp, key, value)
    
    db.commit()
    db.refresh(db_emp)
    return db_emp

@app.delete("/employees/{emp_id}", tags=["الموظفين"])
def delete_employee(emp_id: int, db: Session = Depends(get_db)):
    db_emp = db.query(DBEmployee).filter(DBEmployee.id == emp_id).first()
    if not db_emp:
        raise HTTPException(status_code=404, detail="الموظف غير موجود")
    db.delete(db_emp)
    db.commit()
    return {"msg": "تم حذف الموظف بنجاح"}

