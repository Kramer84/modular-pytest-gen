import re
import textwrap
from typing import Any, List, Optional, Union

from pydantic import BaseModel, Field


class DeprecationDetail(BaseModel):
    r"""
    Represents a deprecation notice with version and message.
    
    Parameters
    ----------
    version : str
        The version in which the feature was deprecated.
    message : str
        The explanation and alternative migration path.
    """

    version: str = Field(
        ..., description="The version in which the feature was deprecated."
    )
    message: str = Field(
        ..., description="The explanation and alternative migration path."
    )


class ParameterDetail(BaseModel):
    r"""
    Define a parameter's metadata for docstring generation.
    
    Parameters
    ----------
    name : str
        The name of the parameter as it appears in the function signature.
    type_hint : str, optional
        The string representation of the type hint (e.g., 'list[str]' or
        'int').
    description : str, optional
        A concise definition of the parameter (1 sentence maximum). Do not
        explain why it is used. DO NOT mention default values here; they
        are appended automatically.
    is_optional : bool, optional
        Indicates whether the parameter is optional. Default is False.
    default_value : Any, optional
        The default value. Can be a string, boolean, or number.
    choices : List[str], optional
        Allowed values, mapping to Literal or NumPy set notation. Default
        value first.
    
    Attributes
    ----------
    name : str
        The name of the parameter.
    type_hint : str
        The type hint of the parameter.
    description : str
        The description of the parameter.
    is_optional : bool
        Whether the parameter is optional.
    default_value : Any
        The default value of the parameter.
    choices : List[str]
        The allowed values for the parameter.
    
    Methods
    -------
    model_dump :
        Convert the model instance to a dictionary.
    
    See Also
    --------
    ClassDocstringSchema :
        The schema used to generate the docstring for a class.
    """

    name: str
    type_hint: str = Field(
        description="The string representation of the type hint (e.g., 'list[str]' or 'int')."
    )
    description: str = Field(
        description="A concise definition of the parameter (1 sentence maximum). Do not explain why it is used. DO NOT mention default values here; they are appended automatically."
    )
    is_optional: bool = False
    default_value: Any = Field(
        default=None,
        description="The default value. Can be a string, boolean, or number.",
    )
    choices: List[str] = Field(
        default_factory=list,
        description="Allowed values, mapping to Literal or NumPy set notation. Default value first.",
    )


class ReturnDetail(BaseModel):
    r"""
    Define a named return value with its type and description.
    
    This class is used to document the return values of functions,
    including optional named returns.
    
    Parameters
    ----------
    name : Optional[str], optional
        The name of the return value.
    type_hint : str
        The string representation of the type hint.
    description : List[str]
        The description of the return value.
    """

    name: Optional[str] = Field(
        None, description="Optionally named return values allowed."
    )
    type_hint: str = Field(description="The string representation of the type hint.")
    description: List[str] = Field(
        description="List of strings. Use separate items for different paragraphs or bullet points."
    )


class SeeAlsoItem(BaseModel):
    r"""
    Create a reference to another function or object.
    
    Parameters
    ----------
    name : str
        The fully qualified name of the related function or object.
    
    Other Parameters
    ----------------
    description : Optional[str], optional
        An optional short description of the relationship.
    """

    name: str = Field(
        ..., description="The fully qualified name of the related function/object."
    )
    description: Optional[str] = Field(
        None, description="An optional short description of the relationship."
    )


class ExceptionDetail(BaseModel):
    exception_type: str = Field(
        ...,
        description="The exact Exception or Warning class name (e.g., 'ValueError').",
    )
    description: List[str] = Field(
        description="List of strings explaining the trigger condition. Use separate items for different paragraphs."
    )


class RoutineListingItem(BaseModel):
    r"""
    Represents a routine in a listing.
    
    Parameters
    ----------
    name : str
        Name of the routine (function or class).
    description : str
        Short summary of the routine.
    """

    name: str = Field(..., description="Name of the routine (function or class).")
    description: str = Field(..., description="Short summary of the routine.")


