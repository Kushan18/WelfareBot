from typing import Optional, List
from typing_extensions import TypedDict


class ConversationState(TypedDict):
    session_id: str
    message: str
    user_profile: Optional[dict]
    intent: Optional[str]
    reply: Optional[str]
    awaiting_name: Optional[bool]
    show_form: Optional[bool]
    show_form_choice: Optional[bool]
    awaiting_confirmation: Optional[bool]
    suggestions: Optional[List[str]]
    chips: Optional[List[str]]
    confirmation_step: Optional[str]
    editing_field: Optional[str]