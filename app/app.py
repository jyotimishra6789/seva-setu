# -*- coding: utf-8 -*-
"""
Sewa Setu - Old Age Pension Portal
Government of Purvanchal, Department of Social Welfare

Developed by: Netlink Infosolutions Pvt Ltd (2023)
Maintenance contract ended 31/01/2026.
"""

import os
import io
import csv
import random
import hashlib
import hmac
import configparser
import secrets
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

import requests
import psycopg2
from psycopg2 import pool
from flask import (Flask, request, session, redirect, url_for, render_template,
                   flash, send_file, abort, jsonify)
from werkzeug.utils import secure_filename
from fpdf import FPDF

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

config = configparser.ConfigParser()
config.read(os.path.join(BASE_DIR, "config", "app.ini"))

app = Flask(__name__)
app.secret_key = os.environ.get("SEWASETU_SECRET_KEY", config.get("app", "secret_key"))
app.config["PERMANENT_SESSION_LIFETIME"] = 300

LANGUAGES = {
    "en": {"name": "English", "speech": "en-IN"},
    "hi": {"name": "हिन्दी", "speech": "hi-IN"},
    "as": {"name": "অসমীয়া", "speech": "as-IN"},
    "bn": {"name": "বাংলা", "speech": "bn-IN"},
}

