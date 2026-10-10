# -*- coding: utf-8 -*-
"""
Sewa Setu - Old Age Pension Portal
Government of Purvanchal, Department of Social Welfare

Developed by: Netlink Infosolutions Pvt Ltd (2023)
Maintenance contract ended 31/01/2026.
Refactored and hardened for Build for Bharat Fellowship 2027.
"""

import os
import io
import csv
import time
import random
import hashlib
import hmac
import configparser
from concurrent.futures import ThreadPoolExecutor
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
app.secret_key = os.environ["SEWASETU_SECRET_KEY"]
app.config["PERMANENT_SESSION_LIFETIME"] = 1800  # 30 mins session

LANGUAGES = {
    "en": {"name": "English", "speech": "en-IN"},
    "hi": {"name": "हिन्दी", "speech": "hi-IN"},
    "as": {"name": "অসমীয়া", "speech": "as-IN"},
    "bn": {"name": "বাংলা", "speech": "bn-IN"},
    "ml": {"name": "മലയാളം", "speech": "ml-IN"},
    "ta": {"name": "தமிழ்", "speech": "ta-IN"},
    "te": {"name": "తెలుగు", "speech": "te-IN"},
    "kn": {"name": "ಕನ್ನಡ", "speech": "kn-IN"},
    "mr": {"name": "मराठी", "speech": "mr-IN"},
    "gu": {"name": "ગુજરાતી", "speech": "gu-IN"},
    "pa": {"name": "ਪੰਜਾਬੀ", "speech": "pa-IN"},
    "or": {"name": "ଓଡ଼ିଆ", "speech": "or-IN"},
}

