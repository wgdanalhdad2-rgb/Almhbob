from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Optional

SQLALCHEMY_DATABASE_URL = "sqlite:///./workshop.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class DBProduct(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    category = Column(String)
    car_brand = Column(String, nullable=True)
    car_model = Column(String, nullable=True)
    price = Column(Float)
    stock = Column(Integer, default=0)
    image_url = Column(String, nullable=True)

class DBJob(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String)
    whatsapp_number = Column(String, nullable=True)
    car_model = Column(String)
    issue_description = Column(String)
    status = Column(String, default="تحت الصيانة")

Base.metadata.create_all(bind=engine)

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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
def get_products(db: Session = Depends(get_db)):
    return db.query(DBProduct).all()

@app.post("/products/")
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    db_product = DBProduct(**product.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@app.delete("/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    db_product = db.query(DBProduct).filter(DBProduct.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(db_product)
    db.commit()
    return {"message": "Deleted successfully"}

@app.get("/jobs/")
def get_jobs(db: Session = Depends(get_db)):
    return db.query(DBJob).all()

@app.post("/jobs/")
def create_job(job: JobCreate, db: Session = Depends(get_db)):
    db_job = DBJob(**job.dict())
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job

@app.put("/jobs/{job_id}/status")
def update_job_status(job_id: int, status: str, db: Session = Depends(get_db)):
    db_job = db.query(DBJob).filter(DBJob.id == job_id).first()
    if not db_job:
        raise HTTPException(status_code=404, detail="Job not found")
    db_job.status = status
    db.commit()
    return db_job

@app.get("/", response_class=HTMLResponse)
def read_root():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/admin", response_class=HTMLResponse)
def read_admin():
    with open("admin.html", "r", encoding="utf-8") as f:
        return f.read()

