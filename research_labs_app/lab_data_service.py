import asyncio
import json
import os
from typing import List, Dict, Optional
from dedalus_labs import AsyncDedalus, DedalusRunner
from dotenv import load_dotenv

load_dotenv()

class LabDataService:
    def __init__(self):
        self.client = AsyncDedalus()
        self.runner = DedalusRunner(self.client)
        
    async def search_university_labs(self, university_name: str, limit: int = 20) -> List[Dict]:
        """Search for research labs at a specific university using MCP agents"""
        
        query = f"""
        Search comprehensively for research laboratories, research groups, and faculty research at {university_name}.
        
        IMPORTANT: For each lab, you MUST find and include the principal investigator's name. Search faculty directories, department pages, lab websites, and research center listings to identify the lead professor or director.
        
        Please find specific research labs and provide the following information for each:
        - Lab Name: [exact name of the research lab or group]
        - Professor: [REQUIRED - full name and title of the principal investigator, lab director, or lead faculty member]
        - Department: [specific academic department or school]
        - Research Focus: [detailed description of research areas, current projects, methodologies, applications, and recent achievements - provide 2-3 sentences with specific details]
        - Website: [lab website URL if available]
        - Email: [contact email if available]
        
        Search strategy:
        1. Look at faculty directory pages for each department
        2. Search for "[university name] research labs faculty"
        3. Search for "[university name] principal investigators"
        4. Check department websites for lab listings with faculty names
        5. Look for research center pages that list lab directors
        
        Focus on active research labs in computer science, engineering, biology, chemistry, physics, materials science, mathematics, and other STEM fields.
        
        CRITICAL: Do not list any lab without identifying its principal investigator or lead faculty member. If you cannot find the professor's name, search more thoroughly or skip that lab.
        
        Provide up to {limit} research labs with complete information including professor names.
        
        Format each lab entry clearly with the field labels above. Do not use markdown formatting like asterisks or bold text in the content - use plain text only.
        """
        
        try:
            result = await self.runner.run(
                input=query,
                model="openai/gpt-4o",  # Use more powerful model for better faculty search
                mcp_servers=[
                    "joerup/exa-mcp",        # Semantic search engine
                    "tsion/brave-search-mcp",  # Privacy-focused web search
                    "modelcontextprotocol/google-search",  # Google search
                ]
            )
            
            # Debug: print raw result (remove this in production)
            if len(result.final_output) < 1000:
                print(f"Raw MCP result for {university_name}:")
                print(result.final_output)
                print("---")
            
            # Parse the result and convert to our lab data format
            labs = self._parse_lab_results(result.final_output, university_name)
            return labs
            
        except Exception as e:
            print(f"Error searching labs for {university_name}: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _parse_lab_results(self, raw_results: str, university_name: str) -> List[Dict]:
        """Parse the raw MCP results into our lab data structure"""
        labs = []
        
        import re
        
        # Split by markdown headers (### 1., ### 2., etc.) or numbered sections
        sections = re.split(r'###\s*\d+\.\s*|\n\d+\.\s*', raw_results)
        
        for section in sections[1:]:  # Skip the first empty section
            if not section.strip():
                continue
            
            lab_info = {}
            lines = section.split('\n')
            
            # First line is usually the lab name
            first_line = lines[0].strip()
            if first_line:
                # Clean up asterisks and markdown formatting from lab name
                clean_name = re.sub(r'\*\*([^*]+)\*\*', r'\1', first_line)  # Remove **bold**
                clean_name = re.sub(r'\*([^*]+)\*', r'\1', clean_name)      # Remove *italic*
                clean_name = clean_name.replace('*', '').strip()            # Remove any remaining asterisks
                lab_info['name'] = clean_name
            
            # Look for structured information in bullet points
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Match patterns like "- **Lab Name**: value" or "- **Professor**: value"
                bullet_match = re.match(r'-\s*\*\*([^*]+)\*\*:?\s*(.+)', line)
                if bullet_match:
                    field = bullet_match.group(1).strip().lower()
                    value = bullet_match.group(2).strip()
                    # Clean up asterisks and markdown formatting
                    value = re.sub(r'\*\*([^*]+)\*\*', r'\1', value)  # Remove **bold**
                    value = re.sub(r'\*([^*]+)\*', r'\1', value)      # Remove *italic*
                    value = value.replace('*', '').strip()            # Remove any remaining asterisks
                    
                    if 'lab name' in field or 'laboratory' in field:
                        lab_info['name'] = value
                    elif 'professor' in field or 'faculty' in field or 'director' in field or 'pi' in field or 'investigator' in field:
                        lab_info['professor'] = value
                    elif 'department' in field or 'school' in field:
                        lab_info['department'] = value
                    elif 'research focus' in field or 'focus' in field or 'research' in field:
                        lab_info['description'] = value
                    elif 'website' in field or 'url' in field:
                        lab_info['url'] = value
                    elif 'email' in field or 'contact' in field:
                        lab_info['professor_email'] = value
                
                # Also look for simple colon-separated patterns
                elif ':' in line:
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        field = parts[0].strip().lower().replace('-', '').replace('*', '')
                        value = parts[1].strip()
                        # Clean up asterisks and markdown formatting
                        value = re.sub(r'\*\*([^*]+)\*\*', r'\1', value)  # Remove **bold**
                        value = re.sub(r'\*([^*]+)\*', r'\1', value)      # Remove *italic*
                        value = value.replace('*', '').strip()            # Remove any remaining asterisks
                        
                        if any(keyword in field for keyword in ['lab name', 'laboratory', 'group']):
                            lab_info['name'] = value
                        elif any(keyword in field for keyword in ['professor', 'faculty', 'director', 'pi', 'investigator', 'lead', 'head']):
                            lab_info['professor'] = value
                        elif any(keyword in field for keyword in ['department', 'school']):
                            lab_info['department'] = value
                        elif any(keyword in field for keyword in ['research', 'focus']):
                            lab_info['description'] = value
                        elif any(keyword in field for keyword in ['website', 'url']):
                            lab_info['url'] = value
                        elif any(keyword in field for keyword in ['email', 'contact']):
                            lab_info['professor_email'] = value
            
            # Create lab entry only if we have both name and professor
            if lab_info.get('name') and lab_info.get('professor'):
                lab = {
                    'name': lab_info.get('name'),
                    'professor': lab_info.get('professor'),
                    'school': university_name,
                    'description': lab_info.get('description', 'Research laboratory'),
                    'url': lab_info.get('url', ''),
                    'professor_email': lab_info.get('professor_email', '')
                }
                labs.append(lab)
            elif lab_info.get('name') and not lab_info.get('professor'):
                # Try to extract professor name from description or other fields
                description = lab_info.get('description', '')
                # Look for patterns like "Dr. Smith", "Professor Johnson", etc.
                import re
                prof_patterns = [
                    r'(?:Dr\.|Professor|Prof\.)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
                    r'([A-Z][a-z]+\s+[A-Z][a-z]+)(?:\s+is|\s+leads|\s+directs|\s+heads)',
                    r'led by\s+(?:Dr\.|Professor|Prof\.)?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
                    r'directed by\s+(?:Dr\.|Professor|Prof\.)?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
                ]
                
                extracted_prof = None
                for pattern in prof_patterns:
                    match = re.search(pattern, description, re.IGNORECASE)
                    if match:
                        extracted_prof = match.group(1).strip()
                        break
                
                if extracted_prof:
                    lab = {
                        'name': lab_info.get('name'),
                        'professor': extracted_prof,
                        'school': university_name,
                        'description': description,
                        'url': lab_info.get('url', ''),
                        'professor_email': lab_info.get('professor_email', '')
                    }
                    labs.append(lab)
        
        return labs
    
    async def populate_major_universities(self) -> List[Dict]:
        """Populate lab data for 10 major universities"""
        major_universities = [
            "University of Texas at Dallas",
            "Massachusetts Institute of Technology",
            "Stanford University", 
            "University of California Berkeley",
            "Carnegie Mellon University",
            "Georgia Institute of Technology",
            "University of Washington",
            "University of Illinois Urbana-Champaign",
            "California Institute of Technology",
            "Princeton University"
        ]
        
        all_labs = []
        
        for university in major_universities:
            print(f"Fetching labs for {university}...")
            try:
                labs = await self.search_university_labs(university, limit=15)
                all_labs.extend(labs)
                print(f"Found {len(labs)} labs for {university}")
                
                # Add a small delay to be respectful to APIs
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"Error fetching labs for {university}: {e}")
                continue
        
        return all_labs
    
    def save_labs_to_file(self, labs: List[Dict], filename: str = "utd_all_labs.json"):
        """Save labs data to JSON file"""
        filepath = os.path.join(os.path.dirname(__file__), 'data', filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(labs, f, indent=2, ensure_ascii=False)
        
        print(f"Saved {len(labs)} labs to {filepath}")

# Standalone script functionality
async def main():
    """Main function to populate lab data"""
    service = LabDataService()
    
    print("Starting lab data collection for major universities...")
    labs = await service.populate_major_universities()
    
    print(f"\nCollected {len(labs)} total labs")
    service.save_labs_to_file(labs)
    
    print("Lab data collection complete!")

if __name__ == "__main__":
    asyncio.run(main())
