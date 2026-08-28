"""
Compatibility wrapper for the MeTTa-backed JSON lookup.

The real implementation lives in utils.py so JSON query handling and MeTTa
execution stay in one place.
"""

try:
    from .utils import find_by_json, json_to_metta_query
except ImportError:
    from utils import find_by_json, json_to_metta_query


if __name__ == "__main__":
    examples = [
        {
            "subject": "Alice",
            "relation": "any",
            "target_attribute": {"type": "Profession", "value": "doctor"},
            "max_depth": 1,
        },
        {
            "subject": "Alice",
            "relation": "any",
            "target_attribute": {"type": "Profession", "value": "nurse"},
            "max_depth": 2,
        },
        {
            "subject": "Alice",
            "relation": "any",
            "target_attribute": {"type": "Profession", "value": "nurse"},
            "max_depth": 3,
        },
    ]

    for example in examples:
        print("=== Query ===")
        print(example)
        print("=> Results (person, depth):", find_by_json(example))
        print()
