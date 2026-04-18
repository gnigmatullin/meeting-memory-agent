import os
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import RunnablePassthrough

from memory_store import search_meetings, get_open_action_items, get_stats

load_dotenv()


SYSTEM_PROMPT = """You are a meeting memory assistant. You help users recall decisions, action items, and key points from their past meetings.
Answer only based on the provided meeting context.
If the context doesn't contain enough information, say so honestly.
Always mention the meeting title and date when referencing specific meetings.
For action items, always include the assignee and completion status.
Be concise and structured."""


def build_llm():
    provider = os.getenv("LLM_PROVIDER", "groq")

    if provider == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(
            model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
            api_key=os.getenv("GROQ_API_KEY"),
        )
    else:
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"),
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            max_tokens=1024,
        )


def build_chain():
    llm = build_llm()

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="history"),
        ("human", "Meeting context:\n{context}\n\nQuestion: {question}")
    ])

    return prompt | llm | StrOutputParser()


def get_context(question: str) -> str:
    """Retrieve relevant meeting chunks + open action items."""
    results = search_meetings(question, n_results=5)
    meeting_context = "\n\n".join([r["text"] for r in results])

    # Always append open action items if question is about actions/tasks
    action_keywords = ["action", "task", "todo", "follow", "next step", "who", "pending", "open"]
    if any(kw in question.lower() for kw in action_keywords):
        actions = get_open_action_items()
        if actions:
            action_text = "\n".join([
                f"- [{a['metadata']['assignee']}] {a['text'][:120]} (completed: {a['metadata']['completed']})"
                for a in actions
            ])
            meeting_context += f"\n\nOpen action items:\n{action_text}"

    return meeting_context


def ask(question: str, history: list[dict] = None) -> str:
    """
    Main function: takes a question and conversation history,
    returns an answer grounded in meeting memory.
    """
    history = history or []

    # Convert history to LangChain message format
    lc_history = []
    for msg in history:
        if msg["role"] == "user":
            lc_history.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            lc_history.append(AIMessage(content=msg["content"]))

    context = get_context(question)

    if not context.strip():
        return "No meetings have been indexed yet. Please upload a meeting transcript first."

    chain = build_chain()
    return chain.invoke({
        "context": context,
        "question": question,
        "history": lc_history,
    })


if __name__ == "__main__":
    stats = get_stats()
    print(f"Stats: {stats}\n")

    if stats["meetings"] == 0:
        print("No meetings indexed. Run memory_store.py first.")
        exit()

    questions = [
        "What was discussed in the last meeting?",
        "What are the open action items?",
        "What did Sarah Chen need to do?",
    ]

    history = []
    for q in questions:
        print(f"Q: {q}")
        answer = ask(q, history)
        print(f"A: {answer}\n")
        history.append({"role": "user", "content": q})
        history.append({"role": "assistant", "content": answer})