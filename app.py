import os
import re
import secrets
import smtplib
import ssl
import uuid
from datetime import date, datetime, timedelta
from email.message import EmailMessage
from email.utils import formataddr
from functools import wraps

from dotenv import load_dotenv
from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, abort)
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from supabase import create_client

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_PUBLISHABLE_KEY = os.environ.get("SUPABASE_PUBLISHABLE_KEY")

SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY") or SUPABASE_PUBLISHABLE_KEY

MANAGER_EMAIL = (os.environ.get("MANAGER_EMAIL") or "").strip().lower()
MANAGER_PASSWORD = os.environ.get("MANAGER_PASSWORD") or ""
MANAGER_NAME = os.environ.get("MANAGER_NAME", "Property Manager")


SMTP_HOST = os.environ.get("SMTP_HOST")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
SMTP_FROM = os.environ.get("SMTP_FROM") or SMTP_USER
MAIL_FROM_NAME = os.environ.get("MAIL_FROM_NAME", "Property Management")
SITE_URL = os.environ.get("SITE_URL", "")


db = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def auth_client():
    return create_client(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY)


ROLES = {
    "tenant": {
        "title": "Tenant", "icon": "🏠", "color": "#2f5d50",
        "tagline": "I already rent a home",
        "blurb": "See your home, pay rent by bank transfer, upload receipts and report problems.",
        "home": "tenant_dashboard",
    },
    "manager": {
        "title": "Manager", "icon": "🛡️", "color": "#3f5a73",
        "tagline": "Property management team",
        "blurb": "Manage buildings, photos, payments, tenants and complaints.",
        "home": "manager_dashboard",
    },
}

PROPERTY_TYPES = ["Room", "Bed Space", "Studio", "1 BHK", "2 BHK", "3 BHK", "Villa"]
PROPERTY_STATUSES = ["Available", "Reserved", "Occupied", "Maintenance", "Unavailable"]
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
RECEIPT_EXT = IMAGE_EXT | {".pdf"}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def generate_reference(prefix):
    return f"{prefix}-{datetime.now().year}-{secrets.token_hex(3).upper()}"


def clean_email(value):
    return (value or "").strip().lower()


def safe_next(target):
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return None


def add_months(d, months):
    m = d.month - 1 + months
    y = d.year + m // 12
    m = m % 12 + 1
    leap = y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)
    last = [31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1]
    return date(y, m, min(d.day, last))


def get_company_settings():
    res = db.table("company_settings").select("*").limit(1).execute()
    return res.data[0] if res.data else {}


def get_cities():
    rows = db.table("buildings").select("city").eq("active", True).execute().data
    return sorted({b["city"] for b in rows if b.get("city")})


def attach_photos(props):
    ids = [p["id"] for p in props]
    by_prop = {}
    if ids:
        rows = (db.table("property_photos").select("*")
                .in_("property_id", ids).order("display_order").execute()).data
        for r in rows:
            by_prop.setdefault(r["property_id"], []).append(r)
    for p in props:
        photos = by_prop.get(p["id"], [])
        p["photos"] = photos
        p["photo_count"] = len(photos)
        p["main_photo"] = next((x for x in photos if x.get("is_main")),
                               photos[0] if photos else None)
    return props


def upload_file(bucket, folder, file_storage, allowed):
    ext = os.path.splitext(file_storage.filename or "")[1].lower()
    if ext not in allowed:
        raise ValueError("Unsupported file type: " + (ext or "unknown"))
    path = f"{folder}/{uuid.uuid4().hex}{ext}"
    db.storage.from_(bucket).upload(
        path, file_storage.read(),
        {"content-type": file_storage.mimetype or "application/octet-stream"})
    return path


def public_url(bucket, path):
    return db.storage.from_(bucket).get_public_url(path)


def signed_url(bucket, path, seconds=300):
    res = db.storage.from_(bucket).create_signed_url(path, seconds)
    url = res.get("signedURL") or res.get("signedUrl")
    if url and not url.startswith("http"):
        url = SUPABASE_URL.rstrip("/") + "/storage/v1" + (url if url.startswith("/") else "/" + url)
    return url


def friendly_auth_error(exc):
    msg = str(exc).lower()
    if "invalid login" in msg or "invalid credentials" in msg:
        return "Wrong email or password."
    if "not confirmed" in msg:
        return "Please confirm your email first (check your inbox), then log in."
    if "already" in msg and "regist" in msg:
        return "This email is already registered. Please log in instead."
    if "password" in msg and ("weak" in msg or "least" in msg or "short" in msg):
        return "Password is too weak. Use at least 8 characters."
    if "rate limit" in msg or "too many" in msg:
        return "Too many attempts. Please wait a minute and try again."
    return "Could not complete the request. Please try again."


def mail_configured():
    return bool(SMTP_HOST and SMTP_FROM)


def site_url():
    return (SITE_URL or request.url_root).rstrip("/")


def send_email(to, subject, text):
    if not mail_configured():
        app.logger.warning("SMTP is not configured -> email to %s was NOT sent (%s)", to, subject)
        return False
    msg = EmailMessage()
    msg["From"] = formataddr((MAIL_FROM_NAME, SMTP_FROM))
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(text)
    try:
        ctx = ssl.create_default_context()
        if SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=15, context=ctx)
        else:
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15)
            server.starttls(context=ctx)
        with server:
            if SMTP_USER:
                server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as exc:
        app.logger.error("Could not send email to %s: %s", to, exc)
        return False


def generate_password(length=10):
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
    while True:
        pw = "".join(secrets.choice(alphabet) for _ in range(length))
        if (any(c.isupper() for c in pw) and any(c.islower() for c in pw)
                and any(c.isdigit() for c in pw)):
            return pw


