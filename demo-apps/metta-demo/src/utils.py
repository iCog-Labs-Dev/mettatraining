import json
import os
from hyperon import MeTTa

# ---------------------------
#  Load MeTTa Data
# ---------------------------
metta = MeTTa()

data_file_path = os.path.join(os.path.dirname(__file__), 'data.metta')
with open(data_file_path, 'r') as f:
    metta.run(f.read())

RELATIONS = ["Friend", "Colleague", "Family", "Neighbor", "Classmate"]

# ---------------------------
#  Build Query
# ---------------------------
def json_to_metta_query(data):
    """
    Convert a JSON query spec into a MeTTa query string.
    Uses getConnections from data.metta for the network search.
    """

    # Accept JSON string or dict
    if isinstance(data, str):
        data = json.loads(data)

    subject = data["subject"]
    relation = data.get("relation", "any")
    attr_type = data["target_attribute"]["type"]
    attr_value = data["target_attribute"]["value"].strip().title()
    depth_value = int(data.get("max_depth", 1))

    # Build composite pattern
    if relation.lower() == "any":
        # Relation is not specified — match any relation with a variable $rel
        pattern = f"! (getConnections () ($any {subject} $x) ({attr_type} $x {attr_value}) {depth_value})"
    else:
        # Single relation
        pattern = f"! (getConnections () ({relation} {subject} $x) ({attr_type} $x {attr_value}) {depth_value})"

    return pattern


def _atom_text(atom):
    return str(atom)


def _atom_children(atom):
    if not hasattr(atom, "get_children"):
        return []
    try:
        return atom.get_children()
    except Exception:
        return []


def _to_int(atom):
    try:
        return int(_atom_text(atom))
    except (TypeError, ValueError):
        return None


def _result_edge(result_atom):
    children = _atom_children(result_atom)
    if len(children) < 2:
        return None

    edge = children[-1]
    edge_children = _atom_children(edge)
    if len(edge_children) != 4:
        return None

    return edge_children


def _normalize_metta_results(raw_results, max_depth):
    """
    Convert getConnections output into sorted (person, depth) pairs.

    getConnections stores the remaining depth on each returned edge. A direct
    match at max_depth=2 has remaining depth 2, so actual depth is 1.
    """
    matches = {}
    for row in raw_results:
        for result_atom in row:
            edge = _result_edge(result_atom)
            if edge is None:
                continue

            _, _, person_atom, remaining_depth_atom = edge
            remaining_depth = _to_int(remaining_depth_atom)
            if remaining_depth is None:
                continue

            person = _atom_text(person_atom)
            depth = max_depth - remaining_depth + 1
            previous_depth = matches.get(person)
            if previous_depth is None or depth < previous_depth:
                matches[person] = depth

    return sorted(matches.items(), key=lambda item: (item[1], item[0]))


# ---------------------------
#  Run Query
# ---------------------------
def find_by_json(json_input):
    """
    Accepts JSON string or dict, runs getConnections in MeTTa, and returns
    (person, depth) pairs sorted by depth ascending, then name.
    """
    data = json.loads(json_input) if isinstance(json_input, str) else json_input
    max_depth = int(data.get("max_depth", 1))
    if max_depth < 1:
        raise ValueError("max_depth must be >= 1")

    query_program = json_to_metta_query(data)
    raw = metta.run(query_program)
    return _normalize_metta_results(raw, max_depth)


# ---------------------------
#  Example Usage
# ---------------------------
if __name__ == "__main__":
    example_json = {
        "subject": "Alice",
        "relation": "any",  # can be "Friend", "Family", etc., or "any"
        "target_attribute": {"type": "Profession", "value": "nurse"},
        "max_depth": 2
    }
    print(find_by_json(example_json))
