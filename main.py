from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import create_engine, Column, Integer, String, Float, desc
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.exc import IntegrityError

# ====================== إعداد قاعدة البيانات ======================
SQLALCHEMY_DATABASE_URL = "sqlite:///./shop_workshop.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ====================== نماذج قاعدة البيانات ======================
class DBProduct(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    category = Column(String, index=True)
    price = Column(Float)
    stock = Column(Integer, default=0)


class DBJobCard(Base):
    __tablename__ = "job_cards"
    id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String)
    car_model = Column(String)
    issue_description = Column(String)
    status = Column(String, default="في الانتظار")


class DBEmployee(Base):
    __tablename__ = "employees"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    role = Column(String)
    phone = Column(String)


Base.metadata.create_all(bind=engine)


# ====================== Pydantic Models ======================
class ProductCreate(BaseModel):
    name: str
    category: str
    price: float
    stock: int = 0


class ProductResponse(ProductCreate):
    id: int

    class Config:
        from_attributes = True


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    stock: Optional[int] = None


class JobCardCreate(BaseModel):
    customer_name: str
    car_model: str
    issue_description: str


class JobCardResponse(JobCardCreate):
    id: int
    status: str

    class Config:
        from_attributes = True


class EmployeeCreate(BaseModel):
    name: str
    role: str
    phone: str


class EmployeeResponse(EmployeeCreate):
    id: int

    class Config:
        from_attributes = True


class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    phone: Optional[str] = None


# ====================== FastAPI App ======================
app = FastAPI(title="نظام ورشة المحبوب", version="2.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # غيرها لاحقاً للدومين الخاص بك
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ====================== الصفحات ======================
@app.get("/", response_class=HTMLResponse)
def client_homepage():
    try:
        with open("index.html", "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        return "<h1>ملف index.html غير موجود</h1>"


@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard():
    try:
        with open("admin.html", "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        return "<h1>ملف admin.html غير موجود</h1>"


# ====================== المنتجات ======================
@app.post("/products/", response_model=ProductResponse, tags=["المنتجات"])
def add_product(product: ProductCreate, db: Session = Depends(get_db)):
    db_product = DBProduct(**product.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


@app.get("/products/", response_model=List[ProductResponse], tags=["المنتجات"])
def get_all_products(
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(DBProduct)
    if category:
        query = query.filter(DBProduct.category == category)
    if search:
        query = query.filter(DBProduct.name.ilike(f"%{search}%"))
    return query.all()


@app.get("/products/{prod_id}", response_model=ProductResponse, tags=["المنتجات"])
def get_product(prod_id: int, db: Session = Depends(get_db)):
    product = db.query(DBProduct).filter(DBProduct.id == prod_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="المنتج غير موجود")
    return product


@app.put("/products/{prod_id}", response_model=ProductResponse, tags=["المنتجات"])
def update_product(prod_id: int, updates: ProductUpdate, db: Session = Depends(get_db)):
    db_product = db.query(DBProduct).filter(DBProduct.id == prod_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="المنتج غير موجود")
    
    for key, value in updates.dict(exclude_unset=True).items():
        setattr(db_product, key, value)
    
    db.commit()
    db.refresh(db_product)
    return db_product


@app.delete("/products/{prod_id}", tags=["المنتجات"])
def delete_product(prod_id: int, db: Session = Depends(get_db)):
    db_prod = db.query(DBProduct).filter(DBProduct.id == prod_id).first()
    if not db_prod:
        raise HTTPException(status_code=404, detail="المنتج غير موجود")
    db.delete(db_prod)
    db.commit()
    return {"msg": "تم حذف المنتج بنجاح"}


# ====================== بطاقات الورشة ======================
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


# ====================== الموظفين ======================
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
