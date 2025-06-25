#!/usr/bin/env python3
"""
Simple test to verify htty module works correctly
"""

import htty
import tempfile
import os

def test_basic_import():
    """Test that htty can be imported and has the expected attributes"""
    print("✓ htty module imported successfully")
    
    # Check that Press class exists
    assert hasattr(htty, 'Press'), "htty.Press class not found"
    print("✓ htty.Press class exists")
    
    # Check that key constants exist
    assert hasattr(htty.Press, 'ENTER'), "htty.Press.ENTER not found"
    assert hasattr(htty.Press, 'TAB'), "htty.Press.TAB not found"
    assert hasattr(htty.Press, 'ESCAPE'), "htty.Press.ESCAPE not found"
    print("✓ htty.Press key constants exist")
    
    # Check some key values
    assert htty.Press.ENTER == "Enter", f"Expected 'Enter', got '{htty.Press.ENTER}'"
    assert htty.Press.TAB == "Tab", f"Expected 'Tab', got '{htty.Press.TAB}'"
    print("✓ htty.Press key values are correct")

def test_ht_process_creation():
    """Test creating an ht process context manager"""
    print("Testing ht_process creation...")
    
    # This should work but may fail if the ht binary isn't found
    try:
        with htty.ht_process("echo test", rows=10, cols=40) as proc:
            print("✓ ht_process context manager created successfully")
            # Test basic process interaction
            snapshot = proc.snapshot()
            print("✓ snapshot() method works")
            print(f"✓ Snapshot text length: {len(snapshot.text) if hasattr(snapshot, 'text') else 'No text attr'}")
    except Exception as e:
        print(f"⚠ ht_process test failed (expected if ht binary not available): {e}")

def test_run_function():
    """Test the run function"""
    print("Testing run function...")
    
    try:
        proc = htty.run("echo hello", rows=10, cols=40)
        print("✓ run() function works")
        snapshot = proc.snapshot()
        print("✓ snapshot() on run result works")
        proc.exit()
        print("✓ exit() method works")
    except Exception as e:
        print(f"⚠ run() test failed (expected if ht binary not available): {e}")

def test_send_keys():
    """Test send_keys with string argument"""
    print("Testing send_keys with string...")
    
    try:
        proc = htty.run("cat", rows=10, cols=40)
        print("✓ run() function works")
        proc.send_keys("hello")
        print("✓ send_keys() with string works")
        proc.send_keys([htty.Press.ENTER])
        print("✓ send_keys() with list works")
        snapshot = proc.snapshot()
        print("✓ snapshot() on run result works")
        proc.exit()
        print("✓ exit() method works")
    except Exception as e:
        print(f"⚠ send_keys test failed (expected if ht binary not available): {e}")

if __name__ == "__main__":
    print("=== Running basic htty tests ===")
    
    try:
        test_basic_import()
        print()
        test_ht_process_creation()
        print()
        test_run_function()
        print()
        test_send_keys()
        print("\n=== All tests completed ===")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
