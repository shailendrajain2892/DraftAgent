# Spec 03: LangGraph agent

Owner: Yashshree Nigudkar. Read `00_shared_overview_and_contracts.md` first.
Contract B (tools) is what you call. Contract D (Python interface) is what the backend calls.

## Your scope

The graph, its state, the system prompt and the draft prompt, and the two entry points
`start_run` and `resume_run`. You do not write Gmail code or style store code: you call tools.

## Graph

```text
START -> gather_agent <-> tools
                |
                v  (no more tool calls)
            ask_user   <- interrupt(): pauses here, waits for the user's answer
                |
                v
              draft    <- one LLM call, no tools
                |
                v
            save_draft <- calls the create_draft tool
                |
                v
               END
```

- `gather_agent`: LLM bound to the three read tools only (`get_thread`, `search_related`,
  `get_style_examples`). Loop through `tools` until the LLM makes no tool call.
  Its final turn must be one specific question for the user.
- `tools`: LangGraph `ToolNode` over the MCP tools, with errors returned to the LLM as text.
- `ask_user`: reads the question from the last message and calls `interrupt()`.
  Resume value is the user's text, or `None` for skip.
- `draft`: one LLM call using the whole message history plus `user_context`. Output is only the reply text.
- `save_draft`: calls `create_draft(thread_id, body_text)` through the tools layer.

Because the order after the gather loop is fixed by edges, the draft cannot be written before
the user has been asked. Do not enforce this in the prompt.

## State

```python
from langgraph.graph import MessagesState

class DraftState(MessagesState):
    # Extra keys carried next to the message history
    gmail_thread_id: str        # the Gmail thread we are replying to (not LangGraph's thread_id)
    user_context: str | None    # the user's answer, None if skipped
    draft: str | None           # final reply text
    gmail_draft_id: str | None  # id returned by create_draft
```

## Important rules for LangGraph

1. **`interrupt()` needs a checkpointer and a thread id.** Compile with `InMemorySaver()` and pass
   `{"configurable": {"thread_id": run_id}}` on every call.
2. **The node re-runs from the top on resume.** Keep `ask_user` free of side effects and LLM calls
   before the `interrupt()` line. The question is generated earlier, in the last `gather_agent` turn.
3. **Two different thread ids.** LangGraph's `thread_id` is `run_id`. The Gmail thread id lives in
   state as `gmail_thread_id`.
4. **`run_id` format:** `{user_id}:{gmail_thread_id}:{uuid8}`.

## Tool wrapper (hidden arguments)

The tools need `user_id` (and the thread id for some). The LLM must not supply them. Wrap each MCP
tool so that `user_id` and `thread_id` come from the run config and state, and are removed from the
schema the LLM sees. `create_draft` is not given to the LLM at all: only the `save_draft` node calls it.

## Prompts (you own the wording)

`gather_agent` system prompt must say:
- You are drafting a reply for the user, not sending it.
- Call `get_thread` first. Then use `search_related` only when the thread refers to earlier history.
  Call `get_style_examples` before you finish.
- Stop calling tools when you have enough. Then reply with one specific question for the user about
  anything you cannot know from the emails (a price, a date, a decision). If there is nothing
  specific, ask a generic "Anything to add before I draft this?".
- Never invent facts, numbers, dates or commitments.

`draft` prompt must include: the thread, related thread summaries, style examples and summary, the
user's answer (or "none"), and rules: match the user's greeting, tone and length; reply only with
the email body (no subject line, no commentary); if a needed fact is missing, leave a visible
placeholder such as `[confirm date]` instead of guessing.

Keep prompts in `agent/prompts.py` so they can be changed without touching the graph.

## Limits

- Maximum `MAX_AGENT_STEPS` (default 6) trips through the gather loop. On the limit, go to
  `ask_user` anyway with whatever context exists.
- Tool errors become text results the LLM can react to. `AuthExpiredError` is not caught: let it
  fail the run so the API returns `AUTH_EXPIRED`.
- Use the OpenAI chat model from `OPENAI_CHAT_MODEL`. Do not hard-code a model name.

## Entry points (Contract D)

```python
# Build once at app startup, with dependencies passed in so tests can fake them
def build_graph(tools: "ToolClient", llm, checkpointer) -> "CompiledGraph": ...

async def start_run(graph, user_id: str, gmail_thread_id: str) -> dict:
    """Runs gather, stops at the interrupt. Returns {"run_id": ..., "question": ...}."""

async def resume_run(graph, run_id: str, user_id: str, answer: str | None) -> dict:
    """Resumes with Command(resume=answer). Returns {"text": ..., "gmail_draft_id": ...}."""
```

`ToolClient` is a small async protocol (`get_thread`, `search_related`, `get_style_examples`,
`create_draft`) that the MCP client and your test fakes both satisfy.

## Working before other parts exist

- Write a `FakeToolClient` that returns fixture threads and style examples (use the shapes in Contract B).
- Run the whole graph in a script or test with the fake client and `InMemorySaver`. No Gmail needed.
- Use a fake LLM for unit tests of routing (tool call, then no tool call). Use the real OpenAI
  model only for a small number of manual runs.

## Definition of done

- [ ] Graph builds and runs end to end with the fake client: gather loop, interrupt, resume, draft, save.
- [ ] `start_run` returns a question and `resume_run` returns the draft text and draft id.
- [ ] Skip (`None`) works and the draft says nothing about the missing answer.
- [ ] The loop cap works. Tool errors do not crash the run. Auth errors do.
- [ ] Draft never contains invented specifics on a thread that lacks them (spot check with 3 fixtures).
- [ ] Works with the real MCP tools once Shailendra's tools layer is up.
- [ ] Prompts are in `prompts.py` and a short README explains how to run the graph locally.

## Not in scope

Multiple agents, streaming tokens to the UI, evaluation (later), persistent checkpointer
(open question 2 in the overview).
