from typing import List, Union

from discord import ButtonStyle, Embed, Interaction, PartialEmoji
from discord.ext.pages import Paginator, PaginatorButton
from discord.ui import Button, View, button


class ConfirmationView(View):
    def __init__(self):
        super().__init__()
        self.value = None

    @button(label="Full send (Yes)", style=ButtonStyle.green, emoji=PartialEmoji.from_str("✅"))
    async def confirm(self, button: Button, interaction: Interaction):
        self.value = True
        self.stop()

    @button(label="On second thought... (Cancel)", style=ButtonStyle.red, emoji=PartialEmoji.from_str("✖️"))
    async def abort(self, button: Button, interaction: Interaction):
        self.value = False
        self.stop()


def make_progress_bar(percent: float, length: int = 10, so_far_char: str = "▰", remaining_char: str = "▱"):

    percent = max(0, min(1, percent))

    progress = round(length*percent)

    progressBar = so_far_char * progress + remaining_char * (length - progress)

    return progressBar


class CustomPaginator(Paginator):
    def __init__(self, pages: Union[List[str], List[Union[List[Embed], Embed]]]):
        buttons = [
            PaginatorButton(
                "first", label="First Page", style=ButtonStyle.blurple),
            PaginatorButton(
                "prev", emoji="⬅️", style=ButtonStyle.green),
            PaginatorButton(
                "page_indicator", style=ButtonStyle.gray, disabled=True),
            PaginatorButton(
                "next", emoji="➡️", style=ButtonStyle.green),
            PaginatorButton(
                "last", label="Last Page", style=ButtonStyle.blurple)
        ]
        super().__init__(
            pages=pages,
            show_disabled=True,
            show_indicator=True,
            show_menu=False,
            author_check=True,
            disable_on_timeout=True,
            use_default_buttons=False,
            default_button_row=0,
            loop_pages=False,
            custom_view=None,
            timeout=180,
            custom_buttons=buttons
        )