TRANSLATIONS = {
    "en": {
        "title": "Sewa Setu - Old Age Pension Portal",
        "department": "Department of Social Welfare · Government of Purvanchal",
        "help": "Need help? This pension service is free. Do not pay an agent or share your OTP.",
        "choose_language": "Choose your language",
        "language_help": "You can change this later at any time. You do not need to pay anyone to apply.",
        "show_all_languages": "Show all Indian languages",
        "detect_language": "Detect location for language",
        "continue": "Continue", "change_language": "Change language",
        "read_aloud": "Read this page aloud", "home": "Home",
        "welcome": "Welcome", "apply": "Apply for Pension",
        "scheme": "The Old Age Pension Scheme provides a monthly pension of Rs. 250 to eligible senior citizens aged 60 years or older who are residents of Purvanchal.",
        "free_help_detail": "If you are applying for the first time, a government help desk at your Block Development Office will assist you free of charge. Ask for a receipt and keep your application number.",
        "window": "Application window closes in approximately", "closed": "The application window for this scheme has closed.",
        "steps": [
            "Enter your mobile number and the one-time code sent to you.",
            "Enter your name exactly as it appears on your age proof document.",
            "Enter your address and bank account details. You can review all details before submit.",
            "Upload an age proof document (Aadhaar, Voter ID, Ration card, or Birth certificate, max 5 MB).",
            "Review your details on the final page, submit, and save or print the acknowledgment number."
        ],
        "safety": "Never share your OTP or bank PIN. The department will never charge a fee to submit this application.",
        "free_assistance": "For free assistance, visit your nearest Block Development Office or use",
        "hours_suffix": "hours (midnight, 31 October).", "service_footer": "Government citizen service · Purvanchal Social Welfare Department",
        "about": "About the Scheme", "rti": "RTI", "grievance": "Grievance Cell", "contact": "Contact Us",
        "status": "Check Application Status", "free_help": "You do not need to pay anyone to apply.",
        "how_to_apply": "How to apply", "apply_help": "For free help, visit your nearest Block Development Office.",
        "step1_label": "Step 1 of 6: Mobile Verification",
        "mobile_verification": "Mobile Verification", "send_otp": "Send OTP",
        "mobile_label": "Mobile Number", "mobile_placeholder": "10-digit mobile number",
        "security_check": "Security Check: What is",
        "otp_note": "An OTP will be sent to your mobile number by SMS. OTP is valid for 10 minutes.",
        "enter_otp": "Enter OTP", "otp_sent_to": "An OTP has been sent to",
        "otp_label": "Enter 6-digit OTP", "verify_button": "Verify & Continue",
        "step2_title": "Step 2 of 6: Personal Details",
        "personal_details": "Personal Details",
        "applicant_name_label": "Full Name of Applicant (as per age proof)",
        "dob_label": "Date of Birth (DD/MM/YYYY)", "dob_placeholder": "DD/MM/YYYY",
        "gender_label": "Gender", "gender_select": "--Select Gender--",
        "gender_male": "Male", "gender_female": "Female", "gender_other": "Other",
        "marital_status_label": "Marital Status", "marital_select": "--Select Status--",
        "marital_married": "Married", "marital_unmarried": "Unmarried", "marital_widowed": "Widowed",
        "husband_name_label": "Spouse's Name (optional)",
        "husband_employer_label": "Husband's Employer (optional)",
        "husband_help": "Note: Spouse details are optional for all applicants.",
        "mandatory_note": "Fields marked with * are mandatory.",
        "save_continue": "Save & Continue",
        "step3_title": "Step 3 of 6: Address Details",
        "address_details": "Address Details",
        "village_label": "Village / Town", "block_label": "Block",
        "block_select": "--Select Block--",
        "step4_title": "Step 4 of 6: Bank Details",
        "bank_details_title": "Bank Details for Pension Disbursement",
        "bank_account_label": "Bank Account Number", "ifsc_label": "IFSC Code",
        "dbt_note": "Pension will be credited by Direct Benefit Transfer (DBT) to this account. Ensure the account is in the name of the applicant.",
        "step5_title": "Step 5 of 6: Document Upload",
        "upload_heading": "Upload Age Proof Document",
        "upload_help": "Accepted documents: Aadhaar card, Voter ID, Ration card, Birth certificate, or School certificate. Accepted formats: JPG, PNG, or PDF (up to 5 MB).",
        "select_doc": "Select Document", "upload_button": "Upload & Continue",
        "step6_title": "Step 6 of 6: Review & Declaration",
        "review_heading": "Review Application Details",
        "review_subheading": "Please verify that all information is correct before final submission.",
        "edit_link": "Edit", "uploaded_doc_label": "Age Proof Document", "doc_uploaded": "Document uploaded successfully",
        "declaration_heading": "Declaration",
        "declaration_text": "I hereby declare that the information furnished above is true to the best of my knowledge and belief. I understand that furnishing false information is punishable under applicable law and will result in cancellation of pension.",
        "agree_checkbox": "I agree to the above declaration.",
        "submit_btn": "Submit Application",
        "submitted_heading": "Application Submitted Successfully",
        "submitted_msg": "Your pension application has been received.",
        "app_no_label": "Application Number",
        "app_received_note": "Please write down your Application Number. You can check your application status on the status portal using your registered mobile number.",
        "download_ack": "Download Acknowledgment (PDF)",
        "status_portal_title": "Citizen Status Portal",
        "password_label": "Password (Date of Birth as DDMMYYYY)",
        "login_btn": "Login", "forgot_password": "Forgot password?",
        "app_status_title": "Application Status",
        "status_label": "Current Status", "submitted_at_label": "Submitted At", "decided_at_label": "Decided At",
        "correct_details_btn": "Correct Application Details",
        "withdraw_btn": "Withdraw Pending Application",
        "edit_heading": "Correct Pending Application",
        "edit_note": "Corrections are allowed while the application is pending. Corrections do not reset the 15-day statutory processing clock.",
        "save_correction": "Save Correction",
        "reset_title": "Reset Password",
        "registered_mobile_label": "Registered Mobile Number",
        "reset_password_btn": "Reset Password via SMS",
    },
    "as": {
        "title": "সেৱা সেতু - বৃদ্ধ পেঞ্চন প'ৰ্টেল",
        "department": "সমাজ কল্যাণ বিভাগ · পূৰ্বাঞ্চল চৰকাৰ",
        "help": "সহায়ৰ প্ৰয়োজন? এই পেঞ্চন সেৱা বিনামূলীয়া। কোনো এজেণ্টক টকা নিদিব আৰু OTP নিদিব।",
        "choose_language": "আপোনাৰ ভাষা বাছনি কৰক",
        "language_help": "আপুনি পিছত যিকোনো সময়তে ভাষা সলনি কৰিব পাৰে। আবেদন কৰিবলৈ কাকো টকা নিদিব।",
        "continue": "আগবাঢ়ক", "change_language": "ভাষা সলনি কৰক",
        "read_aloud": "এই পৃষ্ঠা শুনক", "home": "মুখ্য পৃষ্ঠা",
        "welcome": "স্বাগতম", "apply": "পেঞ্চনৰ বাবে আবেদন কৰক",
        "scheme": "বৃদ্ধ পেঞ্চন আঁচনিয়ে পূৰ্বাঞ্চলৰ ৬০ বছৰ বা তাতকৈ অধিক বয়সৰ যোগ্য জ্যেষ্ঠ নাগৰিকক প্ৰতিমাহে ২৫০ টকা দিয়ে।",
        "free_help_detail": "প্ৰথমবাৰ আবেদন কৰিলে খণ্ড উন্নয়ন কাৰ্যালয়ৰ চৰকাৰী সহায় কেন্দ্ৰই বিনামূলীয়াকৈ সহায় কৰিব। ৰচিদ লওক আৰু আবেদন নম্বৰ ৰাখক।",
        "window": "আবেদনৰ সময়সীমা প্ৰায়", "closed": "এই আঁচনিৰ আবেদনৰ সময়সীমা শেষ হৈছে।",
        "steps": [
            "আপোনাৰ ম'বাইল নম্বৰ আৰু পঠোৱা এবাৰ ব্যৱহাৰযোগ্য ক'ড (OTP) দিয়ক।",
            "বয়সৰ প্ৰমাণপত্ৰত থকা মতে আপোনাৰ সম্পূৰ্ণ নাম দিয়ক।",
            "ঠিকনা আৰু বেংক একাউণ্টৰ তথ্য দিয়ক। আবেদন জমা দিয়াৰ আগতে সকলো পুনৰীক্ষণ কৰিব পাৰিব।",
            "বয়সৰ প্ৰমাণপত্ৰ আপলোড কৰক (আধাৰ, ভোটাৰ আই ডি, ৰেচন কাৰ্ড, বা জন্ম প্ৰমাণপত্ৰ, সৰ্বাধিক ১০ MB)।",
            "শেষ পৃষ্ঠা পঢ়ি আবেদন জমা দিয়ক আৰু স্বীকৃতি নম্বৰ ৰাখক।"
        ],
        "safety": "আপোনাৰ OTP বা বেংক PIN কেতিয়াও নিদিব। আবেদন জমা দিবলৈ বিভাগে কোনো মাচুল নলয়।",
        "free_assistance": "বিনামূলীয়া সহায়ৰ বাবে ওচৰৰ খণ্ড উন্নয়ন কাৰ্যালয়লৈ যাওক বা ইয়াত যাওক:",
        "hours_suffix": "ঘণ্টা (৩১ অক্টোবৰৰ মাজনিশা)।", "service_footer": "চৰকাৰী নাগৰিক সেৱা · পূৰ্বাঞ্চল সমাজ কল্যাণ বিভাগ",
        "about": "আঁচনিৰ বিষয়ে", "rti": "তথ্যৰ অধিকাৰ", "grievance": "অভিযোগ কোষ", "contact": "যোগাযোগ",
        "status": "আবেদনৰ স্থিতি চাওক", "free_help": "আবেদন কৰিবলৈ কাকো টকা দিয়াৰ প্ৰয়োজন নাই।",
        "how_to_apply": "আবেদন কৰাৰ পদ্ধতি", "apply_help": "বিনামূলীয়া সহায়ৰ বাবে ওচৰৰ খণ্ড উন্নয়ন কাৰ্যালয়লৈ যাওক।",
        "step1_label": "স্তৰ ১/৬: ম'বাইল পৰীক্ষণ",
        "mobile_verification": "ম'বাইল পৰীক্ষণ", "send_otp": "OTP পঠিয়াওক",
        "mobile_label": "ম'বাইল নম্বৰ", "mobile_placeholder": "১০ সংখ্যাৰ ম'বাইল নম্বৰ",
        "security_check": "সুৰক্ষা পৰীক্ষা: কিমান হ'ব",
        "otp_note": "আপোনাৰ ম'বাইল নম্বৰলৈ SMS যোগে এটা OTP পঠিওৱা হ'ব। OTP ১০ মিনিটৰ বাবে বৈধ।",
        "enter_otp": "OTP দিয়ক", "otp_sent_to": "OTP পঠিওৱা হৈছে এই নম্বৰলৈ:",
        "otp_label": "৬ সংখ্যাৰ OTP দিয়ক", "verify_button": "পৰীক্ষা কৰি আগবাঢ়ক",
        "step2_title": "স্তৰ ২/৬: ব্যক্তিগত তথ্য",
        "personal_details": "ব্যক্তিগত তথ্য",
        "applicant_name_label": "আবেদনকাৰীৰ সম্পূৰ্ণ নাম (বয়সৰ প্ৰমাণপত্ৰ মতে)",
        "dob_label": "জন্ম তাৰিখ (DD/MM/YYYY)", "dob_placeholder": "দিন/মাহ/বছৰ",
        "gender_label": "লিংগ", "gender_select": "--লিংগ বাছনি কৰক--",
        "gender_male": "পুৰুষ", "gender_female": "মহিলা", "gender_other": "অন্য",
        "marital_status_label": "বৈবাহিক স্থিতি", "marital_select": "--স্থিতি বাছনি কৰক--",
        "marital_married": "বিবাহিত", "marital_unmarried": "অবিবাহিত", "marital_widowed": "বিধৱা/বিপত্তীক",
        "husband_name_label": "স্বামীৰ নাম (কেৱল বিবাহিত মহিলাৰ বাবে)",
        "husband_employer_label": "স্বামীৰ কৰ্মসংস্থান (ঐচ্ছিক)",
        "husband_help": "টোকা: কেৱল বিবাহিত আবেদনকাৰীৰ বাবেহে প্ৰযোজ্য।",
        "mandatory_note": "* চিন দিয়া তথ্যসমূহ দিয়াটো বাধ্যতামূলক।",
        "save_continue": "সংৰক্ষণ কৰি আগবাঢ়ক",
        "step3_title": "স্তৰ ৩/৬: ঠিকনাৰ তথ্য",
        "address_details": "ঠিকনাৰ তথ্য",
        "village_label": "গাঁও / চহৰ", "block_label": "উন্নয়ন খণ্ড",
        "block_select": "--খণ্ড বাছনি কৰক--",
        "step4_title": "স্তৰ ৪/৬: বেংক একাউণ্টৰ তথ্য",
        "bank_details_title": "পেঞ্চন জমাৰ বাবে বেংক একাউণ্টৰ তথ্য",
        "bank_account_label": "বেংক একাউণ্ট নম্বৰ", "ifsc_label": "বেংকৰ IFSC ক'ড",
        "dbt_note": "পেঞ্চনৰ ধন পোনপটীয়াকৈ DBT যোগে এই একাউণ্টত জমা হ'ব। একাউণ্টটো আবেদনকাৰীৰ নিজৰ নামত হ'ব লাগিব।",
        "step5_title": "স্তৰ ৫/৬: প্ৰমাণপত্ৰ আপলোড",
        "upload_heading": "বয়সৰ প্ৰমাণপত্ৰ আপলোড কৰক",
        "upload_help": "গ্ৰহণযোগ্য নথি: আধাৰ কাৰ্ড, ভোটাৰ আই ডি, ৰেচন কাৰ্ড, বা জন্ম প্ৰমাণপত্ৰ। ফৰ্মাট: JPG, PNG, বা PDF (১০ MB লৈকে)।",
        "select_doc": "নথি বাছনি কৰক", "upload_button": "আপলোড কৰি আগবাঢ়ক",
        "step6_title": "স্তৰ ৬/৬: পৰ্যালোচনা আৰু ঘোষণা",
        "review_heading": "আবেদনৰ তথ্য পৰীক্ষা কৰক",
        "review_subheading": "অনুগ্ৰহ কৰি আবেদন জমা দিয়াৰ আগতে সকলো তথ্য সঠিক হয়নে পৰীক্ষা কৰক।",
        "edit_link": "সংশোধন কৰক", "uploaded_doc_label": "আপলোড কৰা প্ৰমাণপত্ৰ", "doc_uploaded": "নথি আপলোড কৰা হৈছে",
        "declaration_heading": "ঘোষণা",
        "declaration_text": "মই ঘোষণা কৰোঁ যে ওপৰত দিয়া সকলো তথ্য মোৰ জ্ঞান মতে সত্য। যদি কোনো তথ্য ভুল প্ৰমাণিত হয়, তেন্তে আইন অনুসৰি পেঞ্চন বাতিল হ'ব পাৰে।",
        "agree_checkbox": "মই ওপৰৰ ঘোষণাত সন্মত।",
        "submit_btn": "আবেদন জমা দিয়ক",
        "submitted_heading": "আবেদন সফলভাৱে জমা হ'ল",
        "submitted_msg": "আপোনাৰ পেঞ্চন আবেদন বিভাগত গ্ৰহণ কৰা হৈছে।",
        "app_no_label": "আবেদন নম্বৰ",
        "app_received_note": "আপোনাৰ আবেদন নম্বৰ সংৰক্ষণ কৰি ৰাখক। আপোনাৰ ম'বাইল নম্বৰ ব্যৱহাৰ কৰি স্থিতি চাব পাৰিব।",
        "download_ack": "স্বীকৃতি পত্ৰ ডাউনলোড কৰক (PDF)",
        "status_portal_title": "নাগৰিক স্থিতি প'ৰ্টেল",
        "password_label": "পাছৱৰ্ড (জন্ম তাৰিখ DDMMYYYY ৰূপত)",
        "login_btn": "প্ৰৱেশ কৰক", "forgot_password": "পাছৱৰ্ড পাহৰিলে?",
        "app_status_title": "আবেদনৰ স্থিতি",
        "status_label": "বৰ্তমান স্থিতি", "submitted_at_label": "জমা দিয়া তাৰিখ", "decided_at_label": "সিদ্ধান্তৰ তাৰিখ",
        "correct_details_btn": "তথ্য সংশোধন কৰক",
        "withdraw_btn": "অপেক্ষাৰত আবেদন প্ৰত্যাহাৰ কৰক",
        "edit_heading": "লিম্বিত আবেদন সংশোধন",
        "edit_note": "আবেদন বিবেচনাধীন হৈ থকালৈকে তথ্য সংশোধন কৰিব পাৰি। ইয়াৰ দ্বাৰা ১৫ দিনীয়া সময়সীমা সলনি নহয়।",
        "save_correction": "সংশোধন সংৰক্ষণ কৰক",
        "reset_title": "পাছৱৰ্ড পুনৰুদ্ধাৰ",
        "registered_mobile_label": "পঞ্জীভুক্ত ম'বাইল নম্বৰ",
        "reset_password_btn": "SMS যোগে পাছৱৰ্ড প্ৰেৰণ কৰক",
    },
    "hi": {
        "title": "सेवा सेतु - वृद्धावस्था पेंशन पोर्टल",
        "department": "समाज कल्याण विभाग · पूर्वांचल सरकार",
        "help": "मदद चाहिए? यह पेंशन सेवा निःशुल्क है। किसी एजेंट को पैसे न दें और OTP साझा न करें।",
        "choose_language": "अपनी भाषा चुनें",
        "language_help": "आप बाद में कभी भी भाषा बदल सकते हैं। आवेदन करने के लिए किसी को पैसे न दें।",
        "continue": "आगे बढ़ें", "change_language": "भाषा बदलें",
        "read_aloud": "यह पृष्ठ सुनें", "home": "मुख्य पृष्ठ",
        "welcome": "स्वागत है", "apply": "पेंशन के लिए आवेदन करें",
        "scheme": "वृद्धावस्था पेंशन योजना पूर्वांचल के 60 वर्ष या उससे अधिक आयु के पात्र वरिष्ठ नागरिकों को हर महीने 250 रुपये देती है।",
        "free_help_detail": "पहली बार आवेदन करने पर प्रखंड विकास कार्यालय का सरकारी सहायता केंद्र निःशुल्क मदद करेगा। रसीद लें और आवेदन संख्या सुरक्षित रखें।",
        "window": "आवेदन की अंतिम समय-सीमा लगभग", "closed": "इस योजना के लिए आवेदन की समय-सीमा समाप्त हो गई है।",
        "steps": [
            "अपना मोबाइल नंबर और भेजा गया एक बार का कोड (OTP) दर्ज करें।",
            "उम्र के प्रमाण-पत्र पर लिखे नाम के अनुसार अपना नाम दर्ज करें।",
            "पता और बैंक खाते की जानकारी दर्ज करें। अंतिम सबमिट से पहले समीक्षा करें।",
            "उम्र का प्रमाण-पत्र अपलोड करें (आधार, वोटर कार्ड, राशन कार्ड, या जन्म प्रमाण पत्र, अधिकतम 10 MB)।",
            "अंतिम पृष्ठ पर विवरण की समीक्षा कर आवेदन जमा करें और पावती संख्या सुरक्षित रखें।"
        ],
        "safety": "अपना OTP या बैंक PIN कभी साझा न करें। आवेदन जमा करने के लिए विभाग कोई शुल्क नहीं लेता।",
        "free_assistance": "निःशुल्क सहायता के लिए निकटतम प्रखंड विकास कार्यालय जाएँ या यहाँ जाएँ:",
        "hours_suffix": "घंटे (31 अक्टूबर की मध्यरात्रि)।", "service_footer": "सरकारी नागरिक सेवा · पूर्वांचल समाज कल्याण विभाग",
        "about": "योजना के बारे में", "rti": "सूचना का अधिकार", "grievance": "शिकायत केंद्र", "contact": "संपर्क करें",
        "status": "आवेदन की स्थिति देखें", "free_help": "आवेदन करने के लिए किसी को पैसे देने की जरूरत नहीं है।",
        "how_to_apply": "आवेदन कैसे करें", "apply_help": "निःशुल्क सहायता के लिए निकटतम प्रखंड विकास कार्यालय जाएँ।",
        "step1_label": "चरण 1/6: मोबाइल सत्यापन",
        "mobile_verification": "मोबाइल सत्यापन", "send_otp": "OTP भेजें",
        "mobile_label": "मोबाइल नंबर", "mobile_placeholder": "10 अंकों का मोबाइल नंबर",
        "security_check": "सुरक्षा जाँच: क्या होगा",
        "otp_note": "आपके मोबाइल नंबर पर SMS द्वारा OTP भेजा जाएगा। यह 10 मिनट के लिए मान्य है।",
        "enter_otp": "OTP दर्ज करें", "otp_sent_to": "इस नंबर पर OTP भेजा गया है:",
        "otp_label": "6 अंकों का OTP दर्ज करें", "verify_button": "सत्यापित करें और आगे बढ़ें",
        "step2_title": "चरण 2/6: व्यक्तिगत विवरण",
        "personal_details": "व्यक्तिगत विवरण",
        "applicant_name_label": "आवेदक का पूरा नाम (आयु प्रमाण के अनुसार)",
        "dob_label": "जन्म तिथि (DD/MM/YYYY)", "dob_placeholder": "दिन/माह/वर्ष",
        "gender_label": "लिंग", "gender_select": "--लिंग चुनें--",
        "gender_male": "पुरुष", "gender_female": "महिला", "gender_other": "अन्य",
        "marital_status_label": "वैवाहिक स्थिति", "marital_select": "--स्थिति चुनें--",
        "marital_married": "विवाहित", "marital_unmarried": "अविवाहित", "marital_widowed": "विधवा/विधुर",
        "husband_name_label": "पति का नाम (यदि विवाहित महिला हों)",
        "husband_employer_label": "पति का कार्यस्थल (वैकल्पिक)",
        "husband_help": "नोट: पति का विवरण केवल विवाहित महिलाओं के लिए वैकल्पिक है।",
        "mandatory_note": "* चिह्नित फ़ील्ड अनिवार्य हैं।",
        "save_continue": "सहेजें और आगे बढ़ें",
        "step3_title": "चरण 3/6: पते का विवरण",
        "address_details": "पते का विवरण",
        "village_label": "गाँव / शहर", "block_label": "प्रखंड (ब्लॉक)",
        "block_select": "--प्रखंड चुनें--",
        "step4_title": "चरण 4/6: बैंक खाता विवरण",
        "bank_details_title": "पेंशन भुगतान हेतु बैंक विवरण",
        "bank_account_label": "बैंक खाता संख्या", "ifsc_label": "IFSC कोड",
        "dbt_note": "पेंशन सीधे DBT द्वारा इस खाते में जमा की जाएगी। खाता आवेदक के नाम पर होना चाहिए।",
        "step5_title": "चरण 5/6: दस्तावेज़ अपलोड",
        "upload_heading": "आयु प्रमाण दस्तावेज़ अपलोड करें",
        "upload_help": "स्वीकृत दस्तावेज़: आधार कार्ड, वोटर आईडी, राशन कार्ड, जन्म प्रमाण पत्र। प्रारूप: JPG, PNG या PDF (10 MB तक)।",
        "select_doc": "दस्तावेज़ चुनें", "upload_button": "अपलोड करें और आगे बढ़ें",
        "step6_title": "चरण 6/6: समीक्षा और घोषणा",
        "review_heading": "आवेदन विवरण की समीक्षा करें",
        "review_subheading": "कृपया आवेदन जमा करने से पहले सभी विवरणों की पुष्टि कर लें।",
        "edit_link": "सुधारें", "uploaded_doc_label": "अपलोड किया गया दस्तावेज़", "doc_uploaded": "दस्तावेज़ संलग्न है",
        "declaration_heading": "घोषणा",
        "declaration_text": "मैं घोषणा करता/करती हूँ कि ऊपर दी गई जानकारी मेरी जानकारी के अनुसार सत्य है। किसी भी असत्य जानकारी पर नियमानुसार पेंशन निरस्त की जा सकती है।",
        "agree_checkbox": "मैं उपरोक्त घोषणा से सहमत हूँ।",
        "submit_btn": "आवेदन जमा करें",
        "submitted_heading": "आवेदन सफलतापूर्वक जमा हो गया",
        "submitted_msg": "आपका पेंशन आवेदन प्राप्त हो गया है।",
        "app_no_label": "आवेदन संख्या",
        "app_received_note": "अपनी आवेदन संख्या नोट कर लें। आप अपने मोबाइल नंबर से स्थिति पोर्टल पर देख सकते हैं।",
        "download_ack": "पावती डाउनलोड करें (PDF)",
        "status_portal_title": "नागरिक स्थिति पोर्टल",
        "password_label": "पासवर्ड (जन्म तिथि DDMMYYYY प्रारूप में)",
        "login_btn": "लॉगिन करें", "forgot_password": "पासवर्ड भूल गए?",
        "app_status_title": "आवेदन की स्थिति",
        "status_label": "वर्तमान स्थिति", "submitted_at_label": "आवेदन तिथि", "decided_at_label": "निर्णय तिथि",
        "correct_details_btn": "आवेदन विवरण सुधारें",
        "withdraw_btn": "लंबित आवेदन वापस लें",
        "edit_heading": "लंबित आवेदन में सुधार",
        "edit_note": "आवेदन लंबित रहने तक सुधार किया जा सकता है। इससे 15 दिनों की वैधानिक समय-सीमा दोबारा शुरू नहीं होती।",
        "save_correction": "सुधार सहेजें",
        "reset_title": "पासवर्ड रीसेट करें",
        "registered_mobile_label": "पंजीकृत मोबाइल नंबर",
        "reset_password_btn": "SMS द्वारा पासवर्ड भेजें",
    },
    "bn": {
        "title": "সেবা সেতু - বার্ধক্য পেনশন পোর্টাল",
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
        "steps": [
            "আপনার মোবাইল নম্বর এবং পাঠানো কোড (OTP) দিন।",
            "বয়সের প্রমাণপত্রে যেমন আছে তেমন নাম লিখুন।",
            "ঠিকানা ও ব্যাঙ্ক অ্যাকাউন্টের তথ্য দিন। জমা দেওয়ার আগে পর্যালোচনা করুন।",
            "বয়সের প্রমাণপত্র আপলোড করুন (আধার, ভোটার কার্ড, রেশন কার্ড, সর্বোচ্চ ১০ MB)।",
            "শেষ পৃষ্ঠা পড়ে আবেদন জমা দিন এবং স্বীকৃতি নম্বর রাখুন।"
        ],
        "safety": "আপনার OTP বা ব্যাঙ্ক PIN কখনও শেয়ার করবেন না। আবেদন জমা দিতে বিভাগ কোনও টাকা নেয় না।",
        "free_assistance": "বিনামূল্যে সাহায্যের জন্য নিকটবর্তী ব্লক উন্নয়ন দপ্তরে যান অথবা এখানে যান:",
        "hours_suffix": "ঘণ্টা (৩১ অক্টোবর মধ্যরাতে)।", "service_footer": "সরকারি নাগরিক পরিষেবা · পূর্বাঞ্চল সমাজকল্যাণ বিভাগ",
        "about": "প্রকল্প সম্পর্কে", "rti": "তথ্যের অধিকার", "grievance": "অভিযোগ কেন্দ্র", "contact": "যোগাযোগ",
        "status": "আবেদনের অবস্থা দেখুন", "free_help": "আবেদন করতে কাউকে টাকা দেওয়ার দরকার নেই।",
        "how_to_apply": "আবেদন করার পদ্ধতি", "apply_help": "বিনামূল্যে সাহায্যের জন্য নিকটবর্তী ব্লক উন্নয়ন দপ্তরে যান।",
        "step1_label": "ধাপ ১/৬: মোবাইল যাচাইকরণ",
        "mobile_verification": "মোবাইল যাচাইকরণ", "send_otp": "OTP পাঠান",
        "mobile_label": "মোবাইল নম্বর", "mobile_placeholder": "১০ সংখ্যার মোবাইল নম্বর",
        "security_check": "নিরাপত্তা পরীক্ষা: কত হবে",
        "otp_note": "আপনার মোবাইল নম্বরে SMS দ্বারা OTP পাঠানো হবে। OTP ১০ মিনিট বৈধ।",
        "enter_otp": "OTP দিন", "otp_sent_to": "OTP পাঠানো হয়েছে এই নম্বরে:",
        "otp_label": "৬ সংখ্যার OTP দিন", "verify_button": "যাচাই করে এগিয়ে যান",
        "step2_title": "ধাপ ২/৬: ব্যক্তিগত বিবরণ",
        "personal_details": "ব্যক্তিগত বিবরণ",
        "applicant_name_label": "আবেদনকারীর পুরো নাম (বয়সের প্রমাণপত্র অনুযায়ী)",
        "dob_label": "জন্ম তারিখ (DD/MM/YYYY)", "dob_placeholder": "দিন/মাস/বছর",
        "gender_label": "লিঙ্গ", "gender_select": "--লিঙ্গ বাছুন--",
        "gender_male": "পুরুষ", "gender_female": "মহিলা", "gender_other": "অন্যান্য",
        "marital_status_label": "বৈবাহিক অবস্থা", "marital_select": "--অবস্থা বাছুন--",
        "marital_married": "বিবাহিত", "marital_unmarried": "অবিবাহিত", "marital_widowed": "বিধবা/বিপত্নীক",
        "husband_name_label": "স্বামীর নাম (শুধুমাত্র বিবাহিত মহিলাদের জন্য)",
        "husband_employer_label": "স্বামীর কর্মস্থল (ঐচ্ছিক)",
        "husband_help": "দ্রষ্টব্য: শুধুমাত্র বিবাহিত আবেদনকারীদের জন্য প্রযোজ্য।",
        "mandatory_note": "* চিহ্নিত ক্ষেত্রগুলি বাধ্যতামূলক।",
        "save_continue": "সংরক্ষণ করে এগিয়ে যান",
        "step3_title": "ধাপ ৩/৬: ঠিকানার বিবরণ",
        "address_details": "ঠিকানার বিবরণ",
        "village_label": "গ্রাম / শহর", "block_label": "ব্লক",
        "block_select": "--ব্লক বাছুন--",
        "step4_title": "ধাপ ৪/৬: ব্যাঙ্ক অ্যাকাউন্টের বিবরণ",
        "bank_details_title": "পেনশন প্রদানের জন্য ব্যাঙ্ক বিবরণ",
        "bank_account_label": "ব্যাঙ্ক অ্যাকাউন্ট নম্বর", "ifsc_label": "IFSC কোড",
        "dbt_note": "পেনশন সরাসরি DBT মাধ্যমে এই অ্যাকাউন্টে জমা হবে। অ্যাকাউন্টটি আবেদনকারীর নিজের নামে হতে হবে।",
        "step5_title": "ধাপ ৫/৬: নথি আপলোড",
        "upload_heading": "বয়সের প্রমাণপত্র আপলোড করুন",
        "upload_help": "গ্রহণযোগ্য নথি: আধার কার্ড, ভোটার কার্ড, রেশন কার্ড, জন্ম সার্টিফিকেট। ফর্ম্যাট: JPG, PNG, বা PDF (১০ MB পর্যন্ত)।",
        "select_doc": "নথি বাছুন", "upload_button": "আপলোড করে এগিয়ে যান",
        "step6_title": "ধাপ ৬/৬: পর্যালোচনা ও ঘোষণা",
        "review_heading": "আবেদনের বিবরণ পর্যালোচনা করুন",
        "review_subheading": "চূড়ান্ত জমা দেওয়ার আগে সমস্ত বিবরণ সঠিক কিনা তা যাচাই করুন।",
        "edit_link": "সম্পাদনা করুন", "uploaded_doc_label": "আপলোড করা নথি", "doc_uploaded": "নথি সফলভাবে আপলোড হয়েছে",
        "declaration_heading": "ঘোষণা",
        "declaration_text": "আমি ঘোষণা করছি যে উপরে প্রদত্ত তথ্য আমার জ্ঞানত সত্য। কোনও তথ্য ভুল প্রমাণিত হলে পেনশন বাতিল হতে পারে।",
        "agree_checkbox": "আমি উপরের ঘোষণায় সম্মত।",
        "submit_btn": "আবেদন জমা দিন",
        "submitted_heading": "আবেদন সফলভাবে জমা হয়েছে",
        "submitted_msg": "আপনার পেনশন আবেদন জমা হয়েছে।",
        "app_no_label": "আবেদন নম্বর",
        "app_received_note": "আপনার আবেদন নম্বর সংরক্ষণ করুন। স্ট্যাটাস পোর্টালে মোবাইল নম্বর দিয়ে স্থিতি দেখতে পারবেন।",
        "download_ack": "স্বীকৃতিপত্র ডাউনলোড করুন (PDF)",
        "status_portal_title": "নাগরিক স্ট্যাটাস পোর্টাল",
        "password_label": "পাসওয়ার্ড (জন্ম তারিখ DDMMYYYY রূপে)",
        "login_btn": "লগইন", "forgot_password": "পাসওয়ার্ড ভুলে গেছেন?",
        "app_status_title": "আবেদনের স্থিতি",
        "status_label": "বর্তমান স্থিতি", "submitted_at_label": "জমার তারিখ", "decided_at_label": "সিদ্ধান্তের তারিখ",
        "correct_details_btn": "বিবরণ সংশোধন করুন",
        "withdraw_btn": "অপেক্ষমাণ আবেদন প্রত্যাহার করুন",
        "edit_heading": "অপেক্ষমাণ আবেদন সংশোধন",
        "edit_note": "আবেদন বিবেচনাধীন থাকাকালীন বিবরণ সংশোধন করা যেতে পারে।",
        "save_correction": "সংশোধন সংরক্ষণ করুন",
        "reset_title": "পাসওয়ার্ড রিসেট করুন",
        "registered_mobile_label": "নিবন্ধিত মোবাইল নম্বর",
        "reset_password_btn": "SMS মাধ্যমে পাসওয়ার্ড পাঠান",
    },
    "ml": {
        "title": "സേവാ സേതു - വയോജന പെൻഷൻ പോർട്ടൽ",
        "department": "സാമൂഹ്യക്ഷേമ വകുപ്പ് · പൂർവാഞ്ചൽ സർക്കാർ",
        "help": "സഹായം വേണമോ? ഈ പെൻഷൻ സേവനം സൗജന്യമാണ്. ഏജന്റിന് പണം നൽകരുത്, OTP പങ്കിടരുത്.",
        "choose_language": "ഭാഷ തിരഞ്ഞെടുക്കുക",
        "language_help": "ഭാഷ പിന്നീട് മാറ്റാം. അപേക്ഷിക്കാൻ ആരെയും പണം നൽകേണ്ടതില്ല.",
        "continue": "തുടരുക", "change_language": "ഭാഷ മാറ്റുക",
        "read_aloud": "ഈ പേജ് വായിച്ചു കേൾപ്പിക്കുക", "home": "ഹോം",
        "welcome": "സ്വാഗതം", "apply": "പെൻഷന് അപേക്ഷിക്കുക",
        "scheme": "60 വയസോ അതിൽ കൂടുതലോ പ്രായമുള്ള അർഹരായ മുതിർന്ന പൗരന്മാർക്കുള്ള പ്രതിമാസ പെൻഷൻ പദ്ധതിയാണിത്.",
        "status": "അപേക്ഷയുടെ സ്ഥിതി പരിശോധിക്കുക", "free_help": "അപേക്ഷിക്കാൻ ആരെയും പണം നൽകേണ്ടതില്ല.",
        "free_help_detail": "സൗജന്യ സഹായത്തിനായി അടുത്തുള്ള ബ്ലോക്ക് ഡെവലപ്മെന്റ് ഓഫീസിൽ പോകുക.",
        "how_to_apply": "എങ്ങനെ അപേക്ഷിക്കാം", "apply_help": "സൗജന്യ സഹായത്തിനായി അടുത്തുള്ള സർക്കാർ ഓഫീസിൽ പോകുക.",
        "mobile_verification": "മൊബൈൽ പരിശോധന", "send_otp": "OTP അയയ്ക്കുക",
        "step1_label": "ഘട്ടം 1/6: മൊബൈൽ പരിശോധന",
        "mobile_label": "മൊബൈൽ നമ്പർ", "mobile_placeholder": "10 അക്ക മൊബൈൽ നമ്പർ",
        "security_check": "സുരക്ഷാ പരിശോധന: എത്രയാണ്",
        "otp_note": "നിങ്ങളുടെ മൊബൈൽ നമ്പറിലേക്ക് OTP അയയ്ക്കും. 10 മിനിറ്റ് സാധുത.",
        "enter_otp": "OTP നൽകുക", "otp_sent_to": "OTP അയച്ചിരിക്കുന്നു:",
        "otp_label": "6 അക്ക OTP നൽകുക", "verify_button": "പരിശോധിച്ച് തുടരുക",
        "step2_title": "ഘട്ടം 2/6: വ്യക്തിഗത വിവരങ്ങൾ",
        "personal_details": "വ്യക്തിഗത വിവരങ്ങൾ",
        "applicant_name_label": "അപേക്ഷകന്റെ മുഴുവൻ പേര്",
        "dob_label": "ജനനത്തീയതി (DD/MM/YYYY)", "dob_placeholder": "DD/MM/YYYY",
        "gender_label": "ലിംഗം", "gender_select": "--തിരഞ്ഞെടുക്കുക--",
        "gender_male": "പുരുഷൻ", "gender_female": "സ്ത്രീ", "gender_other": "മറ്റുള്ളവ",
        "marital_status_label": "വൈവാഹിക പദവി", "marital_select": "--തിരഞ്ഞെടുക്കുക--",
        "marital_married": "വിവാഹിതൻ/വിവാഹിത", "marital_unmarried": "അവിവാഹിതൻ/അവിവാഹിത", "marital_widowed": "വിധവ/വിധുരൻ",
        "husband_name_label": "ഭർത്താവിന്റെ പേര് (വിവാഹിതരായ സ്ത്രീകൾക്ക് മാത്രം)",
        "husband_employer_label": "ഭർത്താവിന്റെ തൊഴിൽ (ഓപ്ഷണൽ)",
        "husband_help": "ശ്രദ്ധിക്കുക: പങ്കാളിയുടെ വിവരങ്ങൾ നിർബന്ധമല്ല.",
        "mandatory_note": "* അടയാളപ്പെടുത്തിയവ നിർബന്ധമാണ്.",
        "save_continue": "സേവ് ചെയ്ത് തുടരുക",
        "step3_title": "ഘട്ടം 3/6: വിലാസം",
        "address_details": "വിലാസം", "village_label": "ഗ്രാമം / പട്ടണം", "block_label": "ബ്ലോക്ക്",
        "block_select": "--ബ്ലോക്ക് തിരഞ്ഞെടുക്കുക--",
        "step4_title": "ഘട്ടം 4/6: ബാങ്ക് വിവരങ്ങൾ",
        "bank_details_title": "പെൻഷൻ ബാങ്ക് വിവരങ്ങൾ",
        "bank_account_label": "ബാങ്ക് അക്കൗണ്ട് നമ്പർ", "ifsc_label": "IFSC കോഡ്",
        "dbt_note": "പെൻഷൻ നേരിട്ട് ബാങ്ക് അക്കൗണ്ടിലേക്ക് എത്തും. അക്കൗണ്ട് അപേക്ഷകന്റെ പേരിൽ ആയിരിക്കണം.",
        "step5_title": "ഘട്ടം 5/6: രേഖ അപ്‌ലോഡ്",
        "upload_heading": "പ്രായ രേഖ അപ്‌ലോഡ് ചെയ്യുക",
        "upload_help": "ആധാർ, വോട്ടർ ഐഡി, റേഷൻ കാർഡ്, ജനന സർട്ടിഫിക്കറ്റ് (JPG, PNG, PDF 10 MB വരെ).",
        "select_doc": "രേഖ തിരഞ്ഞെടുക്കുക", "upload_button": "അപ്‌ലോഡ് ചെയ്യുക",
        "step6_title": "ഘട്ടം 6/6: പരിശോധനയും സത്യപ്രസ്താവനയും",
        "review_heading": "വിവരങ്ങൾ പരിശോധിക്കുക",
        "review_subheading": "സമർപ്പിക്കുന്നതിന് മുൻപ് എല്ലാ വിവരങ്ങളും ശരിയാണെന്ന് ഉറപ്പാക്കുക.",
        "edit_link": "മാറ്റം വരുത്തുക", "uploaded_doc_label": "അപ്‌ലോഡ് ചെയ്ത രേഖ", "doc_uploaded": "രേഖ ലഭ്യമാണ്",
        "declaration_heading": "സത്യപ്രസ്താവന",
        "declaration_text": "മുകളിൽ നൽകിയ വിവരങ്ങൾ സത്യമാണെന്ന് ഞാൻ പ്രസ്താവിക്കുന്നു.",
        "agree_checkbox": "ഞാൻ യോജിക്കുന്നു.", "submit_btn": "അപേക്ഷ സമർപ്പിക്കുക",
        "submitted_heading": "അപേക്ഷ സമർപ്പിച്ചു", "submitted_msg": "നിങ്ങളുടെ അപേക്ഷ ലഭിച്ചു.",
        "app_no_label": "അപേക്ഷ നമ്പർ",
        "app_received_note": "അപേക്ഷ നമ്പർ സൂക്ഷിക്കുക. മൊബൈൽ നമ്പർ ഉപയോഗിച്ച് സ്ഥിതി പരിശോധിക്കാം.",
        "download_ack": "അംഗീകാര പത്രം ഡൗൺലോഡ് ചെയ്യുക (PDF)",
        "status_portal_title": "സ്റ്റാറ്റസ് പോർട്ടൽ",
        "password_label": "പാസ്‌വേഡ് (ജനനത്തീയതി DDMMYYYY)", "login_btn": "ലോഗിൻ", "forgot_password": "പാസ്‌വേഡ് മറന്നോ?",
        "app_status_title": "അപേക്ഷയുടെ സ്ഥിതി",
        "status_label": "നിലവിലെ സ്ഥിതി", "submitted_at_label": "സമർപ്പിച്ച തീയതി", "decided_at_label": "തീരുമാന തീയതി",
        "correct_details_btn": "വിവരങ്ങൾ തിരുത്തുക", "withdraw_btn": "അപേക്ഷ പിൻവലിക്കുക",
        "edit_heading": "അപേക്ഷയിലെ തിരുത്തലുകൾ",
        "edit_note": "തീരുമാനമാകുന്നതുവരെ വിവരങ്ങൾ തിരുത്താം.", "save_correction": "സേവ് ചെയ്യുക",
        "reset_title": "പാസ്‌വേഡ് റീസെറ്റ്",
        "registered_mobile_label": "രജിസ്റ്റർ ചെയ്ത മൊബൈൽ നമ്പർ", "reset_password_btn": "SMS വഴി പാസ്‌വേഡ് അയയ്ക്കുക",
    },
    "mr": {
        "title": "सेवा सेतू - वृद्धापकाळ निवृत्तीवेतन पोर्टल",
        "department": "समाज कल्याण विभाग · पूर्वांचल सरकार",
        "help": "मदत हवी आहे? ही निवृत्तीवेतन सेवा विनामूल्य आहे. एजंटला पैसे देऊ नका किंवा OTP शेअर करू नका.",
        "choose_language": "आपली भाषा निवडा",
        "language_help": "आपण ही भाषा नंतर कधीही बदलू शकता. अर्ज करण्यासाठी कोणालाही पैसे देण्याची गरज नाही.",
        "continue": "पुढे जा", "change_language": "भाषा बदला",
        "read_aloud": "हे पृष्ठ मोठ्याने वाचा", "home": "मुख्यपृष्ठ",
        "welcome": "स्वागत आहे", "apply": "निवृत्तीवेतनासाठी अर्ज करा",
        "scheme": "वृद्धापकाळ निवृत्तीवेतन योजनेअंतर्गत पूर्वांचलमध्ये राहणाऱ्या ६० वर्षे किंवा त्याहून अधिक वयाच्या पात्र ज्येष्ठ नागरिकांना दरमहा रु. २५० निवृत्तीवेतन दिले जाते.",
        "free_help_detail": "आपण प्रथमच अर्ज करत असल्यास, आपल्या ब्लॉक विकास कार्यालयातील सरकारी मदत कक्ष आपल्याला विनामूल्य मदत करेल. पोचपावती घ्या आणि अर्ज क्रमांक जतन करा.",
        "window": "अर्जाची मुदत अंदाजे", "closed": "या योजनेसाठी अर्ज करण्याची मुदत संपली आहे.",
        "steps": [
            "आपला मोबाइल क्रमांक आणि पाठवलेला एकवेळचा कोड (OTP) टाका.",
            "वयाच्या पुराव्याच्या कागदपत्रावर जसे नाव आहे तसेच आपले पूर्ण नाव टाका.",
            "आपला पत्ता आणि बँक खात्याची माहिती टाका. अर्ज सादर करण्यापूर्वी सर्व माहिती तपासता येईल.",
            "वयाचा पुरावा अपलोड करा (आधार, मतदार ओळखपत्र, रेशन कार्ड किंवा जन्म प्रमाणपत्र, कमाल १० MB).",
            "शेवटच्या पृष्ठावर माहिती तपासा, अर्ज सादर करा आणि पोचपावती क्रमांक जतन करा."
        ],
        "safety": "आपला OTP किंवा बँक PIN कधीही शेअर करू नका. अर्ज सादर करण्यासाठी विभाग कोणतेही शुल्क घेत नाही.",
        "free_assistance": "विनामूल्य मदतीसाठी जवळच्या ब्लॉक विकास कार्यालयाला भेट द्या किंवा",
        "hours_suffix": "तास (३१ ऑक्टोबरच्या मध्यरात्री).",
        "service_footer": "सरकारी नागरिक सेवा · पूर्वांचल समाज कल्याण विभाग",
        "about": "योजनेबद्दल", "rti": "माहितीचा अधिकार", "grievance": "तक्रार कक्ष", "contact": "संपर्क करा",
        "status": "अर्जाची स्थिती तपासा", "free_help": "अर्ज करण्यासाठी कोणालाही पैसे देण्याची गरज नाही.",
        "how_to_apply": "अर्ज कसा करावा", "apply_help": "विनामूल्य मदतीसाठी जवळच्या ब्लॉक विकास कार्यालयाला भेट द्या.",
        "step1_label": "टप्पा १/६: मोबाइल पडताळणी", "mobile_verification": "मोबाइल पडताळणी", "send_otp": "OTP पाठवा",
        "mobile_label": "मोबाइल क्रमांक", "mobile_placeholder": "१० अंकी मोबाइल क्रमांक",
        "security_check": "सुरक्षा तपासणी: किती आहे", "otp_note": "आपल्या मोबाइल क्रमांकावर SMS द्वारे OTP पाठवला जाईल. OTP १० मिनिटांसाठी वैध आहे.",
        "enter_otp": "OTP टाका", "otp_sent_to": "या क्रमांकावर OTP पाठवला आहे:", "otp_label": "६ अंकी OTP टाका", "verify_button": "पडताळा आणि पुढे जा",
        "step2_title": "टप्पा २/६: वैयक्तिक माहिती", "personal_details": "वैयक्तिक माहिती",
        "applicant_name_label": "अर्जदाराचे पूर्ण नाव (वयाच्या पुराव्याप्रमाणे)", "dob_label": "जन्मतारीख (DD/MM/YYYY)", "dob_placeholder": "दिवस/महिना/वर्ष",
        "gender_label": "लिंग", "gender_select": "--लिंग निवडा--", "gender_male": "पुरुष", "gender_female": "महिला", "gender_other": "इतर",
        "marital_status_label": "वैवाहिक स्थिती", "marital_select": "--स्थिती निवडा--", "marital_married": "विवाहित", "marital_unmarried": "अविवाहित", "marital_widowed": "विधवा/विधुर",
        "husband_name_label": "पतीचे नाव (विवाहित महिलांसाठी)", "husband_employer_label": "पतीचा नियोक्ता (ऐच्छिक)",
        "husband_help": "टीप: जोडीदाराची माहिती ऐच्छिक असून ती फक्त विवाहित अर्जदारांसाठी लागू आहे.", "mandatory_note": "* चिन्हांकित फील्ड अनिवार्य आहेत.", "save_continue": "जतन करा आणि पुढे जा",
        "step3_title": "टप्पा ३/६: पत्त्याची माहिती", "address_details": "पत्त्याची माहिती", "village_label": "गाव / शहर", "block_label": "ब्लॉक", "block_select": "--ब्लॉक निवडा--",
        "step4_title": "टप्पा ४/६: बँक माहिती", "bank_details_title": "निवृत्तीवेतन जमा करण्यासाठी बँक माहिती", "bank_account_label": "बँक खाते क्रमांक", "ifsc_label": "IFSC कोड",
        "dbt_note": "निवृत्तीवेतन थेट लाभ हस्तांतरणाद्वारे (DBT) या खात्यात जमा केले जाईल. खाते अर्जदाराच्या नावावर असावे.",
        "step5_title": "टप्पा ५/६: कागदपत्र अपलोड", "upload_heading": "वयाचा पुरावा अपलोड करा",
        "upload_help": "स्वीकारलेली कागदपत्रे: आधार कार्ड, मतदार ओळखपत्र, रेशन कार्ड, जन्म प्रमाणपत्र किंवा शाळेचे प्रमाणपत्र. JPG, PNG किंवा PDF (१० MB पर्यंत).",
        "select_doc": "कागदपत्र निवडा", "upload_button": "अपलोड करा आणि पुढे जा",
        "step6_title": "टप्पा ६/६: तपासणी आणि घोषणा", "review_heading": "अर्जाच्या माहितीची तपासणी करा", "review_subheading": "अर्ज सादर करण्यापूर्वी सर्व माहिती अचूक असल्याची खात्री करा.",
        "edit_link": "दुरुस्त करा", "uploaded_doc_label": "अपलोड केलेले कागदपत्र", "doc_uploaded": "कागदपत्र यशस्वीरीत्या अपलोड झाले",
        "declaration_heading": "घोषणा", "declaration_text": "वर दिलेली माहिती माझ्या माहितीनुसार खरी आहे, अशी मी घोषणा करतो/करते. चुकीची माहिती दिल्यास लागू कायद्यानुसार शिक्षा होऊ शकते आणि निवृत्तीवेतन रद्द केले जाऊ शकते.",
        "agree_checkbox": "मी वरील घोषणेशी सहमत आहे.", "submit_btn": "अर्ज सादर करा", "submitted_heading": "अर्ज यशस्वीरीत्या सादर झाला", "submitted_msg": "आपला निवृत्तीवेतन अर्ज प्राप्त झाला आहे.",
        "app_no_label": "अर्ज क्रमांक", "app_received_note": "आपला अर्ज क्रमांक लिहून ठेवा. नोंदणीकृत मोबाइल क्रमांक वापरून अर्जाची स्थिती तपासता येईल.",
        "download_ack": "पोचपावती डाउनलोड करा (PDF)", "status_portal_title": "नागरिक स्थिती पोर्टल", "password_label": "पासवर्ड (जन्मतारीख DDMMYYYY स्वरूपात)",
        "login_btn": "लॉगिन", "forgot_password": "पासवर्ड विसरलात?", "app_status_title": "अर्जाची स्थिती", "status_label": "सध्याची स्थिती", "submitted_at_label": "सादर केल्याची तारीख", "decided_at_label": "निर्णयाची तारीख",
        "correct_details_btn": "अर्जाची माहिती दुरुस्त करा", "withdraw_btn": "प्रलंबित अर्ज मागे घ्या", "edit_heading": "प्रलंबित अर्ज दुरुस्त करा",
        "edit_note": "अर्ज प्रलंबित असेपर्यंत माहिती दुरुस्त करता येईल.", "save_correction": "दुरुस्ती जतन करा", "reset_title": "पासवर्ड रीसेट करा",
        "registered_mobile_label": "नोंदणीकृत मोबाइल क्रमांक", "reset_password_btn": "SMS द्वारे पासवर्ड पाठवा",
        "show_all_languages": "सर्व भारतीय भाषा दाखवा", "detect_language": "भाषेसाठी स्थान शोधा",
    }
}


