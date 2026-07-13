import re
import textwrap
from typing import List, Literal, Optional, Union

from beartype.typing import List, Union
from modular_pytest_gen.smart_wrap import smart_wrap
from pydantic import BaseModel, Field


class BeartypeMeta(BaseModel):
    raw_hint: str = Field(
        description="The string representation of the type hint (e.g., 'list[str]')."
    )
    category: Literal[
        "builtin",
        "pep585_collection",
        "pep604_union",
        "literal",
        "forward_ref",
        "validator",
    ] = "builtin"
    validator_expression: Optional[str] = Field(
        None,
        description="The lambda or expression if using beartype.vale (e.g., 'Is[lambda x: x > 0]').",
    )


class DeprecationDetail(BaseModel):
    version: str = Field(
        ..., description="The version in which the feature was deprecated."
    )
    message: str = Field(
        ..., description="The explanation and alternative migration path."
    )


class ParameterDetail(BaseModel):
    name: str
    beartype_type: BeartypeMeta
    description: str
    is_optional: bool = False
    default_value: Optional[str] = None
    choices: List[str] = Field(
        default_factory=list,
        description="Allowed values, mapping to Literal or NumPy set notation. Default value first.",
    )


class ReturnDetail(BaseModel):
    name: Optional[str] = Field(
        None, description="Optionally named return values allowed."
    )
    beartype_type: BeartypeMeta
    description: List[str] = Field(
        description="List of strings. Use separate items for different paragraphs or bullet points."
    )


class SeeAlsoItem(BaseModel):
    name: str = Field(
        ..., description="The fully qualified name of the related function/object."
    )
    description: Optional[str] = Field(
        None, description="An optional short description of the relationship."
    )


class NumpyDocstringSchema(BaseModel):
    short_summary: str = Field(
        ...,
        description="Short, imperative summary not using variable names or the function name.",
    )
    deprecation: Optional[DeprecationDetail] = None
    extended_summary: Optional[str] = Field(
        None,
        description="Clarifies functionality without implementation details or theory.",
    )
    parameters: List[ParameterDetail] = Field(default_factory=list)
    attributes: List[ParameterDetail] = Field(
        default_factory=list,
        description="Used when documenting classes to define non-method attributes.",
    )
    methods: List[SeeAlsoItem] = Field(
        default_factory=list,
        description="Used when documenting classes to summarize public API methods.",
    )
    returns: Optional[ReturnDetail] = None
    yields: Optional[ReturnDetail] = Field(
        None, description="Explains yieled values and types for generators."
    )
    receives: List[ParameterDetail] = Field(
        default_factory=list,
        description="Documents values passed via generator .send().",
    )
    other_parameters: List[ParameterDetail] = Field(
        default_factory=list, description="Infrequently used keywords."
    )
    raises: List[ReturnDetail] = Field(
        default_factory=list, description="Name field holds Exception class name."
    )
    warns: List[ReturnDetail] = Field(
        default_factory=list, description="Name field holds Warning class name."
    )
    warnings: Optional[str] = Field(
        None, description="Free-text area for highly critical user cautions."
    )
    see_also: List[SeeAlsoItem] = Field(default_factory=list)
    notes: Optional[List[str]] = Field(
        default=None,
        description="Theory, math or algorithm discussion. Each list item represents a new paragraph, a directive, or equation.",
    )
    references: List[str] = Field(
        default_factory=list,
        description="Publications or source documentation citations.",
    )
    examples: List[str] = Field(
        default_factory=list,
        description="Doctest-style lines execution examples (>>>).",
    )
    updated_signature: str = Field(
        ...,
        description="The modified function/class definition line containing beartype hooks.",
    )
    required_imports: List[str] = Field(
        default_factory=list, description="List of required imports for type setting."
    )