TRANSLATIONS = {
    "en": {"title": "Sewa Setu - Old Age Pension Portal",
           "department": "Department of Social Welfare · Government of Purvanchal",
           "help": "Need help? This pension service is free. Do not pay an agent or share your OTP.",
           "choose_language": "Choose your language",
           "language_help": "You can change this later. You do not need to pay anyone to apply.",
           "continue": "Continue", "change_language": "Change language",
           "read_aloud": "Read this page aloud", "home": "Home",
           "welcome": "Welcome", "apply": "Apply for Pension",
           "scheme": "The Old Age Pension Scheme provides a monthly pension of Rs. 250 to eligible senior citizens aged 60 years or older who are residents of Purvanchal.",
           "free_help_detail": "If you are applying for the first time, a government help desk at your Block Development Office will assist you free of charge. Ask for a receipt and keep your application number.",
           "window": "Application window closes in approximately", "closed": "The application window for this scheme has closed.",
           "steps": ["Enter your mobile number and the one-time code sent to you.", "Enter your name exactly as it appears on your age proof.", "Enter your address and bank account details. You can correct a pending application.", "Upload an age proof document (JPG or PDF, maximum 5 MB).", "Read the final page, submit, and save or print the acknowledgment number."],
           "safety": "Never share your OTP or bank PIN. The department will never charge a fee to submit this application.",
           "free_assistance": "For free assistance, visit your nearest Block Development Office or use",
           "hours_suffix": "hours (midnight, 31 October).", "service_footer": "Government citizen service",
           "about": "About the Scheme", "rti": "RTI", "grievance": "Grievance Cell", "contact": "Contact Us",
           "status": "Check Application Status", "free_help": "You do not need to pay anyone to apply.",
           "how_to_apply": "How to apply", "apply_help": "For free help, visit your nearest Block Development Office.",
           "mobile_verification": "Mobile Verification", "send_otp": "Send OTP"},
    "hi": {"title": "सेवा सेतु - वृद्धावस्था पेंशन पोर्टल",
           "department": "समाज कल्याण विभाग · पूर्वांचल सरकार",
           "help": "मदद चाहिए? यह पेंशन सेवा निःशुल्क है। किसी एजेंट को पैसे न दें और OTP साझा न करें।",
           "choose_language": "अपनी भाषा चुनें",
           "language_help": "आप बाद में भाषा बदल सकते हैं। आवेदन करने के लिए किसी को पैसे न दें।",
           "continue": "आगे बढ़ें", "change_language": "भाषा बदलें",
           "read_aloud": "यह पृष्ठ सुनें", "home": "मुख्य पृष्ठ",
           "welcome": "स्वागत है", "apply": "पेंशन के लिए आवेदन करें",
           "scheme": "वृद्धावस्था पेंशन योजना पूर्वांचल के 60 वर्ष या उससे अधिक आयु के पात्र वरिष्ठ नागरिकों को हर महीने 250 रुपये देती है।",
           "free_help_detail": "पहली बार आवेदन करने पर प्रखंड विकास कार्यालय का सरकारी सहायता केंद्र निःशुल्क मदद करेगा। रसीद लें और आवेदन संख्या सुरक्षित रखें।",
           "window": "आवेदन की अंतिम समय-सीमा लगभग", "closed": "इस योजना के लिए आवेदन की समय-सीमा समाप्त हो गई है।",
           "steps": ["अपना मोबाइल नंबर और भेजा गया एक बार का कोड दर्ज करें।", "उम्र के प्रमाण-पत्र पर लिखे नाम के अनुसार अपना नाम दर्ज करें।", "पता और बैंक खाते की जानकारी दर्ज करें। लंबित आवेदन में सुधार किया जा सकता है।", "उम्र का प्रमाण-पत्र अपलोड करें (JPG या PDF, अधिकतम 5 MB)।", "अंतिम पृष्ठ पढ़कर आवेदन जमा करें और पावती संख्या सुरक्षित रखें।"],
           "safety": "अपना OTP या बैंक PIN कभी साझा न करें। आवेदन जमा करने के लिए विभाग कोई शुल्क नहीं लेता।",
           "free_assistance": "निःशुल्क सहायता के लिए निकटतम प्रखंड विकास कार्यालय जाएँ या यहाँ जाएँ:",
           "hours_suffix": "घंटे (31 अक्टूबर की मध्यरात्रि)।", "service_footer": "सरकारी नागरिक सेवा",
           "about": "योजना के बारे में", "rti": "सूचना का अधिकार", "grievance": "शिकायत केंद्र", "contact": "संपर्क करें",
           "status": "आवेदन की स्थिति देखें", "free_help": "आवेदन करने के लिए किसी को पैसे देने की जरूरत नहीं है।",
           "how_to_apply": "आवेदन कैसे करें", "apply_help": "निःशुल्क सहायता के लिए निकटतम प्रखंड विकास कार्यालय जाएँ।",
           "mobile_verification": "मोबाइल सत्यापन", "send_otp": "OTP भेजें"},
    "as": {"title": "সেৱা সেতু - বৃদ্ধ পেঞ্চন প'ৰ্টেল",
           "department": "সমাজ কল্যাণ বিভাগ · পূৰ্বাঞ্চল চৰকাৰ",
           "help": "সহায়ৰ প্ৰয়োজন? এই পেঞ্চন সেৱা বিনামূলীয়া। কোনো এজেণ্টক টকা নিদিব আৰু OTP নিদিব।",
           "choose_language": "আপোনাৰ ভাষা বাছনি কৰক",
           "language_help": "আপুনি পিছত ভাষা সলনি কৰিব পাৰে। আবেদন কৰিবলৈ কাকো টকা নিদিব।",
           "continue": "আগবাঢ়ক", "change_language": "ভাষা সলনি কৰক",
           "read_aloud": "এই পৃষ্ঠা শুনক", "home": "মুখ্য পৃষ্ঠা",
           "welcome": "স্বাগতম", "apply": "পেঞ্চনৰ বাবে আবেদন কৰক",
           "scheme": "বৃদ্ধ পেঞ্চন আঁচনিয়ে পূৰ্বাঞ্চলৰ ৬০ বছৰ বা তাতকৈ অধিক বয়সৰ যোগ্য জ্যেষ্ঠ নাগৰিকক প্ৰতিমাহে ২৫০ টকা দিয়ে।",
           "free_help_detail": "প্ৰথমবাৰ আবেদন কৰিলে খণ্ড উন্নয়ন কাৰ্যালয়ৰ চৰকাৰী সহায় কেন্দ্ৰই বিনামূলীয়াকৈ সহায় কৰিব। ৰচিদ লওক আৰু আবেদন নম্বৰ ৰাখক।",
           "window": "আবেদনৰ সময়সীমা প্ৰায়", "closed": "এই আঁচনিৰ আবেদনৰ সময়সীমা শেষ হৈছে।",
           "steps": ["আপোনাৰ ম'বাইল নম্বৰ আৰু পঠোৱা এবাৰ ব্যৱহাৰযোগ্য ক'ড দিয়ক।", "বয়সৰ প্ৰমাণপত্ৰত থকা মতে আপোনাৰ নাম দিয়ক।", "ঠিকনা আৰু বেংক একাউণ্টৰ তথ্য দিয়ক। অপেক্ষাৰত আবেদন শুধৰাব পাৰি।", "বয়সৰ প্ৰমাণপত্ৰ আপলোড কৰক (JPG বা PDF, সৰ্বাধিক ৫ MB)।", "শেষ পৃষ্ঠা পঢ়ি আবেদন জমা দিয়ক আৰু স্বীকৃতি নম্বৰ ৰাখক।"],
           "safety": "আপোনাৰ OTP বা বেংক PIN কেতিয়াও নিদিব। আবেদন জমা দিবলৈ বিভাগে কোনো মাচুল নলয়।",
           "free_assistance": "বিনামূলীয়া সহায়ৰ বাবে ওচৰৰ খণ্ড উন্নয়ন কাৰ্যালয়লৈ যাওক বা ইয়াত যাওক:",
           "hours_suffix": "ঘণ্টা (৩১ অক্টোবৰৰ মাজনিশা)।", "service_footer": "চৰকাৰী নাগৰিক সেৱা",
           "about": "আঁচনিৰ বিষয়ে", "rti": "তথ্যৰ অধিকাৰ", "grievance": "অভিযোগ কোষ", "contact": "যোগাযোগ",
           "status": "আবেদনৰ স্থিতি চাওক", "free_help": "আবেদন কৰিবলৈ কাকো টকা দিয়াৰ প্ৰয়োজন নাই।",
           "how_to_apply": "আবেদন কৰাৰ পদ্ধতি", "apply_help": "বিনামূলীয়া সহায়ৰ বাবে ওচৰৰ খণ্ড উন্নয়ন কাৰ্যালয়লৈ যাওক।",
           "mobile_verification": "ম'বাইল পৰীক্ষণ", "send_otp": "OTP পঠিয়াওক"},
    "bn": {"title": "সেবা সেতু - বার্ধক্য পেনশন পোর্টাল",
           "department": "সমাজকল্যাণ বিভাগ · পূর্বাঞ্চল সরকার",
           "help": "সাহায্য দরকার? এই পেনশন পরিষেবা বিনামূল্যে। কাউকে টাকা দেবেন না এবং OTP শেয়ার করবেন না।",
           "choose_language": "আপনার ভাষা বেছে নিন",
           "language_help": "আপনি পরে ভাষা বদলাতে পারবেন। আবেদন করতে কাউকে টাকা দেবেন না।",
           "continue": "এগিয়ে যান", "change_language": "ভাষা বদলান",
           "read_aloud": "এই পৃষ্ঠা পড়ে শোনান", "home": "হোম",
           "welcome": "স্বাগতম", "apply": "পেনশনের জন্য আবেদন করুন",
           "scheme": "বার্ধক্য পেনশন প্রকল্প পূর্বাঞ্চলের ৬০ বছর বা তার বেশি বয়সী যোগ্য প্রবীণ নাগরিকদের প্রতি মাসে ২৫০ টাকা দেয়।",
           "free_help_detail": "প্রথমবার আবেদন করলে ব্লক উন্নয়ন দপ্তরের সরকারি সহায়তা কেন্দ্র বিনামূল্যে সাহায্য করবে। রসিদ নিন এবং আবেদন নম্বর রাখুন।",
           "window": "আবেদনের সময়সীমা প্রায়", "closed": "এই প্রকল্পের আবেদনের সময়সীমা শেষ হয়েছে।",
           "steps": ["আপনার মোবাইল নম্বর এবং পাঠানো একবারের কোড দিন।", "বয়সের প্রমাণপত্রে যেমন আছে তেমন নাম লিখুন।", "ঠিকানা ও ব্যাঙ্ক অ্যাকাউন্টের তথ্য দিন। অপেক্ষমাণ আবেদন সংশোধন করা যায়।", "বয়সের প্রমাণপত্র আপলোড করুন (JPG বা PDF, সর্বোচ্চ ৫ MB)।", "শেষ পৃষ্ঠা পড়ে আবেদন জমা দিন এবং স্বীকৃতি নম্বর রাখুন।"],
           "safety": "আপনার OTP বা ব্যাঙ্ক PIN কখনও শেয়ার করবেন না। আবেদন জমা দিতে বিভাগ কোনও টাকা নেয় না।",
           "free_assistance": "বিনামূল্যে সাহায্যের জন্য নিকটবর্তী ব্লক উন্নয়ন দপ্তরে যান অথবা এখানে যান:",
           "hours_suffix": "ঘণ্টা (৩১ অক্টোবর মধ্যরাতে)।", "service_footer": "সরকারি নাগরিক পরিষেবা",
           "about": "প্রকল্প সম্পর্কে", "rti": "তথ্যের অধিকার", "grievance": "অভিযোগ কেন্দ্র", "contact": "যোগাযোগ",
           "status": "আবেদনের অবস্থা দেখুন", "free_help": "আবেদন করতে কাউকে টাকা দেওয়ার দরকার নেই।",
           "how_to_apply": "আবেদন করার পদ্ধতি", "apply_help": "বিনামূল্যে সাহায্যের জন্য নিকটবর্তী ব্লক উন্নয়ন দপ্তরে যান।",
           "mobile_verification": "মোবাইল যাচাই", "send_otp": "OTP পাঠান"},
}


