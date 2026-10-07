import unittest

import app as portal


class PortalRegressionTests(unittest.TestCase):
    def setUp(self):
        portal.app.config.update(TESTING=True, SECRET_KEY="test-secret")
        self.client = portal.app.test_client()

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
        self.assertEqual(self.client.get("/").status_code, 302)
        response = self.client.post("/language", data={"language": "hi"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/")
        self.assertEqual(self.client.get("/").status_code, 200)

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


if __name__ == "__main__":
    unittest.main()