def find_auth_user(email):
    page = 1
    while True:
        users = db.auth.admin.list_users(page=page, per_page=200)
        for u in users:
            if (u.email or "").lower() == email:
                return u
        if len(users) < 200:
            return None
        page += 1


def upsert_account(email, password, role, full_name, phone=None):
    email = clean_email(email)
    prof = db.table("profiles").select("id, role").eq("email", email).limit(1).execute().data
    if prof:
        if prof[0]["role"] != role:
            raise ValueError("This email already belongs to a different kind of account.")
        uid = prof[0]["id"]
        db.auth.admin.update_user_by_id(uid, {"password": password})
        return uid
    try:
        uid = db.auth.admin.create_user({
            "email": email, "password": password, "email_confirm": True,
            "user_metadata": {"full_name": full_name, "role": role}}).user.id
    except Exception:
        existing = find_auth_user(email)
        if not existing:
            raise
        uid = existing.id
        db.auth.admin.update_user_by_id(uid, {"password": password, "email_confirm": True})
    db.table("profiles").insert({"id": uid, "role": role, "full_name": full_name,
                                 "email": email, "phone": phone}).execute()
    return uid


def ensure_manager():
    if not MANAGER_EMAIL:
        app.logger.warning("MANAGER_EMAIL is not set in .env - nobody can log in as manager.")
        return
    try:
        if db.table("profiles").select("id").eq("email", MANAGER_EMAIL).eq("role", "manager") \
                .limit(1).execute().data:
            return
        if len(MANAGER_PASSWORD) < 8:
            app.logger.warning("MANAGER_PASSWORD must be at least 8 characters.")
            return
        upsert_account(MANAGER_EMAIL, MANAGER_PASSWORD, "manager", MANAGER_NAME)
        app.logger.info("Manager account created for %s", MANAGER_EMAIL)
    except Exception as exc:
        app.logger.error("Could not create the manager account: %s "
                         "(check SUPABASE_SERVICE_KEY and that schema.sql v4 was run)", exc)


def provision_tenant_account(tenant, reset=False):
    if tenant.get("user_id") and not reset:
        return None, False
    email = clean_email(tenant["email"])
    password = generate_password()
    uid = upsert_account(email, password, "tenant", tenant["full_name"], tenant.get("phone"))
    db.table("tenants").update({"user_id": uid}).eq("id", tenant["id"]).execute()

    unit = ""
    if tenant.get("property_id"):
        p = (db.table("properties").select("unit_number, buildings(building_name)")
             .eq("id", tenant["property_id"]).limit(1).execute()).data
        if p:
            b = (p[0].get("buildings") or {}).get("building_name")
            unit = f"{p[0]['unit_number']}" + (f" - {b}" if b else "")
    body = (
        f"Hello {tenant['full_name']},\n\n"
        f"Your booking has been approved and your tenant account is ready"
        f"{(' for ' + unit) if unit else ''}.\n\n"
        f"Log in here:  {site_url()}/login/tenant\n"
        f"Email:        {email}\n"
        f"Password:     {password}\n\n"
        "For your security, please change this password after your first login "
        "(Menu > Change password).\n\n"
        f"- {MAIL_FROM_NAME}\n")
    emailed = send_email(email, "Your tenant account is ready", body)
    return password, emailed


def credentials_notice(tenant, password, emailed):
    if emailed:
        return f"Login details were emailed to {tenant['email']}.", "success"
    return (f"Account ready for {tenant['full_name']}, but the email could NOT be sent "
            f"(SMTP is not configured or failed). Give them these details yourself - "
            f"Email: {tenant['email']}  |  Password: {password}"), "creds"


def start_session(user_id, role, name, email):
    session.clear()
    session["uid"] = user_id
    session["role"] = role
    session["name"] = name or email
    session["email"] = email
    if role == "tenant":
        res = db.table("tenants").select("id").eq("user_id", user_id).limit(1).execute()
        if res.data:
            session["tenant_id"] = res.data[0]["id"]