@app.context_processor
def language_context():
    language = session.get("language", "en")
    return {"language": language, "language_info": LANGUAGES[language],
            "t": TRANSLATIONS[language]}

ADMIN_USERNAME = os.environ.get("SEWASETU_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("SEWASETU_ADMIN_PASSWORD",
                                 config.get("app", "admin_password"))

SMS_GATEWAY_URL = config.get("app", "sms_gateway_url")
OTP_VALIDITY_SECONDS = config.getint("app", "otp_validity_seconds")
UPLOAD_DIR = config.get("app", "upload_dir")
IST = ZoneInfo("Asia/Kolkata")
SCHEME_DEADLINE = datetime.strptime(config.get("pension", "scheme_deadline"),
                                    "%Y-%m-%d %H:%M").replace(tzinfo=IST)
MIN_AGE = config.getint("pension", "min_age")
SLA_DAYS = config.getint("pension", "sla_days")

BLOCKS = ["Sonari", "Rajapara", "Dhemaji Pathar", "Borgaon", "Namti", "Khelua"]
DB_POOL = None


def now_ist():
    return datetime.now(IST).replace(tzinfo=None)

import logging
_logdir = "/var/log/sewasetu"
try:
    os.makedirs(_logdir, exist_ok=True)
    _fh = logging.FileHandler(os.path.join(_logdir, "sewasetu-app.log"))
    _fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s in app: %(message)s"))
    app.logger.addHandler(_fh)
    app.logger.setLevel(logging.INFO)
