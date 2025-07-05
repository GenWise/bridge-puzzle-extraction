import os
import re
import json
import fitz  # PyMuPDF
import argparse
from typing import Dict, List, Optional, Tuple, Any

class BridgePuzzleExtractor:
    def __init__(self, pdf_path: str):
        """Initialize the extractor with the path to the PDF file."""
        self.pdf_path = pdf_path
        self.doc = fitz.open(pdf_path)
        self.total_pages = len(self.doc)
        self.puzzles = []
        
    def extract_all_puzzles(self) -> List[Dict[str, Any]]:
        """Extract all puzzles and solutions from the PDF."""
        problem_pattern = re.compile(r'PROBLEM\s+(\d+)', re.IGNORECASE)
        solution_pattern = re.compile(r'SOLUTION\s+(\d+)', re.IGNORECASE)
        
        problem_pages = {}
        solution_pages = {}
        
        # First, find all problem and solution page numbers
        for page_num in range(self.total_pages):
            page = self.doc[page_num]
            text = page.get_text()
            
            problem_match = problem_pattern.search(text)
            if problem_match:
                problem_num = int(problem_match.group(1))
                problem_pages[problem_num] = page_num
                
            solution_match = solution_pattern.search(text)
            if solution_match:
                solution_num = int(solution_match.group(1))
                solution_pages[solution_num] = page_num
        
        # Now extract each problem and its solution
        for problem_num in sorted(problem_pages.keys()):
            if problem_num in solution_pages:
                problem_data = self.extract_problem(problem_num, problem_pages[problem_num])
                solution_data = self.extract_solution(problem_num, solution_pages[problem_num])
                
                # Clean up and normalize the data
                problem_data = self.clean_card_data(problem_data)
                solution_data = self.clean_card_data(solution_data)
                
                puzzle = {
                    "problem_number": problem_num,
                    "problem": problem_data,
                    "solution": solution_data
                }
                
                self.puzzles.append(puzzle)
                
        return self.puzzles
    
    def clean_card_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and normalize card data by replacing symbols and formatting."""
        if not data:
            return data
            
        # Replace common OCR errors and normalize card symbols
        replacements = {
            '®': '♠',  # Spades
            '@': '♠',
            'a': '♠',
            'Y': '♥',  # Hearts
            'O': '♥',
            '©': '♦',  # Diamonds
            'O': '♦',
            '&': '♣',  # Clubs
            'h': '♣'
        }
        
        # Clean card layout text
        for key in ['north_cards', 'south_cards', 'east_cards', 'west_cards']:
            if key in data and data[key]:
                for old, new in replacements.items():
                    data[key] = data[key].replace(old, new)
                
                # Remove extra whitespace and normalize line breaks
                data[key] = re.sub(r'\s+', ' ', data[key]).strip()
        
        # Clean card layout in solution
        if 'card_layout' in data:
            for position in data['card_layout']:
                if data['card_layout'][position]:
                    for old, new in replacements.items():
                        data['card_layout'][position] = data['card_layout'][position].replace(old, new)
                    
                    # Remove extra whitespace and normalize line breaks
                    data['card_layout'][position] = re.sub(r'\s+', ' ', data['card_layout'][position]).strip()
        
        # Clean explanation text
        if 'explanation' in data and data['explanation']:
            for old, new in replacements.items():
                data['explanation'] = data['explanation'].replace(old, new)
        
        return data
    
    def extract_problem(self, problem_num: int, page_num: int) -> Dict[str, Any]:
        """Extract a specific problem from its page."""
        page = self.doc[page_num]
        text = page.get_text()
        
        # Find the start of the problem
        problem_start = text.find(f"PROBLEM {problem_num}")
        if problem_start == -1:
            return {"error": f"Problem {problem_num} not found on page {page_num}"}
        
        # Extract the problem text
        problem_text = text[problem_start:]
        
        # Find the end of the problem (either the next problem or the end of the page)
        next_problem = re.search(r'PROBLEM\s+\d+', problem_text[10:])
        if next_problem:
            problem_text = problem_text[:next_problem.start() + 10]
            
        # Check for "Test Your Play as Declarer" to end the problem
        test_your_play = problem_text.find("Test Your Play as Declarer")
        if test_your_play != -1:
            problem_text = problem_text[:test_your_play]
        
        # Parse the problem components
        game_type_match = re.search(r'(Rubber bridge|Duplicate|Variable conditions)', problem_text)
        game_type = game_type_match.group(1) if game_type_match else "Unknown"
        
        vulnerability_match = re.search(r'(North-South vulnerable|East-West vulnerable|Both sides vulnerable|Neither side vulnerable)', problem_text)
        vulnerability = vulnerability_match.group(1) if vulnerability_match else "Unknown"
        
        # Extract all card layouts (NORTH, SOUTH, EAST, WEST)
        card_layouts = {}
        for position in ["NORTH", "SOUTH", "EAST", "WEST"]:
            pos_match = re.search(f"{position}\\s+(.*?)(?=NORTH|SOUTH|EAST|WEST|West leads|East leads|South leads|North leads|\\n\\n)", problem_text, re.DOTALL)
            if pos_match:
                card_layouts[position.lower()] = pos_match.group(1).strip()
        
        # Extract bidding if present
        bidding_text = ""
        bidding_section = re.search(r'(SOUTH|WEST|NORTH|EAST)\s+(.*?)(?=West leads|East leads|South leads|North leads)', problem_text, re.DOTALL)
        if bidding_section:
            bidding_text = bidding_section.group(0).strip()
        
        # Extract the lead
        lead_match = re.search(r'(West|East|South|North) leads the (.*?)\.', problem_text)
        lead = lead_match.group(0) if lead_match else ""
        
        # Extract the task
        task_match = re.search(r'Plan the play\.', problem_text)
        task = task_match.group(0) if task_match else ""
        
        return {
            "game_type": game_type,
            "vulnerability": vulnerability,
            "north_cards": card_layouts.get("north", ""),
            "south_cards": card_layouts.get("south", ""),
            "east_cards": card_layouts.get("east", ""),
            "west_cards": card_layouts.get("west", ""),
            "bidding": bidding_text,
            "lead": lead,
            "task": task,
            "raw_text": problem_text.strip()
        }
    
    def extract_solution(self, solution_num: int, page_num: int) -> Dict[str, Any]:
        """Extract a specific solution from its page."""
        page = self.doc[page_num]
        text = page.get_text()
        
        # Find the start of the solution
        solution_start = text.find(f"SOLUTION {solution_num}")
        if solution_start == -1:
            return {"error": f"Solution {solution_num} not found on page {page_num}"}
        
        # Extract the solution text
        solution_text = text[solution_start:]
        
        # Find the end of the solution (either the next solution or the end of the page)
        next_solution = re.search(r'SOLUTION\s+\d+', solution_text[10:])
        if next_solution:
            solution_text = solution_text[:next_solution.start() + 10]
        
        # Check for the next problem to end the solution
        next_problem = re.search(r'PROBLEM\s+\d+', solution_text)
        if next_problem:
            solution_text = solution_text[:next_problem.start()]
            
        # Check for "Test Your Play as Declarer" to end the solution
        test_your_play = solution_text.find("Test Your Play as Declarer")
        if test_your_play != -1:
            solution_text = solution_text[:test_your_play]
        
        # Extract the full card layout if present
        card_layout = {}
        for position in ["NORTH", "SOUTH", "EAST", "WEST"]:
            pos_match = re.search(f"{position}\\s+(.*?)(?=NORTH|SOUTH|EAST|WEST|\\n\\n)", solution_text, re.DOTALL)
            if pos_match:
                card_layout[position.lower()] = pos_match.group(1).strip()
        
        # If no explicit card positions found, try to extract the full layout
        if not card_layout:
            # Look for a block of text that likely contains the card layout
            layout_match = re.search(r'SOLUTION\s+\d+\s+(.*?)(?=\n\n)', solution_text, re.DOTALL)
            if layout_match:
                full_layout = layout_match.group(1).strip()
                card_layout["full_layout"] = full_layout
        
        # Extract the explanation text
        explanation = solution_text
        
        # Remove the card layout part from the explanation
        for position in card_layout:
            if position != "full_layout":
                explanation = explanation.replace(card_layout[position], "")
        
        # Remove solution number and other standard text
        explanation = re.sub(r'SOLUTION\s+\d+', '', explanation)
        explanation = re.sub(r'Test Your Play as Declarer', '', explanation)
        
        # Clean up the explanation
        explanation = re.sub(r'NORTH|SOUTH|EAST|WEST', '', explanation)
        explanation = re.sub(r'\s+', ' ', explanation).strip()
        
        # Try to identify the actual explanation part (after the card layout)
        explanation_parts = explanation.split('\n\n')
        if len(explanation_parts) > 1:
            # The explanation is likely after the card layout
            explanation = '\n\n'.join(explanation_parts[1:])
        
        return {
            "card_layout": card_layout,
            "explanation": explanation,
            "raw_text": solution_text.strip()
        }
    
    def parse_card_layout(self, layout_text: str) -> Dict[str, str]:
        """Parse a card layout text into a structured format."""
        result = {
            "spades": "",
            "hearts": "",
            "diamonds": "",
            "clubs": ""
        }
        
        # Look for card suits and their values
        lines = layout_text.strip().split('\n')
        for line in lines:
            line = line.strip()
            if '♠' in line or '@' in line or '®' in line:
                result["spades"] = re.sub(r'[♠@®]\s*', '', line).strip()
            elif '♥' in line or 'Y' in line or 'O' in line:
                result["hearts"] = re.sub(r'[♥YO]\s*', '', line).strip()
            elif '♦' in line or '©' in line or 'O' in line:
                result["diamonds"] = re.sub(r'[♦©O]\s*', '', line).strip()
            elif '♣' in line or '&' in line or 'h' in line:
                result["clubs"] = re.sub(r'[♣&h]\s*', '', line).strip()
        
        return result
    
    def save_to_json(self, output_path: str) -> None:
        """Save the extracted puzzles to a JSON file."""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.puzzles, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(self.puzzles)} puzzles to {output_path}")
    
    def extract_sample(self, num_samples: int = 5) -> List[Dict[str, Any]]:
        """Extract a sample of puzzles for testing."""
        puzzles = self.extract_all_puzzles()
        return puzzles[:min(num_samples, len(puzzles))]

def main():
    parser = argparse.ArgumentParser(description='Extract bridge puzzles from a PDF book.')
    parser.add_argument('pdf_path', help='Path to the PDF file')
    parser.add_argument('--output', '-o', default='bridge_puzzles.json', help='Output JSON file path')
    parser.add_argument('--sample', '-s', type=int, help='Extract only a sample of puzzles for testing')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.pdf_path):
        print(f"Error: PDF file not found at {args.pdf_path}")
        return
    
    extractor = BridgePuzzleExtractor(args.pdf_path)
    
    if args.sample:
        puzzles = extractor.extract_sample(args.sample)
        sample_output = args.output.replace('.json', '_sample.json')
        with open(sample_output, 'w', encoding='utf-8') as f:
            json.dump(puzzles, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(puzzles)} sample puzzles to {sample_output}")
    else:
        extractor.extract_all_puzzles()
        extractor.save_to_json(args.output)

if __name__ == "__main__":
    main() 