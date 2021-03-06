import textwrap
from discord.ext import menus
import re
from discord.ext import commands
import datetime
import time
import random
from collections import deque


class Confirm(menus.Menu):
    def __init__(self, msg, *, timeout=120.0, delete_message_after=True, clear_reactions_after=False):
        super().__init__(
            timeout=timeout, delete_message_after=delete_message_after, clear_reactions_after=clear_reactions_after)
        self.msg = msg
        self.result = None

    async def send_initial_message(self, ctx, channel):
        return await channel.send(self.msg)

    @menus.button('\N{WHITE HEAVY CHECK MARK}')
    async def do_confirm(self, _):
        self.result = True
        self.stop()

    @menus.button('\N{CROSS MARK}')
    async def do_deny(self, _):
        self.result = False
        self.stop()

    async def prompt(self, ctx):
        await self.start(ctx, wait=True)
        return self.result


class EmbedConfirm(menus.Menu):
    def __init__(self, embed, *, timeout=120.0, delete_message_after=True, clear_reactions_after=False):
        super().__init__(
            timeout=timeout, delete_message_after=delete_message_after, clear_reactions_after=clear_reactions_after)
        self.embed = embed
        self.result = None

    async def send_initial_message(self, ctx, channel):
        return await channel.send(embed=self.embed)

    @menus.button('\N{WHITE HEAVY CHECK MARK}')
    async def do_confirm(self, _):
        self.result = True
        self.stop()

    @menus.button('\N{CROSS MARK}')
    async def do_deny(self, _):
        self.result = False
        self.stop()

    async def prompt(self, ctx):
        await self.start(ctx, wait=True)
        return self.result


class ShortTime(commands.Converter):
    async def convert(self, ctx, argument):
        time_unit_mapping = {
            "s": "seconds",    "sec": "seconds",    "second": "seconds",   "seconds": "seconds",
            "m": "minutes",    "min": "minutes",    "minute": "minutes",   "minutes": "minutes",
            "hour": "hours",   "hours": "hours",    "h": "hours",          "hr":   "hours",      "hrs": "hours",
            "day": "days",     "days": "days",      "dys": "days",         "d":   "days",        "dy": "days",
            "week": "weeks",   "weeks": "weeks",    "wks": "weeks",        "wk": "weeks",        "w": "weeks",
        }
        argument = argument.lower()
        number = re.search(r"\d+[.]?\d*?", argument)
        time_unit = re.search(
            f"s|sec|second|seconds|m|min|minute|minutes|hour|hours|h|hr|hrs|day|days|dys|d|dy|week|weeks|wks|wk|w",
            argument)
        if not number:
            raise commands.BadArgument("Invalid duration provided.")
        if not time_unit:
            raise commands.BadArgument("Invalid time unit provided. Some time units than you can use include `min`, `s` and `wks`.")
        number = float(number.group(0))
        time_unit = time_unit_mapping[time_unit.group(0)]
        try:
            return datetime.timedelta(**{time_unit: number})
        except OverflowError:
            raise commands.BadArgument("Time is too large.")


class StopWatch:
    __slots__ = ("start_time", "end_time")

    def __init__(self):
        self.start_time = None
        self.end_time = None

    def start(self):
        self.start_time = time.perf_counter()

    def stop(self):
        self.end_time = time.perf_counter()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.stop()

    @property
    def elapsed(self):
        return self.end_time - self.start_time


class RawPageSource(menus.ListPageSource):
    def __init__(self, data, *, per_page=1):
        super().__init__(data, per_page=per_page)

    async def format_page(self, menu, page):
        return page


