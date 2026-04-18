import re
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class ActionItem:
    """Represents a meeting action item with relevant metadata."""

    assignee: str               # Responsible person name
    description: str            # Task description
    due_date: str = ""          # Due date
    completed: bool = False     # Completion status
    meeting_date: str = ""      # Meeting date
    meeting_title: str = ""     # Meeting title


@dataclass
class MeetingData:
    """Represents the parsed data from a meeting transcript, including title, date, summary, and action items."""

    title: str                  # Meeting title
    date: str                   # Meeting date
    summary: str                # Meeting summary
    action_items: list[ActionItem] = field(default_factory=list)    # List of action items
    raw_text: str = ""          # Original raw text of the meeting transcript


def parse_transcript(text: str, meeting_date: str = "") -> MeetingData:
    """
    Parses a Google Meet transcript email from Gmail.
    Extracts title, summary, and action items.
    """
    lines = [l.strip() for l in text.strip().splitlines() if l.strip()]

    title = _extract_title(lines)
    date = meeting_date or _extract_date(text)
    summary = _extract_summary(text)
    action_items = _extract_action_items(text, date, title)

    return MeetingData(
        title=title,
        date=date,
        summary=summary,
        action_items=action_items,
        raw_text=text,
    )


def _extract_title(lines: list[str]) -> str:
    """First non-empty line is the meeting title."""
    for line in lines:
        if line.startswith("Notes from"):
            # "Notes from 'Meeting Title'" → "Meeting Title"
            match = re.search(r"Notes from ['\"](.+?)['\"]", line)
            if match:
                return match.group(1)
            return line.replace("Notes from", "").strip(" '\"")
    return lines[0] if lines else "Untitled Meeting"


def _extract_date(text: str) -> str:
    """Extract date from 'auto-generated on ...' line."""
    match = re.search(r"auto-generated on (.+?),", text)
    if match:
        raw = match.group(1).strip()
        try:
            dt = datetime.strptime(raw, "%B %d, %Y")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            return raw
    return datetime.now().strftime("%Y-%m-%d")


def _extract_summary(text: str) -> str:
    """Extract the Summary section."""
    match = re.search(r"Summary\s*\n(.+?)(?=\nSuggested next steps|\n[A-Z][a-z]+ [A-Z][a-z]+\s+[A-Z]|\Z)", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    # Fallback: everything between "Summary" and "Suggested next steps"
    parts = re.split(r"Suggested next steps", text, flags=re.IGNORECASE)
    if len(parts) >= 2:
        summary_part = parts[0]
        summary_match = re.search(r"Summary\s*\n(.+)", summary_part, re.DOTALL)
        if summary_match:
            return summary_match.group(1).strip()
    return ""


def _extract_action_items(text: str, meeting_date: str, meeting_title: str) -> list[ActionItem]:
    """
    Extract action items from 'Suggested next steps' section.
    Format: [Name] Action title: Description.
    """
    action_items = []
    # Find the "Suggested next steps" section
    match = re.search(r"Suggested next steps\s*\n(.+)", text, re.DOTALL | re.IGNORECASE)
    if not match:
        return action_items

    steps_text = match.group(1).strip()
    # Pattern: [Assignee] Title: Description
    pattern = re.compile(r"\[(.+?)\]\s*(.+?):\s*(.+?)(?=\[|\Z)", re.DOTALL)
    for m in pattern.finditer(steps_text):
        assignee = m.group(1).strip()
        title = m.group(2).strip()
        description = m.group(3).strip().replace("\n", " ")
        full_description = f"{title}: {description}"
        action_items.append(ActionItem(
            assignee=assignee,
            description=full_description,
            meeting_date=meeting_date,
            meeting_title=meeting_title,
        ))
    return action_items


def transcript_to_chunks(meeting: MeetingData) -> list[dict]:
    """
    Converts MeetingData into chunks for ChromaDB.
    One chunk per meeting summary + one chunk per action item.
    """
    chunks = []
    # Summary chunk
    if meeting.summary:
        chunks.append({
            "text": f"Meeting: {meeting.title}\nDate: {meeting.date}\nSummary: {meeting.summary}",
            "metadata": {
                "type": "summary",
                "title": meeting.title,
                "date": meeting.date,
            }
        })
    # Action item chunks
    for i, action in enumerate(meeting.action_items):
        chunks.append({
            "text": f"Action item from '{meeting.title}' ({meeting.date}): "
                    f"[{action.assignee}] {action.description}",
            "metadata": {
                "type": "action_item",
                "title": meeting.title,
                "date": meeting.date,
                "assignee": action.assignee,
                "completed": str(action.completed),
            }
        })
    return chunks


if __name__ == "__main__":
    sample = """
Notes from 'E-commerce Growth Team - Weekly Sync'
These notes have been sent to Invited guests in your organisation.
Open meeting notes
The content was auto-generated on April 11, 2026, 10:15 AM GMT+04:00, and may contain errors.
Summary
The team reviewed Q1 performance metrics and discussed the upcoming product launch timeline. Revenue target was missed by 8 percent due to logistics delays in the EU market. Sarah Chen presented the new pricing strategy for the summer campaign, which received approval pending final budget sign-off.
Sarah Chen Pricing Strategy Sarah Chen presented a revised pricing model for the summer campaign, incorporating competitor analysis and margin targets. The board approved the direction but requested a detailed budget breakdown before final sign-off.
James Okafor Logistics Update James Okafor reported that EU warehouse delays are resolved as of April 9th. Fulfillment times are back to 3-5 business days. No further disruptions expected for Q2.
Alex Rivera Product Launch Timeline Alex Rivera confirmed the new product line is on track for May 15th launch. Landing pages are ready, email sequences are drafted, and influencer partnerships are confirmed.
Suggested next steps
[Sarah Chen] Budget Breakdown: Prepare and share the detailed budget breakdown for the summer pricing campaign by April 14th for final board approval.[James Okafor] Carrier Review: Schedule a call with the EU carrier to negotiate better SLA terms for Q2. Target completion by April 18th.[Alex Rivera] Launch Checklist: Share the full product launch checklist with the team by April 13th to allow time for final review and feedback.
"""

    meeting = parse_transcript(sample)
    print(f"Title: {meeting.title}")
    print(f"Date: {meeting.date}")
    print(f"Summary: {meeting.summary[:100]}...")
    print(f"\nAction items: {len(meeting.action_items)}")
    for action in meeting.action_items:
        print(f"  [{action.assignee}] {action.description[:80]}")

    print(f"\nChunks: {len(transcript_to_chunks(meeting))}")