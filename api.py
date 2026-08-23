#!/usr/bin/env python3
# This is the entry point for deployment
# It simply imports and runs your main bot file

import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and run the main bot
try:
    # Try to import from main.py
    from main import main
    import asyncio
    
    if __name__ == "__main__":
        asyncio.run(main())
except ImportError:
    print("❌ Error: main.py not found!")
    print("Make sure your bot code is in main.py")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error starting bot: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)