class CoreNumPyDocstringSchema(BaseModel):
    r"""
    Define the schema for NumPy-compliant docstring components.
    
    This class serves as the foundational schema for generating
    NumPy-compliant docstrings. It encapsulates all the necessary fields
    required to construct a comprehensive and standardized documentation
    structure.
    
    Parameters
    ----------
    short_summary : str
        A brief, imperative summary that does not include variable names or
        the function name.
    deprecation : Optional[DeprecationDetail], optional
        Details about the deprecation of the feature, including the version
        and a message explaining the alternative.
    extended_summary : Optional[str], optional
        Provides additional context and clarification about the
        functionality without delving into implementation details or
        theoretical aspects.
    """

    short_summary: str = Field(
        ...,
        description="Short, imperative summary not using variable names or the function name.",
    )
    deprecation: Optional[DeprecationDetail] = None
    extended_summary: Optional[str] = Field(
        None,
        description="Clarifies functionality without implementation details or theory.",
    )


class BaseNumPyDocstringSchema(CoreNumPyDocstringSchema):
    r"""
    Define the schema for NumPy-compliant docstring components.
    
    This class serves as the foundational schema for generating
    NumPy-compliant docstrings. It encapsulates all the necessary fields
    required to construct a comprehensive and standardized documentation
    structure.
    
    Parameters
    ----------
    short_summary : str
        A brief, imperative summary that does not include variable names or
        the function name.
    deprecation : Optional[DeprecationDetail], optional
        Details about the deprecation of the feature, including the version
        and a message explaining the alternative.
    extended_summary : Optional[str], optional
        Provides additional context and clarification about the
        functionality without delving into implementation details or
        theoretical aspects.
    
    Attributes
    ----------
    see_also : List[SeeAlsoItem]
        References to other codes. Optional. Never put references to the
        standard library or well known tools.
    references : List[str]
        Publications or source documentation citations if provided.
        Optional. Do NOT include the '.. [x]' numbering prefix.
    examples : List[str]
        Doctest-style lines execution examples (>>>).
    
    See Also
    --------
    modular_pytest_gen.docstring.CoreNumPyDocstringSchema :
        The base schema for NumPy-compliant docstrings.
    modular_pytest_gen.docstring.DeprecationDetail :
        Details about the deprecation of the feature.
    modular_pytest_gen.docstring.SeeAlsoItem :
        References to other functions or objects.
    """

    see_also: List[SeeAlsoItem] = Field(
        default_factory=list,
        description="References to other codes. Optional. Never put references to the standard library or well known tools.",
    )
    references: List[str] = Field(
        default_factory=list,
        description="Publications or source documentation citations if provided. Optional. Do NOT include the '.. [x]' numbering prefix.",
    )
    examples: List[str] = Field(
        default_factory=list,
        description="Doctest-style lines execution examples (>>>).",
    )


class FunctionDocstringSchema(BaseNumPyDocstringSchema):
    r"""
    Define the schema for function docstring components.
    
    This class extends the base schema to include function-specific fields
    such as parameters, return values, yielded values, and other
    parameters.
    
    Parameters
    ----------
    parameters : List[ParameterDetail]
        Constructor arguments. Do NOT include 'self'.
    returns : Optional[ReturnDetail], optional
        Explains return values and types.
    yields : Optional[ReturnDetail], optional
        Explains yielded values and types for generators.
    receives : List[ParameterDetail]
        Documents values passed via generator .send().
    other_parameters : List[ParameterDetail]
        Infrequently used keywords.
    raises : List[ExceptionDetail]
        Exceptions that may be raised.
    warns : List[ExceptionDetail]
        Warnings that may be issued.
    warnings : Optional[str], optional
        Free-text area for highly critical user cautions.
    notes : Optional[List[str]], optional
        Theory, math or algorithm discussion. Each list item represents a
        new paragraph, a directive, or equation.
    
    Methods
    -------
    model_dump :
        Convert the model instance to a dictionary.
    
    See Also
    --------
    modular_pytest_gen.docstring.CoreNumPyDocstringSchema :
        The base schema for NumPy-compliant docstrings.
    modular_pytest_gen.docstring.DeprecationDetail :
        Details about the deprecation of the feature.
    modular_pytest_gen.docstring.SeeAlsoItem :
        References to other functions or objects.
    """

    parameters: List[ParameterDetail] = Field(default_factory=list)
    returns: Optional[ReturnDetail] = None
    yields: Optional[ReturnDetail] = Field(
        None, description="Explains yielded values and types for generators."
    )
    receives: List[ParameterDetail] = Field(
        default_factory=list,
        description="Documents values passed via generator .send().",
    )
    other_parameters: List[ParameterDetail] = Field(
        default_factory=list, description="Infrequently used keywords."
    )
    raises: List[ExceptionDetail] = Field(default_factory=list)
    warns: List[ExceptionDetail] = Field(default_factory=list)
    warnings: Optional[str] = Field(
        None, description="Free-text area for highly critical user cautions."
    )
    notes: Optional[List[str]] = Field(
        default=None,
        description="Theory, math or algorithm discussion. Each list item represents a new paragraph, a directive, or equation.",
    )