def role_required(role):
    def deco(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if session.get("role") != role:
                flash(f"Please log in as {ROLES[role]['title'].lower()} to continue.", "error")
                return redirect(url_for("login_role", role=role, next=request.path))
            return f(*args, **kwargs)
        return wrapper
    return deco


def tenant_required(f):
    @wraps(f)
    @role_required("tenant")
    def wrapper(*args, **kwargs):
        res = (db.table("tenants").select("*, properties(*, buildings(*))")
               .eq("user_id", session["uid"]).limit(1).execute())
        if not res.data:
            flash("Your account is not linked to a tenancy yet. Please contact the manager.", "error")
            return redirect(url_for("home"))
        return f(res.data[0], *args, **kwargs)
    return wrapper


STOCK = {
    "hero": "1618221639244-c1a8502c0eb9",
    "tenant": "1616594039964-ae9021a400a0",
    "manager": "1651752523215-9bf678c29355",
    "cta": "1649083048597-d7b4f1e8a386",
}


def stock(key, width=1400):
    return f"https://images.unsplash.com/photo-{STOCK[key]}?auto=format&fit=crop&w={width}&q=75"


@app.context_processor
def inject_globals():
    ctx = dict(ROLES=ROLES, PROPERTY_TYPES=PROPERTY_TYPES,
               PROPERTY_STATUSES=PROPERTY_STATUSES, stock=stock)
    if session.get("role") == "manager":
        try:
            ctx["nav_counts"] = {
                "payments": db.table("payments").select("id", count="exact")
                .eq("status", "Pending Verification").execute().count or 0,
                "complaints": db.table("complaints").select("id", count="exact")
                .in_("status", OPEN_COMPLAINT).execute().count or 0}
        except Exception:
            ctx["nav_counts"] = {"payments": 0, "complaints": 0}
    return ctx


@app.route("/login")
def login_chooser():
    if session.get("role") in ROLES:
        return redirect(url_for(ROLES[session["role"]]["home"]))
    return render_template("login_chooser.html")


@app.route("/login/<role>", methods=["GET", "POST"])
def login_role(role):
    if role not in ROLES:
        abort(404)
    nxt = safe_next(request.values.get("next"))
    if request.method == "POST":
        email = clean_email(request.form.get("email"))
        password = request.form.get("password", "")
        again = lambda: render_template("auth_form.html", role=role, next=nxt, email=email)
        if not email or not password:
            flash("Enter your email and password.", "error")
            return again()
        if role == "manager" and email != MANAGER_EMAIL:
            flash("Wrong email or password.", "error")
            return again()
        try:
            user = auth_client().auth.sign_in_with_password(
                {"email": email, "password": password}).user
        except Exception as exc:
            flash(friendly_auth_error(exc), "error")
            return again()

        prof = db.table("profiles").select("*").eq("id", user.id).limit(1).execute().data
        if not prof:
            flash("This account is not active. Please contact the manager.", "error")
            return again()
        real_role = prof[0]["role"]
        if real_role != role:
            flash(f"This email belongs to a {real_role} account. "
                  f"Please use the {real_role} login.", "error")
            return redirect(url_for("login_role", role=real_role))

        start_session(user.id, role, prof[0].get("full_name"), email)
        if role == "tenant" and not session.get("tenant_id"):
            flash("Your account is not linked to a tenancy yet. Contact the manager.", "error")
        return redirect(nxt or url_for(ROLES[role]["home"]))
    return render_template("auth_form.html", role=role, next=nxt)


@app.route("/register/<role>")
def register_role(role):
    flash("Accounts are created by the property manager after your booking is approved.", "error")
    return redirect(url_for("login_chooser"))


reset_serializer = URLSafeTimedSerializer(app.secret_key, salt="manager-password-reset")


def manager_profile():
    rows = (db.table("profiles").select("id, full_name").eq("email", MANAGER_EMAIL)
            .eq("role", "manager").limit(1).execute().data) if MANAGER_EMAIL else []
    return rows[0] if rows else None


@app.route("/manager/forgot", methods=["GET", "POST"])
def manager_forgot():
    if request.method == "POST":
        email = clean_email(request.form.get("email"))
        if email and email == MANAGER_EMAIL:
            prof = manager_profile()
            if prof:
                stamp = str(db.auth.admin.get_user_by_id(prof["id"]).user.updated_at)
                token = reset_serializer.dumps({"uid": prof["id"], "u": stamp})
                link = f"{site_url()}{url_for('manager_reset', token=token)}"
                if not send_email(
                        MANAGER_EMAIL, "Reset your manager password",
                        "Someone asked to reset the manager password.\n\n"
                        f"Open this link within 30 minutes to choose a new password:\n{link}\n\n"
                        "If this was not you, ignore this email - nothing changes."):
                    app.logger.warning("Manager reset link (email not sent): %s", link)

        flash("If that is the manager email, a reset link has been sent to it.", "success")
        return redirect(url_for("login_role", role="manager"))
    return render_template("manager_forgot.html")


@app.route("/manager/reset/<token>", methods=["GET", "POST"])
def manager_reset(token):
    try:
        data = reset_serializer.loads(token, max_age=1800)
        current = str(db.auth.admin.get_user_by_id(data["uid"]).user.updated_at)
        if current != data["u"]:
            raise BadSignature("used")
    except (BadSignature, SignatureExpired, Exception):
        flash("This reset link is invalid or has expired. Request a new one.", "error")
        return redirect(url_for("manager_forgot"))
    if request.method == "POST":
        pw = request.form.get("password", "")
        if len(pw) < 8:
            flash("Password must be at least 8 characters.", "error")
        elif pw != request.form.get("confirm", ""):
            flash("Passwords do not match.", "error")
        else:
            db.auth.admin.update_user_by_id(data["uid"], {"password": pw})
            flash("Password updated. You can log in now.", "success")
            return redirect(url_for("login_role", role="manager"))
    return render_template("manager_reset.html", token=token)


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("home"))


@app.route("/manager/login")
def manager_login():
    return redirect(url_for("login_role", role="manager"))


@app.route("/")
def home():
    featured = (db.table("properties").select("*, buildings(*)")
                .eq("status", "Available").eq("active", True)
                .order("created_at", desc=True).limit(3).execute()).data
    return render_template("index.html", featured=attach_photos(featured), cities=get_cities())


@app.route("/properties")
def properties():
    property_type = request.args.get("type", "")
    city = request.args.get("city", "")
    max_rent = request.args.get("max_rent", "")

    query = (db.table("properties")
             .select("*, buildings!inner(*)" if city else "*, buildings(*)")
             .eq("status", "Available").eq("active", True))
    if property_type:
        query = query.eq("property_type", property_type)
    if city:
        query = query.eq("buildings.city", city)
    if max_rent:
        try:
            query = query.lte("monthly_rent", float(max_rent))
        except ValueError:
            flash("Maximum rent must be a number.", "error")
    props = attach_photos(query.order("monthly_rent").execute().data)
    return render_template("properties.html", properties=props, cities=get_cities(),
                           property_type=property_type, city=city, max_rent=max_rent)


def get_property_or_404(property_id):
    res = (db.table("properties").select("*, buildings(*)")
           .eq("id", property_id).limit(1).execute()).data
    if not res:
        abort(404)
    return res[0]


@app.route("/property/<int:property_id>")
def property_details(property_id):
    prop = get_property_or_404(property_id)
    photos = (db.table("property_photos").select("*").eq("property_id", property_id)
              .order("display_order").execute()).data
    return render_template("property_details.html", property=prop, photos=photos)


