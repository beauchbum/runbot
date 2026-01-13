#!/usr/bin/env python3
"""
Debug script to see what LLM returns for South Brooklyn matching
"""

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from openai import OpenAI
from utils.config_utils import require_variable

def main():
    print("Debug: Testing LLM response for South Brooklyn\n")
    print("=" * 80)

    # Initialize OpenAI client
    openai_api_key = require_variable('openai_api_key')
    client = OpenAI(api_key=openai_api_key)

    # Simulate the prompt that would be sent
    target_names_str = "Thursday South Brooklyn' or 'South Brooklyn"
    candidates_str = """- North Brooklyn Run (1 occurrences, e.g., 2026-01-08)
- North Brooklyn Run Series: Greenpoint Edition (1 occurrences, e.g., 2025-12-11)
- SBK Dumping Run (1 occurrences, e.g., 2025-12-11)
- Thursday Riverside Drive (3 occurrences, e.g., 2025-09-04, 2025-07-31, 2025-07-24)
- Thursday South Brooklyn (1 occurrences, e.g., 2026-01-08)
- Xmas LONG Run (1 occurrences, e.g., 2025-12-25)"""

    prompt = """You are matching run names to find attendance records for the same geographic location/route.

TARGET RUN NAMES (the run we're looking for):
{target_names_str}

CANDIDATE ATTENDANCE RUNS (all on the same day of week):
{candidates_str}

Your task: Identify which candidates are for the SAME RUN/LOCATION as the target.

MATCHING RULES:
1. EXACT or VERY CLOSE matches should ALWAYS be included
2. Same core location = match (e.g., "South Brooklyn", "Queens", "Prospect Park")
3. Ignore day-of-week prefixes (e.g., "Thursday South Brooklyn" = "South Brooklyn Run")
4. Ignore generic suffixes like "Run", "Loop", "Edition", "Series"
5. Common abbreviations: "PP" = Prospect Park, "CP" = Central Park, "SBK" = South Brooklyn

NON-MATCHING RULES:
1. Different event types: "Queens Loop" ≠ "Queens R2C" or "Queens Run2Canvass"
2. Different neighborhoods: "North Brooklyn" ≠ "South Brooklyn"

Be INCLUSIVE - when in doubt, include it. Focus on the geographic location.

OUTPUT FORMAT:
- Return ONLY the candidate name(s) that match (copy exactly from the candidate list)
- One name per line
- If no matches, return exactly "NONE"
- Do NOT add explanations or extra text

Example:
If target is "Thursday South Brooklyn" and candidates include "SBK Dumping Run" and "Thursday South Brooklyn", you should return both (same location).
If target is "Queens Loop" and candidates include "Queens R2C", do NOT match (different event types).""".format(
        target_names_str=target_names_str,
        candidates_str=candidates_str
    )

    print("Sending prompt to LLM...\n")

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that matches run names. Always respond with candidate names or 'NONE'."},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )

    llm_response = response.choices[0].message.content.strip()

    print("=" * 80)
    print("\nLLM RESPONSE:")
    print("-" * 80)
    print(llm_response)
    print("-" * 80)

    # Parse the response
    if llm_response.upper() == "NONE":
        print("\n❌ LLM returned NONE - no matches found")
    else:
        matched_names = [line.strip() for line in llm_response.split('\n') if line.strip()]
        print(f"\n✅ LLM matched {len(matched_names)} name(s):")
        for name in matched_names:
            print(f"  - {name}")

    print("\n" + "=" * 80)
    return 0

if __name__ == "__main__":
    sys.exit(main())
