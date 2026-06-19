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
    Preserves all logs, outputs, and pytest tracebacks in function-specific directories.
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
        max_retries: int = 5
    ) -> Optional[str]:
        
        # Create a dedicated directory for THIS specific function
        rel_module_path = target_file.relative_to(source_root).with_suffix("")
        func_tmp_dir = self.tmp_dir / rel_module_path / func_metadata['name']
        func_tmp_dir.mkdir(parents=True, exist_ok=True)

        current_user_prompt = user_prompt
        traceback_log = ""

        for attempt in range(1, max_retries + 1):
            current_temp = min(0.025 + ((attempt - 1) * 0.2), 0.7)
            try:
                raw_response = client.generate_test(system_prompt, current_user_prompt, tool_schema, temperature=current_temp)
            except Exception as e:
                print(f"    [ERROR] Attempt {attempt}: Connection failed: {e}")
                continue

            # Save the raw LLM output for audit
            (func_tmp_dir / f"attempt_{attempt}_raw_output.txt").write_text(raw_response, encoding="utf-8")

            local_fixtures = ""
            test_cases_list = []
            payload = self._extract_json_payload(raw_response)
            
            if payload and "arguments" in payload:
                args = payload["arguments"]
                local_fixtures = args.get("local_fixtures_and_mocks") or ""
                # Use 'or []' to safely catch 'null' / NoneType returns
                test_cases_list = args.get("test_cases") or []
            elif payload and ("test_cases" in payload or "pytest_code" in payload):
                local_fixtures = payload.get("local_fixtures_and_mocks") or ""
                test_cases_list = payload.get("test_cases") or [payload.get("pytest_code")]
            else:
                test_cases_list = [raw_response]

            # Failsafe: if the LLM completely scrambled the JSON array into a string
            if not isinstance(test_cases_list, list):
                if isinstance(test_cases_list, str) and test_cases_list.strip():
                    test_cases_list = [test_cases_list]
                else:
                    test_cases_list = []

            if not test_cases_list:
                print(f"    [WARN] Attempt {attempt}: Extracted test cases list is empty.")
                # Force loop to continue to next attempt if empty
                traceback_log = "Error: LLM returned an empty or invalid test cases array."
                current_user_prompt = f"""{user_prompt}\n\n⚠️ CRITICAL FAILURE SUMMARY:\nThe previous response did not contain a valid array of test code strings in the JSON payload."""
                continue

            # Reassemble script, forcing the pytest framework import
            full_script_content = ["import pytest"]
            if import_statement:
                full_script_content.append(import_statement)
            full_script_content.append(function_import_statement)
            if local_fixtures:
                full_script_content.append(local_fixtures)
            full_script_content.extend(test_cases_list)

            executable_script = "\n\n".join(full_script_content) + "\n"
            executable_file = func_tmp_dir / f"attempt_{attempt}_runnable.py"
            executable_file.write_text(executable_script, encoding="utf-8")

            # Run verification check with short tracebacks, enforcing a strict 10-second timeout
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "pytest", str(executable_file), "--tb=short"],
                    capture_output=True,
                    text=True,
                    timeout=10.0  # Force kill the test if it hangs
                )
                traceback_log = result.stdout if result.stdout else result.stderr
                return_code = result.returncode
            
            except subprocess.TimeoutExpired as e:
                # Catch the infinite loop/hang, kill it, and feed the timeout back to the LLM
                print(f"    [WARN] Attempt {attempt} triggered a timeout (infinite loop or hang).")
                traceback_log = f"CRITICAL ERROR: Pytest execution timed out after 10 seconds. You likely created an infinite loop or an incredibly slow matrix operation. Optimize the test."
                return_code = 1 # Force failure
            
            # Save the pytest log to disk so YOU can see what the LLM saw
            (func_tmp_dir / f"attempt_{attempt}_pytest.log").write_text(traceback_log, encoding="utf-8")

            if result.returncode == 0:
                print(f"    [SUCCESS] Function '{func_metadata['name']}' verified successfully on attempt {attempt}.")
                # Save the final verified copy
                (func_tmp_dir / f"{func_metadata['name']}_verified.py").write_text(executable_script, encoding="utf-8")
                return executable_script

            print(f"    [WARN] Attempt {attempt} failed verification. Advancing feedback mapping loops...")
            
            current_user_prompt = f"""{user_prompt}

⚠️ CRITICAL FAILURE SUMMARY:
The previous test implementation failed execution validation checks. 
Review the traceback below, correct syntax issues or assertion assumptions, and output a fresh, functional implementation block.

Diagnostic Traceback Error Logs:
```text
{traceback_log}
```    
"""
        # If we exhaust all retries, write a final summary log for the user to inspect
        print(f"    [FAIL] Exhausted all {max_retries} retries for '{func_metadata['name']}'.")
        summary = f"FAILED AFTER {max_retries} ATTEMPTS.\n\nLAST TRACEBACK LOG:\n{traceback_log}"
        (func_tmp_dir / "FINAL_FAILURE.log").write_text(summary, encoding="utf-8")
        
        return None