@app.route("/property/<int:property_id>/apply", methods=["GET", "POST"])
def apply(property_id):
    prop = get_property_or_404(property_id)
    if prop["status"] != "Available":
        flash("Sorry, this property is no longer available.", "error")
        return redirect(url_for("property_details", property_id=property_id))

    prefill = {}

    if request.method == "POST":
        try:
            occupants = int(request.form.get("occupants", 1))
            months = int(request.form.get("rental_months", 12))
        except ValueError:
            flash("Occupants and rental period must be numbers.", "error")
            return render_template("application.html", property=prop, prefill=request.form)
        if occupants > (prop.get("maximum_occupants") or 1):
            flash(f"This property allows at most {prop['maximum_occupants']} occupants.", "error")
            return render_template("application.html", property=prop, prefill=request.form)
        ref = generate_reference("REA")
        db.table("applications").insert({
            "application_reference": ref,
            "property_id": property_id,
            "full_name": request.form["full_name"].strip(),
            "email": clean_email(request.form["email"]),
            "phone": request.form["phone"].strip(),
            "nationality": request.form.get("nationality", "").strip(),
            "occupants": occupants,
            "requested_move_in": request.form["move_in"],
            "rental_months": months,
        }).execute()
        return redirect(url_for("payment_instructions", application_id=ref))

    return render_template("application.html", property=prop, prefill=prefill)


def get_application_or_404(ref):
    res = (db.table("applications").select("*, properties(*, buildings(*))")
           .eq("application_reference", ref).limit(1).execute()).data
    if not res:
        abort(404)
    return res[0]


@app.route("/application/<application_id>/payment", methods=["GET", "POST"])
def payment_instructions(application_id):
    application = get_application_or_404(application_id)
    settings = get_company_settings()

    if request.method == "POST":
        if application["status"] in ("Approved", "Payment Submitted"):
            flash("A payment for this booking is already submitted.", "error")
            return redirect(url_for("payment_instructions", application_id=application_id))
        receipt = request.files.get("receipt")
        if not receipt or not receipt.filename:
            flash("Please upload your transfer receipt.", "error")
            return redirect(request.url)
        try:
            amount = float(request.form.get("amount") or application["properties"]["monthly_rent"])
            path = upload_file("receipts", f"applications/{application_id}", receipt, RECEIPT_EXT)
        except ValueError as exc:
            flash(str(exc) if "file type" in str(exc) else "Amount must be a number.", "error")
            return redirect(request.url)
        db.table("payments").insert({
            "application_id": application["id"],
            "amount": amount,
            "payment_method": "Bank Transfer",
            "bank_reference": request.form.get("bank_reference", "").strip(),
            "transfer_date": request.form.get("transfer_date") or None,
            "receipt_url": path,
            "status": "Pending Verification",
        }).execute()
        db.table("applications").update({"status": "Payment Submitted"}) \
            .eq("id", application["id"]).execute()
        return redirect(url_for("payment_confirmation", application_id=application_id))

    return render_template("payment.html", application=application, settings=settings)


@app.route("/application/<application_id>/confirmation")
def payment_confirmation(application_id):
    return render_template("payment_confirmation.html", reference=application_id)


@app.route("/tenant/dashboard")
@tenant_required
def tenant_dashboard(tenant):
    invoices = (db.table("rent_invoices").select("*").eq("tenant_id", tenant["id"])
                .order("rent_month", desc=True).execute()).data
    return render_template("tenant_dashboard.html", tenant=tenant, invoices=invoices)


@app.route("/tenant/property")
@tenant_required
def tenant_property(tenant):
    photos = (db.table("property_photos").select("*").eq("property_id", tenant["property_id"])
              .order("display_order").execute()).data if tenant.get("property_id") else []
    return render_template("tenant_property.html", tenant=tenant, photos=photos)


@app.route("/tenant/rent")
@tenant_required
def tenant_rent(tenant):
    invoices = (db.table("rent_invoices").select("*").eq("tenant_id", tenant["id"])
                .order("rent_month", desc=True).execute()).data
    return render_template("tenant_rent.html", tenant=tenant, invoices=invoices,
                           settings=get_company_settings())


@app.route("/tenant/invoice/<int:invoice_id>/pay", methods=["POST"])
@tenant_required
def tenant_pay_invoice(tenant, invoice_id):
    inv = (db.table("rent_invoices").select("*").eq("id", invoice_id)
           .eq("tenant_id", tenant["id"]).limit(1).execute()).data
    if not inv:
        abort(404)
    inv = inv[0]
    if inv["status"] not in ("Due", "Overdue", "Upcoming"):
        flash("This invoice is not waiting for payment.", "error")
        return redirect(url_for("tenant_rent"))
    receipt = request.files.get("receipt")
    if not receipt or not receipt.filename:
        flash("Please upload your transfer receipt.", "error")
        return redirect(url_for("tenant_rent"))
    try:
        amount = float(request.form.get("amount") or inv["amount"])
        path = upload_file("receipts", f"tenants/{tenant['id']}", receipt, RECEIPT_EXT)
    except ValueError as exc:
        flash(str(exc) if "file type" in str(exc) else "Amount must be a number.", "error")
        return redirect(url_for("tenant_rent"))
    db.table("payments").insert({
        "tenant_id": tenant["id"], "invoice_id": invoice_id, "amount": amount,
        "payment_method": "Bank Transfer",
        "bank_reference": request.form.get("bank_reference", "").strip(),
        "transfer_date": request.form.get("transfer_date") or None,
        "receipt_url": path, "status": "Pending Verification",
    }).execute()
    db.table("rent_invoices").update({"status": "Pending Verification"}).eq("id", invoice_id).execute()
    flash("Receipt submitted. The manager will verify your payment.", "success")
    return redirect(url_for("tenant_rent"))


