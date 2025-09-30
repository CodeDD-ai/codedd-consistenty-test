#!/usr/bin/env python3
import argparse
import os
from pathlib import Path
import csv
import asyncio
from dotenv import load_dotenv
from run_test.ai_auditor import AIAuditor
from run_test.ai_auditor_num import AIAuditorNum
from run_test.audit_scoring import get_score_for_value, calculate_deviations, format_deviation_summary
import sys

def ensure_output_dir():
    """Create output directory if it doesn't exist"""
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    return output_dir

def get_next_run_number():
    """Get the next available run number for the output directory"""
    output_dir = Path("output")
    existing_runs = [d for d in output_dir.glob("runthrough_*") if d.is_dir()]
    if not existing_runs:
        return 1
    return max(int(d.name.split("_")[1]) for d in existing_runs) + 1

def create_run_directory(run_number):
    """Create a new directory for this run"""
    run_dir = Path("output") / f"runthrough_{run_number:04d}"
    run_dir.mkdir(exist_ok=True)
    return run_dir

def read_code_file(file_path):
    """Read the contents of a code file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def get_code_files():
    """Get all code files from the code_samples directory"""
    samples_dir = Path("code_samples")
    if not samples_dir.exists():
        raise FileNotFoundError("code_samples directory not found")
    return list(samples_dir.glob("*.py"))  # Add more patterns if needed, e.g., "*.js", "*.java"

def count_code_lines(code_content: str) -> tuple[int, int]:
    """
    Count the number of lines of code and documentation in the given content.
    
    Args:
        code_content: The code content to analyze
        
    Returns:
        tuple[int, int]: (lines_of_code, lines_of_doc)
    """
    lines = code_content.split('\n')
    doc_lines = 0
    code_lines = 0
    
    for line in lines:
        line = line.strip()
        if not line:  # Skip empty lines
            continue
            
        # Count documentation lines (comments and docstrings)
        if line.startswith('#') or line.startswith('"""') or line.startswith("'"):
            doc_lines += 1
        else:
            code_lines += 1
            
    return code_lines, doc_lines

async def process_file(auditor: AIAuditor, file_path: Path, cycle: int, fieldnames: list) -> tuple[bool, dict]:
    """Process a single file and return its audit results"""
    try:
        code_content = read_code_file(file_path)
        audit_results = await auditor.audit_content(code_content)
        model_used = audit_results.get('model_used', 'unknown')
        print(f"  📝 Analyzing {file_path.name} using {model_used.title()}...")
        
        # Count lines of code and documentation
        code_lines, doc_lines = count_code_lines(code_content)
        
        # Convert text values to numerical scores
        row = {
            'filename': file_path.name,
            'cycle': cycle,
            'domain': audit_results.get('domain', 'N/A'),
            'model_used': model_used,
            'lines_of_code': code_lines,
            'lines_of_doc': doc_lines
        }

        # Map all other fields to numerical scores
        for field in fieldnames:
            if field not in ['filename', 'cycle', 'domain', 'model_used', 'lines_of_code', 'lines_of_doc']:
                value = audit_results.get(field)
                if value is not None:
                    row[field] = get_score_for_value(field, value)
                else:
                    row[field] = 0
        
        print(f"    ✅ Analysis complete for {file_path.name}")
        return True, row
        
    except Exception as e:
        print(f"    ❌ Error analyzing {file_path.name}: {str(e)}")
        return False, {}

async def process_cycle(auditor: AIAuditor, code_files: list, cycle: int, fieldnames: list) -> list:
    """Process all files in a cycle concurrently"""
    print(f"\n📊 Cycle {cycle}")
    
    tasks = [process_file(auditor, file_path, cycle, fieldnames) for file_path in code_files]
    results = await asyncio.gather(*tasks)
    
    cycle_results = []
    for success, row in results:
        if success:
            cycle_results.append(row)
    
    return cycle_results

