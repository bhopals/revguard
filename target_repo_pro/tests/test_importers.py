import pytest

from ledgerly import importers
from ledgerly.reports import monthly_summary

STATEMENT = """Date,Amount,Description
2026-03-01,-12.50,COFFEE CO
2026-03-02,-40.00,GROCER LTD
2026-03-03,25.00,REFUND GROCER
2026-03-04,-9.99,STREAMFLIX
"""


class TestParse:
    def test_parses_debits_skips_credits(self):
        rows = importers.parse_statement(STATEMENT)
        assert rows == [
            ("2026-03-01", 1250, "COFFEE CO"),
            ("2026-03-02", 4000, "GROCER LTD"),
            ("2026-03-04", 999, "STREAMFLIX"),
        ]

    def test_header_spellings(self):
        text = "Posted,Debit,Memo\n2026-03-01,-5.00,X\n"
        assert importers.parse_statement(text) == [("2026-03-01", 500, "X")]

    def test_bad_date_reports_row(self):
        text = "Date,Amount,Description\n03/01/2026,-5.00,X\n"
        with pytest.raises(importers.ImportError_, match="row 2"):
            importers.parse_statement(text)

    def test_missing_columns(self):
        with pytest.raises(importers.ImportError_):
            importers.parse_statement("Foo,Bar\n1,2\n")


class TestImport:
    def test_import_and_reimport(self, db, user):
        imported, skipped = importers.import_statement(db, user, STATEMENT)
        assert (imported, skipped) == (3, 0)
        imported2, skipped2 = importers.import_statement(db, user, STATEMENT)
        assert (imported2, skipped2) == (0, 3)
        assert monthly_summary(db, user, "2026-03") == {"other": 1250 + 4000 + 999}

    def test_batch_recorded(self, db, user):
        importers.import_statement(db, user, STATEMENT)
        batch = db.query_one("SELECT * FROM import_batches WHERE user_id = ?",
                             (user,))
        assert batch["row_count"] == 3
        assert batch["imported_count"] == 3
