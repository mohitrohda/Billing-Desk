import os, uuid
from dotenv import load_dotenv
load_dotenv()
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO
from fastapi import FastAPI, Depends, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from .database import Base, engine, get_db
from . import models, schemas
from .security import hash_password, verify_password, create_token, current_user

Base.metadata.create_all(bind=engine)
app = FastAPI(title=os.getenv("APP_NAME", "Billing & Invoicing API"), version="1.0.0")
origins = [os.getenv("FRONTEND_ORIGIN", "http://localhost:5173"), "http://localhost:5173", "http://127.0.0.1:5173"]
app.add_middleware(CORSMiddleware, allow_origins=list(set(origins)), allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
CENT = Decimal("0.01")
def money(value): return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)
def require_user(user=Depends(current_user)): return user

@app.get("/api/health")
def health(): return {"status":"ok", "service":"billing-api"}
@app.post("/api/auth/register", response_model=schemas.TokenOut)
def register(payload: schemas.RegisterIn, db: Session=Depends(get_db)):
    if db.query(models.User).filter(func.lower(models.User.email)==payload.email.lower()).first(): raise HTTPException(409, "An account with this email already exists")
    count=db.query(models.User).count()
    user=models.User(full_name=payload.full_name, email=payload.email.lower(), password_hash=hash_password(payload.password), role="admin" if count==0 else "staff")
    db.add(user); db.commit(); db.refresh(user)
    return {"access_token":create_token(user), "user":user}
@app.post("/api/auth/login", response_model=schemas.TokenOut)
def login(payload: schemas.LoginIn, db: Session=Depends(get_db)):
    user=db.query(models.User).filter(func.lower(models.User.email)==payload.email.lower()).first()
    if not user or not verify_password(payload.password,user.password_hash): raise HTTPException(401,"Incorrect email or password")
    return {"access_token":create_token(user),"user":user}
@app.get("/api/auth/me", response_model=schemas.UserOut)
def me(user=Depends(require_user)): return user

@app.get("/api/customers")
def list_customers(q: str="", db: Session=Depends(get_db), user=Depends(require_user)):
    query=db.query(models.Customer)
    if q: query=query.filter(models.Customer.name.ilike(f"%{q}%"))
    return query.order_by(models.Customer.name).all()
@app.post("/api/customers", status_code=201)
def create_customer(p: schemas.CustomerIn, db: Session=Depends(get_db), user=Depends(require_user)):
    row=models.Customer(**p.model_dump()); db.add(row); db.commit(); db.refresh(row); return row
@app.put("/api/customers/{row_id}")
def update_customer(row_id:int,p:schemas.CustomerIn,db:Session=Depends(get_db),user=Depends(require_user)):
    row=db.get(models.Customer,row_id)
    if not row: raise HTTPException(404,"Customer not found")
    for k,v in p.model_dump().items(): setattr(row,k,v)
    db.commit(); db.refresh(row); return row
@app.delete("/api/customers/{row_id}")
def delete_customer(row_id:int,db:Session=Depends(get_db),user=Depends(require_user)):
    row=db.get(models.Customer,row_id)
    if not row: raise HTTPException(404,"Customer not found")
    if db.query(models.Invoice).filter_by(customer_id=row_id).first() or db.query(models.Quote).filter_by(customer_id=row_id).first(): raise HTTPException(409,"Customer has invoices or quotes and cannot be deleted")
    db.delete(row); db.commit(); return {"ok":True}

@app.get("/api/products")
def list_products(db:Session=Depends(get_db),user=Depends(require_user)): return db.query(models.Product).order_by(models.Product.name).all()
@app.post("/api/products",status_code=201)
def create_product(p:schemas.ProductIn,db:Session=Depends(get_db),user=Depends(require_user)):
    row=models.Product(**p.model_dump()); db.add(row); db.commit(); db.refresh(row); return row
@app.put("/api/products/{row_id}")
def update_product(row_id:int,p:schemas.ProductIn,db:Session=Depends(get_db),user=Depends(require_user)):
    row=db.get(models.Product,row_id)
    if not row: raise HTTPException(404,"Product not found")
    for k,v in p.model_dump().items(): setattr(row,k,v)
    db.commit(); db.refresh(row); return row
