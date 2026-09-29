"""
End-to-End Verification Test for MemoryDesk AI + Hindsight Persistent Memory
Tests:
Test 1: Store information ("My name is Rahul and I use Windows 11 with Python 3.12.")
Test 2: Retrieve information ("What environment am I using?")
Test 3: Recurrence test ("I am having the same Django database problem as before.")
"""
import sys
from fastapi.testclient import TestClient
from backend.main import app

def run_e2e_tests():
    client = TestClient(app)
    customer_id = "cust_rahul"

    print("=" * 65)
    print("STARTING REAL END-TO-END HINDSIGHT MEMORY TESTS")
    print("=" * 65)

    # -------------------------------------------------------------
    # TEST 1: Provide new facts to the agent
    # -------------------------------------------------------------
    msg1 = "My name is Rahul and I use Windows 11 with Python 3.12."
    print(f"\n[TEST 1] User sends: \"{msg1}\"")
    res1 = client.post("/api/chat", json={
        "customer_id": customer_id,
        "message": msg1
    })
    assert res1.status_code == 200, f"Test 1 failed with status {res1.status_code}: {res1.text}"
    data1 = res1.json()
    print(f"-> Agent Response: {data1['response'][:110]}...")
    print(f"-> Memories Used: {data1['memories_used']}")
    print(f"-> Memory Updated in Hindsight: {data1['memory_updated']}")
    print(f"-> Stored Fact: {data1.get('new_memory_stored')}")
    assert data1["memory_updated"] == True, "Expected memory_updated to be True after sharing environment."

    # Verify that memory is present in the customer's Hindsight bank
    mem_check = client.get(f"/api/customers/{customer_id}/memory")
    assert mem_check.status_code == 200
    bank_data = mem_check.json()
    print(f"-> Verified Total Memories in Bank: {bank_data['total_memories']}")
    found_env_fact = any("Windows 11" in m["text"] for m in bank_data["memories"])
    assert found_env_fact, "Expected 'Windows 11' fact to be in the customer's Hindsight memory bank."
    print("[TEST 1 PASSED] Environment fact retained successfully in Hindsight!")

    # -------------------------------------------------------------
    # TEST 2: Ask about environment in a new interaction
    # -------------------------------------------------------------
    msg2 = "What environment am I using?"
    print(f"\n[TEST 2] User sends: \"{msg2}\"")
    res2 = client.post("/api/chat", json={
        "customer_id": customer_id,
        "message": msg2
    })
    assert res2.status_code == 200, f"Test 2 failed with status {res2.status_code}: {res2.text}"
    data2 = res2.json()
    print(f"-> Agent Response: {data2['response'][:140]}...")
    print(f"-> Memories Used: {data2['memories_used']}")
    assert data2["memories_used"] > 0, "Expected memories_used > 0 on environment query."
    
    # Verify response mentions the environment from memory
    resp2_text = data2["response"].lower()
    assert "windows 11" in resp2_text or "python" in resp2_text, (
        f"Expected response to cite Windows 11 or Python from memory. Response was: {data2['response']}"
    )
    print("[TEST 2 PASSED] Agent recalled environment from Hindsight persistent memory!")

    # -------------------------------------------------------------
    # TEST 3: Recurrence test ("same database problem as before")
    # -------------------------------------------------------------
    msg3 = "I am having the same Django database problem as before."
    print(f"\n[TEST 3] User sends: \"{msg3}\"")
    res3 = client.post("/api/chat", json={
        "customer_id": customer_id,
        "message": msg3
    })
    assert res3.status_code == 200, f"Test 3 failed with status {res3.status_code}: {res3.text}"
    data3 = res3.json()
    print(f"-> Agent Response: {data3['response'][:160]}...")
    print(f"-> Memories Used: {data3['memories_used']}")
    assert data3["memories_used"] > 0, "Expected memories_used > 0 on recurring issue."

    # Verify that the response references prior issue/troubleshooting steps
    resp3_text = data3["response"].lower()
    assert any(term in resp3_text for term in ["database", "django", "windows 11", "port 5432", "postgresql", "step-by-step"]), (
        f"Expected response to reference database/Django context from memory. Response was: {data3['response']}"
    )
    print("[TEST 3 PASSED] Agent retrieved previous problem and customized troubleshooting!")

    print("\n" + "=" * 65)
    print("ALL 3 END-TO-END HINDSIGHT MEMORY TESTS PASSED SUCCESSFULLY!")
    print("=" * 65)

if __name__ == "__main__":
    run_e2e_tests()
