#!/usr/bin/env python3
import os
import re
import json
import time
import base64
import argparse
import requests
from typing import Dict, List, Any, Optional
from PIL import Image
import fitz  # PyMuPDF
import anthropic

class BridgePuzzleExtractor:
    def __init__(self, pdf_path: str, output_dir: str, api_key: str, batch_size: int = 5, delay: int = 5, model: str = "claude-3-7-sonnet-latest"):
        """Initialize the extractor with the path to the PDF file."""
        self.pdf_path = pdf_path
        self.output_dir = output_dir
        self.images_dir = os.path.join(output_dir, "images")
        self.api_key = api_key
        self.batch_size = batch_size
        self.delay = delay  # Delay between API calls in seconds
        self.model = model
        self.doc = fitz.open(pdf_path)
        self.total_pages = len(self.doc)
        self.puzzles = []
        
        # Create output directories if they don't exist
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.images_dir, exist_ok=True)
        
        # Initialize Claude client
        self.client = anthropic.Anthropic(api_key=self.api_key)
        
    def convert_pdf_to_images(self) -> Dict[int, str]:
        """Convert PDF pages to images and save them to the images directory."""
        print(f"Checking for existing images...")
        page_images = {}
        missing_pages = []
        
        # First check which pages already have images
        for page_num in range(self.total_pages):
            image_path = os.path.join(self.images_dir, f"page_{page_num+1}.png")
            if os.path.exists(image_path):
                page_images[page_num] = image_path
                if (page_num + 1) % 10 == 0:
                    print(f"Found existing image for page {page_num + 1}")
            else:
                missing_pages.append(page_num)
        
        # Only convert pages that don't have images yet
        if missing_pages:
            print(f"Converting {len(missing_pages)} missing pages to images...")
            for page_num in missing_pages:
                page = self.doc[page_num]
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better quality
                image_path = os.path.join(self.images_dir, f"page_{page_num+1}.png")
                pix.save(image_path)
                page_images[page_num] = image_path
                
                if (page_num + 1) % 10 == 0:
                    print(f"Converted page {page_num + 1}")
            
            print(f"Converted {len(missing_pages)} missing pages to images.")
        else:
            print(f"All {self.total_pages} pages already have images. Reusing existing images.")
        
        return page_images
    
    def identify_puzzle_pages(self) -> Dict[str, Dict[int, int]]:
        """Identify pages containing problems and solutions."""
        problem_pattern = re.compile(r'PROBLEM\s+(\d+)', re.IGNORECASE)
        solution_pattern = re.compile(r'SOLUTION\s+(\d+)', re.IGNORECASE)
        
        problem_pages = {}
        solution_pages = {}
        
        print("Identifying problem and solution pages...")
        
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
        
        print(f"Found {len(problem_pages)} problems and {len(solution_pages)} solutions.")
        return {"problems": problem_pages, "solutions": solution_pages}
    
    def encode_image(self, image_path: str) -> str:
        """Encode image to base64 for API submission."""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def process_problem_page(self, problem_num: int, page_num: int, image_path: str) -> Dict[str, Any]:
        """Process a problem page using Claude API."""
        print(f"Processing problem #{problem_num} on page {page_num+1} with model {self.model}...")
        
        # Encode the image
        base64_image = self.encode_image(image_path)
        
        # Create the prompt for Claude
        prompt = f"""
        This image shows a bridge problem from a book. Please analyze the image and extract the following information in a structured way:

        1. Problem Number: {problem_num}
        2. Game Type: (e.g., Rubber bridge, Duplicate, etc.)
        3. Vulnerability: (e.g., North-South vulnerable, East-West vulnerable, etc.)
        4. Card Layout: Extract all hands that are visible in the problem (typically North and South)
           - North's cards (with proper suit symbols: ♠, ♥, ♦, ♣)
           - South's cards (with proper suit symbols: ♠, ♥, ♦, ♣)
           - East's cards if shown (with proper suit symbols: ♠, ♥, ♦, ♣)
           - West's cards if shown (with proper suit symbols: ♠, ♥, ♦, ♣)
        5. Bidding sequence (if shown)
        6. Opening Lead: Extract ONLY the card that is led (e.g., "♠K" for spade king) with no additional text
        7. Task description (e.g., "Plan the play")

        Format your response as a JSON object with these fields. Be precise in your extraction, especially with the card layouts. Use proper suit symbols (♠, ♥, ♦, ♣) and card values.
        """
        
        try:
            # Call Claude API
            response = self.client.messages.create(
                model=self.model,
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
            
            # Extract JSON from response
            response_text = response.content[0].text
            # Find JSON in the response
            json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find any JSON-like structure
                json_str = response_text
            
            try:
                result = json.loads(json_str)
                # Add image path and page number to the result
                result["image_path"] = image_path
                result["page_number"] = page_num + 1  # Convert to 1-indexed
            except json.JSONDecodeError:
                # If JSON parsing fails, return the raw text
                result = {"error": "Failed to parse JSON", "raw_text": response_text, "image_path": image_path, "page_number": page_num + 1}
            
            return result
            
        except Exception as e:
            print(f"Error processing problem #{problem_num}: {str(e)}")
            return {"error": str(e), "image_path": image_path, "page_number": page_num + 1}
    
    def process_solution_page(self, solution_num: int, page_num: int, image_path: str) -> Dict[str, Any]:
        """Process a solution page using Claude API."""
        print(f"Processing solution #{solution_num} on page {page_num+1} with model {self.model}...")
        
        # Encode the image
        base64_image = self.encode_image(image_path)
        
        # Create the prompt for Claude
        prompt = f"""
        This image shows a bridge solution from a book. Please analyze the image and extract the following information in a structured way:

        1. Solution Number: {solution_num}
        2. Complete Card Layout (all four hands should be visible in the solution):
           - North's cards (with proper suit symbols: ♠, ♥, ♦, ♣)
           - South's cards (with proper suit symbols: ♠, ♥, ♦, ♣)
           - East's cards (with proper suit symbols: ♠, ♥, ♦, ♣)
           - West's cards (with proper suit symbols: ♠, ♥, ♦, ♣)
        
        For each hand, organize the cards by suit (spades, hearts, diamonds, clubs) with proper suit symbols.
        
        3. Solution explanation: Extract the full text explaining the solution
        4. Key techniques mentioned (e.g., finesse, endplay, squeeze, etc.)

        Format your response as a JSON object with these fields. Be precise in your extraction, especially with the card layouts. Use proper suit symbols (♠, ♥, ♦, ♣) and card values.
        """
        
        try:
            # Call Claude API
            response = self.client.messages.create(
                model=self.model,
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
            
            # Extract JSON from response
            response_text = response.content[0].text
            # Find JSON in the response
            json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find any JSON-like structure
                json_str = response_text
            
            try:
                result = json.loads(json_str)
                # Add image path and page number to the result
                result["image_path"] = image_path
                result["page_number"] = page_num + 1  # Convert to 1-indexed
            except json.JSONDecodeError:
                # If JSON parsing fails, return the raw text
                result = {"error": "Failed to parse JSON", "raw_text": response_text, "image_path": image_path, "page_number": page_num + 1}
            
            return result
            
        except Exception as e:
            print(f"Error processing solution #{solution_num}: {str(e)}")
            return {"error": str(e), "image_path": image_path, "page_number": page_num + 1}
    
    def extract_puzzles(self, start_puzzle: Optional[int] = None, end_puzzle: Optional[int] = None) -> List[Dict[str, Any]]:
        """Extract all puzzles and solutions from the PDF using Claude API."""
        # Convert PDF to images
        page_images = self.convert_pdf_to_images()
        
        # Identify problem and solution pages
        pages = self.identify_puzzle_pages()
        problem_pages = pages["problems"]
        solution_pages = pages["solutions"]
        
        # Filter puzzles if range is specified
        puzzle_numbers = sorted(problem_pages.keys())
        if start_puzzle is not None:
            puzzle_numbers = [n for n in puzzle_numbers if n >= start_puzzle]
        if end_puzzle is not None:
            puzzle_numbers = [n for n in puzzle_numbers if n <= end_puzzle]
        
        puzzles = []
        
        # Process puzzles in batches
        for i, problem_num in enumerate(puzzle_numbers):
            if problem_num in problem_pages and problem_num in solution_pages:
                problem_page = problem_pages[problem_num]
                solution_page = solution_pages[problem_num]
                
                problem_image = page_images[problem_page]
                solution_image = page_images[solution_page]
                
                # Process problem and solution
                problem_data = self.process_problem_page(problem_num, problem_page, problem_image)
                
                # Add delay between API calls to avoid rate limits
                time.sleep(self.delay)
                
                solution_data = self.process_solution_page(problem_num, solution_page, solution_image)
                
                puzzle = {
                    "problem_number": problem_num,
                    "problem": problem_data,
                    "solution": solution_data
                }
                
                puzzles.append(puzzle)
                
                # Save intermediate results after each batch
                if (i + 1) % self.batch_size == 0:
                    self.save_intermediate_results(puzzles)
                    print(f"Saved intermediate results for {len(puzzles)} puzzles.")
                
                # Add delay between batches
                time.sleep(self.delay)
        
        self.puzzles = puzzles
        return puzzles
    
    def save_intermediate_results(self, puzzles: List[Dict[str, Any]]) -> None:
        """Save intermediate results to avoid losing progress."""
        intermediate_path = os.path.join(self.output_dir, "intermediate_results.json")
        with open(intermediate_path, 'w', encoding='utf-8') as f:
            json.dump(puzzles, f, indent=2, ensure_ascii=False)
    
    def save_to_json(self, output_path: str) -> None:
        """Save the extracted puzzles to a JSON file."""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.puzzles, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(self.puzzles)} puzzles to {output_path}")
    
    def resume_from_intermediate(self) -> List[Dict[str, Any]]:
        """Resume extraction from intermediate results."""
        intermediate_path = os.path.join(self.output_dir, "intermediate_results.json")
        if os.path.exists(intermediate_path):
            with open(intermediate_path, 'r', encoding='utf-8') as f:
                self.puzzles = json.load(f)
            print(f"Resumed from intermediate results with {len(self.puzzles)} puzzles.")
            return self.puzzles
        else:
            print("No intermediate results found. Starting from scratch.")
            return []

def main():
    parser = argparse.ArgumentParser(description='Extract bridge puzzles from a PDF book using Claude API.')
    parser.add_argument('pdf_path', help='Path to the PDF file')
    parser.add_argument('--output', '-o', default='bridge_puzzles_v2.json', help='Output JSON file path')
    parser.add_argument('--output-dir', '-d', default='output', help='Output directory for images and intermediate results')
    parser.add_argument('--api-key', '-k', help='Claude API key (if not provided, will use CLAUDE_API_KEY environment variable)')
    parser.add_argument('--batch-size', '-b', type=int, default=5, help='Number of puzzles to process before saving intermediate results')
    parser.add_argument('--delay', type=int, default=5, help='Delay between API calls in seconds')
    parser.add_argument('--start', type=int, help='Starting puzzle number')
    parser.add_argument('--end', type=int, help='Ending puzzle number')
    parser.add_argument('--resume', action='store_true', help='Resume from intermediate results')
    parser.add_argument('--model', '-m', default='claude-3-7-sonnet-latest', help='Claude model to use')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.pdf_path):
        print(f"Error: PDF file not found at {args.pdf_path}")
        return
    
    # Get API key from command line or environment variable
    api_key = args.api_key or os.environ.get('CLAUDE_API_KEY')
    if not api_key:
        print("Error: Claude API key is required. Please provide it using --api-key or set the CLAUDE_API_KEY environment variable.")
        return
    
    extractor = BridgePuzzleExtractor(
        args.pdf_path, 
        args.output_dir, 
        api_key,
        args.batch_size,
        args.delay,
        args.model
    )
    
    if args.resume:
        puzzles = extractor.resume_from_intermediate()
        # Get the highest puzzle number already processed
        if puzzles:
            max_puzzle = max(puzzle["problem_number"] for puzzle in puzzles)
            args.start = max_puzzle + 1
            print(f"Resuming from puzzle #{args.start}")
    
    puzzles = extractor.extract_puzzles(args.start, args.end)
    extractor.save_to_json(args.output)

if __name__ == "__main__":
    main() 