def mask_account(val):
    if not val:
        return ""
    val_str = str(val).strip()
    if len(val_str) <= 4:
        return val_str
    return "X" * (len(val_str) - 4) + val_str[-4:]


@app.context_processor
def language_context():
    language = session.get("language", "en")
    translated = dict(TRANSLATIONS["en"])
    translated.update(TRANSLATIONS.get(language, {}))
    return {
        "language": language,
        "language_info": LANGUAGES.get(language, LANGUAGES["en"]),
        "t": translated,
        "mask_account": mask_account,
    }


@app.before_request
def require_language_before_citizen_flow():
    # The homepage shows the language chooser itself; protect the application flow.
    protected_endpoints = {
        "apply", "verify", "form_step", "upload",
        "declaration", "status_login", "view_application",
        "edit_application", "withdraw_application", "reset_password",
    }
    if request.endpoint in protected_endpoints and "language" not in session:
        return redirect(url_for("choose_language"))


@app.after_request
def prevent_stale_language_pages(response):
    if response.content_type.startswith("text/html"):
        response.headers["Cache-Control"] = "no-store, max-age=0"
        response.headers["Pragma"] = "no-cache"
    return response


ADMIN_USERNAME = os.environ.get("SEWASETU_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ["SEWASETU_ADMIN_PASSWORD"]

SMS_GATEWAY_URL = config.get("app", "sms_gateway_url")
OTP_VALIDITY_SECONDS = 600  # 10 minutes for elderly citizens
UPLOAD_DIR = config.get("app", "upload_dir")
IST = ZoneInfo("Asia/Kolkata")
SCHEME_DEADLINE = datetime.strptime(config.get("pension", "scheme_deadline"),
                                    "%Y-%m-%d %H:%M").replace(tzinfo=IST)
MIN_AGE = config.getint("pension", "min_age")
SLA_DAYS = config.getint("pension", "sla_days")

BLOCKS = ["Sonari", "Rajapara", "Dhemaji Pathar", "Borgaon", "Namti", "Khelua"]
DB_POOL = None

# Rate limiting for status login: mobile -> list of timestamps
LOGIN_ATTEMPTS = {}


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
            password=os.environ["SEWASETU_DB_PASSWORD"],
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
            try:
                self._connection.rollback()
            except Exception:
                pass
            self._pool.putconn(self._connection)
            self._returned = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def sanitize(value, maxlen=100):
    # Limit by characters, never UTF-8 bytes, so Indic names remain intact.
    if value is None:
        return ""
    return str(value).strip()[:maxlen]


def hash_password(p):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", p.encode("utf-8"), salt, 310000)
    return "pbkdf2_sha256$310000$%s$%s" % (salt.hex(), digest.hex())


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


SMS_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="sms")


