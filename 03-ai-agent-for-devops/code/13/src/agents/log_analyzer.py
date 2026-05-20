"""
Log Analyzer Agent

AI agent that reads logs, alerts the team, and proposes remediation.
Safe tools auto-execute; infrastructure changes require user approval.
"""
import logging

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, ToolMessage

from ..models import create_model
from ..tools import get_all_tools, requires_approval
from ..utils.response import extract_response_text
from ..config import Config

logger = logging.getLogger(__name__)

# Words that count as user confirmation
CONFIRMATIONS = {
    "yes", "y", "confirm", "approve", "go ahead",
    "do it", "ok", "proceed", "sure", "yeah", "yep",
}


def is_confirmation(text: str) -> bool:
    """Return True if the text is a short user confirmation."""
    return text.strip().lower().rstrip("!.,") in CONFIRMATIONS


class LogAnalyzerAgent:
    """
    AI Logging Agent with tool-calling loop.

    The agent sends each LLM response through a loop:
      1. If the LLM wants to call tools, execute them and feed results back.
      2. If a tool requires approval, block it and ask the user to confirm.
      3. When the user confirms, the same tool is allowed through.
      4. Repeat until the LLM produces a final text response.
    """

    def __init__(self, incident_context: str = ""):
        self.model = create_model()
        self.tools = get_all_tools()
        self.llm = self.model.get_llm_with_tools(self.tools)

        system_prompt = Config.get_system_prompt()
        if incident_context:
            system_prompt += "\n\n" + incident_context

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "{input}"),
        ])
        self.pending_actions = []          # blocked tool calls from last turn

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def process_query(self, user_input: str, chat_history: list = None,
                      callbacks=None) -> str:
        """
        Run the agent on a user message and return the final text response.

        Args:
            user_input:   The user's question or command.
            chat_history: Previous LangChain messages (HumanMessage / AIMessage).
            callbacks:    StreamlitProgress instance for live UI updates.
        """
        chat_history = chat_history or []
        self.pending_actions = []

        # Should we let infrastructure tools through this turn?
        approval_granted = is_confirmation(user_input)

        messages = self.prompt.format_messages(
            chat_history=chat_history, input=user_input,
        )

        if callbacks:
            callbacks.on_thinking()

        response = self.llm.invoke(messages)
        return self._tool_loop(response, messages, approval_granted, callbacks)

    # ------------------------------------------------------------------
    # Tool-calling loop
    # ------------------------------------------------------------------
    def _tool_loop(self, response, messages: list,
                   approval_granted: bool, callbacks) -> str:
        """
        Execute tool calls in a loop until the LLM returns a text-only
        response or we hit the iteration limit.
        """
        last_text = ""

        for _ in range(Config.MAX_ITERATIONS):
            # -- No tool calls -> return the final answer --
            if not getattr(response, "tool_calls", None):
                text = extract_response_text(response)
                return text or last_text or "No response generated."

            # Keep any intermediate text the LLM produced alongside tools
            intermediate = extract_response_text(response)
            if intermediate:
                last_text = intermediate

            # Show reasoning in the UI
            if callbacks and intermediate:
                callbacks.on_reasoning(intermediate)

            # -- Execute each tool call --
            tool_results = []
            for tc in response.tool_calls:
                result_msg = self._execute_tool_call(
                    tc, approval_granted, callbacks,
                )
                tool_results.append(result_msg)

            # Feed results back to the LLM
            messages.append(AIMessage(
                content=response.content,
                tool_calls=response.tool_calls,
            ))
            messages.extend(tool_results)

            if callbacks:
                callbacks.on_thinking()

            response = self.llm.invoke(messages)

        # Exhausted iterations
        text = extract_response_text(response)
        return text or last_text or "Reached maximum analysis steps."

    # ------------------------------------------------------------------
    # Single tool-call execution
    # ------------------------------------------------------------------
    def _execute_tool_call(self, tc: dict, approval_granted: bool,
                           callbacks) -> ToolMessage:
        """
        Execute one tool call.  If the tool requires approval and the user
        has not confirmed, block it and record it in pending_actions.
        """
        name, args, call_id = tc["name"], tc["args"], tc["id"]

        # -- Block infrastructure tools until user confirms --
        if requires_approval(name) and not approval_granted:
            self.pending_actions.append(tc)
            if callbacks:
                callbacks.on_approval_skipped(name, args)
            return ToolMessage(
                content=(
                    f"Action '{name}' requires human approval and was not executed. "
                    "Present your findings and ask the user to confirm. "
                    "When the user confirms, call this tool again -- "
                    "the system will allow it through."
                ),
                tool_call_id=call_id,
            )

        # -- Execute the tool --
        if callbacks:
            callbacks.on_tool_start(name, args)

        tool_func = self._find_tool(name)
        if not tool_func:
            return ToolMessage(content=f"Tool '{name}' not found",
                               tool_call_id=call_id)

        try:
            result = str(tool_func.invoke(args))
            if callbacks:
                callbacks.on_tool_end(name, result, success=True)
            return ToolMessage(content=result, tool_call_id=call_id)
        except Exception as e:
            if callbacks:
                callbacks.on_tool_end(name, str(e), success=False)
            return ToolMessage(content=f"Error: {e}", tool_call_id=call_id)

    # ------------------------------------------------------------------
    def _find_tool(self, name: str):
        """Look up a tool by name."""
        for t in self.tools:
            if t.name == name:
                return t
        return None