class _PaginatorSource(commands.Paginator, menus.PageSource):
    """
    TODO:
    """
    def __init__(self, prefix='```', suffix='```', max_page_size=1000):
        super().__init__(prefix, suffix, max_size=max_page_size)
        self.current_page_chars_remaining = max_page_size

    def is_paginating(self):
        return self.get_max_pages() > 1

    def get_max_pages(self):
        return len(self.pages)

    async def get_page(self, page_number: int):
        return self.pages[page_number]

    def add_line(self, line: str = None, *, empty: bool = False):
        if line is None:
            line = ""
        try:
            chars_remaining = len(self.pages[-1])
        except IndexError:
            chars_remaining = self.max_size
        super().add_line(line[:chars_remaining], empty=empty)
        line = line[:-chars_remaining]
        lines = textwrap.wrap(line, self.max_size)
        for line in lines:
            super().add_line(line, empty=empty)

    def close_page(self):
        if self.suffix is not None:
            self._current_page.append(self.suffix)
        self._pages.append(''.join(self._current_page))

        if self.prefix is not None:
            self._current_page = [self.prefix]
            self._count = len(self.prefix) + 1
        else:
            self._current_page = []
            self._count = 0

    async def format_page(self, menu: menus.MenuPages, entries):
        return f"{entries}\n\nPage {menu.current_page + 1}/{self.get_max_pages()}; len = {len(entries)}"


class PaginatorSource(menus.ListPageSource):
    def format_page(self, menu: menus.MenuPages, page):
        return f"```{page}```\nPage {menu.current_page + 1}/{self.get_max_pages()}"


def owoify(text: str):
    """
    Owofies text.
    """
    return text.replace("l", "w").replace("L", "W").replace("r", "w").replace("R", "W")


def humanize_list(li: list):
    """
    "Humanizes" a list.
    """
    if not li:
        return li
    if len(li) == 1:
        return li[0]
    if len(li) == 2:
        return " and ".join(li)
    return f"{', '.join(str(item) for item in li[:-1])} and {li[-1]}"


class SnakeGame:
    def __init__(self, *, snake_head="🟢", snake_body="🟩", apple="🍎", empty="⬜", border="🟥"):
        self.snake_head = snake_head
        self.snake_body = snake_body
        self.apple = apple
        self.empty = empty
        self.border = border
        self.grid = [[[self.empty,self.border][i == 0 or i == 11 or j == 0 or j == 11] for i in range(12)] for j in range(12)]
        self.snake_x = random.randint(1, 10)
        self.snake_y = random.randint(1, 10)
        self.snake = deque()

        self.apple_x = None
        self.apple_y = None

        self.score = 0
        self.lose = False

        self.grid[self.snake_x][self.snake_y] = self.snake_head
        self.snake.appendleft((self.snake_x, self.snake_y))
        self.spawn_apple()

    def show_grid(self):
        li = []
        for grid_entry in self.grid:
            for item in grid_entry:
                li.append(item)
        return "\n".join(["".join([self.grid[i][j] for j in range(12)]) for i in range(12)])

    def spawn_apple(self):
        while True:
            x = random.randint(1, 10)
            y = random.randint(1, 10)
            if self.grid[x][y] == self.empty:
                self.grid[x][y] = self.apple
                self.apple_x = x
                self.apple_y = y
                break

    def move_snake(self, x: int, y: int, *, apple=False):
        tail_coords = self.snake[-1]
        previous_x = self.snake_x
        previous_y = self.snake_y
        self.snake_x += x
        self.snake_y += y
        self.grid[self.snake_x][self.snake_y] = self.snake_head
        if apple:
            self.grid[previous_x][previous_y] = self.snake_body
        else:
            self.grid[tail_coords[0]][tail_coords[1]] = self.empty
            self.grid[previous_x][previous_y] = self.snake_body if self.score != 0 else self.empty
            self.snake.pop()
        self.snake.appendleft((self.snake_x, self.snake_y))

    def update(self, direction: str):
        direction = direction.lower()
        x = y = 0
        if direction == "up":
            x = -1
        elif direction == "left":
            y = -1
        elif direction == "down":
            x = 1
        elif direction == "right":
            y = 1
        else:
            return
        new_x = self.snake_x + x
        new_y = self.snake_y + y
        if self.grid[new_x][new_y] == self.border:
            self.lose = "You hit the edge of the board."
        elif self.grid[new_x][new_y] == self.snake_body:
            self.lose = "You hit your own body."
        elif self.grid[new_x][new_y] == self.apple:
            self.move_snake(x, y, apple=True)
            self.score += 1
            self.spawn_apple()
        else:
            self.move_snake(x, y)