def send_sms_async(mobile, text):
    SMS_EXECUTOR.submit(send_sms, mobile, text)


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
    return render_template(
        "index.html",
        hours_left=deadline_remaining(),
        languages=LANGUAGES,
        show_language_modal=(
            "language" not in session or request.args.get("change") == "1"
        ),
    )


@app.route("/language", methods=["GET", "POST"])
def choose_language():
    if request.method == "POST":
        language = request.form.get("language", "")
        if language not in LANGUAGES:
            abort(400)
        session["language"] = language
        return redirect(url_for("index"))
    return redirect(url_for("index", change="1"))


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
    # Convenience proxy to internal SMS gateway so test probes can read OTPs
    # without opening an extra port.
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
            flash("Please enter a valid 10-digit mobile number.")
            return render_template("apply.html", captcha_q=make_captcha())
        if captcha != str(session.pop("captcha_answer", "")):
            flash("Please solve the security check correctly.")
            return render_template("apply.html", captcha_q=make_captcha())
        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute("SELECT count(*) FROM otps WHERE mobile = %s "
                        "AND created_at > %s",
                        (mobile, now_ist() - timedelta(minutes=15)))
            if cur.fetchone()[0] >= 5:
                flash("Too many OTP requests. Please try again in 15 minutes.")
                return render_template("apply.html", captcha_q=make_captcha())
            code = str(random.randint(100000, 999999))
            cur.execute("INSERT INTO otps (mobile, code, created_at) VALUES (%s, %s, %s)",
                        (mobile, code, now_ist()))
            conn.commit()
        finally:
            cur.close()
            conn.close()

        send_sms_async(mobile, "Your Sewa Setu OTP is %s. Valid for 10 minutes." % code)
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
        try:
            cur.execute("SELECT code, created_at FROM otps WHERE mobile = %s "
                        "ORDER BY id DESC LIMIT 1", (mobile,))
            row = cur.fetchone()
        finally:
            cur.close()
            conn.close()

        if row and row[0] == code:
            age = (now_ist() - row[1]).total_seconds()
            if age > OTP_VALIDITY_SECONDS:
                app.logger.warning("otp expired mobile=%s age=%ds" % (mobile, int(age)))
                flash("OTP expired. Please request a new OTP.")
                return redirect(url_for("apply"))
            session["verified_mobile"] = mobile
            return redirect(url_for("form_step", step=1))
        flash("Invalid OTP. Please check the code sent to your mobile.")
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
            flash("Please select a document to upload.")
            return render_template("upload.html")
        filename = secure_filename(f.filename)
        content = f.read()
        extension = os.path.splitext(filename)[1].lower()
        if extension not in (".pdf", ".jpg", ".jpeg", ".png"):
            flash("Please upload a PDF, JPG, or PNG document.")
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
    return render_template("declaration.html", form_data=session.get("form_data", {}))