except Exception:
    pass


def get_db():
    global DB_POOL
    if DB_POOL is None:
        DB_POOL = pool.ThreadedConnectionPool(
            1,
            int(os.environ.get("SEWASETU_DB_POOL_MAX", "12")),
            host=config.get("database", "host"),
            port=config.get("database", "port"),
            dbname=config.get("database", "name"),
            user=config.get("database", "user"),
            password=config.get("database", "password"),
        )
    return PooledConnection(DB_POOL, DB_POOL.getconn())


class PooledConnection:
    def __init__(self, connection_pool, connection):
        self._pool = connection_pool
        self._connection = connection
        self._returned = False

    def __getattr__(self, name):
        return getattr(self._connection, name)

    def close(self):
        if not self._returned:
            self._connection.rollback()
            self._pool.putconn(self._connection)
            self._returned = True

def sanitize(value, maxlen=100):
    # Limit by characters, never UTF-8 bytes, so Indic names remain intact.
    if value is None:
        return ""
    return value.strip()[:maxlen]


def hash_password(p):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", p.encode("utf-8"), salt, 310000)
    return "pbkdf2_sha256$310000$%s$%s" % (
        salt.hex(), digest.hex())


def verify_password(stored, supplied):
    if stored.startswith("pbkdf2_sha256$"):
        _, iterations, salt_hex, digest_hex = stored.split("$", 3)
        digest = hashlib.pbkdf2_hmac(
            "sha256", supplied.encode("utf-8"), bytes.fromhex(salt_hex),
            int(iterations))
        return hmac.compare_digest(digest.hex(), digest_hex)
    return hmac.compare_digest(stored, hashlib.sha256(
        supplied.encode("utf-8")).hexdigest())


def send_sms(mobile, text):
    try:
        requests.post(SMS_GATEWAY_URL + "/api/send",
                      json={"to": mobile, "text": text}, timeout=5)
    except Exception as e:
        app.logger.error("sms gateway error: %s" % e)


def deadline_remaining():
    delta = SCHEME_DEADLINE - datetime.now(IST)
    if delta.total_seconds() <= 0:
        return None
    return int(delta.total_seconds() // 3600)


def new_application_no():
    return "SSP" + datetime.now(IST).strftime("%y") + secrets.token_hex(3).upper()


def is_admin():
    return session.get("admin") is True


def citizen_owns_application(app_id):
    return (session.get("logged_in") is True and not is_admin()
            and session.get("portal_application_id") == app_id)


# ---------------------------------------------------------------------------
# Public pages
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    if "language" not in session:
        return redirect(url_for("choose_language"))
    return render_template("index.html", hours_left=deadline_remaining())


@app.route("/language", methods=["GET", "POST"])
def choose_language():
    if request.method == "POST":
        language = request.form.get("language", "")
        if language not in LANGUAGES:
            abort(400)
        session["language"] = language
        return redirect(url_for("index"))
    return render_template("language.html", languages=LANGUAGES)


@app.route("/about")
def about():
    return render_template("about.html")


def public_info_page(title, body):
    return render_template("info.html", title=title, body=body)


@app.route("/rti")
def rti():
    return public_info_page(
        "Right to Information",
        "For RTI requests, contact the District Social Welfare Officer at your "
        "Block Development Office. Keep your application number with your request.",
    )


@app.route("/grievance")
def grievance():
    return public_info_page(
        "Grievance Cell",
        "For help with an application, visit your Block Development Office or "
        "contact the Social Welfare help desk with your application number.",
    )


@app.route("/contact")
def contact():
    return public_info_page(
        "Contact Us",
        "Department of Social Welfare, Sonapur District. Office hours are "
        "Monday to Friday, 10:00 to 17:00 IST.",
    )


@app.route("/__gateway/", defaults={"subpath": ""})
@app.route("/__gateway/<path:subpath>")
def gateway_proxy(subpath):
    # Convenience proxy to the internal SMS gateway, so the OTP inbox is reachable
    # on the main site without opening a second port on the host. The gateway
    # itself runs only on the internal network.
    if subpath:
        abort(404)
    try:
        r = requests.get(SMS_GATEWAY_URL + "/" + subpath,
                         params=request.args, timeout=5)
        return (r.content, r.status_code,
                {"Content-Type": r.headers.get("Content-Type", "text/html")})
    except Exception as e:
        return ("SMS gateway unreachable: %s" % e, 502)


# ---------------------------------------------------------------------------
# Application flow: mobile -> OTP -> form steps -> upload -> declaration
# ---------------------------------------------------------------------------

@app.route("/apply", methods=["GET", "POST"])
def apply():
    if deadline_remaining() is None:
        flash("The application window for this scheme has closed.")
        return redirect(url_for("index"))
    if request.method == "POST":
        mobile = request.form.get("mobile", "").strip()
        captcha = request.form.get("captcha", "").strip()
        if len(mobile) != 10 or not mobile.isdigit():
            flash("Something went wrong. Please try again.")
            return render_template("apply.html", captcha_q=make_captcha())
        if captcha != str(session.pop("captcha_answer", "")):
            flash("Please solve the security check correctly.")
            return render_template("apply.html", captcha_q=make_captcha())
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM otps WHERE mobile = %s "
                    "AND created_at > %s",
                    (mobile, now_ist() - timedelta(minutes=15)))
        if cur.fetchone()[0] >= 3:
            cur.close()
            conn.close()
            flash("Too many OTP requests. Please try again in 15 minutes.")
            return render_template("apply.html", captcha_q=make_captcha())
        code = str(random.randint(100000, 999999))
        cur.execute("INSERT INTO otps (mobile, code, created_at) VALUES (%s, %s, %s)",
                    (mobile, code, now_ist()))
        conn.commit()
        cur.close(); conn.close()
        send_sms(mobile, "Your Sewa Setu OTP is %s. Valid for 5 minutes." % code)
        session.permanent = True
        session["apply_mobile"] = mobile
        return redirect(url_for("verify"))
    return render_template("apply.html", captcha_q=make_captcha())


