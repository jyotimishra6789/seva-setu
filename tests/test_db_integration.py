import os
import unittest


class DatabaseIntegrationTests(unittest.TestCase):
    """Run with TEST_DATABASE_URL against the PostgreSQL Compose service."""

    @unittest.skipUnless(os.environ.get("TEST_DATABASE_URL"),
                         "set TEST_DATABASE_URL to run PostgreSQL integration tests")
    def test_database_integration_environment_is_configured(self):
        import psycopg2

        conn = psycopg2.connect(os.environ["TEST_DATABASE_URL"])
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT to_regclass('public.auth_attempts')")
                self.assertEqual(cur.fetchone()[0], "auth_attempts")
                cur.execute("SELECT to_regclass('public.job_runs')")
                self.assertEqual(cur.fetchone()[0], "job_runs")
        finally:
            conn.close()
