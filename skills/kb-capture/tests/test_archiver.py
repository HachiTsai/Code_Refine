import unittest
import os
import shutil
import re
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

from archiver import LogArchiver


# ============================================================
# 🛠️  Helpers
# ============================================================
MASTER_LOG_INIT = (
    "# 📅 核心作業日誌 (Master WorkLog)\n\n"
    "### 🗺️ 快速導航 (Quick Navigation)\n"
    "| 日期 | 核心摘要 (Summary) | 任務狀態 |\n"
    "| :--- | :--- | :---: |\n\n"
    "---\n\n"
    "# 📚 歷史作業日誌歸檔 (Historical Archives)\n\n"
    "（歷史內容保留於此）\n"
)


class TestCaptureChat(unittest.TestCase):
    """Test suite for capture_chat() — v3.x Master Log architecture."""

    def setUp(self):
        self.test_root = "test_env_v3"
        inbox_dir = os.path.join(self.test_root, "00_Inbox")
        worklog_dir = os.path.join(self.test_root, "20_Knowledge_Base", "0_Worklogs")
        os.makedirs(inbox_dir, exist_ok=True)
        os.makedirs(worklog_dir, exist_ok=True)

        self.archiver = LogArchiver(project_root=self.test_root)

        # Pre-populate Master Log with init skeleton
        with open(self.archiver.master_log_path, "w", encoding="utf-8") as f:
            f.write(MASTER_LOG_INIT)

        # Pre-populate Inbox
        with open(self.archiver.inbox_path, "w", encoding="utf-8") as f:
            f.write("測試對話內容 Capture 1")

    def tearDown(self):
        if os.path.exists(self.test_root):
            shutil.rmtree(self.test_root)

    def _read_master(self):
        with open(self.archiver.master_log_path, "r", encoding="utf-8") as f:
            return f.read()

    def _read_inbox(self):
        with open(self.archiver.inbox_path, "r", encoding="utf-8") as f:
            return f.read()

    # ----------------------------------------------------------
    # Test 1: Single capture writes content to Master Log
    # ----------------------------------------------------------
    def test_capture_writes_to_master_log(self):
        self.archiver.capture_chat(target_date="2026-02-23")
        content = self._read_master()
        self.assertIn("2026-02-23", content)
        self.assertIn("測試對話內容 Capture 1", content)

    # ----------------------------------------------------------
    # Test 2: Inbox is reset after capture
    # ----------------------------------------------------------
    def test_inbox_reset_after_capture(self):
        self.archiver.capture_chat(target_date="2026-02-23")
        inbox = self._read_inbox()
        self.assertEqual(inbox.strip(), "")
        self.assertNotIn("測試對話內容", inbox)

    # ----------------------------------------------------------
    # Test 3: Second capture appends to existing day block
    # ----------------------------------------------------------
    def test_second_capture_appends(self):
        self.archiver.capture_chat(target_date="2026-02-23")

        # Write second content to Inbox
        with open(self.archiver.inbox_path, "w", encoding="utf-8") as f:
            f.write("測試對話內容 Capture 2")

        self.archiver.capture_chat(target_date="2026-02-23")
        content = self._read_master()

        self.assertIn("測試對話內容 Capture 1", content)
        self.assertIn("測試對話內容 Capture 2", content)

        # Order: Capture 1 should appear before Capture 2 (earlier timestamp)
        pos1 = content.find("Capture 1")
        pos2 = content.find("Capture 2")
        self.assertLess(pos1, pos2)

    # ----------------------------------------------------------
    # Test 4: Historical archive marker is preserved
    # ----------------------------------------------------------
    def test_historical_archive_preserved(self):
        self.archiver.capture_chat(target_date="2026-02-23")
        content = self._read_master()
        self.assertIn("# 📚 歷史作業日誌歸檔", content)

    # ----------------------------------------------------------
    # Test 5: Empty inbox is silently skipped
    # ----------------------------------------------------------
    def test_empty_inbox_skipped(self):
        with open(self.archiver.inbox_path, "w", encoding="utf-8") as f:
            f.write("")
        # Should not raise, and master log should be unchanged
        self.archiver.capture_chat(target_date="2026-02-23")
        content = self._read_master()
        self.assertNotIn("2026-02-23", content)


