#!/usr/bin/env python3
"""
Test script to debug MCP agent lab search
"""

import asyncio
import sys
import os

# Add the research_labs_app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'research_labs_app'))

from research_labs_app.lab_data_service import LabDataService

async def test_single_university():
    """Test lab search for a single university"""
    service = LabDataService()
    
    # Test with a well-known university
    university = "Massachusetts Institute of Technology"
    print(f"Testing lab search for: {university}")
    print("=" * 50)
    
    try:
        labs = await service.search_university_labs(university, limit=5)
        
        print(f"\nFound {len(labs)} labs:")
        for i, lab in enumerate(labs, 1):
            print(f"\n{i}. {lab['name']}")
            print(f"   Professor: {lab['professor']}")
            print(f"   School: {lab['school']}")
            print(f"   Description: {lab['description']}")
            print(f"   URL: {lab['url']}")
            print(f"   Email: {lab['professor_email']}")
        
        return labs
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == "__main__":
    labs = asyncio.run(test_single_university())
    print(f"\nTotal labs found: {len(labs)}")