@app.delete("/api/products/{row_id}")
def delete_product(row_id:int,db:Session=Depends(get_db),user=Depends(require_user)):
    row=db.get(models.Product,row_id)
    if not row: raise HTTPException(404,"Product not found")
    if db.query(models.InvoiceItem).filter_by(product_id=row_id).first(): raise HTTPException(409,"Product is used by an invoice")
    db.delete(row); db.commit(); return {"ok":True}

def invoice_out(inv, db):
    paid=db.query(func.coalesce(func.sum(models.Payment.amount),0)).filter_by(invoice_id=inv.id).scalar() or 0
    return {"id":inv.id,"invoice_number":inv.invoice_number,"customer_id":inv.customer_id,"customer_name":inv.customer.name if inv.customer else "Unknown customer","issue_date":inv.issue_date.isoformat() if inv.issue_date else None,"due_date":inv.due_date.isoformat() if inv.due_date else None,"status":inv.status,"subtotal":float(inv.subtotal or 0),"tax_total":float(inv.tax_total or 0),"total":float(inv.total or 0),"paid":float(paid),"balance_due":round(max(float(inv.total or 0)-float(paid),0),2),"notes":inv.notes,"items":[{"id":i.id,"product_id":i.product_id,"description":i.description,"quantity":float(i.quantity),"unit_price":float(i.unit_price),"tax_rate":float(i.tax_rate),"line_subtotal":float(i.line_subtotal),"line_tax":float(i.line_tax),"line_total":float(i.line_total)} for i in inv.items]}
@app.get("/api/invoices")
def list_invoices(db:Session=Depends(get_db),user=Depends(require_user)):
    return [invoice_out(x,db) for x in db.query(models.Invoice).options(joinedload(models.Invoice.customer),joinedload(models.Invoice.items)).order_by(models.Invoice.id.desc()).all()]
@app.post("/api/invoices",status_code=201)
def create_invoice(p:schemas.InvoiceIn,db:Session=Depends(get_db),user=Depends(require_user)):
    customer=db.get(models.Customer,p.customer_id)
    if not customer: raise HTTPException(404,"Customer not found")
    invoice=models.Invoice(invoice_number=f"INV-{date.today().year}-{uuid.uuid4().hex[:8].upper()}",customer_id=p.customer_id,issue_date=p.issue_date,due_date=p.due_date,notes=p.notes,status="draft")
    subtotal=Decimal("0"); tax_total=Decimal("0")
    for item in p.items:
        product=db.get(models.Product,item.product_id)
        if not product: raise HTTPException(404,f"Product {item.product_id} not found")
        line_sub=money(item.quantity*product.price); line_tax=money(line_sub*product.tax_rate/Decimal("100")); line_total=line_sub+line_tax
        subtotal+=line_sub; tax_total+=line_tax
        invoice.items.append(models.InvoiceItem(product_id=product.id,description=product.name,quantity=item.quantity,unit_price=product.price,tax_rate=product.tax_rate,line_subtotal=line_sub,line_tax=line_tax,line_total=line_total))
    invoice.subtotal=money(subtotal); invoice.tax_total=money(tax_total); invoice.total=money(subtotal+tax_total)
    db.add(invoice); db.commit(); db.refresh(invoice); return invoice_out(invoice,db)
@app.get("/api/invoices/{invoice_id}")
def get_invoice(invoice_id:int,db:Session=Depends(get_db),user=Depends(require_user)):
    inv=db.query(models.Invoice).options(joinedload(models.Invoice.customer),joinedload(models.Invoice.items)).filter_by(id=invoice_id).first()
    if not inv: raise HTTPException(404,"Invoice not found")
    return invoice_out(inv,db)
@app.patch("/api/invoices/{invoice_id}/status")
def set_invoice_status(invoice_id:int,status:str,db:Session=Depends(get_db),user=Depends(require_user)):
    if status not in {"draft","sent","cancelled"}: raise HTTPException(422,"Status must be draft, sent, or cancelled")
    inv=db.get(models.Invoice,invoice_id)
    if not inv: raise HTTPException(404,"Invoice not found")
    if status=="cancelled" and db.query(models.Payment).filter_by(invoice_id=invoice_id).first(): raise HTTPException(409,"An invoice with payments cannot be cancelled")
    inv.status=status; db.commit(); return invoice_out(inv,db)