def handle_submission():
    mobile = session.get("verified_mobile")
    data = session.get("form_data", {})
    doc_path = session.get("doc_path", "")

    name = sanitize(data.get("applicant_name", ""))
    village = sanitize(data.get("village", ""))
    block = data.get("block", "").strip()
    gender = data.get("gender", "")
    marital = data.get("marital_status", "")
    husband_name = sanitize(data.get("husband_name", ""))
    husband_employer = sanitize(data.get("husband_employer", ""))
    bank_account = data.get("bank_account", "").strip()
    ifsc = data.get("ifsc", "").strip().upper()
    dob_raw = data.get("dob", "").strip()

    if not name:
        flash("Please enter the applicant's full name.")
        return redirect(url_for("form_step", step=1))
    if not dob_raw:
        flash("Please enter the date of birth.")
        return redirect(url_for("form_step", step=1))
    if not village or not block:
        flash("Please enter your complete address and block.")
        return redirect(url_for("form_step", step=2))
    if not bank_account or not ifsc:
        flash("Please enter your bank account number and IFSC code.")
        return redirect(url_for("form_step", step=3))

    # Lenient date parsing: prioritize DD/MM/YYYY for India
    dob = None
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d.%m.%Y"):
        try:
            dob = datetime.strptime(dob_raw, fmt).date()
            break
        except ValueError:
            continue
    if dob is None:
        flash("Please enter a valid date of birth in DD/MM/YYYY format.")
        return redirect(url_for("form_step", step=1))

    today = date.today()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    if age < MIN_AGE:
        flash("Applicant must be 60 years of age or older to be eligible.")
        return redirect(url_for("form_step", step=1))

    if datetime.now(IST) > SCHEME_DEADLINE:
        flash("The application deadline has passed.")
        return redirect(url_for("index"))

    conn = get_db()
    cur = conn.cursor()
    try:
        app_no = new_application_no()
        try:
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
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            flash("An active application already exists for this mobile number. "
                  "You may log in to check its status or correct details.")
            return redirect(url_for("status_login"))
        new_id = cur.fetchone()[0]

        # Status portal account: default password is DOB as DDMMYYYY
        portal_pass = dob.strftime("%d%m%Y")
        cur.execute("SELECT count(*) FROM portal_users WHERE mobile = %s", (mobile,))
        if cur.fetchone()[0] == 0:
            cur.execute("INSERT INTO portal_users (mobile, password_hash) VALUES (%s,%s)",
                        (mobile, hash_password(portal_pass)))
        conn.commit()

        try:
            pdf_bytes = generate_acknowledgment(cur, new_id)
            ack_dir = os.path.join(UPLOAD_DIR, "ack")
            os.makedirs(ack_dir, exist_ok=True)
            with open(os.path.join(ack_dir, "%d.pdf" % new_id), "wb") as out:
                out.write(pdf_bytes)
        except Exception as e:
            app.logger.error("acknowledgment pdf generation warning for %d: %s" % (new_id, e))
    finally:
        cur.close()
        conn.close()

    session.pop("form_data", None)
    session.pop("doc_path", None)
    session.pop("verified_mobile", None)
    session["submitted_application_id"] = new_id
    send_sms_async(mobile, "Sewa Setu: application %s received. Track at the status portal "
                    "with mobile no. and password (DOB as DDMMYYYY)." % app_no)
    return render_template("confirmation.html", app_no=app_no, app_id=new_id)


