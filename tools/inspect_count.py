import pickle
from pathlib import Path

cache_path = Path("src/larrak2/gear/picogk_cache.pkl")
try:
    with open(cache_path, "rb") as f:
        data = pickle.load(f)
    print(f"Total entries: {len(data)}")
    passed = sum(1 for v in data.values() if v.get("passed"))
    print(f"Passed: {passed}")
except Exception as e:
    print(f"Error: {e}")