@app.route("/tenant/payments")
@tenant_required
def tenant_payments(tenant):
    payments = (db.table("payments").select("*, rent_invoices(rent_month)")
                .eq("tenant_id", tenant["id"]).order("created_at", desc=True).execute()).data
    return render_template("tenant_payments.html", tenant=tenant, payments=payments)


@app.route("/receipt/<int:payment_id>")
def view_receipt(payment_id):
    role = session.get("role")
    if role not in ("manager", "tenant"):
        abort(403)
    pay = db.table("payments").select("*").eq("id", payment_id).limit(1).execute().data
    if not pay:
        abort(404)
    pay = pay[0]
    if not (role == "manager" or (pay.get("tenant_id") and pay["tenant_id"] == session.get("tenant_id"))):
        abort(403)
    path = pay.get("receipt_url")
    if not path:
        abort(404)
    if path.startswith("http"):
        return redirect(path)
    return redirect(signed_url("receipts", path))


@app.route("/tenant/password", methods=["GET", "POST"])
@tenant_required
def tenant_password(tenant):
    if request.method == "POST":
        current = request.form.get("current", "")
        new = request.form.get("password", "")
        try:
            auth_client().auth.sign_in_with_password({"email": session["email"], "password": current})
        except Exception:
            flash("Your current password is wrong.", "error")
            return redirect(url_for("tenant_password"))
        if len(new) < 8:
            flash("New password must be at least 8 characters.", "error")
        elif new != request.form.get("confirm", ""):
            flash("Passwords do not match.", "error")
        else:
            db.auth.admin.update_user_by_id(session["uid"], {"password": new})
            flash("Password changed.", "success")
            return redirect(url_for("tenant_dashboard"))
        return redirect(url_for("tenant_password"))
    return render_template("tenant_password.html", tenant=tenant)


@app.route("/tenant/complaint/new", methods=["GET", "POST"])
@tenant_required
def complaint_new(tenant):
    if request.method == "POST":
        ref = generate_reference("CMP")
        db.table("complaints").insert({
            "complaint_reference": ref,
            "tenant_id": tenant["id"],
            "property_id": tenant["property_id"],
            "category": request.form["category"],
            "priority": request.form.get("priority", "Normal"),
            "subject": request.form["subject"].strip(),
            "description": request.form["description"].strip(),
            "status": "Open",
        }).execute()
        return redirect(url_for("complaint_details", reference=ref))
    return render_template("complaint_new.html", tenant=tenant)


@app.route("/tenant/complaint/<reference>", methods=["GET", "POST"])
@tenant_required
def complaint_details(tenant, reference):
    res = (db.table("complaints").select("*").eq("complaint_reference", reference)
           .eq("tenant_id", tenant["id"]).limit(1).execute()).data
    if not res:
        abort(404)
    complaint = res[0]

    if request.method == "POST":
        if request.form.get("comment", "").strip():
            db.table("complaint_comments").insert({
                "complaint_id": complaint["id"], "author_name": tenant["full_name"],
                "author_role": "TENANT", "comment": request.form["comment"].strip(),
            }).execute()
        elif "resolution_check" in request.form:
            fixed = request.form["resolution_check"] == "fixed"
            db.table("complaints").update({
                "status": "Closed" if fixed else "Reopened",
                "closed_at": datetime.now().isoformat() if fixed else None,
            }).eq("id", complaint["id"]).execute()
        return redirect(url_for("complaint_details", reference=reference))

    comments = (db.table("complaint_comments").select("*").eq("complaint_id", complaint["id"])
                .order("created_at").execute()).data
    return render_template("complaint_details.html", tenant=tenant,
                           complaint=complaint, comments=comments)


OPEN_COMPLAINT = ["Open", "Assigned", "In Progress", "Reopened"]