async def main_async():
    try:
        print("\n🔍 CodeDD - Consistency Test\n")
        
        # Load environment variables from .env file
        print("Loading configuration...")
        load_dotenv()
        
        # Get API keys from environment
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        openai_key = os.getenv('OPENAI_API_KEY')

        # Validate at least one API key is present
        if not anthropic_key and not openai_key:
            raise ValueError("At least one API key (ANTHROPIC_API_KEY or OPENAI_API_KEY) must be set in .env file")

        parser = argparse.ArgumentParser(description='Run code auditing cycles using AI')
        parser.add_argument('cycles', type=int, help='Number of audit cycles to run')
        parser.add_argument('--model', '-m', type=int, choices=[1, 2], default=1,
                           help='Select AI model to use (1=Anthropic Claude, 2=OpenAI GPT-4)')
        parser.add_argument('--alt', action='store_true',
                           help='Use alternate numerical scoring method')
        args = parser.parse_args()

        # Initialize AI Auditor with selected model
        model_name = "Anthropic Claude" if args.model == 1 else "OpenAI GPT-4"
        print(f"Initializing AI model ({model_name})...")
        
        # Choose the appropriate auditor based on --alt flag
        if args.alt:
            print("Using alternate numerical scoring method...")
            auditor = AIAuditorNum(
                model_number=args.model,
                anthropic_key=anthropic_key,
                openai_key=openai_key
            )
        else:
            print("Using standard scoring method...")
            auditor = AIAuditor(
                model_number=args.model,
                anthropic_key=anthropic_key,
                openai_key=openai_key
            )

        # Get all code files
        code_files = get_code_files()
        if not code_files:
            raise FileNotFoundError("No code files found in code_samples directory")
        print(f"Found {len(code_files)} files to analyze")

        # Ensure output directory exists
        ensure_output_dir()
        run_number = get_next_run_number()
        run_dir = create_run_directory(run_number)
        print(f"Created output directory: output/runthrough_{run_number:04d}")

        # Prepare CSV file
        csv_file = run_dir / f"{run_number:04d}.csv"
        fieldnames = [
            'filename', 'cycle', 'domain', 'model_used',
            'lines_of_code', 'lines_of_doc',
            'readability', 'consistency', 'modularity', 'maintainability', 'reusability',
            'redundancy', 'technical_debt', 'code_smells',
            'completeness', 'edge_cases', 'error_handling',
            'efficiency', 'scalability', 'resource_utilization', 'load_handling',
            'parallel_processing', 'database_interaction_efficiency', 'concurrency_management',
            'state_management_efficiency', 'modularity_decoupling', 'configuration_customization_ease',
            'input_validation', 'data_handling', 'authentication',
            'independence', 'integration',
            'inline_comments',
            'standards', 'design_patterns', 'code_complexity', 'refactoring_opportunities'
        ]

        all_results = []  # Store all results for deviation analysis

        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            total_cycles = args.cycles
            print(f"\nStarting audit process ({total_cycles} cycles)...")
            print("=" * 50)

            successful_audits = 0
            total_audits = len(code_files) * total_cycles

            # Process each cycle sequentially, but files within cycles in parallel
            for cycle in range(1, total_cycles + 1):
                cycle_results = await process_cycle(auditor, code_files, cycle, fieldnames)
                
                # Write results to CSV and store for analysis
                for row in cycle_results:
                    writer.writerow(row)
                    all_results.append(row)
                    successful_audits += 1

            print("\n" + "=" * 50)
            print(f"Audit completed: {successful_audits}/{total_audits} analyses successful")
            print(f"Results saved to: {csv_file}")

            # Perform consistency analysis
            if successful_audits > 0:
                deviations = calculate_deviations(all_results)
                detailed_summary, console_summary = format_deviation_summary(deviations)
                
                # Save detailed deviation analysis with UTF-8 encoding
                deviation_file = run_dir / f"{run_number:04d}_deviations.txt"
                with open(deviation_file, 'w', encoding='utf-8') as f:
                    f.write(detailed_summary)
                
                # Print concise summary to console
                print("\nConsistency Analysis:")
                print("=" * 50)
                print(console_summary)
                print(f"\nDetailed deviation analysis saved to: {deviation_file}")

    except KeyboardInterrupt:
        print("\n\n⚠️ Process interrupted by user (CTRL+C)")
        print("Saving partial results...")
        
        # Save any results we have so far
        if 'all_results' in locals() and all_results:
            if 'csv_file' in locals() and 'writer' in locals():
                print(f"Partial results saved to: {csv_file}")
                
                if 'successful_audits' in locals() and successful_audits > 0:
                    deviations = calculate_deviations(all_results)
                    detailed_summary, console_summary = format_deviation_summary(deviations)
                    
                    if 'deviation_file' in locals():
                        with open(deviation_file, 'w', encoding='utf-8') as f:
                            f.write(detailed_summary)
                        print(f"Partial deviation analysis saved to: {deviation_file}")
        
        print("Exiting gracefully...")
        return
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        raise

def main():
    """Entry point that runs the async main function"""
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"\nFatal error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
