#!/usr/bin/env python3
"""
Debug script to see what events htty is receiving
"""

import htty
import time
import json

def debug_events(proc):
    """Print all events currently in the process"""
    print("=== Events in process ===")
    try:
        # Access the events directly (this is a hack for debugging)
        events = proc.events.lock().unwrap() if hasattr(proc, 'events') else []
        for i, event in enumerate(events):
            print(f"Event {i}: {event}")
    except:
        print("Could not access events directly")
    print("========================")

def test_echo_with_debug():
    """Test echo command with debug output"""
    print("Testing echo with event debugging...")
    
    try:
        proc = htty.run(["echo", "Hello World"], rows=4, cols=20)
        print("✓ Process created")
        
        # Wait a bit for initial events
        time.sleep(1)
        debug_events(proc)
        
        print("Taking snapshot...")
        try:
            snapshot = proc.snapshot()
            print(f"✓ Snapshot successful: {repr(snapshot.text[:50])}")
        except Exception as e:
            print(f"❌ Snapshot failed: {e}")
            debug_events(proc)
        
        print("Exiting...")
        proc.exit()
        print("✓ Process exited")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_echo_with_debug()