class MethodDocstringSchema(FunctionDocstringSchema):
    r"""
    Define the schema for method docstring components.
    
    This class serves as the foundational schema for generating
    NumPy-compliant docstrings for methods. It encapsulates all the
    necessary fields required to construct a comprehensive and standardized
    documentation structure.
    
    Parameters
    ----------
    parameters : List[ParameterDetail], optional
        Arguments for the method. Do NOT include 'self' in the parameter
        list. Default is [].
    
    See Also
    --------
    modular_pytest_gen.docstring.CoreNumPyDocstringSchema :
        The base schema for NumPy-compliant docstrings.
    modular_pytest_gen.docstring.DeprecationDetail :
        Details about the deprecation of the feature.
    modular_pytest_gen.docstring.SeeAlsoItem :
        References to other functions or objects.
    """

    parameters: List[ParameterDetail] = Field(
        default_factory=list,
        description="Arguments for the method. Do NOT include 'self' in the parameter list.",
    )


class ClassDocstringSchema(BaseNumPyDocstringSchema):
    r"""
    Defines the schema for class docstring components.
    
    Extends the base schema to include class-specific fields such as
    parameters, attributes, methods, and other parameters.
    
    Parameters
    ----------
    short_summary : str
        Defines the schema for class docstring components.
    deprecation : Optional[DeprecationDetail], optional
        Details about the deprecation of the feature.
    extended_summary : Optional[str], optional
        Extends the base schema to include class-specific fields such as
        parameters, attributes, methods, and other parameters.
    see_also : List[SeeAlsoItem], optional
        References to other functions or objects.
    references : List[str], optional
        Publications or source documentation citations if provided.
    parameters : List[ParameterDetail], optional
        Constructor arguments. Do NOT include 'self'.
    attributes : List[ParameterDetail], optional
        Non-method variables.
    methods : List[SeeAlsoItem], optional
        Summary of the public API. Never include private methods starting
        with '_'.
    other_parameters : List[ParameterDetail], optional
        Infrequently used keywords.
    raises : List[ExceptionDetail], optional
        Exceptions that may be raised.
    warns : List[ExceptionDetail], optional
        Warnings that may be issued.
    warnings : Optional[str], optional
        Free-text area for highly critical user cautions.
    notes : Optional[List[str]], optional
        Theory, math or algorithm discussion. Each list item represents a
        new paragraph, a directive, or equation.
    
    See Also
    --------
    modular_pytest_gen.docstring.BaseNumPyDocstringSchema :
        The base schema for NumPy-compliant docstrings.
    modular_pytest_gen.docstring.CoreNumPyDocstringSchema :
        The core schema for NumPy-compliant docstrings.
    modular_pytest_gen.docstring.DeprecationDetail :
        Details about the deprecation of the feature.
    modular_pytest_gen.docstring.ParameterDetail :
        Details about the parameters of the class.
    modular_pytest_gen.docstring.SeeAlsoItem :
        References to other functions or objects.
    """

    parameters: List[ParameterDetail] = Field(
        default_factory=list,
        description="Constructor arguments. Do NOT include 'self'.",
    )
    attributes: List[ParameterDetail] = Field(
        default_factory=list, description="Non-method variables."
    )
    methods: List[SeeAlsoItem] = Field(
        default_factory=list,
        description="Summary of the public API. Never include private methods starting with '_'.",
    )
    other_parameters: List[ParameterDetail] = Field(
        default_factory=list, description="Infrequently used keywords."
    )
    raises: List[ExceptionDetail] = Field(default_factory=list)
    warns: List[ExceptionDetail] = Field(default_factory=list)
    warnings: Optional[str] = Field(
        None, description="Free-text area for highly critical user cautions."
    )
    notes: Optional[List[str]] = Field(
        default=None,
        description="Theory, math or algorithm discussion. Each list item represents a new paragraph, a directive, or equation.",
    )