def generate_acknowledgment(cur, app_id):
    cur.execute("SELECT application_no, applicant_name, mobile, dob, village, block, "
                "bank_account, ifsc, submitted_at, status FROM applications WHERE id = %s",
                (app_id,))
    row = cur.fetchone()
    if not row:
        return b""

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
            "Bengali", "Devanagari", "Arabic", "Gujarati", "Gurmukhi",
            "Kannada", "Malayalam", "Oriya", "Tamil", "Telugu",
        )
        for script in fallback_scripts:
            path = os.path.join(font_dir, "NotoSans%s-Regular.ttf" % script)
            if os.path.exists(path):
                family = "NotoFallback" + script
                pdf.add_font(family, "", path)
                fallback_fonts.append(family)
        if fallback_fonts:
            pdf.set_fallback_fonts(fallback_fonts, exact_match=False)

    font_family = "NotoSans" if has_unicode_font else "Helvetica"
    pdf.set_font(font_family, "B", 14)
    pdf.cell(0, 10, "GOVERNMENT OF PURVANCHAL", ln=1, align="C")
    pdf.set_font(font_family, "", 11)
    pdf.cell(0, 8, "Department of Social Welfare", ln=1, align="C")
    pdf.cell(0, 8, "Old Age Pension Scheme - Acknowledgment Slip", ln=1, align="C")
    pdf.ln(6)

    labels = ["Application No", "Applicant Name", "Mobile", "Date of Birth",
              "Village", "Block", "Bank Account", "IFSC", "Submitted At", "Status"]

    pdf.set_font(font_family, "", 10)
    for label, val in zip(labels, row):
        display_val = str(val) if val is not None else ""
        if label == "Bank Account":
            display_val = mask_account(display_val)
        try:
            pdf.cell(60, 8, label, border=1)
            pdf.cell(0, 8, display_val, border=1, ln=1)
        except Exception:
            pdf.cell(0, 8, sanitize(display_val, 50), border=1, ln=1)

    pdf.ln(8)
    pdf.set_font(font_family, "", 9)
    pdf.multi_cell(0, 5, "This is a computer generated acknowledgment. Processing SLA "
                         "as per the Purvanchal Right to Public Services Act (15 days) applies.")
    return bytes(pdf.output())


