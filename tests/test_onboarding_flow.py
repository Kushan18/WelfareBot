import uuid
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_onboarding_flow():
    session_id = str(uuid.uuid4())
    # Step 1: Provide name
    resp = client.post("/chat", json={"session_id": session_id, "message": "My name is Alice"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "provide_name"
    assert "Hi Alice" in data["reply"]
    assert isinstance(data["chips"], list)
    for chip in data["chips"]:
        assert "label" in chip and "value" in chip
        assert len(chip["value"]) == 2

    # Step 2: Choose language
    resp = client.post("/chat", json={"session_id": session_id, "message": "English"})
    data = resp.json()
    assert data["intent"] == "collect_details"
    assert "Great!" in data["reply"]

    # Step 3: Confirm continue
    resp = client.post("/chat", json={"session_id": session_id, "message": "yes"})
    data = resp.json()
    assert data["intent"] == "collect_details"
    assert "which state" in data["reply"].lower()

    # Fill remaining profile fields
    fields = [
        ("state", "Karnataka"),
        ("occupation", "student"),
        ("caste_category", "General"),
        ("gender", "Female"),
        ("age", "25"),
        ("income_bracket", "200000"),
    ]
    for field, value in fields:
        resp = client.post("/chat", json={"session_id": session_id, "message": value})
        data = resp.json()
        if field == "income_bracket":
            assert data["intent"] == "confirm_details"
            assert "information i have collected" in data["reply"].lower()
            assert isinstance(data.get("details"), dict)
            for f, v in fields:
                assert data["details"][f] == v
            chip_labels = [c["label"].lower() for c in data["chips"]]
            assert "yes" in chip_labels and "edit" in chip_labels and "start over" in chip_labels
        else:
            assert data["intent"] == "collect_details"

    # Final confirmation Yes
    resp = client.post("/chat", json={"session_id": session_id, "message": "Yes"})
    data = resp.json()
    assert data["intent"] == "completed"
    assert "all set" in data["reply"].lower()
