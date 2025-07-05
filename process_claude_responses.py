#!/usr/bin/env python3
import os
import re
import json
import argparse
from typing import Dict, Any, List, Optional

def extract_json_from_response(response_text: str) -> Dict[str, Any]:
    """Extract JSON from Claude's response text."""
    # Try to find JSON within code blocks
    json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', response_text, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        # If no code blocks, try to find anything that looks like JSON
        json_str = response_text
    
    try:
        result = json.loads(json_str)
        return result
    except json.JSONDecodeError:
        # If JSON parsing fails, return the raw text
        return {"error": "Failed to parse JSON", "raw_text": response_text}

def process_response_file(file_path: str) -> Dict[str, Any]:
    """Process a Claude API response file and extract the JSON data."""
    with open(file_path, 'r', encoding='utf-8') as f:
        response_data = json.load(f)
    
    # Extract the text content from the response
    if 'content' in response_data and len(response_data['content']) > 0:
        text_content = response_data['content'][0].get('text', '')
        return extract_json_from_response(text_content)
    else:
        return {"error": "No content found in response"}

def combine_puzzle_data(problem_data: Dict[str, Any], solution_data: Dict[str, Any], puzzle_num: int) -> Dict[str, Any]:
    """Combine problem and solution data into a single puzzle object."""
    return {
        "problem_number": puzzle_num,
        "problem": problem_data,
        "solution": solution_data
    }

def process_directory(directory: str, output_file: str) -> None:
    """Process all response files in a directory and combine them into puzzles."""
    files = os.listdir(directory)
    problem_files = sorted([f for f in files if f.startswith('problem_') and f.endswith('_response.json')])
    solution_files = sorted([f for f in files if f.startswith('solution_') and f.endswith('_response.json')])
    
    puzzles = []
    
    for problem_file in problem_files:
        # Extract puzzle number from filename
        match = re.search(r'problem_(\d+)_response\.json', problem_file)
        if not match:
            continue
        
        puzzle_num = int(match.group(1))
        solution_file = f'solution_{puzzle_num}_response.json'
        
        if solution_file not in solution_files:
            print(f"Warning: No matching solution file for problem {puzzle_num}")
            continue
        
        problem_path = os.path.join(directory, problem_file)
        solution_path = os.path.join(directory, solution_file)
        
        problem_data = process_response_file(problem_path)
        solution_data = process_response_file(solution_path)
        
        puzzle = combine_puzzle_data(problem_data, solution_data, puzzle_num)
        puzzles.append(puzzle)
    
    # Save combined puzzles to output file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(puzzles, f, indent=2, ensure_ascii=False)
    
    print(f"Processed {len(puzzles)} puzzles and saved to {output_file}")

def main():
    parser = argparse.ArgumentParser(description='Process Claude API responses and extract JSON data.')
    parser.add_argument('--input-dir', '-i', required=True, help='Directory containing response files')
    parser.add_argument('--output', '-o', default='processed_puzzles.json', help='Output JSON file path')
    parser.add_argument('--problem-file', '-p', help='Process a single problem response file')
    parser.add_argument('--solution-file', '-s', help='Process a single solution response file')
    parser.add_argument('--puzzle-num', '-n', type=int, help='Puzzle number for single file processing')
    
    args = parser.parse_args()
    
    if args.problem_file and args.solution_file and args.puzzle_num is not None:
        # Process single puzzle
        problem_data = process_response_file(args.problem_file)
        solution_data = process_response_file(args.solution_file)
        
        puzzle = combine_puzzle_data(problem_data, solution_data, args.puzzle_num)
        
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump([puzzle], f, indent=2, ensure_ascii=False)
        
        print(f"Processed puzzle {args.puzzle_num} and saved to {args.output}")
    else:
        # Process all files in directory
        process_directory(args.input_dir, args.output)

if __name__ == "__main__":
    main() 