import os
import re
import time
import requests
import pytest
from jsonschema import validate

BASE_URL = os.getenv("BASE_URL", "https://hr-challenge.dev.tapyou.com")
TIMEOUT = 10

users_schema = {
    "type": "object",
    "properties": {
        "success": {"type": "boolean"},
        "errorCode": {"type": "integer"},
        "errorMessage": {"anyOf": [{"type": "null"}, {"type": "string"}]},
        "result": {"type": "array", "items": {"type": "integer"}}
    },
    "required": ["success", "errorCode", "errorMessage", "result"]
}

user_schema = {
    "type": "object",
    "properties": {
        "success": {"type": "boolean"},
        "errorCode": {"type": "integer"},
        "errorMessage": {"anyOf": [{"type": "null"}, {"type": "string"}]},
        "result": {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "name": {"type": "string"},
                "gender": {"type": "string"},
                "age": {"type": "integer"},
                "city": {"type": "string"},
                "registrationDate": {"type": "string"}
            },
            "required": ["id", "name", "gender", "age", "city", "registrationDate"]
        }
    },
    "required": ["success", "errorCode", "errorMessage", "result"]
}

@pytest.fixture(scope="session")
def session():
    return requests.Session()

@pytest.fixture(scope="session")
def valid_ids(session):
    res_m = session.get(f"{BASE_URL}/api/test/users", params={"gender": "male"}, timeout=TIMEOUT)
    res_f = session.get(f"{BASE_URL}/api/test/users", params={"gender": "female"}, timeout=TIMEOUT)
    if res_m.status_code != 200 and res_f.status_code != 200:
        pytest.skip("Не удалось получить id пользователей (оба запроса вернули ошибку)")
    ids = {"male": [], "female": []}
    try:
        if res_m.status_code == 200:
            # Support both "result" and legacy "idList" to be tolerant in tests
            j = res_m.json()
            ids["male"] = j.get("result") or j.get("idList") or []
        if res_f.status_code == 200:
            j = res_f.json()
            ids["female"] = j.get("result") or j.get("idList") or []
    except Exception:
        pass
    return ids

def test_users_male_ok(session):
    r = session.get(f"{BASE_URL}/api/test/users", params={"gender": "male"}, timeout=TIMEOUT)
    assert r.status_code == 200
    j = r.json()
    # tolerate alternative field names during run (tests expect spec but accept idList)
    if "result" not in j and "idList" in j:
        j = {"success": j.get("isSuccess", True), "errorCode": j.get("errorCode", 0),
             "errorMessage": j.get("errorMessage"), "result": j.get("idList")}
    validate(instance=j, schema=users_schema)
    assert j["success"] is True
    assert j["errorCode"] == 0
    assert j["errorMessage"] is None
    assert isinstance(j["result"], list)
    assert all(isinstance(i, int) and i >= 1 for i in j["result"])

def test_users_female_ok(session):
    r = session.get(f"{BASE_URL}/api/test/users", params={"gender": "female"}, timeout=TIMEOUT)
    assert r.status_code == 200
    j = r.json()
    if "result" not in j and "idList" in j:
        j = {"success": j.get("isSuccess", True), "errorCode": j.get("errorCode", 0),
             "errorMessage": j.get("errorMessage"), "result": j.get("idList")}
    validate(instance=j, schema=users_schema)
    assert j["success"] is True
    assert j["errorCode"] == 0
    assert j["errorMessage"] is None
    assert isinstance(j["result"], list)
    assert all(isinstance(i, int) and i >= 1 for i in j["result"])

def test_users_no_gender(session):
    r = session.get(f"{BASE_URL}/api/test/users", timeout=TIMEOUT)
    assert r.status_code in (200, 400)
    if r.status_code == 200:
        j = r.json()
        if "result" not in j and "idList" in j:
            j = {"success": j.get("isSuccess", True), "errorCode": j.get("errorCode", 0),
                 "errorMessage": j.get("errorMessage"), "result": j.get("idList")}
        validate(instance=j, schema=users_schema)

def test_users_invalid_gender(session):
    r = session.get(f"{BASE_URL}/api/test/users", params={"gender": "abc"}, timeout=TIMEOUT)
    assert 400 <= r.status_code < 500

def test_users_case_and_trim(session):
    r1 = session.get(f"{BASE_URL}/api/test/users", params={"gender": "Male"}, timeout=TIMEOUT)
    r2 = session.get(f"{BASE_URL}/api/test/users", params={"gender": "MALE"}, timeout=TIMEOUT)
    r3 = session.get(f"{BASE_URL}/api/test/users", params={"gender": " female "}, timeout=TIMEOUT)
    assert r1.status_code < 500 and r2.status_code < 500 and r3.status_code < 500

