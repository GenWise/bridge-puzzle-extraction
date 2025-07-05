#!/usr/bin/env python3
import re
import argparse
import fitz  # PyMuPDF
from typing import Dict, List, Tuple

def find_puzzle_pages(pdf_path: str) -> Tuple[Dict[int, int], Dict[int, int]]:
    """Find pages containing problems and solutions in the PDF."""
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    
    problem_pattern = re.compile(r'PROBLEM\s+(\d+)', re.IGNORECASE)
    solution_pattern = re.compile(r'SOLUTION\s+(\d+)', re.IGNORECASE)
    
    problem_pages = {}
    solution_pages = {}
    
    print(f"Scanning {total_pages} pages for puzzles and solutions...")
    
    for page_num in range(total_pages):
        page = doc[page_num]
        text = page.get_text()
        
        problem_match = problem_pattern.search(text)
        if problem_match:
            problem_num = int(problem_match.group(1))
            problem_pages[problem_num] = page_num
            
        solution_match = solution_pattern.search(text)
        if solution_match:
            solution_num = int(solution_match.group(1))
            solution_pages[solution_num] = page_num
        
        if (page_num + 1) % 20 == 0:
            print(f"Scanned {page_num + 1} pages...")
    
    print(f"Found {len(problem_pages)} problems and {len(solution_pages)} solutions.")
    return problem_pages, solution_pages

def print_puzzle_info(puzzle_num: int, problem_pages: Dict[int, int], solution_pages: Dict[int, int]) -> None:
    """Print information about a specific puzzle."""
    if puzzle_num in problem_pages and puzzle_num in solution_pages:
        problem_page = problem_pages[puzzle_num]
        solution_page = solution_pages[puzzle_num]
        print(f"Puzzle #{puzzle_num}:")
        print(f"  Problem page: {problem_page} (0-indexed)")
        print(f"  Solution page: {solution_page} (0-indexed)")
        print(f"\nTo extract this puzzle with test_claude_extraction.py, use:")
        print(f"python test_claude_extraction.py \"Test your play as declarer - Jeff Rubens & Paul Lukacs.pdf\" --problem-page {problem_page} --solution-page {solution_page} --puzzle-num {puzzle_num} --api-key YOUR_API_KEY")
    elif puzzle_num in problem_pages:
        print(f"Puzzle #{puzzle_num}: Problem found on page {problem_pages[puzzle_num]} but no solution found.")
    elif puzzle_num in solution_pages:
        print(f"Puzzle #{puzzle_num}: Solution found on page {solution_pages[puzzle_num]} but no problem found.")
    else:
        print(f"Puzzle #{puzzle_num} not found in the PDF.")

def main():
    parser = argparse.ArgumentParser(description='Find puzzle and solution page numbers in a bridge PDF book.')
    parser.add_argument('pdf_path', help='Path to the PDF file')
    parser.add_argument('--puzzle', '-p', type=int, help='Show information for a specific puzzle number')
    parser.add_argument('--list-all', '-l', action='store_true', help='List all puzzles and their page numbers')
    parser.add_argument('--range', '-r', nargs=2, type=int, metavar=('START', 'END'), help='Show puzzles in a specific range')
    
    args = parser.parse_args()
    
    problem_pages, solution_pages = find_puzzle_pages(args.pdf_path)
    
    if args.puzzle:
        print_puzzle_info(args.puzzle, problem_pages, solution_pages)
    elif args.range:
        start, end = args.range
        for puzzle_num in range(start, end + 1):
            if puzzle_num in problem_pages or puzzle_num in solution_pages:
                print_puzzle_info(puzzle_num, problem_pages, solution_pages)
                print()
    elif args.list_all:
        puzzle_numbers = sorted(set(list(problem_pages.keys()) + list(solution_pages.keys())))
        for puzzle_num in puzzle_numbers:
            print_puzzle_info(puzzle_num, problem_pages, solution_pages)
            print()
    else:
        print("\nPuzzle Summary:")
        print(f"Total puzzles found: {len(set(list(problem_pages.keys()) + list(solution_pages.keys())))}")
        print(f"Problems found: {len(problem_pages)}")
        print(f"Solutions found: {len(solution_pages)}")
        print("\nUse --puzzle, --range, or --list-all to see more details.")

if __name__ == "__main__":
    main() 