class InitMethodDocstringSchema(BaseNumPyDocstringSchema):
    r"""
    Defines the schema for NumPy-compliant docstring components.
    
    This class serves as the foundational schema for generating
    NumPy-compliant docstrings. It encapsulates all the necessary fields
    required to construct a comprehensive and standardized documentation
    structure.
    
    Attributes
    ----------
    notes : Optional[List[str]], optional
        Theory, math or algorithm discussion.
    warnings : Optional[str], optional
        Free-text area for highly critical user cautions.
    
    See Also
    --------
    modular_pytest_gen.docstring.CoreNumPyDocstringSchema :
        The base schema for NumPy-compliant docstrings.
    modular_pytest_gen.docstring.DeprecationDetail :
        Details about the deprecation of the feature.
    modular_pytest_gen.docstring.SeeAlsoItem :
        References to other functions or objects.
    """

    notes: Optional[List[str]] = Field(
        default=None, description="Theory, math or algorithm discussion."
    )
    warnings: Optional[str] = Field(
        None, description="Free-text area for highly critical user cautions."
    )


class ModuleDocstringSchema(BaseNumPyDocstringSchema):
    r"""
    Define the schema for module-level docstrings.
    
    This class extends the base schema to include module-specific fields
    such as routine listings and notes.
    
    Parameters
    ----------
    routine_listings : List[RoutineListingItem], optional
        Listings of classes and functions. Encouraged for large modules.
    notes : Optional[List[str]], optional
        Theory, math or algorithm discussion. Do NOT include author or
        license information here.
    
    See Also
    --------
    modular_pytest_gen.docstring.BaseNumPyDocstringSchema :
        The base schema for NumPy-compliant docstrings.
    modular_pytest_gen.docstring.RoutineListingItem :
        Represents a routine in a listing.
    """

    routine_listings: List[RoutineListingItem] = Field(
        default_factory=list,
        description="Listings of classes and functions. Encouraged for large modules.",
    )
    notes: Optional[List[str]] = Field(
        default=None,
        description="Theory, math or algorithm discussion. Do NOT include author or license information here.",
    )


class ConstantDocstringSchema(CoreNumPyDocstringSchema):
    r"""
    Define the schema for constant docstring components.
    
    Clarifies functionality. ONLY populate this if the constant's value
    derives from a complex formula, has non-obvious side effects, or
    requires specific domain context not apparent from its name. Do not
    exceed 1-2 sentences.
    
    See Also
    --------
    modular_pytest_gen.docstring.CoreNumPyDocstringSchema :
        The base schema for NumPy-compliant docstrings.
    modular_pytest_gen.docstring.DeprecationDetail :
        Details about the deprecation of the feature.
    """

    extended_summary: Optional[str] = Field(
        None,
        description=(
            "Clarifies functionality. ONLY populate this if the constant's value "
            "derives from a complex formula, has non-obvious side effects, or requires "
            "specific domain context not apparent from its name. Do not exceed 1-2 sentences."
        ),
    )


def smart_wrap(
    text_segments: Union[List[str], str], wrapper: textwrap.TextWrapper
) -> List[str]:
    r"""
    Apply custom wrapping rules to text segments.
    
    This function processes text segments to ensure proper formatting while
    preserving the structure of the original content.
    
    Parameters
    ----------
    text_segments : Union[List[str], str]
        The text segments to be wrapped. Can be a single string or a list
        of strings.
    wrapper : textwrap.TextWrapper
        The TextWrapper instance used to wrap the text segments.
    
    Returns
    -------
    List[str]
        The wrapped text segments as a list of strings.
    
        Each string represents a line of wrapped text with proper
        formatting for directives, bullets, and math expressions.
    
    Raises
    ------
    TypeError
        If `text_segments` is not a string or a list of strings.
    
        If `wrapper` is not an instance of `textwrap.TextWrapper`.
    
    Warnings
    --------
    This function does not handle nested directives or complex mathematical
    expressions. Ensure the input text segments are properly formatted for
    optimal results.
    """

    if not text_segments:
        return []
    if isinstance(text_segments, str):
        text_segments = [text_segments]
    lines = []
    for segment in text_segments:
        segment = segment.strip()
        if not segment:
            continue
        if segment.startswith(".."):
            lines.append(f"{wrapper.initial_indent}{segment}")
            lines.append("")
        elif segment.startswith("- ") or segment.startswith("* "):
            bullet_wrapper = textwrap.TextWrapper(
                width=wrapper.width,
                initial_indent=wrapper.initial_indent,
                subsequent_indent=wrapper.subsequent_indent + "  ",
                break_long_words=False,
                break_on_hyphens=False,
            )
            lines.extend(bullet_wrapper.wrap(segment))
        elif re.match("^[A-Za-z_0-9{}\\\\^]+\\s*=", segment) or segment.startswith(
            ":math:"
        ):
            lines.append(f"{wrapper.subsequent_indent}    {segment}")
            lines.append("")
        else:
            lines.extend(wrapper.wrap(segment))
            lines.append("")
    while lines and lines[-1] == "":
        lines.pop()
    return lines