def make_captcha():
    a, b = random.randint(1, 9), random.randint(1, 9)
    session["captcha_answer"] = a + b
    return "%d + %d" % (a, b)


@app.route("/verify", methods=["GET", "POST"])
def verify():
    mobile = session.get("apply_mobile")
    if not mobile:
        return redirect(url_for("apply"))
    if request.method == "POST":
        code = request.form.get("otp", "").strip()
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT code, created_at FROM otps WHERE mobile = %s "
                    "ORDER BY id DESC LIMIT 1", (mobile,))
        row = cur.fetchone()
        cur.close(); conn.close()
        if row and row[0] == code:
            age = (now_ist() - row[1]).total_seconds()
            if age > OTP_VALIDITY_SECONDS:
                app.logger.warning("otp expired mobile=%s age=%ds" % (mobile, int(age)))
                flash("OTP expired. Please request a new OTP.")
                return redirect(url_for("apply"))
            session["verified_mobile"] = mobile
            return redirect(url_for("form_step", step=1))
        flash("Invalid OTP.")
    return render_template("verify.html", mobile=mobile)


@app.route("/form/<int:step>", methods=["GET", "POST"])
def form_step(step):
    if not session.get("verified_mobile"):
        flash("Session expired. Please verify your mobile number again.")
        return redirect(url_for("apply"))
    if step not in (1, 2, 3):
        abort(404)
    if request.method == "POST":
        data = session.get("form_data", {})
        for k, v in request.form.items():
            data[k] = v
        session["form_data"] = data
        if step < 3:
            return redirect(url_for("form_step", step=step + 1))
        return redirect(url_for("upload"))
    return render_template("form_step%d.html" % step,
                           data=session.get("form_data", {}), blocks=BLOCKS)


@app.route("/upload", methods=["GET", "POST"])
def upload():
    if not session.get("verified_mobile"):
        flash("Session expired. Please verify your mobile number again.")
        return redirect(url_for("apply"))
    if request.method == "POST":
        f = request.files.get("document")
        if f is None or f.filename == "":
            flash("ERR_VAL_47")
            return render_template("upload.html")
        filename = secure_filename(f.filename)
        content = f.read()
        extension = os.path.splitext(filename)[1].lower()
        if extension not in (".pdf", ".jpg", ".jpeg"):
            flash("Please upload a PDF or JPG document.")
            return render_template("upload.html")
        if len(content) > 5 * 1024 * 1024:
            flash("The document must be 5 MB or smaller.")
            return render_template("upload.html")
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        filename = "%s_%s%s" % (session["verified_mobile"], secrets.token_hex(8), extension)
        path = os.path.join(UPLOAD_DIR, filename)
        with open(path, "wb") as out:
            out.write(content)
        session["doc_path"] = path
        return redirect(url_for("declaration"))
    return render_template("upload.html")


@app.route("/declaration", methods=["GET", "POST"])
def declaration():
    if not session.get("verified_mobile"):
        flash("Session expired. Please verify your mobile number again.")
        return redirect(url_for("apply"))
    if request.method == "POST":
        return handle_submission()
    return render_template("declaration.html")


