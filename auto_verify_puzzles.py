#!/usr/bin/env python3
import os
import json
import argparse
import random
import datetime
from typing import Dict, Any, List, Optional, Tuple

class AutomaticVerifier:
    def __init__(self, results_file: str, log_file: Optional[str] = None):
        """Initialize the verifier with the path to the results file."""
        self.results_file = results_file
        self.log_file = log_file or f"auto_verification_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        # Load the results
        with open(results_file, 'r', encoding='utf-8') as f:
            self.results = json.load(f)
            
    def verify_random_puzzles(self, count: int = 10) -> None:
        """Verify a random selection of puzzles and log the results."""
        # Get all puzzle numbers
        puzzle_numbers = [puzzle["problem_number"] for puzzle in self.results]
        
        # Ensure we don't try to select more puzzles than exist
        count = min(count, len(puzzle_numbers))
        
        # Randomly select puzzles
        selected_puzzles = random.sample(puzzle_numbers, count)
        
        print(f"Selected {count} random puzzles for verification: {selected_puzzles}")
        
        # Initialize the log file
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write(f"Automatic Verification Log - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Randomly selected puzzles: {selected_puzzles}\n\n")
        
        # Verify each selected puzzle
        for puzzle_num in selected_puzzles:
            result = self._verify_puzzle(puzzle_num)
            
            # Log the result
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(f"Puzzle #{puzzle_num} Verification:\n")
                f.write(json.dumps(result, indent=2))
                f.write("\n\n")
            
            print(f"Verified puzzle #{puzzle_num} - Results logged to {self.log_file}")
    
    def _verify_puzzle(self, puzzle_num: int) -> Dict[str, Any]:
        """Verify a puzzle and return the verification results."""
        # Find the puzzle in the results
        puzzle = next((p for p in self.results if p["problem_number"] == puzzle_num), None)
        if not puzzle:
            return {"error": f"Puzzle #{puzzle_num} not found in results"}
        
        result = {
            "puzzle_number": puzzle_num,
            "verification_time": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "problem": self._verify_problem(puzzle["problem"]),
            "solution": self._verify_solution(puzzle["solution"])
        }
        
        return result
    
    def _verify_problem(self, problem: Dict[str, Any]) -> Dict[str, Any]:
        """Verify problem data with automated checks."""
        issues = []
        
        # Check for required fields
        required_fields = ["problemNumber", "gameType", "vulnerability", "cardLayout", "biddingSequence", "openingLead", "taskDescription"]
        for field in required_fields:
            if field not in problem:
                issues.append(f"Missing required field: {field}")
        
        # Check card layout
        if "cardLayout" in problem:
            card_layout = problem["cardLayout"]
            
            # Check that North and South hands are present (case-insensitive)
            north_present = any(hand.lower() == "north" for hand in card_layout)
            south_present = any(hand.lower() == "south" for hand in card_layout)
            
            if not north_present:
                issues.append("North hand is missing in card layout")
            if not south_present:
                issues.append("South hand is missing in card layout")
            
            # Check for valid card suits in each hand (case-insensitive)
            for hand_name in card_layout:
                hand = card_layout[hand_name]
                if hand:  # Only check if the hand is not empty
                    for suit in hand:
                        if suit not in ["♠", "♥", "♦", "♣", "spades", "hearts", "diamonds", "clubs"]:
                            issues.append(f"Invalid suit {suit} in {hand_name} hand")
        
        # Check bidding sequence
        if "biddingSequence" in problem:
            bidding = problem["biddingSequence"]
            if not isinstance(bidding, list):
                issues.append("Bidding sequence is not a list")
        
        # Check opening lead
        if "openingLead" in problem and not problem["openingLead"]:
            issues.append("Opening lead is empty")
        
        # Check task description
        if "taskDescription" in problem and not problem["taskDescription"]:
            issues.append("Task description is empty")
        
        return {
            "issues": issues,
            "status": "OK" if not issues else "Issues found",
            "issue_count": len(issues)
        }
    
    def _verify_solution(self, solution: Dict[str, Any]) -> Dict[str, Any]:
        """Verify solution data with automated checks."""
        issues = []
        
        # Check for required fields
        required_fields = ["solutionNumber", "cardLayout", "solutionExplanation"]
        for field in required_fields:
            if field not in solution:
                issues.append(f"Missing required field: {field}")
        
        # Check card layout
        if "cardLayout" in solution:
            card_layout = solution["cardLayout"]
            
            # Check that all four hands are present (case-insensitive)
            hands = ["north", "south", "east", "west"]
            for hand in hands:
                hand_present = any(h.lower() == hand for h in card_layout)
                if not hand_present:
                    issues.append(f"{hand.capitalize()} hand is missing in solution card layout")
            
            # Check for valid card suits in each hand
            for hand_name in card_layout:
                hand = card_layout[hand_name]
                if hand:  # Only check if the hand is not empty
                    for suit in hand:
                        if suit not in ["♠", "♥", "♦", "♣", "spades", "hearts", "diamonds", "clubs"]:
                            issues.append(f"Invalid suit {suit} in solution {hand_name} hand")
        
        # Check solution explanation
        if "solutionExplanation" in solution and not solution["solutionExplanation"]:
            issues.append("Solution explanation is empty")
        
        # Check key techniques
        if "keyTechniques" in solution:
            if not isinstance(solution["keyTechniques"], list):
                issues.append("Key techniques is not a list")
            elif not solution["keyTechniques"]:
                issues.append("Key techniques list is empty")
        else:
            issues.append("Missing key techniques")
        
        return {
            "issues": issues,
            "status": "OK" if not issues else "Issues found",
            "issue_count": len(issues)
        }
    
    def verify_all_puzzles(self) -> None:
        """Verify all puzzles in the results file."""
        print(f"Verifying all {len(self.results)} puzzles...")
        
        # Initialize the log file
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write(f"Automatic Verification Log - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Verifying all {len(self.results)} puzzles\n\n")
        
        # Track statistics
        total_issues = 0
        puzzles_with_issues = 0
        
        # Verify each puzzle
        for puzzle in self.results:
            puzzle_num = puzzle["problem_number"]
            result = self._verify_puzzle(puzzle_num)
            
            # Count issues
            problem_issues = len(result["problem"]["issues"])
            solution_issues = len(result["solution"]["issues"])
            
            if problem_issues > 0 or solution_issues > 0:
                puzzles_with_issues += 1
                total_issues += problem_issues + solution_issues
                
                # Log puzzles with issues
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(f"Puzzle #{puzzle_num} Verification:\n")
                    f.write(json.dumps(result, indent=2))
                    f.write("\n\n")
                
                print(f"Puzzle #{puzzle_num} has {problem_issues + solution_issues} issues")
        
        # Log summary
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"\nVerification Summary:\n")
            f.write(f"Total puzzles: {len(self.results)}\n")
            f.write(f"Puzzles with issues: {puzzles_with_issues}\n")
            f.write(f"Total issues found: {total_issues}\n")
        
        print(f"\nVerification complete:")
        print(f"Total puzzles: {len(self.results)}")
        print(f"Puzzles with issues: {puzzles_with_issues}")
        print(f"Total issues found: {total_issues}")
        print(f"Results logged to {self.log_file}")

def main():
    parser = argparse.ArgumentParser(description='Automatically verify bridge puzzle extraction results.')
    parser.add_argument('results_file', help='Path to the JSON results file')
    parser.add_argument('--random', '-r', type=int, default=10, help='Verify a random selection of puzzles (default: 10)')
    parser.add_argument('--all', '-a', action='store_true', help='Verify all puzzles')
    parser.add_argument('--log-file', '-l', help='Path to log file for verification results')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.results_file):
        print(f"Error: Results file not found at {args.results_file}")
        return
    
    verifier = AutomaticVerifier(args.results_file, args.log_file)
    
    if args.all:
        verifier.verify_all_puzzles()
    else:
        verifier.verify_random_puzzles(args.random)

if __name__ == "__main__":
    main() 