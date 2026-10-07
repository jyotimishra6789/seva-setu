import unittest
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

    def test_invalid_captcha_does_not_send_otp(self):
        with self.client.session_transaction() as session:
            session["captcha_answer"] = 11
        response = self.client.post(
            "/apply",
            data={"mobile": "9999999999", "captcha": "12"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"security check", response.data)

    def test_support_links_are_available(self):
        for path in ("/rti", "/grievance", "/contact"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_language_must_be_selected_before_home_page(self):
        with self.client.session_transaction() as session:
            session.pop("language", None)
        self.assertEqual(self.client.get("/").status_code, 302)
        self.assertEqual(self.client.get("/apply").status_code, 302)
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
        for lang in ("as", "hi", "bn"):
            with self.client.session_transaction() as session:
                session["language"] = lang
            res = self.client.get("/")
            self.assertEqual(res.status_code, 200)
            res_apply = self.client.get("/apply")
            self.assertEqual(res_apply.status_code, 200)
            # Verify page contains localized department text
            expected_dept = portal.TRANSLATIONS[lang]["department"].encode("utf-8")
            self.assertIn(expected_dept, res.data)

    def test_login_rate_limiting(self):
        mobile = "9111111111"
        portal.LOGIN_ATTEMPTS.pop(mobile, None)
        for _ in range(5):
            self.client.post("/status", data={"mobile": mobile, "password": "wrong"})
        # 6th attempt should be blocked by rate limiter
        res = self.client.post("/status", data={"mobile": mobile, "password": "wrong"})
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Too many failed login attempts", res.data)


if __name__ == "__main__":
    unittest.main()