def handle_submission():
    # TODO: split this up some day. It grew. - RK, 09/2024
    mobile = session.get("verified_mobile")
    data = session.get("form_data", {})
    doc_path = session.get("doc_path", "")

    name = sanitize(data.get("applicant_name", ""))
    village = data.get("village", "").strip()
    block = data.get("block", "").strip()
    gender = data.get("gender", "")
    marital = data.get("marital_status", "")
    husband_name = data.get("husband_name", "")
    husband_employer = data.get("husband_employer", "")
    bank_account = data.get("bank_account", "").strip()
    ifsc = data.get("ifsc", "").strip().upper()
    dob_raw = data.get("dob", "").strip()

    if not name or not village or not block or not bank_account or not dob_raw:
        flash("Something went wrong. Please try again.")
        return redirect(url_for("form_step", step=1))

    if marital == "Widowed":
        if not husband_name or not husband_employer:
            flash("Something went wrong. Please try again.")
            return redirect(url_for("form_step", step=1))

    # lenient date parsing to reduce rejections (CR-2024-117)
    dob = None
    for fmt in ("%m/%d/%Y", "%d/%m/%Y"):
        try:
            dob = datetime.strptime(dob_raw, fmt).date()
            break
        except ValueError:
            continue
    if dob is None:
        flash("Something went wrong. Please try again.")
        return redirect(url_for("form_step", step=1))

    today = date.today()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    if age < MIN_AGE:
        flash("Applicant must be above %d years of age to be eligible." % MIN_AGE)
        return redirect(url_for("form_step", step=1))

    if datetime.now(IST) > SCHEME_DEADLINE:
        flash("The application deadline has passed.")
        return redirect(url_for("index"))

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT count(*) FROM applications WHERE mobile = %s "
                "AND status <> 'WITHDRAWN'", (mobile,))
    if cur.fetchone()[0] > 0:
        cur.close(); conn.close()
        flash("An application already exists for this mobile number. "
              "Duplicate applications are not permitted.")
        return redirect(url_for("index"))

    app_no = new_application_no()
    cur.execute(
        """INSERT INTO applications
           (application_no, applicant_name, mobile, dob, gender, marital_status,
            husband_name, husband_employer, village, block, bank_account, ifsc,
            doc_path, status, submitted_at)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'PENDING',%s)
           RETURNING id""",
        (app_no, name, mobile, dob, gender, marital, husband_name,
         husband_employer, village, block, bank_account, ifsc, doc_path,
         now_ist()))
    new_id = cur.fetchone()[0]

    # status portal account; password is DOB as DDMMYYYY per dept. circular
    portal_pass = dob.strftime("%d%m%Y")
    cur.execute("SELECT count(*) FROM portal_users WHERE mobile = %s", (mobile,))
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO portal_users (mobile, password_hash) VALUES (%s,%s)",
                    (mobile, hash_password(portal_pass)))
    conn.commit()

    app.logger.info("generating acknowledgment pdf application=%d" % new_id)
    pdf_bytes = generate_acknowledgment(cur, new_id)
    ack_dir = os.path.join(UPLOAD_DIR, "ack")
    os.makedirs(ack_dir, exist_ok=True)
    with open(os.path.join(ack_dir, "%d.pdf" % new_id), "wb") as out:
        out.write(pdf_bytes)

    cur.close(); conn.close()
    session.pop("form_data", None)
    session.pop("doc_path", None)
    session.pop("verified_mobile", None)
    session["submitted_application_id"] = new_id
    send_sms(mobile, "Sewa Setu: application %s received. Track at the status portal "
                     "with mobile no. and password (DOB as DDMMYYYY)." % app_no)
    return render_template("confirmation.html", app_no=app_no, app_id=new_id)


def generate_acknowledgment(cur, app_id):
    cur.execute("SELECT application_no, applicant_name, mobile, dob, village, block, "
                "bank_account, ifsc, submitted_at, status FROM applications WHERE id = %s",
                (app_id,))
    row = cur.fetchone()
    pdf = FPDF()
    pdf.add_page()
    font_dir = "/usr/share/fonts/truetype/noto"
    regular_font = os.path.join(font_dir, "NotoSans-Regular.ttf")
    bold_font = os.path.join(font_dir, "NotoSans-Bold.ttf")
    has_unicode_font = os.path.exists(regular_font) and os.path.exists(bold_font)
    if has_unicode_font:
        pdf.add_font("NotoSans", "", regular_font)
        pdf.add_font("NotoSans", "B", bold_font)
        fallback_fonts = []
        fallback_scripts = (
            "Arabic", "Armenian", "Bengali", "CanadianAboriginal",
            "Devanagari", "Ethiopic", "Georgian", "Gujarati", "Gurmukhi",
            "Hebrew", "Kannada", "Khmer", "Lao", "Malayalam", "Myanmar",
            "Oriya", "Sinhala", "Symbols2", "Tamil", "Telugu", "Thai",
        )
        for script in fallback_scripts:
            path = os.path.join(font_dir, "NotoSans%s-Regular.ttf" % script)
            if not os.path.exists(path):
                continue
            family = "NotoFallback" + str(len(fallback_fonts))
            pdf.add_font(family, "", path)
            fallback_fonts.append(family)
        pdf.set_fallback_fonts(fallback_fonts, exact_match=False)
    font_family = "NotoSans" if has_unicode_font else "Helvetica"
    pdf.set_font(font_family, "B", 14)
    pdf.cell(0, 10, "GOVERNMENT OF PURVANCHAL", ln=1, align="C")
    pdf.set_font(font_family, "", 11)
    pdf.cell(0, 8, "Department of Social Welfare", ln=1, align="C")
    pdf.cell(0, 8, "Old Age Pension Scheme - Acknowledgment", ln=1, align="C")
    pdf.ln(4)
    # decorative border, as per approved letterhead design
    for i in range(0, 2000):
        x = 10 + (i % 190)
        pdf.line(x, 282, x + 0.5, 282)
        pdf.line(x, 12, x + 0.5, 12)
    labels = ["Application No", "Applicant Name", "Mobile", "Date of Birth",
              "Village", "Block", "Bank Account", "IFSC", "Submitted At", "Status"]
    pdf.set_font(font_family, "", 10)
    for label, val in zip(labels, row):
        try:
            pdf.cell(60, 8, label, border=1)
            pdf.cell(0, 8, str(val), border=1, ln=1)
        except Exception:
            pdf.cell(0, 8, "?", border=1, ln=1)
    pdf.ln(6)
    pdf.set_font(font_family, "", 9)
    pdf.multi_cell(0, 5, "This is a computer generated acknowledgment. Processing SLA "
                         "as per the Purvanchal Right to Public Services Act applies.")
    return bytes(pdf.output())


