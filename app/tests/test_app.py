import unittest
import time
from datetime import datetime, timedelta

import app as portal


class PortalRegressionTests(unittest.TestCase):
    def setUp(self):
        portal.app.config.update(TESTING=True, SECRET_KEY="test-secret")
        self.client = portal.app.test_client()
        with self.client.session_transaction() as session:
            session["language"] = "en"

    def test_unicode_names_are_limited_by_characters(self):
        name = "অসমীয়া নাগৰিক"
        self.assertEqual(portal.sanitize(name, maxlen=100), name)
        self.assertEqual(len(portal.sanitize("অ" * 50, maxlen=10)), 10)

    def test_dates_are_parsed_day_first(self):
        self.assertEqual(
            portal.parse_date_of_birth("03/04/1950"),
            datetime(1950, 4, 3).date(),
        )
        self.assertIsNone(portal.parse_date_of_birth("04/31/1950"))

    def test_document_signature_is_checked(self):
        self.assertTrue(portal.document_signature_matches(".pdf", b"%PDF-1.7"))
        self.assertTrue(portal.document_signature_matches(".jpg", b"\xff\xd8\xff\xe0"))
        self.assertFalse(portal.document_signature_matches(".jpg", b"%PDF-1.7"))

    def test_submission_requires_uploaded_document(self):
        with self.client.session_transaction() as session:
            session["verified_mobile"] = "9888888888"
            session["form_data"] = {
                "applicant_name": "Kamala Devi",
                "dob": "15/08/1955",
                "village": "Namti Gaon",
                "block": "Namti",
                "bank_account": "123456789012",
                "ifsc": "SBIN0001234",
            }
        response = self.client.post("/declaration")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/upload")

    def test_citizen_cannot_view_another_application(self):
        with self.client.session_transaction() as session:
            session["logged_in"] = True
            session["admin"] = False
            session["portal_application_id"] = 10
        response = self.client.get("/application/11")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/status")

    def test_citizen_cannot_approve_an_application(self):
        with self.client.session_transaction() as session:
            session["logged_in"] = True
            session["admin"] = False
        response = self.client.post("/admin/approve/10")
        self.assertEqual(response.status_code, 403)

    def test_invalid_mobile_does_not_send_otp(self):
        response = self.client.post(
            "/apply",
            data={"mobile": "123"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"valid 10-digit mobile number", response.data)

    def test_support_links_are_available(self):
        for path in ("/rti", "/grievance", "/contact"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_home_page_shows_language_modal_before_selection(self):
        with self.client.session_transaction() as session:
            session.pop("language", None)
        home = self.client.get("/")
        self.assertEqual(home.status_code, 200)
        self.assertIn(b"language-modal", home.data)
        self.assertEqual(self.client.get("/apply").status_code, 200)
        response = self.client.post("/language", data={"language": "hi"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/")
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_selected_language_redirects_to_localized_home(self):
        response = self.client.post("/language", data={"language": "ml"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/")
        home = self.client.get("/")
        self.assertEqual(home.status_code, 200)
        self.assertIn("സേവാ സേതു".encode("utf-8"), home.data)
        self.assertEqual(home.headers["Cache-Control"], "no-store, max-age=0")

    def test_language_selection_always_stays_on_home_page(self):
        language_page = self.client.get("/language")
        self.assertEqual(language_page.status_code, 302)
        self.assertEqual(language_page.headers["Location"], "/?change=1")
        home = self.client.get("/?change=1")
        self.assertEqual(home.status_code, 200)
        self.assertIn(b"language-modal", home.data)

    def test_password_hashes_are_not_deterministic(self):
        first = portal.hash_password("04071950")
        second = portal.hash_password("04071950")
        self.assertNotEqual(first, second)
        self.assertTrue(portal.verify_password(first, "04071950"))
        self.assertFalse(portal.verify_password(first, "wrong"))

    def test_new_submission_can_download_its_acknowledgment(self):
        with self.client.session_transaction() as session:
            session["submitted_application_id"] = 123
        with self.client.session_transaction() as session:
            self.assertEqual(session["submitted_application_id"], 123)

    def test_bank_account_masking(self):
        self.assertEqual(portal.mask_account("123456789012"), "XXXXXXXX9012")
        self.assertEqual(portal.mask_account("9876"), "9876")
        self.assertEqual(portal.mask_account(""), "")

    def test_widow_not_blocked_by_husband_fields(self):
        with self.client.session_transaction() as session:
            session["verified_mobile"] = "9888888888"
            session["form_data"] = {
                "applicant_name": "Kamala Devi",
                "dob": "15/08/1955",
                "gender": "Female",
                "marital_status": "Widowed",
                "husband_name": "",
                "husband_employer": "",
                "village": "Namti Gaon",
                "block": "Namti",
                "bank_account": "123456789012",
                "ifsc": "SBIN0001234",
            }
            session["doc_path"] = "/var/sewasetu/uploads/dummy.jpg"

        response = self.client.get("/declaration")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Kamala Devi", response.data)
        # Verify bank account is masked in the review table
        self.assertIn(b"XXXXXXXX9012", response.data)

    def test_language_translations_propagate_to_all_pages(self):
        for lang in ("as", "hi", "bn", "mr"):
            res = self.client.get("/?lang=%s" % lang)
            self.assertEqual(res.status_code, 200)
            res_apply = self.client.get("/apply")
            self.assertEqual(res_apply.status_code, 200)
            # Verify page contains localized department text
            expected_dept = portal.TRANSLATIONS[lang]["department"].encode("utf-8")
            self.assertIn(expected_dept, res.data)
            upload_text = portal.TRANSLATIONS[lang]["upload_help"]
            self.assertNotIn("10 MB", upload_text)
            self.assertIn(str(portal.UPLOAD_MAX_MB), res_apply.data.decode("utf-8"))

    def test_marathi_language_is_used_after_selection(self):
        response = self.client.post("/language", data={"language": "mr"})
        self.assertEqual(response.status_code, 302)
        home = self.client.get("/")
        self.assertIn("स्वागत आहे".encode("utf-8"), home.data)
        self.assertIn("निवृत्तीवेतनासाठी अर्ज करा".encode("utf-8"), home.data)
        self.assertNotIn(b"Welcome", home.data)

    def test_login_rate_limiting(self):
        mobile = "9111111111"
        portal.LOGIN_ATTEMPTS[mobile] = [time.time()] * 5
        # 6th attempt should be blocked by rate limiter
        res = self.client.post("/status", data={"mobile": mobile, "password": "wrong"})
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Too many failed login attempts", res.data)

    def test_effective_status_deems_old_pending_application(self):
        old = datetime.now() - timedelta(days=portal.SLA_DAYS, minutes=1)
        self.assertEqual(
            portal.effective_status("PENDING", old),
            "DEEMED_APPROVED",
        )
        self.assertEqual(portal.effective_status("PENDING", datetime.now()), "PENDING")


if __name__ == "__main__":
    unittest.main()
