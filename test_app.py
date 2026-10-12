import unittest
import tempfile
import os
from pathlib import Path
from datetime import datetime, date, timedelta
import app


class PrepTrackTestCase(unittest.TestCase):
    def setUp(self):
        # Create an isolated temporary SQLite database for each test
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        app.app.config["DATABASE"] = Path(self.db_path)
        app.app.config["TESTING"] = True
        app.init_db()
        self.client = app.app.test_client()

    def tearDown(self):
        os.close(self.db_fd)
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_database_initialization(self):
        with app.get_db() as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
            table_names = [row["name"] for row in tables]
            self.assertIn("dsa_questions", table_names)
            self.assertIn("aptitude_logs", table_names)
            self.assertIn("mock_tests", table_names)

            # Verify completed_at column exists in dsa_questions
            columns = [row["name"] for row in conn.execute("PRAGMA table_info(dsa_questions)").fetchall()]
            self.assertIn("completed_at", columns)

    def test_dashboard_empty_state(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"PrepTrack", response.data)
        self.assertIn(b"No DSA questions yet", response.data)
        self.assertIn(b"0%", response.data)

    def test_dsa_flow(self):
        # 1. Add valid question
        res = self.client.post(
            "/add-dsa",
            data={"title": "Binary Search", "topic": "Algorithms", "difficulty": "Medium"},
            follow_redirects=True,
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"DSA question added!", res.data)
        self.assertIn(b"Binary Search", res.data)
        self.assertIn(b"Medium", res.data)
        self.assertIn(b"Pending", res.data)

        # 2. Toggle status to Completed
        with app.get_db() as conn:
            q_id = conn.execute("SELECT id FROM dsa_questions WHERE title='Binary Search'").fetchone()["id"]

        res = self.client.post(f"/toggle-dsa/{q_id}", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Question status updated to Completed.", res.data)
        self.assertIn(b"Completed", res.data)

        # Toggle back to Pending
        res = self.client.post(f"/toggle-dsa/{q_id}", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Question status updated to Pending.", res.data)

        # 3. Delete question
        res = self.client.post(f"/delete-dsa/{q_id}", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"DSA question deleted.", res.data)
        self.assertNotIn(b"Binary Search", res.data)

    def test_dsa_validation(self):
        # Missing title
        res = self.client.post(
            "/add-dsa",
            data={"title": "", "topic": "Arrays", "difficulty": "Easy"},
            follow_redirects=True,
        )
        self.assertIn(b"Please enter both a question title and topic.", res.data)

        # Missing topic
        res = self.client.post(
            "/add-dsa",
            data={"title": "Two Sum", "topic": "   ", "difficulty": "Easy"},
            follow_redirects=True,
        )
        self.assertIn(b"Please enter both a question title and topic.", res.data)

        # Invalid difficulty defaults safely to Easy
        res = self.client.post(
            "/add-dsa",
            data={"title": "Reverse Linked List", "topic": "Linked Lists", "difficulty": "Extreme"},
            follow_redirects=True,
        )
        self.assertIn(b"DSA question added!", res.data)
        with app.get_db() as conn:
            row = conn.execute("SELECT difficulty FROM dsa_questions WHERE title='Reverse Linked List'").fetchone()
            self.assertEqual(row["difficulty"], "Easy")

    def test_aptitude_flow_and_validation(self):
        # 1. Valid insertion
        res = self.client.post(
            "/add-aptitude",
            data={
                "aptitude_topic": "Time and Work",
                "questions_solved": "15",
                "minutes_spent": "45",
                "practice_date": "2026-10-10",
            },
            follow_redirects=True,
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Aptitude practice saved!", res.data)
        self.assertIn(b"Time and Work", res.data)
        self.assertIn(b"15", res.data)

        # 2. Negative questions or minutes rejected
        res = self.client.post(
            "/add-aptitude",
            data={
                "aptitude_topic": "Speed & Distance",
                "questions_solved": "-5",
                "minutes_spent": "30",
                "practice_date": "2026-10-10",
            },
            follow_redirects=True,
        )
        self.assertIn(b"Questions and minutes cannot be negative.", res.data)

        # 3. Invalid date rejected
        res = self.client.post(
            "/add-aptitude",
            data={
                "aptitude_topic": "Profit & Loss",
                "questions_solved": "10",
                "minutes_spent": "20",
                "practice_date": "invalid-date",
            },
            follow_redirects=True,
        )
        self.assertIn(b"Please provide a valid date in YYYY-MM-DD format.", res.data)

        # 4. Delete aptitude log
        with app.get_db() as conn:
            log_id = conn.execute("SELECT id FROM aptitude_logs WHERE topic='Time and Work'").fetchone()["id"]

        res = self.client.post(f"/delete-aptitude/{log_id}", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Aptitude practice log deleted.", res.data)
        self.assertNotIn(b"Time and Work", res.data)

    def test_mock_test_flow_and_validation(self):
        # 1. Valid insertion
        res = self.client.post(
            "/add-mock",
            data={
                "test_name": "Infosys Pseudocode Mock",
                "score": "38",
                "total_marks": "40",
                "test_date": "2026-10-11",
            },
            follow_redirects=True,
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Mock-test score saved!", res.data)
        self.assertIn(b"Infosys Pseudocode Mock", res.data)

        # 2. Score > total marks rejected
        res = self.client.post(
            "/add-mock",
            data={
                "test_name": "Invalid Score Test",
                "score": "55",
                "total_marks": "50",
                "test_date": "2026-10-11",
            },
            follow_redirects=True,
        )
        self.assertIn(b"Score must be between 0 and total marks; total must be above zero.", res.data)

        # 3. Total marks <= 0 rejected
        res = self.client.post(
            "/add-mock",
            data={
                "test_name": "Zero Total Test",
                "score": "0",
                "total_marks": "0",
                "test_date": "2026-10-11",
            },
            follow_redirects=True,
        )
        self.assertIn(b"Score must be between 0 and total marks; total must be above zero.", res.data)

        # 4. Invalid date rejected
        res = self.client.post(
            "/add-mock",
            data={
                "test_name": "Bad Date Test",
                "score": "10",
                "total_marks": "20",
                "test_date": "not-a-date",
            },
            follow_redirects=True,
        )
        self.assertIn(b"Please provide a valid date in YYYY-MM-DD format.", res.data)

        # 5. Delete mock test
        with app.get_db() as conn:
            mock_id = conn.execute("SELECT id FROM mock_tests WHERE test_name='Infosys Pseudocode Mock'").fetchone()["id"]

        res = self.client.post(f"/delete-mock/{mock_id}", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Mock-test record deleted.", res.data)
        self.assertNotIn(b"Infosys Pseudocode Mock", res.data)

    def test_dashboard_statistics_calculations(self):
        # Add 3 DSA questions (2 completed, 1 pending -> 67% completion)
        self.client.post("/add-dsa", data={"title": "Q1", "topic": "Arrays", "difficulty": "Easy"})
        self.client.post("/add-dsa", data={"title": "Q2", "topic": "Strings", "difficulty": "Medium"})
        self.client.post("/add-dsa", data={"title": "Q3", "topic": "Trees", "difficulty": "Hard"})

        with app.get_db() as conn:
            q1_id = conn.execute("SELECT id FROM dsa_questions WHERE title='Q1'").fetchone()["id"]
            q2_id = conn.execute("SELECT id FROM dsa_questions WHERE title='Q2'").fetchone()["id"]
        self.client.post(f"/toggle-dsa/{q1_id}")
        self.client.post(f"/toggle-dsa/{q2_id}")

        # Add 2 aptitude logs (20 + 30 = 50 total questions)
        self.client.post("/add-aptitude", data={"aptitude_topic": "T1", "questions_solved": "20", "minutes_spent": "30", "practice_date": "2026-10-10"})
        self.client.post("/add-aptitude", data={"aptitude_topic": "T2", "questions_solved": "30", "minutes_spent": "40", "practice_date": "2026-10-11"})

        # Add 2 mock tests: (40/50 = 80%) and (90/100 = 90%) -> avg = 85.0%
        self.client.post("/add-mock", data={"test_name": "M1", "score": "40", "total_marks": "50", "test_date": "2026-10-10"})
        self.client.post("/add-mock", data={"test_name": "M2", "score": "90", "total_marks": "100", "test_date": "2026-10-11"})

        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        # Check DSA stats: 3 total, 2 completed, 67%
        self.assertIn(b"3", res.data)
        self.assertIn(b"2 completed", res.data)
        self.assertIn(b"67%", res.data)
        # Check Aptitude total: 50
        self.assertIn(b"50", res.data)
        # Check Mock avg score: 85.0%
        self.assertIn(b"85.0%", res.data)

    def test_sql_parameterized_safety(self):
        # Test input containing characters like single quotes and SQL statements
        malicious_title = "'); DROP TABLE dsa_questions; --"
        res = self.client.post(
            "/add-dsa",
            data={"title": malicious_title, "topic": "SQL", "difficulty": "Hard"},
            follow_redirects=True,
        )
        self.assertEqual(res.status_code, 200)

        # Verify dsa_questions table is still intact and the question title is safely stored as literal text
        with app.get_db() as conn:
            row = conn.execute("SELECT title FROM dsa_questions WHERE title = ?", (malicious_title,)).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["title"], malicious_title)

    # ------------------ Day 2 Feature Tests ------------------

    def test_dsa_search_by_title(self):
        self.client.post("/add-dsa", data={"title": "Custom Alpha Target", "topic": "Arrays", "difficulty": "Easy"})
        self.client.post("/add-dsa", data={"title": "Custom Beta Target", "topic": "Arrays", "difficulty": "Medium"})
        self.client.post("/add-dsa", data={"title": "Binary Search Tree", "topic": "Trees", "difficulty": "Medium"})

        # Search by partial match "Target"
        res = self.client.get("/?search=Target")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Custom Alpha Target", res.data)
        self.assertIn(b"Custom Beta Target", res.data)
        self.assertNotIn(b"Binary Search Tree", res.data)

        # Case-insensitive search "binary"
        res = self.client.get("/?search=binary")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Binary Search Tree", res.data)
        self.assertNotIn(b"Custom Alpha Target", res.data)

        # Search with no match
        res = self.client.get("/?search=NonExistentQuestion")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"No matching questions found", res.data)
        self.assertNotIn(b"Binary Search Tree", res.data)

    def test_dsa_filters_topic_difficulty_status(self):
        self.client.post("/add-dsa", data={"title": "Merge Intervals", "topic": "Intervals", "difficulty": "Medium"})
        self.client.post("/add-dsa", data={"title": "Maximum Subarray", "topic": "Arrays", "difficulty": "Easy"})
        self.client.post("/add-dsa", data={"title": "Trapping Rain Water", "topic": "Arrays", "difficulty": "Hard"})

        # Toggle "Maximum Subarray" to Completed
        with app.get_db() as conn:
            sub_id = conn.execute("SELECT id FROM dsa_questions WHERE title='Maximum Subarray'").fetchone()["id"]
        self.client.post(f"/toggle-dsa/{sub_id}")

        # Filter by Topic = "Arrays"
        res = self.client.get("/?topic=Arrays")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Maximum Subarray", res.data)
        self.assertIn(b"Trapping Rain Water", res.data)
        self.assertNotIn(b"Merge Intervals", res.data)

        # Filter by Difficulty = "Hard"
        res = self.client.get("/?difficulty=Hard")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Trapping Rain Water", res.data)
        self.assertNotIn(b"Maximum Subarray", res.data)
        self.assertNotIn(b"Merge Intervals", res.data)

        # Filter by Status = "Completed"
        res = self.client.get("/?status=Completed")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Maximum Subarray", res.data)
        self.assertNotIn(b"Trapping Rain Water", res.data)

        # Filter by Status = "Pending"
        res = self.client.get("/?status=Pending")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Trapping Rain Water", res.data)
        self.assertIn(b"Merge Intervals", res.data)
        self.assertNotIn(b"Maximum Subarray", res.data)

        # Combined filter: Topic=Arrays, Difficulty=Hard, Status=Pending
        res = self.client.get("/?topic=Arrays&difficulty=Hard&status=Pending")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Trapping Rain Water", res.data)
        self.assertNotIn(b"Maximum Subarray", res.data)
        self.assertNotIn(b"Merge Intervals", res.data)

    def test_dsa_edit_flow_and_validation(self):
        self.client.post("/add-dsa", data={"title": "Initial Title", "topic": "Initial Topic", "difficulty": "Easy"})
        with app.get_db() as conn:
            q_id = conn.execute("SELECT id FROM dsa_questions WHERE title='Initial Title'").fetchone()["id"]

        # 1. GET edit page
        res = self.client.get(f"/edit-dsa/{q_id}")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Initial Title", res.data)
        self.assertIn(b"Initial Topic", res.data)

        # 2. GET non-existent question
        res = self.client.get("/edit-dsa/99999", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Question not found.", res.data)

        # 3. Successful POST edit
        res = self.client.post(
            f"/edit-dsa/{q_id}",
            data={"title": "Updated Title", "topic": "Updated Topic", "difficulty": "Hard"},
            follow_redirects=True,
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"DSA question updated!", res.data)
        self.assertIn(b"Updated Title", res.data)
        self.assertIn(b"Updated Topic", res.data)
        self.assertIn(b"Hard", res.data)

        with app.get_db() as conn:
            row = conn.execute("SELECT * FROM dsa_questions WHERE id = ?", (q_id,)).fetchone()
            self.assertEqual(row["title"], "Updated Title")
            self.assertEqual(row["topic"], "Updated Topic")
            self.assertEqual(row["difficulty"], "Hard")

        # 4. Empty title in edit rejected
        res = self.client.post(
            f"/edit-dsa/{q_id}",
            data={"title": "   ", "topic": "Updated Topic", "difficulty": "Hard"},
            follow_redirects=True,
        )
        self.assertIn(b"Please enter both a question title and topic.", res.data)

        # 5. Invalid difficulty in edit rejected
        res = self.client.post(
            f"/edit-dsa/{q_id}",
            data={"title": "Valid Title", "topic": "Valid Topic", "difficulty": "SuperHard"},
            follow_redirects=True,
        )
        self.assertIn(b"Please select a valid difficulty", res.data)

        # 6. Edit non-existent question
        res = self.client.post(
            "/edit-dsa/99999",
            data={"title": "Non-existent", "topic": "Topic", "difficulty": "Easy"},
            follow_redirects=True,
        )
        self.assertIn(b"Question not found.", res.data)

    def test_enhanced_server_side_validations(self):
        # 1. DSA title too long (> 120)
        res = self.client.post(
            "/add-dsa",
            data={"title": "A" * 121, "topic": "Arrays", "difficulty": "Easy"},
            follow_redirects=True,
        )
        self.assertIn(b"Question title must not exceed 120 characters.", res.data)

        # 2. DSA topic too long (> 60)
        res = self.client.post(
            "/add-dsa",
            data={"title": "Valid Title", "topic": "B" * 61, "difficulty": "Easy"},
            follow_redirects=True,
        )
        self.assertIn(b"Topic must not exceed 60 characters.", res.data)

        # 3. Aptitude topic too long (> 80)
        res = self.client.post(
            "/add-aptitude",
            data={
                "aptitude_topic": "C" * 81,
                "questions_solved": "10",
                "minutes_spent": "20",
                "practice_date": "2026-10-10",
            },
            follow_redirects=True,
        )
        self.assertIn(b"Topic must not exceed 80 characters.", res.data)

        # 4. Aptitude questions or minutes unreasonably large
        res = self.client.post(
            "/add-aptitude",
            data={
                "aptitude_topic": "Number Series",
                "questions_solved": "10001",
                "minutes_spent": "20",
                "practice_date": "2026-10-10",
            },
            follow_redirects=True,
        )
        self.assertIn(b"Questions solved must not exceed 10,000", res.data)

        res = self.client.post(
            "/add-aptitude",
            data={
                "aptitude_topic": "Number Series",
                "questions_solved": "10",
                "minutes_spent": "1441",
                "practice_date": "2026-10-10",
            },
            follow_redirects=True,
        )
        self.assertIn(b"minutes must not exceed 1,440", res.data)

        # 5. Mock test name too long (> 100)
        res = self.client.post(
            "/add-mock",
            data={
                "test_name": "T" * 101,
                "score": "20",
                "total_marks": "30",
                "test_date": "2026-10-10",
            },
            follow_redirects=True,
        )
        self.assertIn(b"Test name must not exceed 100 characters.", res.data)

        # 6. Mock test total marks too large (> 10000)
        res = self.client.post(
            "/add-mock",
            data={
                "test_name": "Massive Test",
                "score": "10001",
                "total_marks": "10001",
                "test_date": "2026-10-10",
            },
            follow_redirects=True,
        )
        self.assertIn(b"Total marks cannot exceed 10,000.", res.data)

        # 7. Mock test NaN or Inf
        res = self.client.post(
            "/add-mock",
            data={
                "test_name": "NaN Mock",
                "score": "NaN",
                "total_marks": "50",
                "test_date": "2026-10-10",
            },
            follow_redirects=True,
        )
        self.assertIn(b"Score and total marks must be finite numbers.", res.data)

    def test_streak_calculation_scenarios(self):
        today = date.today()
        yesterday = today - timedelta(days=1)

        # 1. Empty database: streak is 0
        with app.get_db() as conn:
            self.assertEqual(app.calculate_streak(conn, as_of_date=today), 0)
            self.assertFalse(app.has_practiced_today(conn, as_of_date=today))

        # 2. Activity today only: streak is 1
        self.client.post(
            "/add-aptitude",
            data={
                "aptitude_topic": "Permutations",
                "questions_solved": "10",
                "minutes_spent": "20",
                "practice_date": today.strftime("%Y-%m-%d"),
            },
        )
        with app.get_db() as conn:
            self.assertEqual(app.calculate_streak(conn, as_of_date=today), 1)
            self.assertTrue(app.has_practiced_today(conn, as_of_date=today))

        # 3. Add activity yesterday: streak becomes 2
        self.client.post(
            "/add-mock",
            data={
                "test_name": "Yesterday Mock",
                "score": "45",
                "total_marks": "50",
                "test_date": yesterday.strftime("%Y-%m-%d"),
            },
        )
        with app.get_db() as conn:
            self.assertEqual(app.calculate_streak(conn, as_of_date=today), 2)

        # 4. Multiple activities on the same date:
        # Today has both aptitude and mock test; streak should still be 2, not 3 (no duplicate date counting!)
        self.client.post(
            "/add-mock",
            data={
                "test_name": "Today Second Test",
                "score": "40",
                "total_marks": "50",
                "test_date": today.strftime("%Y-%m-%d"),
            },
        )
        with app.get_db() as conn:
            practice_dates = app.get_practice_dates(conn)
            self.assertEqual(len(practice_dates), 2)  # only today and yesterday
            self.assertEqual(app.calculate_streak(conn, as_of_date=today), 2)

        # 5. Streak active from yesterday when no activity today
        tomorrow = today + timedelta(days=1)
        with app.get_db() as conn:
            # Tomorrow has no activity yet, but yesterday (relative to tomorrow, which is today) had activity
            self.assertEqual(app.calculate_streak(conn, as_of_date=tomorrow), 2)

        # 6. Broken streak: test when last activity was 2 days ago
        three_days_later = today + timedelta(days=3)
        with app.get_db() as conn:
            # 3 days later, neither today nor yesterday had any activity
            self.assertEqual(app.calculate_streak(conn, as_of_date=three_days_later), 0)

        # 7. DSA completion sets completed_at and adds to practice dates
        self.client.post("/add-dsa", data={"title": "Streak DSA", "topic": "Graphs", "difficulty": "Medium"})
        with app.get_db() as conn:
            q_row = conn.execute("SELECT id, completed_at FROM dsa_questions WHERE title='Streak DSA'").fetchone()
            self.assertIsNone(q_row["completed_at"])

        # Toggle to completed
        self.client.post(f"/toggle-dsa/{q_row['id']}")
        with app.get_db() as conn:
            q_row = conn.execute("SELECT id, completed_at FROM dsa_questions WHERE title='Streak DSA'").fetchone()
            self.assertIsNotNone(q_row["completed_at"])

        # Toggle back to pending clears completed_at
        self.client.post(f"/toggle-dsa/{q_row['id']}")
        with app.get_db() as conn:
            q_row = conn.execute("SELECT id, completed_at FROM dsa_questions WHERE title='Streak DSA'").fetchone()
            self.assertIsNone(q_row["completed_at"])

    # ------------------ Day 3 Feature Tests ------------------

    def test_weekly_progress_statistics_empty_state(self):
        with app.get_db() as conn:
            weekly = app.get_weekly_stats(conn, as_of_date="2026-10-12")
            self.assertEqual(weekly["active_days"], 0)
            self.assertEqual(weekly["total_days"], 7)
            self.assertEqual(weekly["aptitude_questions"], 0)
            self.assertEqual(weekly["aptitude_minutes"], 0)
            self.assertEqual(weekly["dsa_completed"], 0)
            self.assertEqual(weekly["mock_tests_taken"], 0)
            self.assertEqual(weekly["mock_avg_score"], 0.0)
            self.assertEqual(len(weekly["days_breakdown"]), 7)
            self.assertTrue(all(not d["active"] for d in weekly["days_breakdown"]))
            # The last day in breakdown is the target date
            self.assertTrue(weekly["days_breakdown"][-1]["is_today"])
            self.assertEqual(weekly["days_breakdown"][-1]["date"], "2026-10-12")

    def test_weekly_progress_statistics_calculation_and_windowing(self):
        target = date(2026, 10, 12)
        # Inside 7-day window (2026-10-06 to 2026-10-12):
        self.client.post(
            "/add-aptitude",
            data={
                "aptitude_topic": "Probability",
                "questions_solved": "25",
                "minutes_spent": "45",
                "practice_date": "2026-10-10",
            },
        )
        self.client.post(
            "/add-mock",
            data={
                "test_name": "TCS NQT Mock",
                "score": "40",
                "total_marks": "50",
                "test_date": "2026-10-11",
            },
        )
        # Add and complete DSA question inside window
        self.client.post(
            "/add-dsa",
            data={"title": "Weekly Tree Problem", "topic": "Trees", "difficulty": "Medium"},
        )
        with app.get_db() as conn:
            tree_id = conn.execute("SELECT id FROM dsa_questions WHERE title='Weekly Tree Problem'").fetchone()["id"]
        self.client.post(f"/toggle-dsa/{tree_id}")

        # OUTSIDE 7-day window (e.g. 2026-09-25, 17 days ago):
        self.client.post(
            "/add-aptitude",
            data={
                "aptitude_topic": "Old Topic",
                "questions_solved": "90",
                "minutes_spent": "120",
                "practice_date": "2026-09-25",
            },
        )
        self.client.post(
            "/add-mock",
            data={
                "test_name": "Old Mock",
                "score": "20",
                "total_marks": "50",
                "test_date": "2026-09-25",
            },
        )

        with app.get_db() as conn:
            weekly = app.get_weekly_stats(conn, as_of_date=target)
            # Only inside window should be counted:
            self.assertEqual(weekly["aptitude_questions"], 25)  # 90 excluded
            self.assertEqual(weekly["aptitude_minutes"], 45)    # 120 excluded
            self.assertEqual(weekly["mock_tests_taken"], 1)     # Old Mock excluded
            self.assertEqual(weekly["mock_avg_score"], 80.0)    # 40/50 = 80.0%
            self.assertEqual(weekly["dsa_completed"], 1)
            # Active days: 2026-10-10 (aptitude), 2026-10-11 (mock), today (dsa completed)
            self.assertGreaterEqual(weekly["active_days"], 2)

    def test_day3_charts_html_and_empty_dataset_handling(self):
        # Empty database GET /
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)

        # Check all 3 chart canvases and their empty state elements
        self.assertIn(b'id="dsaChart"', res.data)
        self.assertIn(b'id="mockChart"', res.data)
        self.assertIn(b'id="aptitudeChart"', res.data)
        self.assertIn(b'id="dsa-empty-overlay"', res.data)
        self.assertIn(b'id="mock-empty-overlay"', res.data)
        self.assertIn(b'id="aptitude-empty-overlay"', res.data)
        self.assertIn(b'id="analytics-data"', res.data)

        # Weekly momentum section
        self.assertIn(b"WEEKLY MOMENTUM", res.data)
        self.assertIn(b"Last 7 Days Progress", res.data)
        self.assertIn(b"0 / 7", res.data)

    def test_day3_charts_populated_analytics_payload(self):
        import json
        import re

        # Add 1 pending and 1 completed DSA
        self.client.post("/add-dsa", data={"title": "Pending DSA", "topic": "DP", "difficulty": "Hard"})
        self.client.post("/add-dsa", data={"title": "Done DSA", "topic": "DP", "difficulty": "Easy"})
        with app.get_db() as conn:
            done_id = conn.execute("SELECT id FROM dsa_questions WHERE title='Done DSA'").fetchone()["id"]
        self.client.post(f"/toggle-dsa/{done_id}")

        # Add mock test and aptitude log
        self.client.post("/add-mock", data={"test_name": "Accenture Mock", "score": "45", "total_marks": "50", "test_date": "2026-10-11"})
        self.client.post("/add-aptitude", data={"aptitude_topic": "Pipes", "questions_solved": "30", "minutes_spent": "40", "practice_date": "2026-10-11"})

        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)

        # Extract and parse analytics-data JSON
        match = re.search(r'<script id="analytics-data" type="application/json">(.*?)</script>', res.data.decode("utf-8"), re.DOTALL)
        self.assertIsNotNone(match)
        data = json.loads(match.group(1))

        # 1. DSA Analytics
        self.assertEqual(data["dsa"]["total"], 2)
        self.assertEqual(data["dsa"]["completed"], 1)
        self.assertEqual(data["dsa"]["pending"], 1)

        # 2. Mock Test Analytics
        self.assertEqual(len(data["mock_tests"]), 1)
        self.assertEqual(data["mock_tests"][0]["name"], "Accenture Mock")
        self.assertEqual(data["mock_tests"][0]["percentage"], 90.0)
        self.assertEqual(data["mock_tests"][0]["date"], "2026-10-11")

        # 3. Aptitude Analytics
        self.assertEqual(len(data["aptitude"]), 1)
        self.assertEqual(data["aptitude"][0]["date"], "2026-10-11")
        self.assertEqual(data["aptitude"][0]["questions"], 30)
        self.assertEqual(data["aptitude"][0]["minutes"], 40)


if __name__ == "__main__":
    unittest.main()

