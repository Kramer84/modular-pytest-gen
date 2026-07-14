import re
import textwrap
from typing import List, Optional, Union

from pydantic import BaseModel, Field


class DeprecationDetail(BaseModel):
    version: str = Field(
        ..., description="The version in which the feature was deprecated."
    )
    message: str = Field(
        ..., description="The explanation and alternative migration path."
    )


class ParameterDetail(BaseModel):
    name: str
    type_hint: str = Field(
        description="The string representation of the type hint (e.g., 'list[str]' or 'int')."
    )
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
    type_hint: str = Field(description="The string representation of the type hint.")
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


class ExceptionDetail(BaseModel):
    exception_type: str = Field(
        ...,
        description="The exact Exception or Warning class name (e.g., 'ValueError').",
    )
    description: List[str] = Field(
        description="List of strings explaining the trigger condition. Use separate items for different paragraphs."
    )


class RoutineListingItem(BaseModel):
    name: str = Field(..., description="Name of the routine (function or class).")
    description: str = Field(..., description="Short summary of the routine.")


class BaseNumPyDocstringSchema(BaseModel):
    short_summary: str = Field(
        ...,
        description="Short, imperative summary not using variable names or the function name.",
    )
    deprecation: Optional[DeprecationDetail] = None
    extended_summary: Optional[str] = Field(
        None,
        description="Clarifies functionality without implementation details or theory.",
    )
    see_also: List[SeeAlsoItem] = Field(default_factory=list)
    references: List[str] = Field(
        default_factory=list,
        description="Publications or source documentation citations. Do NOT include the '.. [x]' numbering prefix; the builder automatically applies it.",
    )
    examples: List[str] = Field(
        default_factory=list,
        description="Doctest-style lines execution examples (>>>).",
    )


class FunctionDocstringSchema(BaseNumPyDocstringSchema):
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
    parameters: List[ParameterDetail] = Field(
        default_factory=list,
        description="Arguments for the method. Do NOT include 'self' in the parameter list.",
    )


class ClassDocstringSchema(BaseNumPyDocstringSchema):
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
    notes: Optional[List[str]] = Field(
        default=None, description="Theory, math or algorithm discussion."
    )
    warnings: Optional[str] = Field(
        None, description="Free-text area for highly critical user cautions."
    )


class ModuleDocstringSchema(BaseNumPyDocstringSchema):
    routine_listings: List[RoutineListingItem] = Field(
        default_factory=list,
        description="Listings of classes and functions. Encouraged for large modules.",
    )
    notes: Optional[List[str]] = Field(
        default=None,
        description="Theory, math or algorithm discussion. Do NOT include author or license information here.",
    )


class ConstantDocstringSchema(BaseNumPyDocstringSchema):
    pass


def smart_wrap(
    text_segments: Union[List[str], str], wrapper: textwrap.TextWrapper
) -> List[str]:

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
                desc_text += f" (the default is {p.default_value})."
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
