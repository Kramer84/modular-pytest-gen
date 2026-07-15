import ast
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional


class TestValidator:
    r"""
    Validates and heals generated test cases for a target function.

    The validator orchestrates a closed-loop validation system that
    executes generated tests, captures tracebacks, and dynamically adjusts
    the LLM's temperature to force creative solutions when tests fail.

    Parameters
    ----------
    config : Any
        The configuration object containing project settings.

    Attributes
    ----------
    config : Any
        The configuration object containing project settings.
    tmp_dir : Path
        The temporary directory for storing test artifacts.

    Methods
    -------
    validate_and_heal :
        Validates and heals generated test cases for a target function.

    Raises
    ------
    subprocess.TimeoutExpired
        The pytest execution timed out after 10 seconds.

    Warnings
    --------
    The validator may fail to generate valid test cases for complex
    functions.
    """

    def __init__(self, config: Any):
        r"""
        Initialize the test runner with configuration.

        Sets up the test runner environment using the provided
        configuration object. Creates a temporary directory for test
        execution.

        Warnings
        --------
        Ensure the configuration object contains valid layout settings to
        avoid runtime errors.

        See Also
        --------
        pytest :
            The underlying test framework used for execution.

        Notes
        -----
        The temporary directory path is derived from the `test_root`
        attribute of the configuration layout, defaulting to 'tests.tmp' if
        not specified.
        """

        self.config = config
        test_root_name = getattr(config.layout, "test_root", "tests")
        self.tmp_dir = Path(f"{test_root_name}.tmp")

    def _extract_json_payload(self, text: str) -> Optional[Dict[str, Any]]:
        r"""
        Extract JSON payload from text

        Searches for a JSON object within the provided text and parses it
        into a Python dictionary.

        Parameters
        ----------
        text : str
            The input text containing the JSON payload

        Returns
        -------
        Optional[Dict[str, Any]]
            The parsed JSON object as a dictionary if found and valid.

            Returns `None` if no valid JSON payload is found or if parsing
            fails.

        Raises
        ------
        json.JSONDecodeError
            Raised if the extracted text is not valid JSON.
        """

        try:
            match = re.search("\\{.*\\}", text, re.DOTALL)
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
        max_retries: int = 5,
    ) -> Optional[str]:
        r"""
        Execute test cases in a controlled environment.

        This method orchestrates the closed-loop validation mechanism,
        dynamically adjusting the model's temperature to force creative
        solutions when tests fail.

        Parameters
        ----------
        target_file : Path
            The file containing the function to be tested.
        source_root : Path
            The root directory of the source code.
        func_metadata : Dict[str, Any]
            Metadata about the function, including its name.
        system_prompt : str
            The system prompt for the LLM.
        user_prompt : str
            The user prompt for the LLM.
        import_statement : str
            The import statement for the module containing the function.
        function_import_statement : str
            The import statement for the function to be tested.
        client : Any
            The client used to generate test cases.
        tool_schema : Optional[Dict[str, Any]], optional
            The schema for the tool used to generate test cases.
        max_retries : int
            The maximum number of retries for generating and validating
            test cases. Default is 5.

        Returns
        -------
        Optional[str]
            The validated and healed test script if successful, otherwise
            `None`.

        Raises
        ------
        subprocess.TimeoutExpired
            If the pytest execution times out.

        Warnings
        --------
        This method may trigger multiple retries and temperature
        adjustments to force creative solutions when tests fail.
        """

        rel_module_path = target_file.relative_to(source_root).with_suffix("")
        func_tmp_dir = self.tmp_dir / rel_module_path / func_metadata["name"]
        func_tmp_dir.mkdir(parents=True, exist_ok=True)
        prompt_log_path = func_tmp_dir / "initial_prompt_context.md"
        prompt_log_content = f"# System Prompt\n\n```text\n{system_prompt}\n```\n\n# Initial User Prompt\n\n```text\n{user_prompt}\n```\n"
        if tool_schema:
            prompt_log_content += f"\n# Tool Schema\n\n```json\n{json.dumps(tool_schema, indent=2)}\n```\n"
        prompt_log_path.write_text(prompt_log_content, encoding="utf-8")
        current_user_prompt = user_prompt
        traceback_log = ""
        for attempt in range(1, max_retries + 1):
            current_temp = min(0.025 + (attempt - 1) * 0.2, 0.7)
            try:
                raw_response = client.generate_test(
                    system_prompt,
                    current_user_prompt,
                    tool_schema,
                    temperature=current_temp,
                )
            except Exception as e:
                print(f"    [ERROR] Attempt {attempt}: Connection failed: {e}")
                continue
            (func_tmp_dir / f"attempt_{attempt}_raw_output.txt").write_text(
                raw_response, encoding="utf-8"
            )
            local_fixtures = ""
            test_cases_list = []
            payload = self._extract_json_payload(raw_response)
            if payload and "arguments" in payload:
                args = payload["arguments"]
                local_fixtures = args.get("local_fixtures_and_mocks") or ""
                test_cases_list = args.get("test_cases") or []
            elif payload and ("test_cases" in payload or "pytest_code" in payload):
                local_fixtures = payload.get("local_fixtures_and_mocks") or ""
                test_cases_list = payload.get("test_cases") or [
                    payload.get("pytest_code")
                ]
            else:
                test_cases_list = [raw_response]
            if not isinstance(test_cases_list, list):
                if isinstance(test_cases_list, str) and test_cases_list.strip():
                    test_cases_list = [test_cases_list]
                else:
                    test_cases_list = []
            if not test_cases_list:
                print(
                    f"    [WARN] Attempt {attempt}: Extracted test cases list is empty."
                )
                traceback_log = (
                    "Error: LLM returned an empty or invalid test cases array."
                )
                current_user_prompt = f"{user_prompt}\n\n⚠️ CRITICAL FAILURE SUMMARY:\nThe previous response did not contain a valid array of test code strings in the JSON payload."
                continue
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
            try:
                env = os.environ.copy()
                src_path_str = str(source_root.resolve())
                env["PYTHONPATH"] = (
                    f"{src_path_str}{os.pathsep}{env.get('PYTHONPATH', '')}"
                )
                result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "pytest",
                        str(executable_file),
                        "--tb=short",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10.0,
                    env=env,
                )
                traceback_log = result.stdout if result.stdout else result.stderr
                return_code = result.returncode
            except subprocess.TimeoutExpired as e:
                print(
                    f"    [WARN] Attempt {attempt} triggered a timeout (infinite loop or hang)."
                )
                traceback_log = f"CRITICAL ERROR: Pytest execution timed out after 10 seconds. You likely created an infinite loop or an incredibly slow matrix operation. Optimize the test."
                return_code = 1
            (func_tmp_dir / f"attempt_{attempt}_pytest.log").write_text(
                traceback_log, encoding="utf-8"
            )
            if return_code == 0:
                print(
                    f"    [SUCCESS] Function '{func_metadata['name']}' verified successfully on attempt {attempt}."
                )
                (func_tmp_dir / f"{func_metadata['name']}_verified.py").write_text(
                    executable_script, encoding="utf-8"
                )
                return executable_script
            print(
                f"    [WARN] Attempt {attempt} failed verification. Advancing feedback mapping loops..."
            )
            current_user_prompt = f"{user_prompt}\n\nCRITICAL FAILURE SUMMARY:\nThe previous test implementation failed execution validation checks. \n\nDiagnostic Traceback Error Logs:\n```text\n{traceback_log}\n\n```\n\nCRITIC PROTOCOL INITIATED:\nBefore you write any code, you MUST write a brief root-cause analysis of the failure.\nIdentify exactly which assumption in the previous test caused the error (e.g., 'The LLM assumed the matrix was 2D, but the function requires 3D', or 'The assertion used == on floats').\n\nFormat your response exactly like this:\n\n[Your root-cause analysis here]\n\n\n[Then output the fixed Python/JSON implementation]\n"
        print(
            f"    [FAIL] Exhausted all {max_retries} retries for '{func_metadata['name']}'."
        )
        summary = f"FAILED AFTER {max_retries} ATTEMPTS.\n\nLAST TRACEBACK LOG:\n{traceback_log}"
        (func_tmp_dir / "FINAL_FAILURE.log").write_text(summary, encoding="utf-8")
        return None