class TestCaptureIdea(unittest.TestCase):
    """Test suite for capture_idea()."""

    def setUp(self):
        self.test_root = "test_env_v3_idea"
        inbox_dir = os.path.join(self.test_root, "00_Inbox")
        worklog_dir = os.path.join(self.test_root, "20_Knowledge_Base", "0_Worklogs")
        os.makedirs(inbox_dir, exist_ok=True)
        os.makedirs(worklog_dir, exist_ok=True)

        self.archiver = LogArchiver(project_root=self.test_root)

        with open(self.archiver.master_log_path, "w", encoding="utf-8") as f:
            f.write(MASTER_LOG_INIT)

        with open(self.archiver.inbox_path, "w", encoding="utf-8") as f:
            f.write("一個關於自動化的創新想法")

    def tearDown(self):
        if os.path.exists(self.test_root):
            shutil.rmtree(self.test_root)

    def test_idea_injected_to_master_log(self):
        self.archiver.capture_idea(target_date="2026-02-23")
        with open(self.archiver.master_log_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("IDEA-", content)
        self.assertIn("💡 靈感孵化 (Incubator)", content)


class TestValidateIntegrity(unittest.TestCase):
    """Test suite for validate_integrity() — the safety guardian."""

    def setUp(self):
        self.archiver = LogArchiver()

    def test_passes_identical_content(self):
        content = "# Header\n\n## 2026-02-23\n\n# 📚 歷史作業日誌歸檔\n\n舊內容"
        result = self.archiver.validate_integrity(content, content)
        self.assertTrue(result)

    def test_raises_on_missing_archive_marker(self):
        old = "## 2026-02-23\n\n# 📚 歷史作業日誌歸檔\n\n舊內容"
        new = "## 2026-02-23\n\n沒有歸檔標記了"
        with self.assertRaises(RuntimeError):
            self.archiver.validate_integrity(old, new)

    def test_raises_on_date_section_loss(self):
        old = "## 2026-02-22\n\n## 2026-02-23\n\n# 📚 歷史作業日誌歸檔\n\n舊內容"
        new = "## 2026-02-23\n\n# 📚 歷史作業日誌歸檔\n\n舊內容"
        with self.assertRaises(RuntimeError):
            self.archiver.validate_integrity(old, new)

    def test_raises_on_history_shrinkage(self):
        old_history = "A" * 1000
        new_history = "A" * 100  # 大幅縮短，低於 95% 閾值
        old = f"## 2026-02-23\n\n# 📚 歷史作業日誌歸檔\n\n{old_history}"
        new = f"## 2026-02-23\n\n# 📚 歷史作業日誌歸檔\n\n{new_history}"
        with self.assertRaises(RuntimeError):
            self.archiver.validate_integrity(old, new)


class TestMarkAsCompleted(unittest.TestCase):
    """Test suite for mark_as_completed()."""

    def setUp(self):
        self.test_root = "test_env_v3_finish"
        worklog_dir = os.path.join(self.test_root, "20_Knowledge_Base", "0_Worklogs")
        inbox_dir = os.path.join(self.test_root, "00_Inbox")
        os.makedirs(worklog_dir, exist_ok=True)
        os.makedirs(inbox_dir, exist_ok=True)
        self.archiver = LogArchiver(project_root=self.test_root)

    def tearDown(self):
        if os.path.exists(self.test_root):
            shutil.rmtree(self.test_root)

    def test_marks_today_as_completed(self):
        today = self.archiver.get_now().strftime("%Y-%m-%d")
        init_content = (
            f"# 📅 核心作業日誌 (Master WorkLog)\n\n"
            f"### 🗺️ 快速導航 (Quick Navigation)\n"
            f"| 日期 | 核心摘要 (Summary) | 任務狀態 |\n"
            f"| :--- | :--- | :---: |\n"
            f"| [[#{today}]] | 測試摘要 | [ ] |\n\n---\n\n"
            f"## {today}\n\n"
            f"> [!abstract]- {today} [ ] 任務已完成\n\n"
            f"---\n\n"
            f"# 📚 歷史作業日誌歸檔 (Historical Archives)\n\n（無）\n"
        )
        with open(self.archiver.master_log_path, "w", encoding="utf-8") as f:
            f.write(init_content)

        self.archiver.mark_as_completed()

        with open(self.archiver.master_log_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("[x] 任務已完成", content)
        self.assertNotIn("[ ] 任務已完成", content)


if __name__ == "__main__":
    unittest.main(verbosity=2)