def build_numpy_docstring(
    schema: "BaseNumPyDocstringSchema", base_indent: int = 4, max_line_length: int = 75
) -> str:
    r"""
    Construct a NumPy-compliant docstring from a schema.
    
    This function generates a properly formatted docstring by processing
    the provided schema and applying text wrapping rules to ensure
    compliance with NumPy standards.
    
    Parameters
    ----------
    schema : BaseNumPyDocstringSchema
        The schema containing the docstring components.
    base_indent : int, optional
        The number of spaces to indent the docstring. Default is 4.
    max_line_length : int, optional
        The maximum line length for the docstring. Default is 75.
    
    Returns
    -------
    str
        The generated NumPy-compliant docstring.
    
        If the schema is empty, returns an empty docstring.
    
    Raises
    ------
    TypeError
        If `schema` is not an instance of `BaseNumPyDocstringSchema`.
    
        If `base_indent` or `max_line_length` are not integers.
    
    Warnings
    --------
    This function does not handle nested directives or complex mathematical
    expressions. Ensure the input schema is properly formatted for optimal
    results.
    """

    indent = " " * base_indent
    content_width = max_line_length - base_indent
    wrapper = textwrap.TextWrapper(
        width=content_width, break_long_words=False, break_on_hyphens=False
    )
    desc_wrapper = textwrap.TextWrapper(
        width=content_width,
        initial_indent="    ",
        subsequent_indent="    ",
        break_long_words=False,
        break_on_hyphens=False,
    )
    lines = []

    def _format_parameter_block(params: List["ParameterDetail"]):
        block_lines = []
        for p in params:
            if p.choices:
                clean_choices = [c.strip("\"'") for c in p.choices]
                type_str = f"{{{', '.join((repr(c) for c in clean_choices))}}}"
            else:
                type_str = p.type_hint
            if p.is_optional:
                type_str += ", optional"
            if type_str:
                block_lines.append(f"{p.name} : {type_str}")
            else:
                block_lines.append(p.name)
            desc_text = p.description
            if p.default_value is not None:
                desc_text = re.sub(
                    r"(?i)\s*\(\s*(?:the\s+)?default(?:s\s+to|is|\s+value\s+is|:).*?\)",
                    "",
                    desc_text,
                )

                desc_text = re.sub(
                    r"(?i)\s*\b(?:the\s+)?default(?:s\s+to|is|\s+value\s+is|:)\b.*?(?:\.\s+|\.$|$)",
                    " ",
                    desc_text,
                )

                desc_text = desc_text.strip()
                desc_text = re.sub(r"\s{2,}", " ", desc_text)
                desc_text = desc_text.rstrip(".") + "."

                desc_text += f" Default is {p.default_value}."

            segments = desc_text.split("\n\n")
            block_lines.extend(smart_wrap(segments, desc_wrapper))
        return block_lines

    def _format_return_block(returns_list: List["ReturnDetail"]):
        block_lines = []
        for r in returns_list:
            if r.name:
                block_lines.append(f"{r.name} : {r.type_hint}")
            else:
                block_lines.append(r.type_hint)
            block_lines.extend(smart_wrap(r.description, desc_wrapper))
        return block_lines

    def _format_exception_block(exceptions_list: List["ExceptionDetail"]):
        block_lines = []
        for e in exceptions_list:
            block_lines.append(e.exception_type)
            block_lines.extend(smart_wrap(e.description, desc_wrapper))
        return block_lines

    if schema.short_summary:
        lines.extend(wrapper.wrap(schema.short_summary))
    if getattr(schema, "deprecation", None):
        lines.append("")
        lines.append(f".. deprecated:: {schema.deprecation.version}")
        dep_msg_wrapper = textwrap.TextWrapper(
            width=content_width, initial_indent="   ", subsequent_indent="   "
        )
        lines.extend(dep_msg_wrapper.wrap(schema.deprecation.message))
    if getattr(schema, "extended_summary", None):
        lines.append("")
        segments = schema.extended_summary.split("\n\n")
        lines.extend(smart_wrap(segments, wrapper))
    if getattr(schema, "routine_listings", None):
        lines.extend(["", "Routine Listings", "----------------"])
        for r in schema.routine_listings:
            if r.description:
                lines.append(f"{r.name} :")
                segments = r.description.split("\n\n")
                lines.extend(smart_wrap(segments, desc_wrapper))
            else:
                lines.append(r.name)
    if getattr(schema, "parameters", None):
        lines.extend(["", "Parameters", "----------"])
        lines.extend(_format_parameter_block(schema.parameters))
    if getattr(schema, "attributes", None):
        lines.extend(["", "Attributes", "----------"])
        lines.extend(_format_parameter_block(schema.attributes))
    if getattr(schema, "methods", None):
        lines.extend(["", "Methods", "-------"])
        for m in schema.methods:
            if m.description:
                lines.append(f"{m.name} :")
                segments = m.description.split("\n\n")
                lines.extend(smart_wrap(segments, desc_wrapper))
            else:
                lines.append(m.name)
    if getattr(schema, "returns", None):
        lines.extend(["", "Returns", "-------"])
        lines.extend(_format_return_block([schema.returns]))
    if getattr(schema, "yields", None):
        lines.extend(["", "Yields", "------"])
        lines.extend(_format_return_block([schema.yields]))
    if getattr(schema, "receives", None):
        lines.extend(["", "Receives", "--------"])
        lines.extend(_format_parameter_block(schema.receives))
    if getattr(schema, "other_parameters", None):
        lines.extend(["", "Other Parameters", "----------------"])
        lines.extend(_format_parameter_block(schema.other_parameters))
    if getattr(schema, "raises", None):
        lines.extend(["", "Raises", "------"])
        lines.extend(_format_exception_block(schema.raises))
    if getattr(schema, "warns", None):
        lines.extend(["", "Warns", "-----"])
        lines.extend(_format_exception_block(schema.warns))
    if getattr(schema, "warnings", None):
        lines.extend(["", "Warnings", "--------"])
        segments = schema.warnings.split("\n\n")
        lines.extend(smart_wrap(segments, wrapper))
    if getattr(schema, "see_also", None):
        lines.extend(["", "See Also", "--------"])
        simple_items = [item.name for item in schema.see_also if not item.description]
        if simple_items:
            lines.extend(wrapper.wrap(", ".join(simple_items)))
        for item in schema.see_also:
            if item.description:
                lines.append(f"{item.name} :")
                segments = item.description.split("\n\n")
                lines.extend(smart_wrap(segments, desc_wrapper))
    if getattr(schema, "notes", None):
        lines.extend(["", "Notes", "-----"])
        lines.extend(smart_wrap(schema.notes, wrapper))
    if getattr(schema, "references", None):
        lines.extend(["", "References", "----------"])
        for i, ref in enumerate(schema.references, 1):
            ref_wrapper = textwrap.TextWrapper(
                width=content_width,
                initial_indent=f".. [{i}] ",
                subsequent_indent="   ",
            )
            lines.extend(ref_wrapper.wrap(ref))
    if getattr(schema, "examples", None):
        lines.extend(["", "Examples", "--------"])
        for ex in schema.examples:
            lines.extend(ex.split("\n"))
    if not lines:
        return 'r"""\n"""'
    formatted_lines = [f"{indent}{line}" if line else indent for line in lines]
    joined_lines = "\n".join(formatted_lines)
    return f'r"""\n{joined_lines}\n{indent}"""'
