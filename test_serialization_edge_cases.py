#!/usr/bin/env python3
"""Test serialization edge cases."""

from src.core.services.tool_handlers_service import _serialize_ast_node
from src.core.models.cobol_analysis_model import ProgramNode, DivisionNode, DivisionType

print("=" * 80)
print("Testing AST serialization edge cases")
print("=" * 80)

# Test 1: Serialize a proper ProgramNode
print("\nTEST 1: Serialize proper ProgramNode")
print("-" * 80)
program = ProgramNode(program_name="TEST")
serialized = _serialize_ast_node(program)
print(f"Type: {serialized.get('type')}")
print(f"Keys: {list(serialized.keys())}")

# Test 2: Serialize None
print("\n\nTEST 2: Serialize None")
print("-" * 80)
try:
    serialized = _serialize_ast_node(None)
    print(f"Type: {serialized.get('type')}")
    print(f"Result: {serialized}")
except Exception as e:
    print(f"Exception: {type(e).__name__}: {e}")

# Test 3: Serialize a dict (not an AST node)
print("\n\nTEST 3: Serialize a dict")
print("-" * 80)
try:
    serialized = _serialize_ast_node({"foo": "bar"})
    print(f"Type: {serialized.get('type')}")
    print(f"Result: {serialized}")
except Exception as e:
    print(f"Exception: {type(e).__name__}: {e}")

# Test 4: Serialize an empty string
print("\n\nTEST 4: Serialize empty string")
print("-" * 80)
try:
    serialized = _serialize_ast_node("")
    print(f"Type: {serialized.get('type')}")
    print(f"Result: {serialized}")
except Exception as e:
    print(f"Exception: {type(e).__name__}: {e}")

# Test 5: Check if location=None causes issues
print("\n\nTEST 5: Serialize ProgramNode with explicit None location")
print("-" * 80)
program = ProgramNode(program_name="TEST", location=None)
serialized = _serialize_ast_node(program)
print(f"Type: {serialized.get('type')}")
print(f"Location: {serialized.get('location')}")

print("\n" + "=" * 80)
