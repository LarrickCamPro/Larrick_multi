import pickle
from pathlib import Path

cache_path = Path("src/larrak2/gear/picogk_cache.pkl")
try:
    with open(cache_path, "rb") as f:
        data = pickle.load(f)
    
    print(f"Total entries: {len(data)}")
    passed = sum(1 for v in data.values() if v.get("passed"))
    failed = len(data) - passed
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    # Show first 3 entries
    print("\nSample Entries:")
    for i, (k, v) in enumerate(list(data.items())[:3]):
        print(f"--- Entry {i} ---")
        print(f"Key: {k}")
        print(f"Result: {v}")

except Exception as e:
    print(f"Error reading cache: {e}")
