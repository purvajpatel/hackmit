#!/usr/bin/env python3
"""
Script to populate initial lab data using the MCP agent
Run this to fetch lab data for major universities and populate the database
"""

import asyncio
import sys
import os

# Add the research_labs_app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'research_labs_app'))

from research_labs_app.lab_data_service import LabDataService

async def main():
    """Main function to populate lab data for major universities"""
    print("🔬 ResearchConnect Lab Data Population")
    print("=" * 50)
    
    service = LabDataService()
    
    print("Starting lab data collection for major universities...")
    print("This may take several minutes as we search each university...")
    print()
    
    try:
        labs = await service.populate_major_universities()
        
        print(f"\n✅ Successfully collected {len(labs)} total labs")
        service.save_labs_to_file(labs)
        
        print("\n🎉 Lab data population complete!")
        print("The app is now ready to use with fresh lab data.")
        
    except Exception as e:
        print(f"\n❌ Error during lab data collection: {e}")
        print("Please check your environment setup and API keys.")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
