#!/usr/bin/env python3
import os
import json
import base64
import argparse
import fitz  # PyMuPDF
import anthropic
from typing import Dict, Any

def encode_image(image_path: str) -> str:
    """Encode image to base64 for API submission."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def extract_page_as_image(pdf_path: str, page_num: int, output_dir: str) -> str:
    """Extract a specific page from PDF as image."""
    os.makedirs(output_dir, exist_ok=True)
    image_path = os.path.join(output_dir, f"page_{page_num+1}.png")
    
    # Check if the image already exists
    if os.path.exists(image_path):
        print(f"Image for page {page_num+1} already exists. Reusing existing image.")
        return image_path
    
    # Extract the image if it doesn't exist
    doc = fitz.open(pdf_path)
    page = doc[page_num]
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better quality
    pix.save(image_path)
    print(f"Extracted page {page_num+1} as image: {image_path}")
    
    return image_path

def process_problem_with_claude(api_key: str, image_path: str, problem_num: int, model: str) -> Dict[str, Any]:
    """Process a problem image with Claude API."""
    client = anthropic.Anthropic(api_key=api_key)
    base64_image = encode_image(image_path)
    
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
    
    response = client.messages.create(
        model=model,
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
    
    return response

def process_solution_with_claude(api_key: str, image_path: str, solution_num: int, model: str) -> Dict[str, Any]:
    """Process a solution image with Claude API."""
    client = anthropic.Anthropic(api_key=api_key)
    base64_image = encode_image(image_path)
    
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
    
    response = client.messages.create(
        model=model,
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
    
    return response

def main():
    parser = argparse.ArgumentParser(description='Test Claude API extraction with a single puzzle.')
    parser.add_argument('pdf_path', help='Path to the PDF file')
    parser.add_argument('--problem-page', type=int, required=True, help='Page number (0-indexed) of the problem')
    parser.add_argument('--solution-page', type=int, required=True, help='Page number (0-indexed) of the solution')
    parser.add_argument('--puzzle-num', type=int, required=True, help='Puzzle number')
    parser.add_argument('--api-key', '-k', required=True, help='Claude API key')
    parser.add_argument('--output-dir', '-d', default='test_output', help='Output directory for images and results')
    parser.add_argument('--model', '-m', default='claude-3-7-sonnet-latest', help='Claude model to use')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.pdf_path):
        print(f"Error: PDF file not found at {args.pdf_path}")
        return
    
    # Extract pages as images
    problem_image = extract_page_as_image(args.pdf_path, args.problem_page, args.output_dir)
    solution_image = extract_page_as_image(args.pdf_path, args.solution_page, args.output_dir)
    
    print(f"Extracted problem image: {problem_image}")
    print(f"Extracted solution image: {solution_image}")
    
    # Process problem with Claude
    print(f"Processing problem #{args.puzzle_num} with Claude API (model: {args.model})...")
    problem_response = process_problem_with_claude(args.api_key, problem_image, args.puzzle_num, args.model)
    
    # Process solution with Claude
    print(f"Processing solution #{args.puzzle_num} with Claude API (model: {args.model})...")
    solution_response = process_solution_with_claude(args.api_key, solution_image, args.puzzle_num, args.model)
    
    # Save responses
    problem_output = os.path.join(args.output_dir, f"problem_{args.puzzle_num}_response.json")
    problem_data = problem_response.model_dump()
    problem_data["image_path"] = problem_image  # Add the image path to the JSON
    with open(problem_output, 'w', encoding='utf-8') as f:
        json.dump(problem_data, f, indent=2)
    
    solution_output = os.path.join(args.output_dir, f"solution_{args.puzzle_num}_response.json")
    solution_data = solution_response.model_dump()
    solution_data["image_path"] = solution_image  # Add the image path to the JSON
    with open(solution_output, 'w', encoding='utf-8') as f:
        json.dump(solution_data, f, indent=2)
    
    # Print results
    print(f"\nProblem Response:")
    print(problem_response.content[0].text)
    
    print(f"\nSolution Response:")
    print(solution_response.content[0].text)
    
    print(f"\nSaved responses to {problem_output} and {solution_output}")

if __name__ == "__main__":
    main() 