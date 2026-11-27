# -*- coding: utf-8 -*-
from student_database import StudentDatabase


def test_workbook_profile_is_remembered_only_when_called_and_similarity_is_ranked(tmp_path):
    db = StudentDatabase(tmp_path / "memory.sqlite3")
    assert db.workbook_learning_stats() == {"profiles": 0, "confirmations": 0}
    assert db.remember_workbook_profile(".xlsx", "Students", ["اسم الطالب", "كود الطالب"])
    db.remember_workbook_profile(".xlsx", "Students 2027", ["اسم الطالب", "كود الطالب"])
    matches = db.find_similar_workbook_profiles(".xlsx", ["اسم الطالب", "كود الطالب"])
    assert matches[0]["similarity"] == 1.0
    assert db.workbook_learning_stats()["profiles"] == 2


def test_confirmed_relationship_is_counted_and_symmetric(tmp_path):
    db = StudentDatabase(tmp_path / "memory.sqlite3")
    assert db.remember_confirmed_relationship("قيد", "رسوم")
    assert db.remember_confirmed_relationship("رسوم", "قيد")
    relationships = db.confirmed_relationships()
    assert len(relationships) == 1
    assert relationships[0]["confirmation_count"] == 2


def test_invalid_relationship_is_not_saved(tmp_path):
    db = StudentDatabase(tmp_path / "memory.sqlite3")
    assert not db.remember_confirmed_relationship("قيد", "قيد")
    assert db.confirmed_relationships() == []