def smart_wrap(
    text_segments: Union[List[str], str], wrapper: textwrap.TextWrapper) -> List[str]:
    r"""
    Wrap text segments with configurable indentation and line breaks.
    
    This function intelligently wraps text segments according to the
    provided TextWrapper configuration, handling special cases like
    directives, bullet points, and mathematical expressions.
    
    Parameters
    ----------
    text_segments : Union[List[str], str]
        The text segments to be wrapped. Can be a single string or a list
        of strings.
    wrapper : textwrap.TextWrapper
        The TextWrapper instance configured with desired wrapping
        parameters.
    
    Returns
    -------
    List[str]
        The wrapped text segments as a list of strings.
    
        Each string represents a line of wrapped text.
    
    Notes
    -----
    Special handling for directives (starting with '..'), bullet points
    (starting with '- ' or '* '), and mathematical expressions (starting
    with ':math:').
    
    Empty lines are automatically removed from the end of the output.
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
    schema: NumpyDocstringSchema, base_indent: int = 4, max_line_length: int = 75) -> str:
    r"""
    Constructs a NumPy-compliant docstring from a schema object.
    
    This function generates a properly formatted docstring by processing
    the provided schema object. It handles various sections including
    parameters, returns, warnings, and more, ensuring proper indentation
    and text wrapping.
    
    Parameters
    ----------
    schema : NumpyDocstringSchema
        The schema object containing all the necessary information to build
        the docstring.
    base_indent : int, optional (default is 4)
        The base indentation level for the docstring.
    max_line_length : int, optional (default is 75)
        The maximum line length for the docstring.
    
    Returns
    -------
    str
        The generated NumPy-compliant docstring as a string.
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

    def _format_parameter_block(params: List[ParameterDetail]):
        block_lines = []
        for p in params:
            if p.choices:
                type_str = f"{{{', '.join((repr(c) for c in p.choices))}}}"
            else:
                type_str = p.beartype_type.raw_hint
            if p.is_optional:
                type_str += ", optional"
            if p.default_value is not None:
                type_str += f" (default is {p.default_value})"
            block_lines.append(f"{p.name} : {type_str}" if type_str else p.name)
            segments = p.description.split("\n\n")
            block_lines.extend(smart_wrap(segments, desc_wrapper))
        return block_lines

    def _format_return_block(returns_list: List[ReturnDetail]):
        block_lines = []
        for r in returns_list:
            if r.name:
                block_lines.append(f"{r.name} : {r.beartype_type.raw_hint}")
            else:
                block_lines.append(r.beartype_type.raw_hint)
            block_lines.extend(smart_wrap(r.description, desc_wrapper))
        return block_lines

    if schema.short_summary:
        lines.extend(wrapper.wrap(schema.short_summary))
    if schema.deprecation:
        lines.append("")
        lines.append(f".. deprecated:: {schema.deprecation.version}")
        dep_msg_wrapper = textwrap.TextWrapper(
            width=content_width, initial_indent="   ", subsequent_indent="   "
        )
        lines.extend(dep_msg_wrapper.wrap(schema.deprecation.message))
    if schema.extended_summary:
        lines.append("")
        segments = schema.extended_summary.split("\n\n")
        lines.extend(smart_wrap(segments, wrapper))
    if schema.parameters:
        lines.extend(["", "Parameters", "----------"])
        lines.extend(_format_parameter_block(schema.parameters))
    if schema.attributes:
        lines.extend(["", "Attributes", "----------"])
        lines.extend(_format_parameter_block(schema.attributes))
    if schema.methods:
        lines.extend(["", "Methods", "-------"])
        for m in schema.methods:
            lines.append(m.name)
            if m.description:
                segments = m.description.split("\n\n")
                lines.extend(smart_wrap(segments, desc_wrapper))
    if schema.returns:
        lines.extend(["", "Returns", "-------"])
        lines.extend(_format_return_block([schema.returns]))
    if schema.yields:
        lines.extend(["", "Yields", "------"])
        lines.extend(_format_return_block([schema.yields]))
    if schema.receives:
        lines.extend(["", "Receives", "--------"])
        lines.extend(_format_parameter_block(schema.receives))
    if schema.other_parameters:
        lines.extend(["", "Other Parameters", "----------------"])
        lines.extend(_format_parameter_block(schema.other_parameters))
    if schema.raises:
        lines.extend(["", "Raises", "------"])
        lines.extend(_format_return_block(schema.raises))
    if schema.warns:
        lines.extend(["", "Warns", "-----"])
        lines.extend(_format_return_block(schema.warns))
    if schema.warnings:
        lines.extend(["", "Warnings", "--------"])
        segments = schema.warnings.split("\n\n")
        lines.extend(smart_wrap(segments, wrapper))
    if schema.see_also:
        lines.extend(["", "See Also", "--------"])
        simple_items = [item.name for item in schema.see_also if not item.description]
        if simple_items:
            lines.extend(wrapper.wrap(", ".join(simple_items)))
        for item in schema.see_also:
            if item.description:
                lines.append(f"{item.name} :")
                segments = item.description.split("\n\n")
                lines.extend(smart_wrap(segments, desc_wrapper))
    if schema.notes:
        lines.extend(["", "Notes", "-----"])
        lines.extend(smart_wrap(schema.notes, wrapper))
    if schema.references:
        lines.extend(["", "References", "----------"])
        for i, ref in enumerate(schema.references, 1):
            ref_wrapper = textwrap.TextWrapper(
                width=content_width,
                initial_indent=f".. [{i}] ",
                subsequent_indent="   ",
            )
            lines.extend(ref_wrapper.wrap(ref))
    if schema.examples:
        lines.extend(["", "Examples", "--------"])
        for ex in schema.examples:
            lines.extend(ex.split("\n"))
    if not lines:
        return 'r"""\n"""'
    formatted_lines = [f"{indent}{line}" if line else indent for line in lines]
    joined_lines = "\n".join(formatted_lines)
    return f'r"""\n{joined_lines}\n{indent}"""'
