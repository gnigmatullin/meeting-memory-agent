import json
from datetime import datetime
from dotenv import load_dotenv
import chromadb
import os
from chromadb.utils.embedding_functions import GoogleGeminiEmbeddingFunction

from transcript_processor import MeetingData, ActionItem, transcript_to_chunks

load_dotenv()

MEETINGS_COLLECTION = "meetings"
ACTIONS_COLLECTION = "action_items"


def get_client(persist_dir: str = "./chroma_db") -> chromadb.PersistentClient:
    return chromadb.PersistentClient(path=persist_dir)


def get_ef():
    return GoogleGeminiEmbeddingFunction(
        api_key_env_var="GOOGLE_API_KEY"
    )


def get_collection(client, name: str):
    return client.get_or_create_collection(
        name=name,
        embedding_function=get_ef(),
        metadata={"hnsw:space": "cosine"}
    )


# --- Store ---

def store_meeting(meeting: MeetingData, persist_dir: str = "./chroma_db") -> int:
    """
    Stores meeting chunks in ChromaDB.
    Returns number of chunks stored.
    """
    client = get_client(persist_dir)
    meetings_col = get_collection(client, MEETINGS_COLLECTION)
    actions_col = get_collection(client, ACTIONS_COLLECTION)

    chunks = transcript_to_chunks(meeting)
    meeting_id = f"{meeting.date}_{meeting.title}".replace(" ", "_").lower()

    summary_chunks = [c for c in chunks if c["metadata"]["type"] == "summary"]
    action_chunks = [c for c in chunks if c["metadata"]["type"] == "action_item"]

    # Store summary
    if summary_chunks:
        meetings_col.upsert(
            documents=[c["text"] for c in summary_chunks],
            metadatas=[c["metadata"] for c in summary_chunks],
            ids=[f"{meeting_id}_summary"]
        )

    # Store action items with completion tracking
    for i, chunk in enumerate(action_chunks):
        action_id = f"{meeting_id}_action_{i}"
        meta = {**chunk["metadata"], "action_id": action_id}
        actions_col.upsert(
            documents=[chunk["text"]],
            metadatas=[meta],
            ids=[action_id]
        )

    return len(chunks)


# --- Retrieve ---

def search_meetings(query: str, n_results: int = 5,
                    persist_dir: str = "./chroma_db") -> list[dict]:
    """Semantic search across meeting summaries."""
    client = get_client(persist_dir)
    col = get_collection(client, MEETINGS_COLLECTION)

    if col.count() == 0:
        return []

    results = col.query(
        query_texts=[query],
        n_results=min(n_results, col.count())
    )

    return [
        {"text": doc, "metadata": meta}
        for doc, meta in zip(results["documents"][0], results["metadatas"][0])
    ]


def get_open_action_items(assignee: str = "",
                          persist_dir: str = "./chroma_db") -> list[dict]:
    """Returns all open (incomplete) action items, optionally filtered by assignee."""
    client = get_client(persist_dir)
    col = get_collection(client, ACTIONS_COLLECTION)

    if col.count() == 0:
        return []

    where = {"completed": "False"}
    if assignee:
        where = {"$and": [{"completed": "False"}, {"assignee": assignee}]}

    results = col.get(where=where)

    return [
        {"text": doc, "metadata": meta, "id": id_}
        for doc, meta, id_ in zip(
            results["documents"], results["metadatas"], results["ids"]
        )
    ]


def mark_action_complete(action_id: str, persist_dir: str = "./chroma_db") -> bool:
    """Marks an action item as completed."""
    client = get_client(persist_dir)
    col = get_collection(client, ACTIONS_COLLECTION)

    try:
        result = col.get(ids=[action_id])
        if not result["ids"]:
            return False

        meta = result["metadatas"][0]
        meta["completed"] = "True"
        meta["completed_at"] = datetime.now().strftime("%Y-%m-%d")

        col.update(ids=[action_id], metadatas=[meta])
        return True
    except Exception:
        return False


def get_all_meetings(persist_dir: str = "./chroma_db") -> list[dict]:
    """Returns all stored meeting summaries sorted by date."""
    client = get_client(persist_dir)
    col = get_collection(client, MEETINGS_COLLECTION)

    if col.count() == 0:
        return []

    results = col.get()
    meetings = [
        {"text": doc, "metadata": meta}
        for doc, meta in zip(results["documents"], results["metadatas"])
    ]

    return sorted(meetings, key=lambda x: x["metadata"].get("date", ""), reverse=True)


def get_stats(persist_dir: str = "./chroma_db") -> dict:
    """Returns summary stats for the sidebar."""
    client = get_client(persist_dir)
    meetings_col = get_collection(client, MEETINGS_COLLECTION)
    actions_col = get_collection(client, ACTIONS_COLLECTION)

    all_actions = actions_col.get() if actions_col.count() > 0 else {"metadatas": []}
    open_count = sum(1 for m in all_actions["metadatas"] if m.get("completed") == "False")
    done_count = sum(1 for m in all_actions["metadatas"] if m.get("completed") == "True")

    return {
        "meetings": meetings_col.count(),
        "open_actions": open_count,
        "completed_actions": done_count,
    }


if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    from transcript_processor import parse_transcript

    text = open("sample_transcript.txt").read()
    meeting = parse_transcript(text)

    print(f"Storing meeting: {meeting.title}")
    count = store_meeting(meeting, persist_dir="./chroma_db")
    print(f"Stored {count} chunks")

    print("\nOpen action items:")
    actions = get_open_action_items(persist_dir="./chroma_db")
    for a in actions:
        print(f"  [{a['metadata']['assignee']}] {a['text'][:80]}... (id: {a['id']})")

    print("\nStats:", get_stats(persist_dir="./chroma_db"))

    # Test mark complete
    if actions:
        action_id = actions[0]["id"]
        print(f"\nMarking complete: {action_id}")
        mark_action_complete(action_id, persist_dir="./chroma_db")
        print("Open actions after:", len(get_open_action_items(persist_dir="./chroma_db")))