@app.route("/manager/dashboard")
@role_required("manager")
def manager_dashboard():
    today = date.today()
    cur = (get_company_settings().get("currency") or "QAR")


    props = db.table("properties").select("status").eq("active", True).execute().data
    by_status = {}
    for p in props:
        by_status[p["status"]] = by_status.get(p["status"], 0) + 1
    total = len(props)
    seg = [("Occupied", by_status.get("Occupied", 0), "#2f5d50"),
           ("Reserved", by_status.get("Reserved", 0), "#d9a441"),
           ("Available", by_status.get("Available", 0), "#8fb7a6"),
           ("Maintenance / other", total - sum(by_status.get(k, 0) for k in ("Occupied", "Reserved", "Available")), "#c9ced6")]
    stops, acc = [], 0.0
    for _, n, color in seg:
        if n and total:
            stops.append(f"{color} {acc:.2f}% {acc + 100 * n / total:.2f}%")
            acc += 100 * n / total
    donut = "conic-gradient(" + ", ".join(stops) + ")" if stops else "conic-gradient(#e5e9ef 0 100%)"
    occupancy = round(100 * by_status.get("Occupied", 0) / total) if total else 0


    first = add_months(today.replace(day=1), -5)
    paid = (db.table("payments").select("amount, verified_at").eq("status", "Paid")
            .gte("verified_at", first.isoformat()).execute()).data
    sums = {}
    for p in paid:
        sums[p["verified_at"][:7]] = sums.get(p["verified_at"][:7], 0) + float(p["amount"])
    months = []
    for i in range(6):
        m = add_months(first, i)
        months.append({"label": m.strftime("%b"), "amount": sums.get(m.strftime("%Y-%m"), 0)})
    top = max([m["amount"] for m in months] + [1])
    for m in months:
        m["pct"] = max(4, round(100 * m["amount"] / top)) if m["amount"] else 0
    collected = months[-1]["amount"]
    last_month = months[-2]["amount"]
    change = round(100 * (collected - last_month) / last_month) if last_month else None

    inv = (db.table("rent_invoices").select("amount, status, due_date")
           .in_("status", ["Due", "Overdue", "Upcoming", "Pending Verification"]).execute()).data
    outstanding = sum(float(i["amount"]) for i in inv if i["status"] in ("Due", "Overdue"))
    overdue = [i for i in inv if i["status"] in ("Due", "Overdue") and i["due_date"] < today.isoformat()]


    pending = (db.table("payments")
               .select("*, applications(full_name, application_reference, properties(unit_number)), tenants(full_name, properties(unit_number))")
               .eq("status", "Pending Verification").order("created_at", desc=True).limit(5).execute()).data
    pending_total = (db.table("payments").select("id", count="exact")
                     .eq("status", "Pending Verification").execute().count) or 0
    complaints = (db.table("complaints").select("*, tenants(full_name), properties(unit_number)")
                  .in_("status", OPEN_COMPLAINT).order("created_at", desc=True).limit(40).execute()).data
    rank = {"Emergency": 0, "Urgent": 1, "High": 2, "Normal": 3, "Low": 4}
    complaints.sort(key=lambda c: rank.get(c.get("priority"), 3))
    urgent = sum(1 for c in complaints if c.get("priority") in ("Urgent", "Emergency"))
    apps = (db.table("applications").select("*, properties(unit_number, property_type)")
            .order("created_at", desc=True).limit(5).execute()).data
    new_apps = (db.table("applications").select("id", count="exact")
                .in_("status", ["Pending", "Payment Submitted"]).execute().count) or 0
    ending = (db.table("tenants").select("id, full_name, contract_end, properties(unit_number)")
              .eq("status", "Active").gte("contract_end", today.isoformat())
              .lte("contract_end", (today + timedelta(days=45)).isoformat())
              .order("contract_end").limit(5).execute()).data
    for t in ending:
        t["days_left"] = (date.fromisoformat(t["contract_end"]) - today).days
    tenants = (db.table("tenants").select("id", count="exact").eq("status", "Active").execute().count) or 0

    hour = datetime.now().hour
    greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 18 else "Good evening"
    return render_template(
        "manager_dashboard.html", greeting=greeting, today=today, currency=cur,
        total=total, by_status=by_status, seg=seg, donut=donut, occupancy=occupancy,
        months=months, collected=collected, change=change,
        outstanding=outstanding, overdue_count=len(overdue),
        pending=pending, pending_total=pending_total, complaints=complaints[:5],
        open_total=len(complaints), urgent=urgent, apps=apps, new_apps=new_apps,
        ending=ending, tenants=tenants)


@app.route("/manager/properties")
@role_required("manager")
def manager_properties():
    props = (db.table("properties").select("*, buildings(*)").eq("active", True)
             .order("created_at", desc=True).execute()).data
    return render_template("manager_properties.html", properties=attach_photos(props))


@app.route("/manager/property/new", methods=["GET", "POST"])
@role_required("manager")
def manager_property_new():
    buildings = db.table("buildings").select("*").eq("active", True).order("building_name").execute().data
    if request.method == "POST":
        f = request.form
        building_id = f.get("building_id")
        if building_id == "new":
            name = f.get("new_building_name", "").strip()
            if not name:
                flash("Enter the new building name.", "error")
                return render_template("manager_property_new.html", buildings=buildings, form=f)
            b = db.table("buildings").insert({
                "building_name": name, "address": f.get("new_building_address", "").strip(),
                "city": f.get("new_building_city", "").strip()}).execute().data[0]
            building_id = b["id"]
        try:
            row = db.table("properties").insert({
                "building_id": int(building_id), "unit_number": f["unit_number"].strip(),
                "property_type": f["property_type"], "bedrooms": int(f.get("bedrooms") or 0),
                "bathrooms": int(f.get("bathrooms") or 1), "monthly_rent": float(f["monthly_rent"]),
                "security_deposit": float(f.get("security_deposit") or 0),
                "maximum_occupants": int(f.get("maximum_occupants") or 1),
                "description": f.get("description", "").strip(), "status": "Available",
            }).execute().data[0]
        except (ValueError, KeyError, TypeError):
            flash("Please check the numbers you entered.", "error")
            return render_template("manager_property_new.html", buildings=buildings, form=f)
        except Exception:
            flash("Could not save: this unit number may already exist in that building.", "error")
            return render_template("manager_property_new.html", buildings=buildings, form=f)
        flash("Property created. Now add its photos.", "success")
        return redirect(url_for("manager_property_edit", property_id=row["id"]))
    return render_template("manager_property_new.html", buildings=buildings, form={})


def storage_path_from_url(url):
    marker = "/property-images/"
    if url and "/storage/" in url and marker in url:
        return url.split(marker, 1)[1].split("?")[0]
    return None


