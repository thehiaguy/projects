from typing import Any, Sequence

import vertexai
from vertexai.generative_models import GenerativeModel, Tool, ToolConfig


def get_client(*, project: str, location: str = "us-central1") -> None:
    """Initialize Vertex AI with ADC. Returns None — state is global."""
    vertexai.init(project=project, location=location)


async def generate_kg_tool_calls(
    *,
    client: Any,
    model_name: str,
    system_prompt: str,
    user_prompt: str,
    tool_declarations: Sequence[Any],
) -> dict[str, Any]:
    model = GenerativeModel(
        model_name=model_name,
        system_instruction=system_prompt,
        tools=tool_declarations,
    )

    response = model.generate_content(
        user_prompt,
        tool_config=ToolConfig(
            function_calling_config=ToolConfig.FunctionCallingConfig(
                mode=ToolConfig.FunctionCallingConfig.Mode.ANY,
            )
        ),
    )

    tool_calls: list[dict[str, Any]] = []
    try:
        for part in response.candidates[0].content.parts:
            fc = part.function_call
            if fc and fc.name:
                tool_calls.append({
                    "name": fc.name,
                    "arguments": dict(fc.args),
                })
    except (IndexError, AttributeError):
        pass

    return {
        "tool_calls": tool_calls,
        "raw_response": str(response),
        "usage": {},
    }
