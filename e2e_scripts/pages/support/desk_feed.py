"""Stand-ins for the support desk's reads and canned answers for its writes.

The ticket list and the chat come from Marg's live desk, scoped to the login's licence, so a test cannot
seed them; the cascade lists are Marg-wide. The tests therefore serve their own data in the shapes the
Angular source reads (field names below, with the file:line that reads them). Every shape is still to be
checked against a live response (spec "To verify live").
"""

from dataclasses import dataclass

from playwright.sync_api import Page

from pages.components.stubbed_endpoint import StubbedEndpoint, StubReply
from pages.support.desk_endpoints import CHAT_HISTORY, DISPOSITIONS, SUGGESTIONS, TICKET_LIST

SUCCESS = "1"
REFUSED = "0"


@dataclass(frozen=True)
class Choice:
    """An option of one of the three cascading selects; `parent_id` is the option it hangs under."""

    choice_id: str
    name: str
    parent_id: str = ""


@dataclass(frozen=True)
class DeskTicket:
    """One row of `MargPrtnerSupprtDetail` (`support-ticket.component.ts:144-165`, `:222-228`,
    `create-ticket.component.ts:118-147`, `support-chat.component.ts:37-49`)."""

    ticket_id: int
    ticket_no: str
    status: str
    description: str
    main_disposition: Choice
    sub_disposition: Choice
    problem_type: Choice
    ticket_date: str
    image_name: str = ""

    def as_api_row(self) -> dict[str, object]:
        return {
            "ID": self.ticket_id,
            "TicketNo": self.ticket_no,
            "Status": self.status,
            "StatusID": "1",
            "Description": self.description,
            "Problem": self.description,
            "Problemtype": self.problem_type.name,
            "SubDispostionID": self.main_disposition.choice_id,
            "SubDispostionDescriptin": self.main_disposition.name,
            "ProblemTypeMargBookID": self.sub_disposition.choice_id,
            "ProblemTypeMargBookDescriptin": self.sub_disposition.name,
            "SubProblemTypeMargBookID": self.problem_type.choice_id,
            "SubProblemTypeMargDescriptin": self.problem_type.name,
            "TicketDate": self.ticket_date,
            "ImageName": self.image_name,
            "ImagePath": "",
            "chats": 0,
        }


@dataclass(frozen=True)
class DispositionTree:
    """`MargSupportStaticData` (`create-ticket.component.ts:476-482`, `:462`, `:828-830`)."""

    main: tuple[Choice, ...]
    sub: tuple[Choice, ...]
    problem: tuple[Choice, ...]

    def as_api_data(self) -> dict[str, object]:
        return {
            "SubDispostion": [{"ID": item.choice_id, "Name": item.name} for item in self.main],
            "ProblemTypeMargBook": [
                {"ID": item.choice_id, "Name": item.name, "Subdispositionid": item.parent_id}
                for item in self.sub
            ],
            "SubProblemTypeMargBook": [
                {"ID": item.choice_id, "Name": item.name, "ProblemTypeID": item.parent_id}
                for item in self.problem
            ],
        }


@dataclass(frozen=True)
class ChatLine:
    """One `MBSupportGetChatRecord` detail (`support-chat.component.html:20-35`); "C" is the customer."""

    text: str
    sent_at: str
    message_from: str = "P"


@dataclass(frozen=True)
class Suggestion:
    """One `GetQuestionSugestion` detail (`create-ticket.component.html:92-103`)."""

    question: str
    url: str


def write_accepted() -> StubReply:
    """What the app treats as a successful save, delete or reply (`status.status == '1'`)."""
    return StubReply({"Data": SUCCESS, "status": {"status": SUCCESS, "error": {}}})


def write_refused(message: str) -> StubReply:
    """A refusal `showError` shows as an error toast with `message` (`alertbox.ts:74-79`)."""
    return StubReply({"Data": None, "status": {"status": REFUSED, "error": {"message": message}}})


class DeskFeed:
    """Serves the desk's reads on one page; route before the page's first navigation."""

    def __init__(self, page: Page) -> None:
        self.ticket_list = StubbedEndpoint(page, TICKET_LIST)
        self.suggestions = StubbedEndpoint(page, SUGGESTIONS)
        self._dispositions = StubbedEndpoint(page, DISPOSITIONS)
        self._chat_history = StubbedEndpoint(page, CHAT_HISTORY)

    def serve_tickets(self, tickets: tuple[DeskTicket, ...]) -> None:
        rows = [ticket.as_api_row() for ticket in tickets]
        self.ticket_list.answer_with(_desk_reply({"Data": {"Details": rows}}))

    def serve_dispositions(self, tree: DispositionTree) -> None:
        self._dispositions.answer_with(_desk_reply(tree.as_api_data()))

    def serve_chat(self, lines: tuple[ChatLine, ...]) -> None:
        details = [
            {
                "MessageFrom": line.message_from,
                "Remarks": "",
                "Description": line.text,
                "Cr_date": line.sent_at,
            }
            for line in lines
        ]
        self._chat_history.answer_with(_desk_reply({"Data": {"Status": "success", "Details": details}}))

    def serve_suggestions(self, suggestions: tuple[Suggestion, ...]) -> None:
        details = [{"Question": item.question, "URL": item.url} for item in suggestions]
        self.suggestions.answer_with(StubReply({"Status": "success", "Details": details}))


def _desk_reply(data: object) -> StubReply:
    return StubReply({"Data": data, "status": {"status": SUCCESS, "error": {}}})