@app.route("/manager/property/<int:property_id>/edit", methods=["GET", "POST"])
@role_required("manager")
def manager_property_edit(property_id):
    prop = get_property_or_404(property_id)

    if request.method == "POST":
        action = request.form.get("action", "details")
        back = redirect(url_for("manager_property_edit", property_id=property_id))

        if action == "upload":
            files = [f for f in request.files.getlist("photos") if f and f.filename]
            if not files:
                flash("Choose at least one photo.", "error")
                return back
            existing = db.table("property_photos").select("id, display_order") \
                .eq("property_id", property_id).execute().data
            next_order = max([r["display_order"] or 0 for r in existing], default=-1) + 1
            make_main = request.form.get("is_main") == "on" or not existing
            caption = request.form.get("caption", "").strip()
            done = 0
            for f in files:
                try:
                    path = upload_file("property-images", f"property-{property_id}", f, IMAGE_EXT)
                except ValueError as exc:
                    flash(f"{f.filename}: {exc}", "error")
                    continue
                is_main = make_main and done == 0
                if is_main:
                    db.table("property_photos").update({"is_main": False}) \
                        .eq("property_id", property_id).execute()
                db.table("property_photos").insert({
                    "property_id": property_id, "image_url": public_url("property-images", path),
                    "caption": caption or f.filename.rsplit(".", 1)[0],
                    "is_main": is_main, "display_order": next_order + done}).execute()
                done += 1
            if done:
                flash(f"{done} photo(s) uploaded.", "success")
            return back

        if action == "set_main":
            pid = int(request.form["photo_id"])
            db.table("property_photos").update({"is_main": False}).eq("property_id", property_id).execute()
            db.table("property_photos").update({"is_main": True, "display_order": -1}) \
                .eq("id", pid).eq("property_id", property_id).execute()
            flash("Main photo updated.", "success")
            return back

        if action == "caption":
            db.table("property_photos").update({"caption": request.form.get("caption", "").strip()}) \
                .eq("id", int(request.form["photo_id"])).eq("property_id", property_id).execute()
            flash("Caption saved.", "success")
            return back

        if action == "delete_photo":
            pid = int(request.form["photo_id"])
            row = db.table("property_photos").select("*").eq("id", pid) \
                .eq("property_id", property_id).limit(1).execute().data
            if row:
                path = storage_path_from_url(row[0]["image_url"])
                if path:
                    try:
                        db.storage.from_("property-images").remove([path])
                    except Exception:
                        pass
                db.table("property_photos").delete().eq("id", pid).execute()
                if row[0]["is_main"]:
                    left = db.table("property_photos").select("id").eq("property_id", property_id) \
                        .order("display_order").limit(1).execute().data
                    if left:
                        db.table("property_photos").update({"is_main": True}).eq("id", left[0]["id"]).execute()
                flash("Photo deleted.", "success")
            return back


        try:
            db.table("properties").update({
                "monthly_rent": float(request.form["monthly_rent"]),
                "security_deposit": float(request.form.get("security_deposit") or 0),
                "status": request.form["status"],
                "description": request.form.get("description", "").strip(),
                "maximum_occupants": int(request.form.get("maximum_occupants") or 1),
            }).eq("id", property_id).execute()
            flash("Property saved.", "success")
        except ValueError:
            flash("Please check the numbers you entered.", "error")
        return back

    photos = (db.table("property_photos").select("*").eq("property_id", property_id)
              .order("display_order").execute()).data
    return render_template("manager_property_edit.html", property=prop, photos=photos)


@app.route("/manager/tenants", methods=["GET", "POST"])
@role_required("manager")
def manager_tenants():
    if request.method == "POST":
        f = request.form
        try:
            prop = get_property_or_404(int(f["property_id"]))
            start = date.fromisoformat(f["contract_start"])
            months = int(f.get("months") or 12)
            rent = float(f.get("monthly_rent") or prop["monthly_rent"])
            row = db.table("tenants").insert({
                "full_name": f["full_name"].strip(), "email": clean_email(f["email"]),
                "phone": f.get("phone", "").strip(), "property_id": prop["id"],
                "contract_start": start.isoformat(),
                "contract_end": (add_months(start, months) - timedelta(days=1)).isoformat(),
                "monthly_rent": rent, "status": "Active"}).execute().data[0]
            db.table("properties").update({"status": "Occupied"}).eq("id", prop["id"]).execute()
            pw, emailed = provision_tenant_account(row)
            msg, cat = credentials_notice(row, pw, emailed)
            flash("Tenant added. " + msg, cat)
        except (ValueError, KeyError):
            flash("Please check the form values.", "error")
        except Exception:
            flash("Could not save: this email may already belong to a tenant.", "error")
        return redirect(url_for("manager_tenants"))

    tenants = (db.table("tenants").select("*, properties(*, buildings(*))")
               .order("created_at", desc=True).execute()).data
    free = (db.table("properties").select("id, unit_number, monthly_rent, property_type")
            .in_("status", ["Available", "Reserved"]).eq("active", True).execute()).data
    return render_template("manager_tenants.html", tenants=tenants, free_properties=free,
                           today=date.today().isoformat(),
                           this_month=date.today().strftime("%Y-%m"))


@app.route("/manager/tenant/<int:tenant_id>/invoice", methods=["POST"])
@role_required("manager")
def manager_generate_invoice(tenant_id):
    t = db.table("tenants").select("*").eq("id", tenant_id).limit(1).execute().data
    if not t:
        abort(404)
    t = t[0]
    try:
        y, m = request.form["month"].split("-")
        month = date(int(y), int(m), 1)
    except (ValueError, KeyError):
        flash("Choose a valid month.", "error")
        return redirect(url_for("manager_tenants"))
    exists = db.table("rent_invoices").select("id").eq("tenant_id", tenant_id) \
        .eq("rent_month", month.isoformat()).execute().data
    if exists:
        flash("An invoice for that month already exists.", "error")
    else:
        db.table("rent_invoices").insert({
            "tenant_id": tenant_id, "property_id": t["property_id"],
            "rent_month": month.isoformat(), "due_date": month.isoformat(),
            "amount": t["monthly_rent"], "status": "Due"}).execute()
        flash(f"Invoice for {month.strftime('%B %Y')} created.", "success")
    return redirect(url_for("manager_tenants"))


