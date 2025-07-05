# Bridge Puzzle Extractor

This tool extracts bridge puzzles and their solutions from the book "Test your play as declarer - Jeff Rubens & Paul Lukacs" and saves them as structured JSON data.

## Features

- Extracts all problems and solutions from the PDF
- Parses key components of each problem:
  - Game type (Rubber bridge, Duplicate, etc.)
  - Vulnerability
  - Card layouts (North, South, East, West)
  - Bidding information
  - Opening lead
  - Task description
- Extracts solution details:
  - Complete card layout (all four hands)
  - Explanation text
  - Key techniques used
- Saves all data in a structured JSON format for further processing
- Includes verification tools to check extraction accuracy
- Reuses previously extracted images to save processing time

## Approaches

This repository contains two different approaches for extracting bridge puzzles:

### 1. Text-Based Extraction (extract_bridge_puzzles.py)

This approach uses PyMuPDF to extract text from the PDF and then uses regex patterns to identify and parse the problems and solutions. While faster, it may have limitations with card symbols and layout recognition.

### 2. Image-Based Extraction with Claude API (extract_bridge_puzzles_v2.py)

This approach converts PDF pages to images and uses the Claude 3.7 Sonnet API to analyze the images and extract structured data. This provides more accurate extraction, especially for card symbols and layouts, but requires an API key and processes more slowly due to rate limits.

## Installation

1. Clone this repository
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Text-Based Extraction

```bash
python extract_bridge_puzzles.py "Test your play as declarer - Jeff Rubens & Paul Lukacs.pdf"
```

By default, the output will be saved to `bridge_puzzles.json`. You can specify a different output file:

```bash
python extract_bridge_puzzles.py "Test your play as declarer - Jeff Rubens & Paul Lukacs.pdf" --output my_puzzles.json
```

### Image-Based Extraction with Claude API

```bash
python extract_bridge_puzzles_v2.py "Test your play as declarer - Jeff Rubens & Paul Lukacs.pdf" --api-key YOUR_CLAUDE_API_KEY
```

Additional options:

```bash
python extract_bridge_puzzles_v2.py "Test your play as declarer - Jeff Rubens & Paul Lukacs.pdf" \
  --api-key YOUR_CLAUDE_API_KEY \
  --output my_puzzles_v2.json \
  --output-dir output_folder \
  --batch-size 5 \
  --delay 5 \
  --start 1 \
  --end 10
```

To resume a previously interrupted extraction:

```bash
python extract_bridge_puzzles_v2.py "Test your play as declarer - Jeff Rubens & Paul Lukacs.pdf" \
  --api-key YOUR_CLAUDE_API_KEY \
  --resume
```

### Testing Single Puzzle Extraction

You can test the extraction on a single puzzle using the test script:

```bash
python test_claude_extraction.py "Test your play as declarer - Jeff Rubens & Paul Lukacs.pdf" \
  --problem-page 10 \
  --solution-page 11 \
  --puzzle-num 1
```

### Verifying Extraction Results

After extraction, you can verify the results against the original images:

```bash
# Verify a specific puzzle
python verify_extraction.py output/intermediate_results.json --puzzle-num 1

# Verify all puzzles in batch mode
python verify_extraction.py output/intermediate_results.json --batch
```

The verification tool provides two modes:
1. Interactive mode: Shows the original image and extracted data side by side
2. Batch mode: Uses Claude to verify the extraction accuracy automatically

The verification process uses several methods to match puzzles with their correct images:
- Image paths stored in the JSON output (most reliable)
- Number of visible hands (problems typically have 2 hands, solutions have all 4)
- Text pattern matching for "PROBLEM" and "SOLUTION" labels
- Page number patterns (odd/even)

## JSON Structure

The output JSON file contains an array of puzzle objects, each with the following structure:

```json
{
  "problem_number": 1,
  "problem": {
    "game_type": "Rubber bridge",
    "vulnerability": "East-West vulnerable",
    "north_cards": "♠A86 ♥2652 ♦104 ♣AT6432",
    "south_cards": "♠95 ♥AQ54 ♦AJ3 ♣KQ98",
    "bidding": "...",
    "lead": "West leads the spade king.",
    "task": "Plan the play."
  },
  "solution": {
    "card_layout": {
      "north": "♠A86 ♥2 ♦104 ♣AT6432",
      "south": "♠95 ♥AQ54 ♦AJ3 ♣KQ98",
      "east": "♠742 ♥J973 ♦Q9862 ♣J5",
      "west": "♠KQJ103 ♥K108 ♦75 ♣764"
    },
    "explanation": "...",
    "techniques": ["finesse", "endplay"]
  }
}
```

## Analysis Tools

You can analyze the extracted puzzles using the provided `analyze_puzzles.py` script:

```bash
# Show statistics about the puzzles
python analyze_puzzles.py bridge_puzzles.json --stats

# Search for puzzles containing a specific keyword
python analyze_puzzles.py bridge_puzzles.json --search "finesse"

# Show a specific puzzle by number
python analyze_puzzles.py bridge_puzzles.json --puzzle 10

# Show common bridge techniques and related puzzles
python analyze_puzzles.py bridge_puzzles.json --techniques
```

## Further Processing

The extracted JSON data can be used for:
- Creating a bridge puzzle database
- Developing bridge training applications
- Analyzing common patterns in bridge problems
- Building an interactive bridge learning tool 

## Environment Setup

The extraction scripts use the Claude API, which requires an API key. For convenience, you can set the API key in your environment:

```bash
# Add to your .zshrc or .bashrc
export CLAUDE_API_KEY="your_api_key_here"
```

This way, you won't need to provide the API key every time you run the scripts. 