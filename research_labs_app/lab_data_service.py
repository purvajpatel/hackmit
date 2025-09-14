"""
Lab Data Service - MCP Agent Integration for Research Lab Discovery
"""

import os
import json
import asyncio
from typing import List, Dict
from dedalus_labs import AsyncDedalus, DedalusRunner
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class LabDataService:
    def __init__(self):
        # Configure Dedalus client with proper API key
        dedalus_api_key = os.getenv('DEDALUS_API_KEY')
        if not dedalus_api_key:
            raise ValueError("No DEDALUS_API_KEY found. Please set DEDALUS_API_KEY in your .env file")
        
        self.client = AsyncDedalus(api_key=dedalus_api_key)
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
        
        CRITICAL REQUIREMENTS:
        1. Every lab entry MUST have a professor name - no exceptions
        2. If you cannot find a professor name after thorough searching, DO NOT include that lab
        3. Search multiple sources: faculty directories, lab websites, research center pages, department listings
        4. Look for titles like: Professor, Dr., Principal Investigator, Lab Director, Research Scientist, Assistant Professor, Associate Professor
        5. Verify professor names are real people, not generic titles or descriptions
        6. Search deeper - check "People", "Faculty", "Team", "About" sections of lab websites
        7. If a lab page doesn't list the PI, search the university's faculty directory for that lab name
        
        Only provide labs where you have successfully identified the principal investigator or lead faculty member.
        Target: {limit} research labs with complete information including verified professor names.
        
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
            
            # Debug: print raw result
            print(f"Raw MCP result for {university_name}:")
            print(f"Result length: {len(result.final_output)} characters")
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
        
        print(f"Parsing results for {university_name}...")
        print(f"Raw results preview: {raw_results[:500]}...")
        
        # Split by markdown headers (### 1., ### 2., etc.) or numbered sections
        sections = re.split(r'###\s*\d+\.\s*|\n\d+\.\s*', raw_results)
        print(f"Found {len(sections)} sections after splitting")
        
        for i, section in enumerate(sections[1:], 1):  # Skip the first empty section
            if not section.strip():
                continue
            
            print(f"Processing section {i}: {section[:200]}...")
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
                professor_name = lab_info.get('professor').strip()
                
                print(f"Found lab: {lab_info.get('name')} with professor: {professor_name}")
                
                # Validate professor name - must be a real person, not generic title
                invalid_names = [
                    'not specified', 'faculty member', 'unknown', 'tbd', 'to be determined',
                    'research team', 'lab team', 'multiple faculty', 'various faculty',
                    'staff', 'researchers', 'n/a', 'none', 'contact lab', 'see website',
                    'not explicitly named', 'not provided', 'associated with', 'center for',
                    'department of', 'school of', 'institute of', 'laboratory', 'group'
                ]
                
                # Check if professor name contains any invalid phrases
                is_valid_name = True
                professor_lower = professor_name.lower()
                
                # Check for exact matches or partial matches with invalid names
                # But be more lenient - only reject if the ENTIRE name is invalid
                for invalid in invalid_names:
                    if professor_lower.strip() == invalid or professor_lower.startswith(invalid + ' ') or professor_lower.endswith(' ' + invalid):
                        is_valid_name = False
                        print(f"Rejected lab {lab_info.get('name')} - invalid professor name: {professor_name}")
                        break
                
                # Simplified validation: just check if it contains at least one capitalized word that looks like a name
                # This is much more permissive and will catch most valid professor names
                has_proper_name = bool(re.search(r'[A-Z][a-z]{2,}', professor_name))
                
                # Must be longer than 3 characters and not contain common invalid phrases
                if (is_valid_name and len(professor_name) > 3 and has_proper_name and 
                    not any(phrase in professor_lower for phrase in ['contact', 'email', 'website', 'page'])):
                    lab = {
                        'name': lab_info.get('name'),
                        'professor': professor_name,
                        'school': university_name,
                        'description': lab_info.get('description', 'Research laboratory'),
                        'url': lab_info.get('url', ''),
                        'professor_email': lab_info.get('professor_email', '')
                    }
                    labs.append(lab)
                    print(f"Added lab: {lab_info.get('name')}")
                else:
                    print(f"Rejected lab {lab_info.get('name')} - failed validation: valid_name={is_valid_name}, length={len(professor_name)}, has_proper_name={bool(has_proper_name)}")
            elif lab_info.get('name'):
                print(f"Lab {lab_info.get('name')} missing professor information")
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
                all_text = f"{lab_info.get('name', '')} {description}"
                
                for pattern in prof_patterns:
                    match = re.search(pattern, all_text, re.IGNORECASE)
                    if match:
                        candidate = match.group(1).strip()
                        # Validate it's a real name (has at least first and last name)
                        if (len(candidate.split()) >= 2 and 
                            not any(word.lower() in candidate.lower() for word in ['lab', 'group', 'center', 'institute']) and
                            not any(phrase in candidate.lower() for phrase in ['contact', 'email', 'website', 'page'])):
                            extracted_prof = candidate
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
        
        print(f"Final result: Found {len(labs)} valid labs for {university_name}")
        for lab in labs:
            print(f"  - {lab['name']} (Prof: {lab['professor']})")
        
        return labs
    
    async def populate_major_universities(self) -> List[Dict]:
        """Populate lab data for 10 major universities"""
        major_universities = [
            "University of Texas at Dallas",
            "Massachusetts Institute of Technology",
            "Stanford University", 
            "University of California Berkeley",
            "Carnegie Mellon University",
            "California Institute of Technology",
            "Harvard University",
            "Princeton University",
            "University of Washington",
            "Georgia Institute of Technology"
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