@app.route("/manager/tenant/<int:tenant_id>/credentials", methods=["POST"])
@role_required("manager")
def manager_tenant_credentials(tenant_id):
    t = db.table("tenants").select("*").eq("id", tenant_id).limit(1).execute().data
    if not t:
        abort(404)
    try:
        pw, emailed = provision_tenant_account(t[0], reset=True)
        msg, cat = credentials_notice(t[0], pw, emailed)
        flash(msg, cat)
    except Exception as exc:
        app.logger.error("credentials failed: %s", exc)
        flash("Could not create the account: " + str(exc), "error")
    return redirect(url_for("manager_tenants"))


@app.route("/manager/payments")
@role_required("manager")
def manager_payments():
    pending = (db.table("payments")
               .select("*, applications(*, properties(*)), tenants(*, properties(*))")
               .eq("status", "Pending Verification").order("created_at", desc=True).execute()).data
    return render_template("manager_payments.html", payments=pending)


@app.route("/manager/payment/<int:payment_id>/verify", methods=["POST"])
@role_required("manager")
def manager_payment_verify(payment_id):
    confirm = request.form.get("action") == "confirm"
    now = datetime.now().isoformat()

    upd = db.table("payments").update({
        "status": "Paid" if confirm else "Rejected", "verified_at": now,
        "verified_by": session.get("name", "Manager")}) \
        .eq("id", payment_id).eq("status", "Pending Verification").execute()
    if not upd.data:
        flash("This payment was already processed.", "error")
        return redirect(url_for("manager_payments"))
    pay = upd.data[0]

    if pay.get("application_id"):
        a = db.table("applications").select("*, properties(*)") \
            .eq("id", pay["application_id"]).limit(1).execute().data[0]
        if confirm:
            db.table("applications").update({"status": "Approved"}).eq("id", a["id"]).execute()
            db.table("properties").update({"status": "Reserved"}).eq("id", a["property_id"]).execute()

            tenant = db.table("tenants").select("*").eq("email", a["email"]).limit(1).execute().data
            if tenant:
                tenant = tenant[0]
            else:
                start = date.fromisoformat(a["requested_move_in"]) if a.get("requested_move_in") else date.today()
                tenant = db.table("tenants").insert({
                    "full_name": a["full_name"], "email": a["email"], "phone": a["phone"],
                    "property_id": a["property_id"], "contract_start": start.isoformat(),
                    "contract_end": (add_months(start, a.get("rental_months") or 12) - timedelta(days=1)).isoformat(),
                    "monthly_rent": a["properties"]["monthly_rent"], "status": "Active"}).execute().data[0]
            flash("Payment confirmed. Booking approved.", "success")
            try:
                pw, emailed = provision_tenant_account(tenant)
                if pw:
                    msg, cat = credentials_notice(tenant, pw, emailed)
                    flash(msg, cat)
            except Exception as exc:
                app.logger.error("tenant account failed: %s", exc)
                flash("Booking approved, but the tenant account could not be created. "
                      "Open Tenants and press 'Send login details'.", "error")
        else:
            db.table("applications").update({"status": "Payment Rejected"}).eq("id", a["id"]).execute()
            flash("Payment rejected. The customer can submit a new receipt.", "success")

    if pay.get("invoice_id"):
        if confirm:
            db.table("rent_invoices").update({"status": "Paid", "paid_at": now}) \
                .eq("id", pay["invoice_id"]).execute()
            flash("Rent payment confirmed.", "success")
        else:
            db.table("rent_invoices").update({"status": "Due"}).eq("id", pay["invoice_id"]).execute()
            flash("Payment rejected. The invoice is open again.", "success")
    return redirect(url_for("manager_payments"))


@app.route("/manager/complaints")
@role_required("manager")
def manager_complaints():
    complaints = (db.table("complaints").select("*, tenants(*), properties(*)")
                  .order("created_at", desc=True).execute()).data
    return render_template("manager_complaints.html", complaints=complaints)


@app.route("/manager/complaint/<reference>", methods=["GET", "POST"])
@role_required("manager")
def manager_complaint_details(reference):
    res = (db.table("complaints").select("*, tenants(*), properties(*)")
           .eq("complaint_reference", reference).limit(1).execute()).data
    if not res:
        abort(404)
    complaint = res[0]
    if request.method == "POST":
        if request.form.get("comment", "").strip():
            db.table("complaint_comments").insert({
                "complaint_id": complaint["id"], "author_name": session.get("name", "Manager"),
                "author_role": "MANAGER", "comment": request.form["comment"].strip()}).execute()
        else:
            status = request.form["status"]
            patch = {"status": status, "assigned_to": request.form.get("assigned_to", ""),
                     "resolution": request.form.get("resolution", "")}
            if status.startswith("Resolved"):
                patch["resolved_at"] = datetime.now().isoformat()
            db.table("complaints").update(patch).eq("id", complaint["id"]).execute()
        return redirect(url_for("manager_complaint_details", reference=reference))
    comments = (db.table("complaint_comments").select("*").eq("complaint_id", complaint["id"])
                .order("created_at").execute()).data
    return render_template("manager_complaint_details.html", complaint=complaint, comments=comments)


@app.template_filter("rent_month")
def rent_month(value):
    if not value:
        return ""
    try:
        d = datetime.strptime(value[:10], "%Y-%m-%d") if isinstance(value, str) else value
        return d.strftime("%B %Y")
    except Exception:
        return str(value)[:7]


@app.template_filter("img")
def img(url, width=800):
    if url and "images.unsplash.com" in url:
        if re.search(r"[?&]w=\d+", url):
            return re.sub(r"([?&])w=\d+", lambda m: f"{m.group(1)}w={int(width)}", url)
        return url + ("&" if "?" in url else "?") + f"w={int(width)}"
    return url


@app.template_filter("money")
def money(value):
    try:
        return "{:,.0f}".format(float(value or 0))
    except (TypeError, ValueError):
        return "0"


ensure_manager()

if __name__ == "__main__":
    app.run(debug=True)
