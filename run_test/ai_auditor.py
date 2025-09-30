from anthropic import AsyncAnthropic
from openai import OpenAI
from typing import Optional, Dict, Any, Tuple
import re
import asyncio
from asyncio import Semaphore
import json
from .score_mappings import get_score

class AIAuditor:
    """AI Auditor class that handles code analysis using specified AI models."""
    
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # seconds
    MAX_CONCURRENT = 5  # Maximum number of concurrent API calls
    
    def __init__(self, model_number: int = 1, anthropic_key: str = None, openai_key: str = None):
        """
        Initialize the AI Auditor with the selected model.
        
        Args:
            model_number: Integer (1 for Anthropic, 2 for OpenAI)
            anthropic_key: Anthropic API key (required if model_number is 1)
            openai_key: OpenAI API key (required if model_number is 2)
        """
        self.model_number = model_number
        self.anthropic_key = anthropic_key
        self.openai_key = openai_key
        self.semaphore = Semaphore(self.MAX_CONCURRENT)
        
        # Validate model selection and API keys
        if model_number == 1 and not anthropic_key:
            raise ValueError("Anthropic API key is required when using model 1")
        elif model_number == 2 and not openai_key:
            raise ValueError("OpenAI API key is required when using model 2")
        elif model_number not in [1, 2]:
            raise ValueError("Invalid model number. Choose 1 for Anthropic or 2 for OpenAI")

    async def _try_anthropic(self, combined_prompt: str) -> tuple[bool, Optional[str]]:
        """Attempt to get a response from Anthropic's Claude."""
        try:
            async with self.semaphore:  # Limit concurrent API calls
                client = AsyncAnthropic(api_key=self.anthropic_key)
                response = await client.messages.create(
                    model="claude-3-7-sonnet-latest",
                    max_tokens=4096,
                    messages=[{"role": "user", "content": combined_prompt}]
                )
                return True, response.content[0].text
        except Exception as e:
            return False, str(e)

    def _try_openai_sync(self, combined_prompt: str) -> tuple[bool, Optional[str]]:
        """Synchronous attempt to get a response from OpenAI's GPT-4."""
        try:
            client = OpenAI(api_key=self.openai_key)
            response = client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[{"role": "user", "content": combined_prompt}],
                max_tokens=4096
            )
            return True, response.choices[0].message.content
        except Exception as e:
            return False, str(e)

    async def audit_content(self, code_content: str) -> dict:
        """
        Audit code content using the selected AI model with retry logic.
        
        Args:
            code_content: The code content to analyze
            
        Returns:
            dict: Audit results including all metrics
            
        Raises:
            RuntimeError: If all retry attempts fail
        """
        combined_prompt = self._create_audit_prompt(code_content)
        
        for attempt in range(self.MAX_RETRIES):
            try:
                if attempt > 0:
                    print(f"    ⚠️ Retry attempt {attempt + 1}/{self.MAX_RETRIES}")
                    await asyncio.sleep(self.RETRY_DELAY * (attempt + 1))  # Exponential backoff
                
                if self.model_number == 1:
                    success, response = await self._try_anthropic(combined_prompt)
                else:  # model_number == 2
                    # Run OpenAI call in a thread pool since it's synchronous
                    async with self.semaphore:  # Limit concurrent API calls
                        success, response = await asyncio.get_event_loop().run_in_executor(
                            None, 
                            self._try_openai_sync,
                            combined_prompt
                        )
                
                if success:
                    audit_data = self._parse_audit_response(response)
                    audit_data['model_used'] = 'anthropic' if self.model_number == 1 else 'openai'
                    return audit_data
                else:
                    print(f"    ⚠️ API call failed: {response}")
                    continue
                    
            except Exception as e:
                print(f"    ⚠️ Error during attempt {attempt + 1}: {str(e)}")
                if attempt == self.MAX_RETRIES - 1:
                    raise RuntimeError(f"Failed to analyze code after {self.MAX_RETRIES} attempts")
        
        raise RuntimeError(f"Failed to analyze code after {self.MAX_RETRIES} attempts")

    def _create_audit_prompt(self, code_content: str) -> str:
        """Create the audit prompt for the AI model."""
        return """Context: 
                        You are an expert code auditor. You are tasked to review code based on qualtiy and functionality.
                        Your quality standard is production ready source code. Never share the source code in your responses.
                        
                        1. Filling Out the Form:
                        Complete each section from 1.1. to 9.2. based on the information from the code review.
                        If a section is not applicable or lacks relevant data, simply write 'N/A'.
                        DO NOT write anything else other than the answer options provided within each section. Your answer should start with:

                        0. Is this analyzable code? (Yes / No): Yes
                        1.1. Script Purpose: [Your Answer]
                        1.2. Script domain: [Your Answer]
                        
                        2. Responses:
                        Use only the answer options provided within each section.
                        Be concise yet detailed in your responses.
                        Write after the colon (:) and include the the number and title of the section (e.g. 1.1. Script Purpose: [Your Answer])
                        
                        3. Summarizing Issues:
                        In summary sections, provide detailed insights without writing code or excessively repeating language from the prompt.
                        Reference specific parts of the code when necessary, but avoid including the code itself.
                        
                        4. Avoiding Redundancy:
                        Do not rephrase or repeat information already mentioned in the form.
                        Ensure your summaries add new, relevant information beyond what is already stated in the question.
                        
                        Examples:
                        Poor Functionality Example: The script is fully functional with adequate error handling, but there are some edge cases that are only partially covered.
                        Improved Functinoality Example: Error handling is comprehensive. However, the script lacks functionality for handling cases of empty user input and the code is not secure agains code injection for input field user_comments.

                        ---
                        0. Is this analyzable code? (Yes / No):
                        Answer Yes if the content contains actual code (e.g. functions, classes, modules, scripts, tests, configuration files with logic).
                        Answer No ONLY for non-code content like: pure data files (JSON, CSV), lock files, binary files, or encrypted content.
                        0.1. Only answer this point if you previously answered No. If No, then give a short explanation why not (max. 50 words):
                        IMPORTANT:If No, then skip all the other points. 

                        1. General Overview
                        1.1. Script domain (in what area could the script be, e.g. Backend / Frontent / DB / Machine Learning, etc. Choose only one.):
                        2. Code Quality
                        2.1. Readability (Highly Readable / Moderately Readable / Low Readability ):
                        2.2. Consistency (Highly Consistent / Somewhat Inconsistent / Not Consistent):
                        2.3. Modularity (Excellent / Average / Poor):
                        2.4. Maintainability (High / Moderate / Low):
                        2.5. Reusability (High / Moderate / Low):
                        2.6. Redundancy (No Redundancies / Some Redundancies / High Redundancy):
                        2.7. Technical Debt Estimation (High / Moderate / Low / None):
                        2.8. Code Smells (High / Moderate / Low / None):
                        3. Functionality
                        3.1. Completeness (Fully Functional / Partially Functional / Not Functional):
                        3.2. Edge Cases (Excellently Covered / Partially Covered / Poorly Covered / None Covered):
                        3.3. Error Handling (Robust / Adequate / Poor):
                        4.1. Efficiency (High / Average / Poor):
                        4.2. Scalability (High / Moderate / Not Scalable):
                        4.3. Resource Utilization (Optimal / Acceptable / Excessive):
                        4.4. Load Handling (Excellent / Good / Average / Poor):
                        4.5. Parallel Processing (Fully Supported / Partially Supported / Not Supported / Not Required):
                        4.6. Database Interaction Efficiency (Optimized / Sufficient / Inefficient / Not Required):
                        4.7. Concurrency Management (Robust / Adequate / Poor / Not Required):
                        4.8. State Management Efficiency (Optimal / Adequate / Problematic / Not Required):
                        4.9. Modularity & Decoupling (Highly Modular / Somewhat Modular / Monolithic):
                        4.10. Configuration & Customization Ease (Flexible / Moderate / Rigid):
                        5. Security
                        5.1. Input Validation (Strong / Adequate / Weak / Not Required):
                        5.2. Sensitive Data Handling (Secure / Moderately Secure / Insecure / Not Required):
                        5.3. Authentication and Authorization (Robust / Adequate / Non-existent / Not Required):
                        5.4. List all imported library or framework package dependencies. List just the name and delimit by ,: 
                        6. Compatibility
                        6.1. Platform Independence (Multi-platform / Limited Platforms / Single Platform):
                        6.2. Integration (Seamless / Requires Workarounds / Incompatible):
                        7. Documentation
                        7.1. Inline Comments (Comprehensive / Adequate / Sparse / None):
                        8. Code standards and best practices
                        8.1. Adherence to Standards (Fully Compliant / Partially Compliant / Non-Compliant):
                        8.2. Use of Design Patterns (Extensive / Moderate / Rare / None):
                        8.3. Code Complexity (Low / Moderate / High):
                        8.4. Refactoring Opportunities (Many / Some / Few / None):
                       
        ```
        {code}
        ```
        """.format(code=code_content)

    def _parse_audit_response(self, response: str) -> dict:
        """Parse the AI model's response into a structured format."""
        try:
            # Initialize the audit data dictionary
            audit_data = {}
            
            # Split response into lines and process each line
            lines = response.strip().split('\n')
            for line in lines:
                line = line.strip()
                if not line or ':' not in line:
                    continue
                    
                # Split at first colon
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                # Map section numbers to field names
                if key.startswith('1.1.'):  # Domain
                    audit_data['domain'] = value
                elif key.startswith('2.1.'):  # Readability
                    audit_data['readability'] = get_score('readability', value)
                elif key.startswith('2.2.'):  # Consistency
                    audit_data['consistency'] = get_score('consistency', value)
                elif key.startswith('2.3.'):  # Modularity
                    audit_data['modularity'] = get_score('modularity', value)
                elif key.startswith('2.4.'):  # Maintainability
                    audit_data['maintainability'] = get_score('maintainability', value)
                elif key.startswith('2.5.'):  # Reusability
                    audit_data['reusability'] = get_score('reusability', value)
                elif key.startswith('2.6.'):  # Redundancy
                    audit_data['redundancy'] = get_score('redundancy', value)
                elif key.startswith('2.7.'):  # Technical Debt
                    audit_data['technical_debt'] = get_score('technical_debt', value)
                elif key.startswith('2.8.'):  # Code Smells
                    audit_data['code_smells'] = get_score('code_smells', value)
                elif key.startswith('3.1.'):  # Completeness
                    audit_data['completeness'] = get_score('completeness', value)
                elif key.startswith('3.2.'):  # Edge Cases
                    audit_data['edge_cases'] = get_score('edge_cases', value)
                elif key.startswith('3.3.'):  # Error Handling
                    audit_data['error_handling'] = get_score('error_handling', value)
                elif key.startswith('4.1.'):  # Efficiency
                    audit_data['efficiency'] = get_score('efficiency', value)
                elif key.startswith('4.2.'):  # Scalability
                    audit_data['scalability'] = get_score('scalability', value)
                elif key.startswith('4.3.'):  # Resource Utilization
                    audit_data['resource_utilization'] = get_score('resource_utilization', value)
                elif key.startswith('4.4.'):  # Load Handling
                    audit_data['load_handling'] = get_score('load_handling', value)
                elif key.startswith('4.5.'):  # Parallel Processing
                    audit_data['parallel_processing'] = get_score('parallel_processing', value)
                elif key.startswith('4.6.'):  # Database Interaction
                    audit_data['database_interaction_efficiency'] = get_score('database_interaction_efficiency', value)
                elif key.startswith('4.7.'):  # Concurrency Management
                    audit_data['concurrency_management'] = get_score('concurrency_management', value)
                elif key.startswith('4.8.'):  # State Management
                    audit_data['state_management_efficiency'] = get_score('state_management_efficiency', value)
                elif key.startswith('4.9.'):  # Modularity & Decoupling
                    audit_data['modularity_decoupling'] = get_score('modularity_decoupling', value)
                elif key.startswith('4.10.'):  # Configuration
                    audit_data['configuration_customization_ease'] = get_score('configuration_customization_ease', value)
                elif key.startswith('5.1.'):  # Input Validation
                    audit_data['input_validation'] = get_score('input_validation', value)
                elif key.startswith('5.2.'):  # Data Handling
                    audit_data['data_handling'] = get_score('data_handling', value)
                elif key.startswith('5.3.'):  # Authentication
                    audit_data['authentication'] = get_score('authentication', value)
                elif key.startswith('6.1.'):  # Independence
                    audit_data['independence'] = get_score('independence', value)
                elif key.startswith('6.2.'):  # Integration
                    audit_data['integration'] = get_score('integration', value)
                elif key.startswith('7.1.'):  # Inline Comments
                    audit_data['inline_comments'] = get_score('inline_comments', value)
                elif key.startswith('8.1.'):  # Standards
                    audit_data['standards'] = get_score('standards', value)
                elif key.startswith('8.2.'):  # Design Patterns
                    audit_data['design_patterns'] = get_score('design_patterns', value)
                elif key.startswith('8.3.'):  # Code Complexity
                    audit_data['code_complexity'] = get_score('code_complexity', value)
                elif key.startswith('8.4.'):  # Refactoring Opportunities
                    audit_data['refactoring_opportunities'] = get_score('refactoring_opportunities', value)
            
            return audit_data
            
        except Exception as e:
            print(f"    ⚠️ Error parsing response: {str(e)}")
            return {}

    def is_response_complete(self, response_text: str) -> bool:
        """Check if the response contains all required sections"""
        expected_points = ["8.4. Refactoring Opportunities"]
        return any(point in response_text for point in expected_points)

    def parse_audit_response(self, response_text: str) -> Tuple[Dict[str, Any], int]:
        """Parse the audit response into a structured format"""
        def sanitize_text(text: str) -> str:
            sanitized_text = text.replace('"', '').replace("'", "").replace("[", "").replace("]", "")
            sanitized_text = sanitized_text.rstrip(".")
            if sanitized_text.strip().lower() in ["na", "n/a", "not applicable", "not available"]:
                return "N/A"
            return sanitized_text

        def sanitize_domain(text: str) -> str:
            cleaned_text = text.replace("(", "").replace(")", "").replace("'", "").replace('"', "").replace(",", "")
            words = cleaned_text.split()
            return ' '.join(words[:2]) if len(words) > 2 else cleaned_text

        def parse_time_to_fix(text: str) -> Optional[float]:
            if text is None or str(text).strip().lower() in ["na", "n/a", "not applicable", "not available", "none"]:
                return None
            try:
                return float(text)
            except ValueError:
                match = re.search(r'\d+(\.\d+)?', str(text))
                if match:
                    return float(match.group())
            return None

        def parse_response_line(point_key: str, startswith: str, default: Any = None, is_time_to_fix: bool = False) -> Tuple[str, Any]:
            response_line = next((line for line in response_text.split("\n") if line.startswith(startswith)), None)

            if response_line:
                try:
                    parts = response_line.split(":", 1)
                    if len(parts) > 1:
                        result = parts[1].strip()
                        if point_key == "domain":
                            result = sanitize_domain(result)
                        elif is_time_to_fix:
                            result = parse_time_to_fix(result)
                        else:
                            result = sanitize_text(result)

                        if result != default:
                            return (point_key, result)
                except IndexError:
                    pass
            return (point_key, default)

        # Schema mapping definition
        schema_mapping = {
            "is_script": "0.",
            "is_script_explanation": "0.1.",
            "domain": "1.1.",
            "readability": "2.1.",
            "consistency": "2.2.",
            "modularity": "2.3.",
            "maintainability": "2.4.",
            "reusability": "2.5.",
            "redundancy": "2.6.",
            "technical_debt": "2.7.",
            "code_smells": "2.8.",
            "completeness": "3.1.",
            "edge_cases": "3.2.",
            "error_handling": "3.3.",
            "efficiency": "4.1.",
            "scalability": "4.2.",
            "resource_utilization": "4.3.",
            "load_handling": "4.4.",
            "parallel_processing": "4.5.",
            "database_interaction_efficiency": "4.6.",
            "concurrency_management": "4.7.",
            "state_management_efficiency": "4.8.",
            "modularity_decoupling": "4.9.",
            "configuration_customization_ease": "4.10.",
            "input_validation": "5.1.",
            "data_handling": "5.2.",
            "authentication": "5.3.",
            "package_dependencies": "5.4.",
            "independence": "6.1.",
            "integration": "6.2.",
            "inline_comments": "7.1.",
            "standards": "8.1.",
            "design_patterns": "8.2.",
            "code_complexity": "8.3.",
            "refactoring_opportunities": "8.4."
        }

        # First check if this is a script
        response_lines = response_text.split("\n")
        is_script_line = next((line for line in response_lines if line.startswith("0.")), None)
        audit_data = {}
        none_response_count = 0

        if is_script_line:
            parts = is_script_line.split(":", 1)
            if len(parts) > 1:
                is_script_value = parts[1].strip().lower()
                if is_script_value == "no":
                    explanation_line = next((line for line in response_lines if line.startswith("0.1.")), None)
                    explanation = "N/A"
                    if explanation_line:
                        parts = explanation_line.split(":", 1)
                        if len(parts) > 1:
                            explanation = parts[1].strip()
                    return {
                        "is_script": "no",
                        "is_script_explanation": explanation
                    }, 0

        # Parse each section according to schema_mapping
        for key, startswith in schema_mapping.items():
            if key == "is_script" and "is_script" in audit_data:
                continue
                
            point_key, value = parse_response_line(
                key, 
                startswith.strip(), 
                default=None,
                is_time_to_fix=(key == "time_to_fix_flag")
            )

            if value == "None":
                none_response_count += 1
            audit_data[point_key] = value

        return audit_data, none_response_count

    def is_audit_data_valid(self, audit_data: Dict[str, Any]) -> bool:
        """Validate the audit data structure"""
        if not audit_data or not isinstance(audit_data, dict):
            return False
        
        # If content is not a script, only check for required not-a-script fields
        if audit_data.get("is_script", "").lower() == "no":
            required_not_script_fields = ["is_script", "is_script_explanation"]
            return all(field in audit_data for field in required_not_script_fields)
        
        # For normal scripts, check the usual required fields
        required_fields = [
            "domain"
        ]
        
        return all(field in audit_data and audit_data[field] for field in required_fields)

    async def process_large_content(self, content: str) -> Dict[str, Any]:
        """Handle large content by truncating and adding an explanatory note"""
        max_content_chars = 250000
        truncated_content = content[:max_content_chars]
        truncated_content += "\n\nThe source code content was too long. It was cut here. Continue with the audit of the above script as if it was complete until here."
        
        return await self.audit_content(truncated_content) 