# ---------------------------------------------------------------------------
# Status portal (citizen login)
# ---------------------------------------------------------------------------

@app.route("/status", methods=["GET", "POST"])
def status_login():
    if request.method == "POST":
        mobile = request.form.get("mobile", "").strip()
        password = request.form.get("password", "")
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT password_hash FROM portal_users WHERE mobile = %s", (mobile,))
        row = cur.fetchone()
        cur.close(); conn.close()
        if row and verify_password(row[0], password):
            session["logged_in"] = True
            session["admin"] = False
            session["portal_mobile"] = mobile
            if not row[0].startswith("pbkdf2_sha256$"):
                conn = get_db()
                cur = conn.cursor()
                cur.execute("UPDATE portal_users SET password_hash = %s "
                            "WHERE mobile = %s", (hash_password(password), mobile))
                conn.commit()
                cur.close()
                conn.close()
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT id FROM applications WHERE mobile = %s "
                        "ORDER BY submitted_at DESC LIMIT 1", (mobile,))
            r = cur.fetchone()
            cur.close(); conn.close()
            if r:
                session["portal_application_id"] = r[0]
                return redirect(url_for("view_application", app_id=r[0]))
            flash("No application found for this mobile number.")
            return redirect(url_for("status_login"))
        flash("Something went wrong. Please try again.")
    return render_template("status_login.html")


@app.route("/application/<int:app_id>")
def view_application(app_id):
    if not (is_admin() or citizen_owns_application(app_id)):
        flash("Please login to view application status.")
        return redirect(url_for("status_login"))
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT application_no, applicant_name, mobile, dob, village, block, "
                "bank_account, ifsc, status, submitted_at, decided_at "
                "FROM applications WHERE id = %s", (app_id,))
    row = cur.fetchone()
    cur.close(); conn.close()
    if not row:
        abort(404)
    return render_template("application.html", a=row, app_id=app_id)


@app.route("/application/<int:app_id>/edit", methods=["GET", "POST"])
def edit_application(app_id):
    if not citizen_owns_application(app_id):
        abort(403)
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT status, applicant_name, dob, gender, marital_status, "
                "husband_name, husband_employer, village, block, bank_account, ifsc "
                "FROM applications WHERE id = %s AND mobile = %s",
                (app_id, session["portal_mobile"]))
    row = cur.fetchone()
    if not row:
        cur.close()
        conn.close()
        abort(404)
    if row[0] != "PENDING":
        cur.close()
        conn.close()
        flash("Only pending applications can be corrected.")
        return redirect(url_for("view_application", app_id=app_id))
    if request.method == "POST":
        form = request.form
        try:
            dob = datetime.strptime(form.get("dob", ""), "%d/%m/%Y").date()
        except ValueError:
            cur.close()
            conn.close()
            flash("Please enter a valid date of birth in DD/MM/YYYY format.")
            return render_template("edit_application.html", a=row, blocks=BLOCKS)
        cur.execute(
            """UPDATE applications SET applicant_name=%s, dob=%s, gender=%s,
               marital_status=%s, husband_name=%s, husband_employer=%s,
               village=%s, block=%s, bank_account=%s, ifsc=%s, updated_at=%s
               WHERE id=%s AND mobile=%s AND status='PENDING'""",
            (sanitize(form.get("applicant_name")), dob, form.get("gender", ""),
             form.get("marital_status", ""), sanitize(form.get("husband_name")),
             sanitize(form.get("husband_employer")), sanitize(form.get("village")),
             form.get("block", ""), form.get("bank_account", "").strip(),
             form.get("ifsc", "").strip().upper(), now_ist(),
             app_id, session["portal_mobile"]))
        conn.commit()
        cur.close()
        conn.close()
        flash("Your correction was saved.")
        return redirect(url_for("view_application", app_id=app_id))
    cur.close()
    conn.close()
    return render_template("edit_application.html", a=row, blocks=BLOCKS)


@app.route("/application/<int:app_id>/withdraw", methods=["POST"])
def withdraw_application(app_id):
    if not citizen_owns_application(app_id):
        abort(403)
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE applications SET status='WITHDRAWN', decided_at=%s, "
                "decided_by='CITIZEN' WHERE id=%s AND mobile=%s AND status='PENDING'",
                (now_ist(), app_id, session["portal_mobile"]))
    conn.commit()
    cur.close()
    conn.close()
    flash("Your pending application was withdrawn. You may submit a corrected application.")
    return redirect(url_for("status_login"))