# ---------------------------------------------------------------------------
# Status portal (citizen login)
# ---------------------------------------------------------------------------

@app.route("/status", methods=["GET", "POST"])
def status_login():
    if request.method == "POST":
        mobile = request.form.get("mobile", "").strip()
        password = request.form.get("password", "")

        # Rate limiting: max 5 failed attempts per 15 mins
        now = time.time()
        attempts = [t for t in LOGIN_ATTEMPTS.get(mobile, []) if now - t < 900]
        LOGIN_ATTEMPTS[mobile] = attempts
        if len(attempts) >= 5:
            flash("Too many failed login attempts. Please try again in 15 minutes.")
            return render_template("status_login.html")

        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute("SELECT password_hash FROM portal_users WHERE mobile = %s", (mobile,))
            row = cur.fetchone()
        finally:
            cur.close()
            conn.close()

        if row and verify_password(row[0], password):
            LOGIN_ATTEMPTS.pop(mobile, None)
            session["logged_in"] = True
            session["admin"] = False
            session["portal_mobile"] = mobile

            # Upgrade to salted pbkdf2 if old sha256
            if not row[0].startswith("pbkdf2_sha256$"):
                conn = get_db()
                cur = conn.cursor()
                try:
                    cur.execute("UPDATE portal_users SET password_hash = %s WHERE mobile = %s",
                                (hash_password(password), mobile))
                    conn.commit()
                finally:
                    cur.close()
                    conn.close()

            conn = get_db()
            cur = conn.cursor()
            try:
                cur.execute("SELECT id FROM applications WHERE mobile = %s "
                            "ORDER BY submitted_at DESC LIMIT 1", (mobile,))
                r = cur.fetchone()
            finally:
                cur.close()
                conn.close()

            if r:
                session["portal_application_id"] = r[0]
                return redirect(url_for("view_application", app_id=r[0]))
            flash("No application found for this mobile number.")
            return redirect(url_for("status_login"))

        LOGIN_ATTEMPTS.setdefault(mobile, []).append(now)
        flash("Invalid mobile number or password.")
    return render_template("status_login.html")


