import ast
import json
import re
import sys
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

class TestValidator:
    """
    Handles standalone code verification via isolated background processes.
    Preserves all logs and files for explicit debugging.
    """
    def __init__(self, config: Any):
        self.config = config
        test_root_name = getattr(config.layout, "test_root", "tests")
        self.tmp_dir = Path(f"{test_root_name}.tmp")

    def _extract_json_payload(self, text: str) -> Optional[Dict[str, Any]]:
        """Finds and parses a JSON object embedded anywhere within the text."""
        try:
            # Look for structural curly brace blocks
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
        return None

    def validate_and_heal(
        self,
        target_file: Path,
        source_root: Path,
        func_metadata: Dict[str, Any],
        system_prompt: str,
        user_prompt: str,
        import_statement: str,
        function_import_statement: str,
        client: Any,
        tool_schema: Optional[Dict[str, Any]],
        max_retries: int = 3
    ) -> Optional[str]:
        """
        Runs the generation verification loop. Stores raw outputs and executable files
        permanently inside a modular directory layout for inspection.
        """
        # Organize temporary spaces into target module directory slots
        rel_module_path = target_file.relative_to(source_root).with_suffix("")
        module_tmp_dir = self.tmp_dir / rel_module_path
        module_tmp_dir.mkdir(parents=True, exist_ok=True)

        current_user_prompt = user_prompt

        for attempt in range(1, max_retries + 1):
            try:
                raw_response = client.generate_test(system_prompt, current_user_prompt, tool_schema)
            except Exception as e:
                print(f"    [ERROR] Attempt {attempt}: Connection failed: {e}")
                continue

            # File names are structured by attempt index to preserve history
            prefix = f"{func_metadata['name']}_attempt_{attempt}"
            (module_tmp_dir / f"{prefix}_raw_output.txt").write_text(raw_response, encoding="utf-8")

            # Resolve the response string layout
            local_fixtures = ""
            test_cases_list = []

            payload = self._extract_json_payload(raw_response)
            if payload and "arguments" in payload:
                # Handle standard structured mode tool parameters
                args = payload["arguments"]
                local_fixtures = args.get("local_fixtures_and_mocks", "")
                test_cases_list = args.get("test_cases", [])
            elif payload and ("test_cases" in payload or "pytest_code" in payload):
                # Handle raw unstructured JSON fallback configurations
                local_fixtures = payload.get("local_fixtures_and_mocks", "")
                test_cases_list = payload.get("test_cases", [payload.get("pytest_code", "")])
            else:
                # Fallback treatment for unstructured plain python script representations
                test_cases_list = [raw_response]

            # Reassemble into an integrated, executable test script
            full_script_content = []
            if import_statement:
                full_script_content.append(import_statement)
            full_script_content.append(function_import_statement)
            if local_fixtures:
                full_script_content.append(local_fixtures)
            full_script_content.extend(test_cases_list)

            executable_script = "\n\n".join(full_script_content) + "\n"
            executable_file = module_tmp_dir / f"{prefix}_runnable.py"
            executable_file.write_text(executable_script, encoding="utf-8")

            # Run verification check under the active interpreter workspace mapping environment
            result = subprocess.run(
                [sys.executable, "-m", "pytest", str(executable_file), "-q"],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                print(f"    [SUCCESS] Function '{func_metadata['name']}' verified successfully on attempt {attempt}.")
                # Save an alias pointer reference file indicating the winning candidate copy
                (module_tmp_dir / f"{func_metadata['name']}_verified.py").write_text(executable_script, encoding="utf-8")
                return executable_script

            print(f"    [WARN] Attempt {attempt} failed verification requirements. Advancing feedback mapping loops...")
            traceback_log = result.stdout if result.stdout else result.stderr
            
            # Append feedback directly to the ongoing user instruction array
            current_user_prompt = f"""{user_prompt}

⚠️ CRITICAL FAILURE SUMMARY:
The previous test implementation failed execution validation checks with the following diagnostic runtime logs. 
Review the traceback, correct syntax issues or assumptions, and output a fresh, functional implementation block.

Diagnostic Traceback Error Logs:
```text
{traceback_log}
```    
"""
        return None  # All attempts exhausted without a valid test suite