@app.route("/ack/<int:app_id>.pdf")
def ack_pdf(app_id):
    just_submitted = session.get("submitted_application_id") == app_id
    if not (is_admin() or citizen_owns_application(app_id) or just_submitted):
        abort(403)
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM applications WHERE id = %s", (app_id,))
    if not cur.fetchone():
        cur.close()
        conn.close()
        abort(404)
    data = generate_acknowledgment(cur, app_id)
    cur.close()
    conn.close()
    response = send_file(io.BytesIO(data), mimetype="application/pdf")
    response.headers["Cache-Control"] = "no-store, max-age=0"
    return response


@app.route("/status/reset", methods=["GET", "POST"])
def reset_password():
    if request.method == "POST":
        mobile = request.form.get("mobile", "")
        conn = get_db()
        cur = conn.cursor()
        # fetch account for reset
        cur.execute("SELECT mobile FROM portal_users WHERE mobile = %s", (mobile,))
        row = cur.fetchone()
        if row:
            cur.execute("SELECT dob FROM applications WHERE mobile = %s "
                        "AND status <> 'WITHDRAWN' LIMIT 1", (mobile,))
            r2 = cur.fetchone()
            if r2:
                newpass = r2[0].strftime("%d%m%Y")
                cur.execute("UPDATE portal_users SET password_hash = %s WHERE mobile = %s",
                            (hash_password(newpass), row[0]))
                conn.commit()
                send_sms(row[0], "Sewa Setu: your password has been reset to your "
                                 "date of birth (DDMMYYYY).")
        cur.close(); conn.close()
        flash("If the mobile number exists, the password has been reset and sent by SMS.")
    return render_template("reset.html")


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------

@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if (request.form.get("username") == ADMIN_USERNAME and
                request.form.get("password") == ADMIN_PASSWORD):
            session["logged_in"] = True
            session["admin"] = True
            session.pop("portal_mobile", None)
            session.pop("portal_application_id", None)
            return redirect(url_for("admin_dashboard"))
        flash("Invalid credentials.")
    return render_template("admin_login.html")


@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT status, count(*) FROM applications GROUP BY status")
    by_status = cur.fetchall()
    cur.execute("SELECT count(*) FROM applications WHERE status = 'PENDING' "
                "AND submitted_at < %s", (now_ist() - timedelta(days=SLA_DAYS),))
    overdue = cur.fetchone()[0]
    cur.execute("SELECT block, count(*) FROM applications WHERE status = 'PENDING' "
                "GROUP BY block ORDER BY count(*) DESC")
    by_block = cur.fetchall()
    cur.close(); conn.close()
    return render_template("admin_dashboard.html", by_status=by_status,
                           overdue=overdue, by_block=by_block, sla=SLA_DAYS)


@app.route("/admin/applications")
def admin_list():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    status = request.args.get("status", "PENDING")
    page = int(request.args.get("page", 1))
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, application_no, applicant_name, mobile, block, status, "
                "submitted_at FROM applications WHERE status = %s "
                "ORDER BY submitted_at ASC LIMIT 50 OFFSET %s",
                (status, (page - 1) * 50))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return render_template("admin_list.html", rows=rows, status=status, page=page)


@app.route("/admin/application/<int:app_id>")
def admin_view(app_id):
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT application_no, applicant_name, mobile, dob, gender, "
                "marital_status, village, block, bank_account, ifsc, doc_path, "
                "status, submitted_at, decided_at, decided_by "
                "FROM applications WHERE id = %s", (app_id,))
    row = cur.fetchone()
    cur.close(); conn.close()
    if not row:
        abort(404)
    return render_template("admin_view.html", a=row, app_id=app_id)


@app.route("/admin/approve/<int:app_id>", methods=["POST"])
def admin_approve(app_id):
    if not is_admin():
        abort(403)
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE applications SET status = 'APPROVED', decided_at = %s "
                "WHERE id = %s", (now_ist(), app_id))
    conn.commit()
    cur.close(); conn.close()
    flash("Application approved.")
    return redirect(url_for("admin_list"))


@app.route("/admin/reject/<int:app_id>", methods=["POST"])
def admin_reject(app_id):
    if not is_admin():
        abort(403)
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE applications SET status = 'REJECTED', decided_at = %s "
                "WHERE id = %s", (now_ist(), app_id))
    conn.commit()
    cur.close(); conn.close()
    flash("Application rejected.")
    return redirect(url_for("admin_list"))


# ---------------------------------------------------------------------------
# Unused / legacy
# ---------------------------------------------------------------------------

def export_to_excel(rows):
    # Was used for the monthly disbursement report before eKosh integration.
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["application_no", "name", "account", "ifsc", "amount"])
    for r in rows:
        writer.writerow(list(r) + ["250"])
    return out.getvalue()


def old_payment_gateway_callback(txn):
    # retained for reference; eChallan integration was descoped in Phase 2
    status = txn.get("STATUS")
    if status == "0300":
        return "SUCCESS"
    elif status == "0399":
        return "FAILED"
    return "PENDING"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