@app.get("/api/invoices/{invoice_id}/pdf")
def invoice_pdf(invoice_id:int,db:Session=Depends(get_db),user=Depends(require_user)):
    inv=db.query(models.Invoice).options(joinedload(models.Invoice.customer),joinedload(models.Invoice.items)).filter_by(id=invoice_id).first()
    if not inv: raise HTTPException(404,"Invoice not found")
    buf=BytesIO(); c=canvas.Canvas(buf,pagesize=A4); width,height=A4; y=height-55
    settings=db.query(models.BusinessSetting).first(); business=settings.business_name if settings else "My Business"
    c.setFont("Helvetica-Bold",18); c.drawString(48,y,business); y-=30
    c.setFont("Helvetica-Bold",15); c.drawString(48,y,f"INVOICE {inv.invoice_number}"); y-=28
    c.setFont("Helvetica",10); c.drawString(48,y,f"Bill to: {inv.customer.name if inv.customer else 'Customer'}"); y-=16
    c.drawString(48,y,f"Issue date: {inv.issue_date or '—'}   Due date: {inv.due_date or '—'}"); y-=30
    c.setFont("Helvetica-Bold",9); c.drawString(48,y,"Description"); c.drawString(315,y,"Qty"); c.drawString(365,y,"Unit price"); c.drawString(450,y,"Total"); y-=15
    c.setFont("Helvetica",9)
    for item in inv.items:
        if y<100: c.showPage(); y=height-55
        c.drawString(48,y,item.description[:42]); c.drawRightString(345,y,str(item.quantity)); c.drawRightString(425,y,f"{float(item.unit_price):.2f}"); c.drawRightString(540,y,f"{float(item.line_total):.2f}"); y-=16
    y-=12; c.drawRightString(540,y,f"Subtotal: {float(inv.subtotal):.2f}"); y-=16; c.drawRightString(540,y,f"Tax: {float(inv.tax_total):.2f}"); y-=18
    c.setFont("Helvetica-Bold",12); c.drawRightString(540,y,f"Total: {float(inv.total):.2f}")
    if inv.notes: y-=25; c.setFont("Helvetica",9); c.drawString(48,y, f"Notes: {inv.notes[:100]}")
    c.save(); buf.seek(0)
    return StreamingResponse(buf,media_type="application/pdf",headers={"Content-Disposition":f'attachment; filename="{inv.invoice_number}.pdf"'})

@app.get("/api/invoices/{invoice_id}/payments")
def list_payments(invoice_id:int,db:Session=Depends(get_db),user=Depends(require_user)):
    if not db.get(models.Invoice,invoice_id): raise HTTPException(404,"Invoice not found")
    return db.query(models.Payment).filter_by(invoice_id=invoice_id).order_by(models.Payment.payment_date.desc()).all()
@app.post("/api/invoices/{invoice_id}/payments",status_code=201)
def create_payment(invoice_id:int,p:schemas.PaymentIn,db:Session=Depends(get_db),user=Depends(require_user)):
    inv=db.query(models.Invoice).filter_by(id=invoice_id).with_for_update().first()
    if not inv: raise HTTPException(404,"Invoice not found")
    if inv.status=="cancelled": raise HTTPException(409,"Cannot pay a cancelled invoice")
    paid=db.query(func.coalesce(func.sum(models.Payment.amount),0)).filter_by(invoice_id=invoice_id).scalar() or Decimal("0")
    balance=money(Decimal(inv.total)-Decimal(paid))
    if p.amount>balance: raise HTTPException(422,f"Payment exceeds balance due ({balance})")
    payment=models.Payment(invoice_id=invoice_id,**p.model_dump()); db.add(payment); db.flush()
    if p.amount==balance: inv.status="paid"
    elif p.amount>0: inv.status="partially_paid"
    db.commit(); db.refresh(payment); return payment

