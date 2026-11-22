"""Lesson detail, export, validation and persistence tests."""
from __future__ import annotations

import io
import zipfile


def test_library_lists_seeded_lesson(client, lesson):
    response = client.get("/library")
    assert response.status_code == 200
    assert "دورة الماء في الطبيعة" in response.get_data(as_text=True)


def test_lesson_detail_has_accessible_tabs(client, lesson):
    response = client.get(f"/lessons/{lesson}")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'role="tablist"' in html
    assert 'id="tab-sheet"' in html
    assert 'id="tab-exercises"' in html
    assert 'id="tab-assessment"' in html
    assert 'aria-controls="panel-sheet"' in html
    assert 'aria-controls="panel-exercises"' in html
    assert 'aria-controls="panel-assessment"' in html
    assert html.count('role="tabpanel"') == 3
    assert 'aria-labelledby="tab-sheet"' in html


def test_print_view_has_table_scope(client, lesson):
    response = client.get(f"/lessons/{lesson}/print")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'scope="col"' in html
    assert "دورة الماء في الطبيعة" in html


def test_api_lesson_payload_keeps_success_contract(client, lesson):
    response = client.get(f"/api/lessons/{lesson}")
    assert response.status_code == 200
    payload = response.json
    assert payload["success"] is True
    assert payload["lesson"]["id"] == lesson
    assert payload["lesson"]["content"]["title"] == "دورة الماء في الطبيعة"


def test_docx_export_is_a_valid_word_document(client, lesson):
    response = client.get(f"/api/lessons/{lesson}/export.docx")
    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert response.data[:2] == b"PK"
    with zipfile.ZipFile(io.BytesIO(response.data)) as archive:
        assert "word/document.xml" in archive.namelist()


def test_validate_endpoint_scores_sample_plan(client, sample_plan):
    response = client.post("/api/lessons/validate", json=sample_plan)
    assert response.status_code == 200
    payload = response.json
    assert payload["success"] is True
    assert payload["validation_errors"] == []
    assert payload["score"] >= 70
    assert payload["rubric"]


def test_duplicate_and_delete_lesson(client, lesson):
    duplicate = client.post(f"/api/lessons/{lesson}/duplicate")
    assert duplicate.status_code == 201
    new_id = duplicate.json["lesson_id"]
    assert new_id != lesson
    assert duplicate.json["success"] is True

    assert client.get(f"/lessons/{new_id}").status_code == 200

    deleted = client.delete(f"/api/lessons/{new_id}")
    assert deleted.status_code == 200
    assert deleted.json == {"success": True, "deleted": new_id}
    assert client.get(f"/api/lessons/{new_id}").status_code == 404
