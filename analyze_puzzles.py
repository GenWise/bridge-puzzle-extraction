#!/usr/bin/env python3
import json
import argparse
import os
from collections import Counter
from typing import Dict, List, Any

class BridgePuzzleAnalyzer:
    def __init__(self, json_path: str):
        """Initialize the analyzer with the path to the JSON file."""
        self.json_path = json_path
        with open(json_path, 'r', encoding='utf-8') as f:
            self.puzzles = json.load(f)
        print(f"Loaded {len(self.puzzles)} puzzles from {json_path}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get basic statistics about the puzzle collection."""
        game_types = Counter()
        vulnerabilities = Counter()
        leads = Counter()
        
        for puzzle in self.puzzles:
            problem = puzzle.get("problem", {})
            game_types[problem.get("game_type", "Unknown")] += 1
            vulnerabilities[problem.get("vulnerability", "Unknown")] += 1
            
            lead = problem.get("lead", "")
            if lead:
                # Extract just the suit/card from the lead
                lead_parts = lead.split("leads the ")
                if len(lead_parts) > 1:
                    card_led = lead_parts[1].replace(".", "").strip()
                    leads[card_led] += 1
        
        return {
            "total_puzzles": len(self.puzzles),
            "game_types": dict(game_types),
            "vulnerabilities": dict(vulnerabilities),
            "leads": dict(sorted(leads.items(), key=lambda x: x[1], reverse=True)[:10])  # Top 10 leads
        }
    
    def search_puzzles(self, keyword: str) -> List[Dict[str, Any]]:
        """Search for puzzles containing a specific keyword in the explanation."""
        results = []
        
        for puzzle in self.puzzles:
            solution = puzzle.get("solution", {})
            explanation = solution.get("explanation", "").lower()
            
            if keyword.lower() in explanation:
                results.append({
                    "problem_number": puzzle.get("problem_number"),
                    "snippet": explanation[:200] + "..." if len(explanation) > 200 else explanation
                })
        
        return results
    
    def get_puzzle_by_number(self, number: int) -> Dict[str, Any]:
        """Get a specific puzzle by its number."""
        for puzzle in self.puzzles:
            if puzzle.get("problem_number") == number:
                return puzzle
        return {}
    
    def extract_techniques(self) -> Dict[str, List[int]]:
        """Extract common bridge techniques mentioned in the solutions."""
        techniques = {
            "finesse": [],
            "endplay": [],
            "squeeze": [],
            "elimination": [],
            "trump coup": [],
            "dummy reversal": [],
            "safety play": [],
            "duck": [],
            "overtake": [],
            "discard": [],
            "ruffing": [],
            "crossruff": []
        }
        
        for puzzle in self.puzzles:
            problem_num = puzzle.get("problem_number")
            solution = puzzle.get("solution", {})
            explanation = solution.get("explanation", "").lower()
            
            for technique in techniques:
                if technique in explanation:
                    techniques[technique].append(problem_num)
        
        # Filter out techniques with no occurrences
        return {k: v for k, v in techniques.items() if v}
    
    def print_puzzle_summary(self, puzzle: Dict[str, Any]) -> None:
        """Print a summary of a puzzle."""
        problem = puzzle.get("problem", {})
        solution = puzzle.get("solution", {})
        
        print(f"Problem #{puzzle.get('problem_number')}")
        print(f"Game Type: {problem.get('game_type', 'Unknown')}")
        print(f"Vulnerability: {problem.get('vulnerability', 'Unknown')}")
        print(f"Lead: {problem.get('lead', 'Unknown')}")
        print("\nNorth Cards:")
        print(problem.get("north_cards", ""))
        print("\nSouth Cards:")
        print(problem.get("south_cards", ""))
        print("\nTask:")
        print(problem.get("task", ""))
        
        print("\nSolution Explanation:")
        explanation = solution.get("explanation", "")
        # Print first 300 characters of explanation
        print(explanation[:300] + "..." if len(explanation) > 300 else explanation)
        print("\n" + "-"*50)

def main():
    parser = argparse.ArgumentParser(description='Analyze bridge puzzles from extracted JSON data.')
    parser.add_argument('json_path', help='Path to the JSON file with puzzle data')
    parser.add_argument('--stats', action='store_true', help='Show statistics about the puzzles')
    parser.add_argument('--search', type=str, help='Search for puzzles containing a specific keyword')
    parser.add_argument('--puzzle', type=int, help='Show a specific puzzle by number')
    parser.add_argument('--techniques', action='store_true', help='Show common bridge techniques and related puzzles')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.json_path):
        print(f"Error: JSON file not found at {args.json_path}")
        return
    
    analyzer = BridgePuzzleAnalyzer(args.json_path)
    
    if args.stats:
        stats = analyzer.get_statistics()
        print("\nPuzzle Statistics:")
        print(f"Total Puzzles: {stats['total_puzzles']}")
        
        print("\nGame Types:")
        for game_type, count in stats['game_types'].items():
            print(f"  {game_type}: {count}")
        
        print("\nVulnerabilities:")
        for vuln, count in stats['vulnerabilities'].items():
            print(f"  {vuln}: {count}")
        
        print("\nTop 10 Opening Leads:")
        for lead, count in stats['leads'].items():
            print(f"  {lead}: {count}")
    
    if args.search:
        results = analyzer.search_puzzles(args.search)
        print(f"\nFound {len(results)} puzzles containing '{args.search}':")
        for result in results:
            print(f"\nProblem #{result['problem_number']}:")
            print(f"  {result['snippet']}")
    
    if args.puzzle:
        puzzle = analyzer.get_puzzle_by_number(args.puzzle)
        if puzzle:
            analyzer.print_puzzle_summary(puzzle)
        else:
            print(f"Puzzle #{args.puzzle} not found.")
    
    if args.techniques:
        techniques = analyzer.extract_techniques()
        print("\nBridge Techniques and Related Puzzles:")
        for technique, puzzles in techniques.items():
            print(f"\n{technique.title()}:")
            print(f"  Found in puzzles: {', '.join(map(str, puzzles))}")

if __name__ == "__main__":
    main() 