@app.get("/api/quotes")
def list_quotes(db:Session=Depends(get_db),user=Depends(require_user)):
    rows=db.query(models.Quote).order_by(models.Quote.id.desc()).all()
    return [{"id":r.id,"quote_number":r.quote_number,"customer_id":r.customer_id,"customer_name":db.get(models.Customer,r.customer_id).name if db.get(models.Customer,r.customer_id) else "Unknown","issue_date":r.issue_date.isoformat(),"expiry_date":r.expiry_date.isoformat() if r.expiry_date else None,"status":r.status,"total":float(r.total),"notes":r.notes} for r in rows]
@app.post("/api/quotes",status_code=201)
def create_quote(p:schemas.QuoteIn,db:Session=Depends(get_db),user=Depends(require_user)):
    if not db.get(models.Customer,p.customer_id): raise HTTPException(404,"Customer not found")
    row=models.Quote(quote_number=f"QUO-{date.today().year}-{uuid.uuid4().hex[:8].upper()}",**p.model_dump()); db.add(row); db.commit(); db.refresh(row); return row
@app.patch("/api/quotes/{quote_id}/status")
def quote_status(quote_id:int,status:str,db:Session=Depends(get_db),user=Depends(require_user)):
    if status not in {"draft","sent","accepted","rejected"}: raise HTTPException(422,"Invalid quote status")
    row=db.get(models.Quote,quote_id)
    if not row: raise HTTPException(404,"Quote not found")
    row.status=status; db.commit(); return row

@app.get("/api/expenses")
def list_expenses(db:Session=Depends(get_db),user=Depends(require_user)): return db.query(models.Expense).order_by(models.Expense.expense_date.desc()).all()
@app.post("/api/expenses",status_code=201)
def create_expense(p:schemas.ExpenseIn,db:Session=Depends(get_db),user=Depends(require_user)):
    row=models.Expense(**p.model_dump()); db.add(row); db.commit(); db.refresh(row); return row
@app.delete("/api/expenses/{row_id}")
def delete_expense(row_id:int,db:Session=Depends(get_db),user=Depends(require_user)):
    row=db.get(models.Expense,row_id)
    if not row: raise HTTPException(404,"Expense not found")
    db.delete(row); db.commit(); return {"ok":True}

@app.get("/api/settings")
def get_settings(db:Session=Depends(get_db),user=Depends(require_user)):
    row=db.query(models.BusinessSetting).first()
    if not row:
        row=models.BusinessSetting(); db.add(row); db.commit(); db.refresh(row)
    return row
@app.put("/api/settings")
def update_settings(p:schemas.SettingsIn,db:Session=Depends(get_db),user=Depends(require_user)):
    row=db.query(models.BusinessSetting).first()
    if not row: row=models.BusinessSetting(); db.add(row)
    for k,v in p.model_dump().items(): setattr(row,k,v)
    db.commit(); db.refresh(row); return row

@app.get("/api/dashboard/summary")
def dashboard(db:Session=Depends(get_db),user=Depends(require_user)):
    invoices=db.query(models.Invoice).filter(models.Invoice.status!="cancelled").all()
    total_invoiced=sum((Decimal(i.total or 0) for i in invoices),Decimal("0"))
    total_collected=sum((Decimal(db.query(func.coalesce(func.sum(models.Payment.amount),0)).filter_by(invoice_id=i.id).scalar() or 0) for i in invoices),Decimal("0"))
    overdue=sum(1 for i in invoices if i.status in {"sent","partially_paid"} and i.due_date and i.due_date<date.today())
    recent=db.query(models.Invoice).options(joinedload(models.Invoice.customer),joinedload(models.Invoice.items)).order_by(models.Invoice.id.desc()).limit(5).all()
    return {"total_customers":db.query(models.Customer).count(),"total_products":db.query(models.Product).count(),"total_invoices":len(invoices),"total_invoiced":float(money(total_invoiced)),"total_collected":float(money(total_collected)),"outstanding_balance":float(money(max(total_invoiced-total_collected,Decimal('0')))),"overdue_invoices":overdue,"total_expenses":float(db.query(func.coalesce(func.sum(models.Expense.amount),0)).scalar() or 0),"recent_invoices":[invoice_out(i,db) for i in recent]}