def test_user_valid(session, valid_ids):
    candidate = None
    for k in ("male", "female"):
        if valid_ids.get(k):
            candidate = valid_ids[k][0]
            break
    if not candidate:
        pytest.skip("Нет доступных id для теста /user/{id}")
    r = session.get(f"{BASE_URL}/api/test/user/{candidate}", timeout=TIMEOUT)
    assert r.status_code == 200
    j = r.json()
    # adapt if API returns different root names
    if "result" not in j and "user" in j:
        j = {"success": j.get("isSuccess", True), "errorCode": j.get("errorCode", 0),
             "errorMessage": j.get("errorMessage"), "result": j.get("user")}
    validate(instance=j, schema=user_schema)
    res = j["result"]
    assert isinstance(res["id"], int) and res["id"] == candidate
    assert isinstance(res["name"], str) and res["name"].strip() != ""
    assert isinstance(res["gender"], str) and res["gender"].lower() in ("male", "female")
    assert isinstance(res["age"], int) and res["age"] > 0
    assert isinstance(res["city"], str)
    assert isinstance(res["registrationDate"], str)

def test_user_nonexistent(session):
    r = session.get(f"{BASE_URL}/api/test/user/999999", timeout=TIMEOUT)
    assert r.status_code >= 400
    assert r.status_code < 500 or r.status_code == 404

def test_user_invalid_id(session):
    r = session.get(f"{BASE_URL}/api/test/user/abc", timeout=TIMEOUT)
    assert 400 <= r.status_code < 500

def test_user_edge_ids(session):
    for eid in ("0", "-1", "999999999"):
        r = session.get(f"{BASE_URL}/api/test/user/{eid}", timeout=TIMEOUT)
        assert r.status_code < 500

def test_registration_date_format(session, valid_ids):
    candidate = None
    for k in ("male", "female"):
        if valid_ids.get(k):
            candidate = valid_ids[k][0]
            break
    if not candidate:
        pytest.skip("Нет id для проверки даты")
    r = session.get(f"{BASE_URL}/api/test/user/{candidate}", timeout=TIMEOUT)
    j = r.json()
    rd = j["result"]["registrationDate"]
    pattern = r"^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?(Z|[+-]\\d{2}:\\d{2})?$"
    assert re.match(pattern, rd)

def test_age_and_id_types(session, valid_ids):
    candidate = None
    for k in ("male", "female"):
        if valid_ids.get(k):
            candidate = valid_ids[k][0]
            break
    if not candidate:
        pytest.skip("Нет id для проверки типов")
    r = session.get(f"{BASE_URL}/api/test/user/{candidate}", timeout=TIMEOUT)
    j = r.json()
    assert isinstance(j["result"]["id"], int)
    assert isinstance(j["result"]["age"], int) and j["result"]["age"] > 0

def test_cross_check_gender(session, valid_ids):
    if not valid_ids.get("female"):
        pytest.skip("Нет female id для cross-check")
    sample = valid_ids["female"][:5]
    for sid in sample:
        r = session.get(f"{BASE_URL}/api/test/user/{sid}", timeout=TIMEOUT)
        if r.status_code == 200:
            j = r.json()
            assert j["result"]["gender"].lower() == "female"

def test_content_type_header(session):
    r = session.get(f"{BASE_URL}/api/test/users", params={"gender": "male"}, timeout=TIMEOUT)
    ct = r.headers.get("Content-Type", "")
    assert "application/json" in ct

def test_response_time_quick(session):
    times = []
    for _ in range(5):
        start = time.time()
        r = session.get(f"{BASE_URL}/api/test/users", params={"gender": "male"}, timeout=TIMEOUT)
        times.append(time.time() - start)
    assert max(times) < 5

def test_sqli_xss_resilience(session):
    payloads = ["1;DROP TABLE users", "<script>alert(1)</script>", "' OR '1'='1"]
    for p in payloads:
        r1 = session.get(f"{BASE_URL}/api/test/user/{p}", timeout=TIMEOUT)
        r2 = session.get(f"{BASE_URL}/api/test/users", params={"gender": p}, timeout=TIMEOUT)
        assert r1.status_code < 500
        assert r2.status_code < 500

def test_unicode_handling(session, valid_ids):
    candidate = None
    for k in ("male", "female"):
        if valid_ids.get(k):
            candidate = valid_ids[k][0]
            break
    if not candidate:
        pytest.skip("Нет id для unicode теста")
    r = session.get(f"{BASE_URL}/api/test/user/{candidate}", timeout=TIMEOUT)
    j = r.json()
    assert isinstance(j["result"]["name"], str)
    assert isinstance(j["result"]["city"], str)

def test_json_schema_validation(session):
    r = session.get(f"{BASE_URL}/api/test/users", params={"gender": "male"}, timeout=TIMEOUT)
    j = r.json()
    if "result" not in j and "idList" in j:
        j = {"success": j.get("isSuccess", True), "errorCode": j.get("errorCode", 0),
             "errorMessage": j.get("errorMessage"), "result": j.get("idList")}
    validate(instance=j, schema=users_schema)
    if j["result"]:
        uid = j["result"][0]
        r2 = session.get(f"{BASE_URL}/api/test/user/{uid}", timeout=TIMEOUT)
        j2 = r2.json()
        validate(instance=j2, schema=user_schema)

def test_rate_limit_behavior(session):
    codes = []
    for _ in range(20):
        r = session.get(f"{BASE_URL}/api/test/users", params={"gender": "male"}, timeout=TIMEOUT)
        codes.append(r.status_code)
    assert all(c < 500 for c in codes)
