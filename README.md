# CodeDD - Code Consistency Test

A tool to analyze code quality and consistency using AI models.

## Setup

1. Clone this repository
2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy `.env.template` to `.env` and fill in your API key(s):
   ```bash
   cp .env.template .env
   ```
   You need at least one of these API keys:
   - `ANTHROPIC_API_KEY` - Required for using Anthropic's Claude (Model 1)
   - `OPENAI_API_KEY` - Required for using OpenAI's GPT-4 (Model 2)

## Usage

1. Place your code files in the `code_samples` directory
2. Run the analysis with the desired number of cycles and model:
   ```bash
   python run_test.py <cycles> [--model MODEL]
   ```
   
   Arguments:
   - `cycles`: Number of audit cycles to run (required)
   - `--model` or `-m`: Select AI model to use (optional)
     - `1`: Anthropic Claude (default)
     - `2`: OpenAI GPT-4

   Examples:
   ```bash
   # Run 5 cycles with default model (Anthropic Claude)
   python run_test.py 5

   # Run 3 cycles with OpenAI GPT-4
   python run_test.py 3 --model 2
   # or
   python run_test.py 3 -m 2
   ```

## Output

The script creates a new directory for each run under `output/runthrough_XXXX/` containing:
1. A CSV file with detailed metrics for each file and cycle
2. A text file with deviation analysis showing:
   - Overall consistency statistics
   - Per-metric deviation analysis
   - Detailed per-file analysis (in the text file only)

## Error Handling

- The script will retry failed API calls up to 3 times with exponential backoff
- If a file fails all retry attempts, it will be skipped and the analysis will continue with the next file
- At least one API key must be provided for the selected model

## Metrics Evaluated

The tool evaluates various aspects of code quality including:
- Code Quality (readability, consistency, modularity, etc.)
- Functionality (completeness, error handling, etc.)
- Performance (efficiency, scalability, etc.)
- Security (input validation, data handling, etc.)
- Documentation and Standards

Each metric is scored on a scale and analyzed for consistency across multiple audit cycles.

# AI Code Auditor

A simplified tool for running automated code audits using AI models (Claude and/or GPT-4).

## Setup

1. Create and activate a virtual environment:

```bash
# On Windows
python -m venv venv
.\venv\Scripts\activate

# On macOS/Linux
python -m venv venv
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure API Keys:
```bash
# Copy the template file
# On Windows
copy .env.template .env

# On macOS/Linux
cp .env.template .env

# Edit the .env file and add your API keys
# You need at least one of these keys:
ANTHROPIC_API_KEY=your_anthropic_key_here
OPENAI_API_KEY=your_openai_key_here
```

## Usage

Run the script with the desired number of audit cycles:

```bash
python run_test.py 5  # Runs 5 audit cycles
```

## Output

The script creates a directory structure under `output/` with the following format:
```
output/
└── runthrough_XXXX/
    └── XXXX.csv
```

The CSV file contains the following metrics for each audit cycle:
- Code Quality (readability, consistency, modularity, etc.)
- Functionality (completeness, edge cases, error handling)
- Performance & Scalability
- Security
- Compatibility
- Documentation
- Code Standards

## Notes

- At least one API key (Anthropic or OpenAI) must be configured in the `.env` file
- The script will use Claude (Anthropic) as the primary model if available, with GPT-4 (OpenAI) as a fallback
- Each audit cycle processes the sample code and stores results in a CSV file
- The output directory is created automatically if it doesn't exist

