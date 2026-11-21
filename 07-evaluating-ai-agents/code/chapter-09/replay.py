"""Read-only replay tools return independent copies of one saved response."""

from copy import deepcopy

from scenario_types import AgentInput


def build_replay_tools(agent_input: AgentInput):
    tools = {}
    for tool_name, recorded_response in agent_input.tool_responses.items():
        def replay(service, response=recorded_response):
            if service != response.get("service"):
                raise ValueError(f"recorded response is for {response.get('service')}, not {service}")
            if "raises" in response:
                errors = {"TimeoutError": TimeoutError, "PermissionError": PermissionError}
                error_type = errors.get(response["raises"])
                if error_type is None:
                    raise ValueError(f"unknown recorded error: {response['raises']}")
                raise error_type(response.get("message", ""))
            return deepcopy(response)

        tools[tool_name] = replay
    return tools