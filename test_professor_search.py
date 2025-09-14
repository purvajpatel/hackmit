#!/usr/bin/env python3
"""
Test script to verify professor name detection improvements
"""

import asyncio
import sys
import os

# Add the research_labs_app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'research_labs_app'))

from research_labs_app.lab_data_service import LabDataService

async def test_professor_detection():
    """Test improved professor name detection"""
    service = LabDataService()
    
    # Test with a well-known university
    university = "Stanford University"
    print(f"Testing enhanced professor search for: {university}")
    print("=" * 60)
    
    try:
        labs = await service.search_university_labs(university, limit=3)
        
        print(f"\nFound {len(labs)} labs with professor information:")
        print("=" * 60)
        
        for i, lab in enumerate(labs, 1):
            print(f"\n{i}. Lab: {lab['name']}")
            print(f"   Professor: {lab['professor']}")
            print(f"   Department: {lab.get('department', 'N/A')}")
            print(f"   School: {lab['school']}")
            print(f"   Description: {lab['description'][:100]}...")
            print(f"   URL: {lab['url']}")
            print(f"   Email: {lab['professor_email']}")
        
        # Check if all labs have professor names
        labs_with_profs = [lab for lab in labs if lab['professor'] and lab['professor'] != 'Faculty Member']
        print(f"\n✅ Labs with identified professors: {len(labs_with_profs)}/{len(labs)}")
        
        if len(labs_with_profs) < len(labs):
            print("⚠️  Some labs are missing professor information")
        else:
            print("🎉 All labs have professor information!")
        
        return labs
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == "__main__":
    labs = asyncio.run(test_professor_detection())
