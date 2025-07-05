#!/usr/bin/env python3
import os
import json
import argparse
import base64
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import anthropic
import re
import fitz  # PyMuPDF
import random
import datetime
from typing import Dict, Any, List, Optional, Tuple

class ExtractionVerifier:
    def __init__(self, results_file: str, images_dir: str, api_key: Optional[str] = None, log_file: Optional[str] = None):
        """Initialize the verifier with the path to the results file and images directory."""
        self.results_file = results_file
        self.images_dir = images_dir
        self.api_key = api_key or os.environ.get('CLAUDE_API_KEY')
        self.log_file = log_file or f"verification_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        # Load the results
        with open(results_file, 'r', encoding='utf-8') as f:
            self.results = json.load(f)
            
        # Initialize the client if API key is provided
        if self.api_key:
            self.client = anthropic.Anthropic(api_key=self.api_key)
        else:
            self.client = None
            
        # Create a mapping of puzzle numbers to page numbers
        self.puzzle_page_map = self._build_puzzle_page_map()
            
    def _build_puzzle_page_map(self) -> Dict[int, Dict[str, int]]:
        """Build a mapping of puzzle numbers to their corresponding page numbers."""
        puzzle_map = {}
        
        # First, scan all image files for problem and solution markers
        problem_pattern = re.compile(r'PROBLEM\s+(\d+)', re.IGNORECASE)
        solution_pattern = re.compile(r'SOLUTION\s+(\d+)', re.IGNORECASE)
        
        # Get all image files
        image_files = [f for f in os.listdir(self.images_dir) if f.startswith('page_') and f.endswith('.png')]
        
        # Extract page numbers from filenames
        page_numbers = []
        for image_file in image_files:
            match = re.search(r'page_(\d+)\.png', image_file)
            if match:
                page_numbers.append(int(match.group(1)))
        
        # Sort page numbers
        page_numbers.sort()
        
        # Check if we have a PDF file to extract text from
        pdf_path = None
        for file in os.listdir(os.path.dirname(self.images_dir)):
            if file.endswith('.pdf'):
                pdf_path = os.path.join(os.path.dirname(self.images_dir), file)
                break
        
        if pdf_path and os.path.exists(pdf_path):
            print(f"Found PDF file: {pdf_path}")
            # Open the PDF
            doc = fitz.open(pdf_path)
            
            # Scan each page for problem and solution markers
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                
                problem_match = problem_pattern.search(text)
                if problem_match:
                    problem_num = int(problem_match.group(1))
                    if problem_num not in puzzle_map:
                        puzzle_map[problem_num] = {}
                    puzzle_map[problem_num]['problem'] = page_num
                    print(f"Found Problem #{problem_num} on page {page_num+1}")
                
                solution_match = solution_pattern.search(text)
                if solution_match:
                    solution_num = int(solution_match.group(1))
                    if solution_num not in puzzle_map:
                        puzzle_map[solution_num] = {}
                    puzzle_map[solution_num]['solution'] = page_num
                    print(f"Found Solution #{solution_num} on page {page_num+1}")
            
            # Close the PDF
            doc.close()
        else:
            print("No PDF file found. Using alternative matching method.")
            # If no PDF is available, try to match based on the results data
            for puzzle in self.results:
                puzzle_num = puzzle["problem_number"]
                puzzle_map[puzzle_num] = {}
                
                # Try to find the problem and solution pages
                # This is a simplistic approach - in a real implementation, you'd need better matching
                for page_num in page_numbers:
                    image_path = os.path.join(self.images_dir, f"page_{page_num}.png")
                    
                    # Use OCR or text recognition to determine if this page contains the problem or solution
                    # For now, we'll use a simple heuristic based on page numbers
                    if page_num % 2 == 1 and 'problem' not in puzzle_map[puzzle_num]:  # Odd pages for problems
                        puzzle_map[puzzle_num]['problem'] = page_num - 1  # Convert to 0-indexed
                    elif page_num % 2 == 0 and 'solution' not in puzzle_map[puzzle_num]:  # Even pages for solutions
                        puzzle_map[puzzle_num]['solution'] = page_num - 1  # Convert to 0-indexed
        
        return puzzle_map
    
    def get_puzzle_image_paths(self, puzzle_num: int) -> Dict[str, str]:
        """Get the image paths for a specific puzzle from the JSON data."""
        # Find the puzzle in the results
        puzzle = next((p for p in self.results if p["problem_number"] == puzzle_num), None)
        if not puzzle:
            raise ValueError(f"Puzzle #{puzzle_num} not found in results")
        
        result = {}
        
        # Check if the image paths are stored in the JSON
        if "problem" in puzzle and "image_path" in puzzle["problem"]:
            problem_image = puzzle["problem"]["image_path"]
            if os.path.exists(problem_image):
                result["problem"] = problem_image
            else:
                print(f"Warning: Problem image not found at {problem_image}")
        
        if "solution" in puzzle and "image_path" in puzzle["solution"]:
            solution_image = puzzle["solution"]["image_path"]
            if os.path.exists(solution_image):
                result["solution"] = solution_image
            else:
                print(f"Warning: Solution image not found at {solution_image}")
        
        # If image paths are not in the JSON, use fallback method
        if not result:
            print("Image paths not found in JSON. Using fallback method.")
            result = self._get_puzzle_image_paths_fallback(puzzle_num, puzzle)
        
        return result
    
    def _get_puzzle_image_paths_fallback(self, puzzle_num: int, puzzle: Dict[str, Any]) -> Dict[str, str]:
        """Fallback method to get image paths when they're not in the JSON."""
        # Get all image files
        image_files = [f for f in os.listdir(self.images_dir) if f.startswith('page_') and f.endswith('.png')]
        image_files.sort(key=lambda x: int(re.search(r'page_(\d+)\.png', x).group(1)))
        
        result = {}
        
        # Check each image to determine if it's a problem or solution
        for image_file in image_files:
            image_path = os.path.join(self.images_dir, image_file)
            image_type = self._determine_image_type(image_path, puzzle_num, puzzle)
            
            if image_type == "problem" and "problem" not in result:
                result["problem"] = image_path
            elif image_type == "solution" and "solution" not in result:
                result["solution"] = image_path
            
            if "problem" in result and "solution" in result:
                break
        
        return result
    
    def _determine_image_type(self, image_path: str, puzzle_num: int, puzzle: Dict[str, Any]) -> Optional[str]:
        """Determine if an image is a problem or solution based on content."""
        # Check if the image exists
        if not os.path.exists(image_path):
            return None
        
        # For a more accurate approach, we could use OCR or Claude to analyze the image
        # But for now, we'll use a simple heuristic based on the number of hands in the puzzle data
        
        # Problem pages typically have 2 hands (North and South)
        # Solution pages typically have all 4 hands
        
        # Count the number of hands in the problem data
        problem_hands = 0
        if "problem" in puzzle and "CardLayout" in puzzle["problem"]:
            for hand in ["North", "South", "East", "West"]:
                if hand in puzzle["problem"]["CardLayout"] and puzzle["problem"]["CardLayout"][hand]:
                    problem_hands += 1
        
        # Count the number of hands in the solution data
        solution_hands = 0
        if "solution" in puzzle and "cardLayout" in puzzle["solution"]:
            for hand in ["north", "south", "east", "west"]:
                if hand in puzzle["solution"]["cardLayout"] and puzzle["solution"]["cardLayout"][hand]:
                    solution_hands += 1
        
        # Extract page number from the image path
        match = re.search(r'page_(\d+)\.png', image_path)
        if not match:
            return None
        
        page_num = int(match.group(1))
        
        # Try to match the image with problem or solution based on the number of hands
        # and the page number (problems typically come before solutions)
        
        # If we have a clear distinction in the number of hands
        if problem_hands <= 2 and solution_hands >= 4:
            # Use OCR or pattern matching to check the page content
            # For now, we'll use a simple heuristic based on page numbers
            if page_num % 2 == 1:  # Odd pages are often problems
                return "problem"
            else:  # Even pages are often solutions
                return "solution"
        
        # If we can't determine based on hands, try to use text patterns
        try:
            # Use PyMuPDF to extract text from the image
            doc = fitz.open(image_path)
            page = doc[0]
            text = page.get_text()
            
            # Look for problem/solution indicators
            if re.search(r'PROBLEM\s+' + str(puzzle_num), text, re.IGNORECASE):
                return "problem"
            elif re.search(r'SOLUTION\s+' + str(puzzle_num), text, re.IGNORECASE):
                return "solution"
        except Exception as e:
            print(f"Error extracting text from image: {str(e)}")
        
        # If all else fails, use page number as a heuristic
        if page_num % 2 == 1:  # Odd pages are often problems
            return "problem"
        else:  # Even pages are often solutions
            return "solution"
    
    def verify_puzzle(self, puzzle_num: int) -> None:
        """Verify a specific puzzle by displaying the image and extracted data side by side."""
        # Find the puzzle in the results
        puzzle = next((p for p in self.results if p["problem_number"] == puzzle_num), None)
        if not puzzle:
            print(f"Puzzle #{puzzle_num} not found in results")
            return
        
        # Get the image paths
        image_paths = self.get_puzzle_image_paths(puzzle_num)
        
        if not image_paths.get('problem') and not image_paths.get('solution'):
            print(f"No images found for puzzle #{puzzle_num}")
            return
        
        # Create a GUI to display the image and extracted data
        root = tk.Tk()
        root.title(f"Puzzle #{puzzle_num} Verification")
        root.geometry("1200x800")
        
        # Create a notebook with tabs for problem and solution
        notebook = ttk.Notebook(root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create frames for problem and solution
        problem_frame = ttk.Frame(notebook)
        solution_frame = ttk.Frame(notebook)
        
        notebook.add(problem_frame, text="Problem")
        notebook.add(solution_frame, text="Solution")
        
        # Load and display the problem image
        if image_paths.get('problem'):
            self._setup_verification_view(problem_frame, image_paths['problem'], puzzle["problem"], "problem")
        else:
            ttk.Label(problem_frame, text="Problem image not found").pack()
        
        # Load and display the solution image
        if image_paths.get('solution'):
            self._setup_verification_view(solution_frame, image_paths['solution'], puzzle["solution"], "solution")
        else:
            ttk.Label(solution_frame, text="Solution image not found").pack()
        
        root.mainloop()
    
    def _setup_verification_view(self, parent, image_path: str, data: Dict[str, Any], data_type: str) -> None:
        """Set up the verification view with image and data side by side."""
        # Create a paned window
        paned_window = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True)
        
        # Create frames for image and data
        image_frame = ttk.Frame(paned_window)
        data_frame = ttk.Frame(paned_window)
        
        paned_window.add(image_frame, weight=1)
        paned_window.add(data_frame, weight=1)
        
        # Load and display the image
        try:
            img = Image.open(image_path)
            img = img.resize((600, 800), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            
            image_label = ttk.Label(image_frame, image=photo)
            image_label.image = photo  # Keep a reference to prevent garbage collection
            image_label.pack(fill=tk.BOTH, expand=True)
            
            # Display the image path
            path_label = ttk.Label(image_frame, text=f"Image: {os.path.basename(image_path)}")
            path_label.pack(pady=5)
        except Exception as e:
            ttk.Label(image_frame, text=f"Error loading image: {str(e)}").pack()
        
        # Display the extracted data
        data_text = tk.Text(data_frame, wrap=tk.WORD)
        data_text.pack(fill=tk.BOTH, expand=True)
        
        # Format the data as pretty JSON
        data_text.insert(tk.END, json.dumps(data, indent=2))
        
        # Add buttons for verification actions
        button_frame = ttk.Frame(data_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="Mark as Correct", 
                  command=lambda: self._mark_verification(data_type, True)).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Mark as Incorrect", 
                  command=lambda: self._mark_verification(data_type, False)).pack(side=tk.LEFT, padx=5)
    
    def _mark_verification(self, data_type: str, is_correct: bool) -> None:
        """Mark the verification status."""
        status = "correct" if is_correct else "incorrect"
        print(f"Marked {data_type} as {status}")
        
    def verify_all_puzzles(self) -> None:
        """Verify all puzzles in batch mode."""
        for puzzle in self.results:
            puzzle_num = puzzle["problem_number"]
            print(f"Verifying puzzle #{puzzle_num}...")
            
            # Here you would implement batch verification logic
            # For example, you could use Claude to verify the extraction
            if self.client:
                self._verify_with_claude(puzzle_num)
            else:
                print("No API key provided for Claude verification")
    
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
            f.write(f"Verification Log - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Randomly selected puzzles: {selected_puzzles}\n\n")
        
        # Verify each selected puzzle
        for puzzle_num in selected_puzzles:
            result = self._verify_puzzle_for_logging(puzzle_num)
            
            # Log the result
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(f"Puzzle #{puzzle_num} Verification:\n")
                f.write(json.dumps(result, indent=2))
                f.write("\n\n")
            
            print(f"Verified puzzle #{puzzle_num} - Results logged to {self.log_file}")
    
    def _verify_puzzle_for_logging(self, puzzle_num: int) -> Dict[str, Any]:
        """Verify a puzzle and return the verification results for logging."""
        # Find the puzzle in the results
        puzzle = next((p for p in self.results if p["problem_number"] == puzzle_num), None)
        if not puzzle:
            return {"error": f"Puzzle #{puzzle_num} not found in results"}
        
        # Get the image paths
        try:
            image_paths = self.get_puzzle_image_paths(puzzle_num)
        except Exception as e:
            return {"error": f"Error getting image paths: {str(e)}"}
        
        result = {
            "puzzle_number": puzzle_num,
            "verification_time": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "problem": {},
            "solution": {}
        }
        
        # Verify problem
        if image_paths.get('problem'):
            result["problem"] = {
                "image_path": image_paths['problem'],
                "verification": self._verify_problem_data(image_paths['problem'], puzzle["problem"])
            }
        else:
            result["problem"] = {"error": "Problem image not found"}
        
        # Verify solution
        if image_paths.get('solution'):
            result["solution"] = {
                "image_path": image_paths['solution'],
                "verification": self._verify_solution_data(image_paths['solution'], puzzle["solution"])
            }
        else:
            result["solution"] = {"error": "Solution image not found"}
        
        return result
    
    def _verify_problem_data(self, image_path: str, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Verify problem data against the image."""
        # For now, we'll just return a simple verification result
        # In a real implementation, you would use OCR or Claude to verify the extraction
        
        return {
            "status": "verification_needed",
            "message": "Manual verification required",
            "extracted_data": extracted_data
        }
    
    def _verify_solution_data(self, image_path: str, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Verify solution data against the image."""
        # For now, we'll just return a simple verification result
        # In a real implementation, you would use OCR or Claude to verify the extraction
        
        return {
            "status": "verification_needed",
            "message": "Manual verification required",
            "extracted_data": extracted_data
        }
    
    def _verify_with_claude(self, puzzle_num: int) -> None:
        """Use Claude to verify the extraction."""
        if not self.client:
            print("Claude client not initialized")
            return
            
        # Find the puzzle in the results
        puzzle = next((p for p in self.results if p["problem_number"] == puzzle_num), None)
        if not puzzle:
            print(f"Puzzle #{puzzle_num} not found in results")
            return
            
        # Get the image paths
        image_paths = self.get_puzzle_image_paths(puzzle_num)
        
        if not image_paths.get('problem') and not image_paths.get('solution'):
            print(f"Could not find images for puzzle #{puzzle_num}")
            return
            
        # Verify the problem
        if image_paths.get('problem'):
            self._verify_problem_with_claude(puzzle_num, image_paths['problem'], puzzle["problem"])
        
        # Verify the solution
        if image_paths.get('solution'):
            self._verify_solution_with_claude(puzzle_num, image_paths['solution'], puzzle["solution"])
    
    def _verify_problem_with_claude(self, problem_num: int, image_path: str, extracted_data: Dict[str, Any]) -> None:
        """Verify a problem extraction with Claude."""
        print(f"Verifying problem #{problem_num} with Claude...")
        
        # Encode the image
        base64_image = self._encode_image(image_path)
        
        # Create the prompt for Claude
        prompt = f"""
        This image shows a bridge problem from a book. I have extracted the following data from it:
        
        ```json
        {json.dumps(extracted_data, indent=2)}
        ```
        
        Please verify if this extraction is correct. Focus on the following aspects:
        1. Is the problem number correct?
        2. Is the game type correct?
        3. Is the vulnerability correct?
        4. Are the card layouts for each hand correct?
        5. Is the bidding sequence correct?
        6. Is the opening lead correct?
        7. Is the task description correct?
        
        If there are any errors, please specify what they are and provide the correct information.
        """
        
        try:
            # Call Claude API
            response = self.client.messages.create(
                model="claude-3-7-sonnet-latest",
                max_tokens=4000,
                temperature=0,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": base64_image}}
                        ]
                    }
                ]
            )
            
            # Print the verification result
            print(f"Verification result for problem #{problem_num}:")
            print(response.content[0].text)
            print()
            
            # Log the result
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(f"Problem #{problem_num} Claude Verification:\n")
                f.write(response.content[0].text)
                f.write("\n\n")
            
        except Exception as e:
            print(f"Error verifying problem #{problem_num}: {str(e)}")
    
    def _verify_solution_with_claude(self, solution_num: int, image_path: str, extracted_data: Dict[str, Any]) -> None:
        """Verify a solution extraction with Claude."""
        print(f"Verifying solution #{solution_num} with Claude...")
        
        # Encode the image
        base64_image = self._encode_image(image_path)
        
        # Create the prompt for Claude
        prompt = f"""
        This image shows a bridge solution from a book. I have extracted the following data from it:
        
        ```json
        {json.dumps(extracted_data, indent=2)}
        ```
        
        Please verify if this extraction is correct. Focus on the following aspects:
        1. Is the solution number correct?
        2. Are the card layouts for all four hands correct?
        3. Is the solution explanation correctly extracted?
        4. Are the key techniques correctly identified?
        
        If there are any errors, please specify what they are and provide the correct information.
        """
        
        try:
            # Call Claude API
            response = self.client.messages.create(
                model="claude-3-7-sonnet-latest",
                max_tokens=4000,
                temperature=0,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": base64_image}}
                        ]
                    }
                ]
            )
            
            # Print the verification result
            print(f"Verification result for solution #{solution_num}:")
            print(response.content[0].text)
            print()
            
            # Log the result
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(f"Solution #{solution_num} Claude Verification:\n")
                f.write(response.content[0].text)
                f.write("\n\n")
            
        except Exception as e:
            print(f"Error verifying solution #{solution_num}: {str(e)}")
    
    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64 for API submission."""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

def main():
    parser = argparse.ArgumentParser(description='Verify bridge puzzle extraction results against original images.')
    parser.add_argument('results_file', help='Path to the JSON results file')
    parser.add_argument('--images-dir', '-d', default='output/images', help='Directory containing the page images')
    parser.add_argument('--puzzle-num', '-p', type=int, help='Specific puzzle number to verify')
    parser.add_argument('--api-key', '-k', help='Claude API key (optional, will use CLAUDE_API_KEY env var if not provided)')
    parser.add_argument('--batch', '-b', action='store_true', help='Verify all puzzles in batch mode')
    parser.add_argument('--random', '-r', type=int, default=10, help='Verify a random selection of puzzles (default: 10)')
    parser.add_argument('--log-file', '-l', help='Path to log file for verification results')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.results_file):
        print(f"Error: Results file not found at {args.results_file}")
        return
    
    if not os.path.exists(args.images_dir):
        print(f"Error: Images directory not found at {args.images_dir}")
        return
    
    verifier = ExtractionVerifier(args.results_file, args.images_dir, args.api_key, args.log_file)
    
    if args.random:
        verifier.verify_random_puzzles(args.random)
    elif args.batch:
        verifier.verify_all_puzzles()
    elif args.puzzle_num:
        verifier.verify_puzzle(args.puzzle_num)
    else:
        print("Please specify either a puzzle number to verify, use --batch to verify all puzzles, or use --random to verify a random selection")

if __name__ == "__main__":
    main() 