@app.route("/application/<int:app_id>")
def view_application(app_id):
    if not (is_admin() or citizen_owns_application(app_id)):
        flash("Please login to view application status.")
        return redirect(url_for("status_login"))
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT application_no, applicant_name, mobile, dob, village, block, "
                    "bank_account, ifsc, status, submitted_at, decided_at "
                    "FROM applications WHERE id = %s", (app_id,))
        row = cur.fetchone()
    finally:
        cur.close()
        conn.close()
    if not row:
        abort(404)
    return render_template("application.html", a=row, app_id=app_id)


@app.route("/application/<int:app_id>/edit", methods=["GET", "POST"])
def edit_application(app_id):
    if not citizen_owns_application(app_id):
        abort(403)
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT status, applicant_name, dob, gender, marital_status, "
                    "husband_name, husband_employer, village, block, bank_account, ifsc "
                    "FROM applications WHERE id = %s AND mobile = %s",
                    (app_id, session["portal_mobile"]))
        row = cur.fetchone()
    finally:
        cur.close()
        conn.close()

    if not row:
        abort(404)
    if row[0] != "PENDING":
        flash("Only pending applications can be corrected.")
        return redirect(url_for("view_application", app_id=app_id))

    if request.method == "POST":
        form = request.form
        dob_raw = form.get("dob", "").strip()
        dob = None
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d.%m.%Y", "%m/%d/%Y"):
            try:
                dob = datetime.strptime(dob_raw, fmt).date()
                break
            except ValueError:
                continue
        if dob is None:
            flash("Please enter a valid date of birth in DD/MM/YYYY format.")
            return render_template("edit_application.html", a=row, blocks=BLOCKS)

        conn = get_db()
        cur = conn.cursor()
        try:
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
        finally:
            cur.close()
            conn.close()

        flash("Your correction was saved successfully.")
        return redirect(url_for("view_application", app_id=app_id))

    return render_template("edit_application.html", a=row, blocks=BLOCKS)


@app.route("/application/<int:app_id>/withdraw", methods=["POST"])
def withdraw_application(app_id):
    if not citizen_owns_application(app_id):
        abort(403)
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE applications SET status='WITHDRAWN', decided_at=%s, "
                    "decided_by='CITIZEN' WHERE id=%s AND mobile=%s AND status='PENDING'",
                    (now_ist(), app_id, session["portal_mobile"]))
        conn.commit()
    finally:
        cur.close()
        conn.close()
    flash("Your pending application was withdrawn. You may now submit a new application.")
    return redirect(url_for("status_login"))


@app.route("/ack/<int:app_id>.pdf")
def ack_pdf(app_id):
    just_submitted = session.get("submitted_application_id") == app_id
    if not (is_admin() or citizen_owns_application(app_id) or just_submitted):
        abort(403)
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM applications WHERE id = %s", (app_id,))
        if not cur.fetchone():
            abort(404)
        data = generate_acknowledgment(cur, app_id)
    finally:
        cur.close()
        conn.close()

    response = send_file(io.BytesIO(data), mimetype="application/pdf")
    response.headers["Cache-Control"] = "no-store, max-age=0"
    return response


@app.route("/status/reset", methods=["GET", "POST"])
def reset_password():
    if request.method == "POST":
        mobile = request.form.get("mobile", "").strip()
        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute("SELECT mobile FROM portal_users WHERE mobile = %s", (mobile,))
            row = cur.fetchone()
            if row:
                cur.execute("SELECT dob FROM applications WHERE mobile = %s "
                            "AND status <> 'WITHDRAWN' ORDER BY id DESC LIMIT 1", (mobile,))
                r2 = cur.fetchone()
                if r2:
                    newpass = r2[0].strftime("%d%m%Y")
                    cur.execute("UPDATE portal_users SET password_hash = %s WHERE mobile = %s",
                                (hash_password(newpass), row[0]))
                    conn.commit()
                    send_sms_async(row[0], "Sewa Setu: your password has been reset to your "
                                           "date of birth (DDMMYYYY).")
        finally:
            cur.close()
            conn.close()
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
    try:
        cur.execute("SELECT status, count(*) FROM applications GROUP BY status")
        by_status = cur.fetchall()
        cur.execute("SELECT count(*) FROM applications WHERE status = 'PENDING' "
                    "AND submitted_at < %s", (now_ist() - timedelta(days=SLA_DAYS),))
        overdue = cur.fetchone()[0]
        cur.execute("SELECT block, count(*) FROM applications WHERE status = 'PENDING' "
                    "GROUP BY block ORDER BY count(*) DESC")
        by_block = cur.fetchall()
    finally:
        cur.close()
        conn.close()
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
    try:
        cur.execute("SELECT id, application_no, applicant_name, mobile, block, status, "
                    "submitted_at FROM applications WHERE status = %s "
                    "ORDER BY submitted_at ASC LIMIT 50 OFFSET %s",
                    (status, (page - 1) * 50))
        rows = cur.fetchall()
    finally:
        cur.close()
        conn.close()
    return render_template("admin_list.html", rows=rows, status=status, page=page)


@app.route("/admin/application/<int:app_id>")
def admin_view(app_id):
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT application_no, applicant_name, mobile, dob, gender, "
                    "marital_status, village, block, bank_account, ifsc, doc_path, "
                    "status, submitted_at, decided_at, decided_by "
                    "FROM applications WHERE id = %s", (app_id,))
        row = cur.fetchone()
    finally:
        cur.close()
        conn.close()
    if not row:
        abort(404)
    return render_template("admin_view.html", a=row, app_id=app_id)


@app.route("/admin/approve/<int:app_id>", methods=["POST"])
def admin_approve(app_id):
    if not is_admin():
        abort(403)
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE applications SET status = 'APPROVED', decided_at = %s, decided_by = %s "
                    "WHERE id = %s", (now_ist(), ADMIN_USERNAME, app_id))
        conn.commit()
    finally:
        cur.close()
        conn.close()
    flash("Application approved.")
    return redirect(url_for("admin_list"))


@app.route("/admin/reject/<int:app_id>", methods=["POST"])
def admin_reject(app_id):
    if not is_admin():
        abort(403)
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE applications SET status = 'REJECTED', decided_at = %s, decided_by = %s "
                    "WHERE id = %s", (now_ist(), ADMIN_USERNAME, app_id))
        conn.commit()
    finally:
        cur.close()
        conn.close()
    flash("Application rejected.")
    return redirect(url_for("admin_list"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
