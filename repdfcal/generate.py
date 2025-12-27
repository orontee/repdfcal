"""Everything about PDF generation."""

import logging
import locale
import datetime

from .events import DailyEvent
from .holidays import collect_french_holidays

import fpdf
from fpdf import FPDF

LOGGER = logging.getLogger(__name__)

FONT = "dejavu"

# close to a4 sizes in mm, but matching the remarkable 2
PAGE_WIDTH = 210
PAGE_HEIGTH = 280

# clear the remarkable tool bar
LEFT_MARGIN = 10
RIGHT_MARGIN = 20
TOP_MARGIN = 20
BOTTOM_MARGIN = 20

MONTH_COLOR: list[tuple[int, int, int]] = [
    (-1, -1, -1),  # month 0
    (180, 180, 180),
    (128, 0, 128),
    (0, 128, 0),
    (155, 255, 100),
    (250, 128, 114),
    (0, 0, 255),
    (255, 0, 0),
    (255, 215, 0),
    (80, 200, 212),
    (255, 165, 0),
    (0, 0, 0),
    (178, 34, 34),
]

HOLYDAY_COLOR = (180, 180, 180)

locale.setlocale(locale.LC_ALL, "")
# propagate OS locale

DAYS: list[str] = []
FULLDAYS: list[str] = []

for abdayid, dayid in (
    (locale.ABDAY_2, locale.DAY_2),
    (locale.ABDAY_3, locale.DAY_3),
    (locale.ABDAY_4, locale.DAY_4),
    (locale.ABDAY_5, locale.DAY_5),
    (locale.ABDAY_6, locale.DAY_6),
    (locale.ABDAY_7, locale.DAY_7),
    (locale.ABDAY_1, locale.DAY_1),
):
    DAYS.append(locale.nl_langinfo(abdayid))
    FULLDAYS.append(locale.nl_langinfo(dayid))

MONTHS: list[str] = [
    "None",
]

for monthid in (
    locale.MON_1,
    locale.MON_2,
    locale.MON_3,
    locale.MON_4,
    locale.MON_5,
    locale.MON_6,
    locale.MON_7,
    locale.MON_8,
    locale.MON_9,
    locale.MON_10,
    locale.MON_11,
    locale.MON_12,
):
    MONTHS.append(locale.nl_langinfo(monthid))


def initialize_document(year: int) -> FPDF:
    doc = FPDF(
        orientation="portrait",
        unit="mm",
        format=(PAGE_WIDTH, PAGE_HEIGTH),
    )
    doc.set_margins(0, 0)
    doc.set_auto_page_break(False)
    doc.set_title("Agenda for %04d" % (year))
    doc.set_author("repdfcal")
    doc.add_font(FONT, "", fname="repdfcal/fonts/DejaVuSansCondensed.ttf")
    doc.add_font(FONT, "B", fname="repdfcal/fonts/DejaVuSansCondensed-Bold.ttf")

    return doc


def generate_links(doc: FPDF, year: int) -> dict[str, int]:
    """Create links for every day and month of the given year.

    Return a mapping from day or month ids to link numbers.

    As a side-effect, creates title page.
    """
    doc.add_page()

    links_mapping: dict[str, int] = {}

    # link for year page
    links_mapping["%04d" % (year)] = doc.add_link()

    for mon in range(1, 12 + 1):
        # link for month overview page
        links_mapping["%04d-%02d" % (year, mon)] = doc.add_link()

        # links for day page
        for day in range(1, 31 + 1):
            links_mapping["%04d-%02d-%02d" % (year, mon, day)] = doc.add_link()

    doc.set_font(FONT, "B", 40)
    doc.set_xy(0, 0)
    doc.cell(text="%04d" % (year), align="C", w=PAGE_WIDTH, h=20)
    doc.set_link(links_mapping["%04d" % (year)])

    return links_mapping


def __insert_month_overview(
    doc: FPDF,
    year: int,
    mon: int,
    links: dict[str, int],
    events: dict[str, dict[str, list[DailyEvent]]],
    *,
    highlighted_day: int | None,
    highlighted_holidays: bool,
    size: int,
    x: int,
    y: int,
    day_font=None,
    border=False,
    full_page=False,
    display_year=True,
    ysize=None,
):
    """An overview on the given month.

    This function doesn't insert a new page. A month overview can be
    displayed on its own page or not (like in the year page or day
    pages)."""
    if not ysize:
        ysize = size
    if not day_font:
        day_font = size * 1.8

    doc.set_font(FONT, "B", 2 * size)
    doc.set_text_color(255)
    doc.set_fill_color(*(MONTH_COLOR[mon]))

    if display_year:
        header = "%s %04d" % (MONTHS[mon], year)
    else:
        header = MONTHS[mon]

    if full_page:
        link = links["%04d" % (year)]
    else:
        link = links["%04d-%02d" % (year, mon)]

    doc.set_xy(x, y)
    doc.cell(w=7 * size, h=1.5 * size, text=header, align="C", fill=True, link=link)

    y += int(size * 1.5)

    # draw the days of the week above the table
    doc.set_fill_color(255)
    doc.set_text_color(0)
    doc.set_font(FONT, "", size)
    for weekday in range(0, 7):
        doc.set_xy(x + weekday * size, y)
        doc.cell(
            h=size * 0.5,
            w=size,
            text=DAYS[weekday],
            fill=True,
            align="C",
        )

    week = 0
    y += int(size * 0.5)

    # draw the table for days of the month
    doc.set_text_color(0)

    for day in range(1, 31 + 1):
        try:
            date = datetime.date(year, mon, day)
        except Exception:
            continue

        weekday = date.weekday()
        ymd = "%04d-%02d-%02d" % (year, mon, day)
        link = links[ymd]

        if weekday == 0 and day != 1:
            week += 1

        day_x = x + weekday * size
        day_y = y + week * ysize

        day_events: dict[str, list[DailyEvent]] = events.get(ymd, {})

        if border:
            doc.rect(day_x, day_y, size, ysize)

        is_weekend: bool = (weekday in (5, 6))
        is_holiday: bool = False
        if not is_weekend:
            for _, evs in day_events.items():
                if any([ev.is_holiday() for ev in evs]):
                    is_holiday = True
                    break

        if is_weekend or is_holiday:
            doc.set_text_color(0)
            doc.set_fill_color(*HOLYDAY_COLOR)
            doc.rect(day_x, day_y, size, ysize, style=fpdf.enums.RenderStyle.F)

        doc.set_xy(day_x, day_y)
        doc.set_font(FONT, "B" if day  == highlighted_day else "", day_font)
        doc.cell(
            w=size,
            h=day_font / 2 + 1.5,
            text="%d" % (day),
            align="R",
            link=link,
        )

        if not border:
            continue
        if not day_events:
            continue

        doc.set_font(FONT, "", day_font * 0.8)
        all_day = ""
        for hms, evs in sorted(day_events.items()):
            for ev in evs:
                if hms != "00:00" or ev.duration != 0:
                    # not an all day event
                    continue
                all_day += ev.title + "\n"
        if all_day:
            doc.set_xy(day_x + 1, day_y + day_font / 2 + 2)
            doc.multi_cell(
                w=size,
                h=day_font / 3,
                text=all_day,
                align="L",
            )


def __add_day_page(
    doc: FPDF,
    year: int,
    mon: int,
    day: int,
    links: dict[str, int],
    events: dict[str, dict[str, list[DailyEvent]]],
    *,
    time_block_line_width: int,
    time_block_line_color: int,
):
    """A full-page view on the given day.

    It contains an overview for the corresponding month."""
    try:
        date = datetime.date(year, mon, day)
    except Exception:
        return

    ymd = "%04d-%02d-%02d" % (year, mon, day)
    doc.add_page()
    doc.set_link(links[ymd])

    cal_size = 8
    date_y = 0
    cal_w = 7 * cal_size
    cal_h = 8 * cal_size
    cal_y = 50
    cal_x = PAGE_WIDTH - cal_w - 4

    __insert_month_overview(
        doc,
        year,
        mon,
        links,
        events,
        highlighted_day=day,
        highlighted_holidays=True,
        size=cal_size,
        x=cal_x,
        y=cal_y,
        ysize=cal_size - 0.0,
    )

    # big date and day of week
    doc.set_font(FONT, "B", 125)
    doc.set_xy(cal_x, date_y + 8)
    doc.cell(
        text="%d" % (day),
        align="C",
        w=cal_w,
        h=50,
        link=str(links["%04d-%02d" % (year, mon)]),
    )

    doc.set_font(FONT, "B", 26)
    doc.set_xy(cal_x, date_y)
    doc.cell(
        text=FULLDAYS[date.weekday()],
        w=cal_w,
        h=15,
        align="C",
        link=str(
            links["%04d" % (year)],
        ),
    )

    # add the todo blocks
    doc.set_draw_color(time_block_line_color)
    doc.set_line_width(time_block_line_width)
    doc.set_fill_color(240)
    doc.set_text_color(40)

    line_height = PAGE_HEIGTH / 30
    for i in range(1, 30):
        line_y = i * line_height + TOP_MARGIN
        if line_y > PAGE_HEIGTH - BOTTOM_MARGIN:
            break

        if line_y < cal_y + cal_h:
            line_x = cal_x - 8
        else:
            line_x = PAGE_WIDTH - RIGHT_MARGIN

        doc.line(LEFT_MARGIN, line_y, line_x, line_y)

    # add prepopulated entries if there are any
    if not (day_events := events.get(ymd)):
        return

    all_day = ""

    doc.set_font(FONT, "", 10)
    line_x = cal_x - 8

    for hms, evs in sorted(day_events.items()):
        for ev in evs:
            if hms == "00:00" and ev.duration == 0:
                all_day += ev.title + "\n"
                continue

    if all_day:
        doc.set_font(FONT, "B", 16)
        doc.set_xy(LEFT_MARGIN, TOP_MARGIN)
        doc.multi_cell(
            w=line_x - LEFT_MARGIN,
            h=line_height / 2,
            text=all_day,
            align="C",
        )


def add_year_page(
    doc: FPDF,
    year: int,
    links: dict[str, int],
    events: dict[str, dict[str, list[DailyEvent]]],
):
    """A full-page view on given year.

    The page contains 12 month overviews."""
    for mon in range(0, 12):
        xsize = 9 * 7
        ysize = 9 * 7
        __insert_month_overview(
            doc,
            year,
            mon + 1,
            links,
            events,
            highlighted_day=None,
            highlighted_holidays=True,
            size=8,
            x=(mon % 3) * xsize + LEFT_MARGIN,
            y=(mon // 3) * ysize + 20,
            display_year=False,
            ysize=8,
        )


def add_months_pages(
    doc: FPDF,
    year: int,
    links: dict[str, int],
    events: dict[str, dict[str, list[DailyEvent]]],
    *,
    time_block_line_width: int,
    time_block_line_color: int,
):
    """Add pages related to all months.

    For each month, the first page is a full-page overview of the
    month; Then, one page per day is added."""

    for mon in range(1, 12 + 1):
        # month overview page
        doc.add_page()
        doc.set_link(links["%04d-%02d" % (year, mon)])
        __insert_month_overview(
            doc,
            year,
            mon,
            links,
            events,
            highlighted_day=None,
            highlighted_holidays=True,
            size=(PAGE_WIDTH - LEFT_MARGIN) // 7,
            x=LEFT_MARGIN,
            y=0,
            day_font=12,
            border=True,
            full_page=True,
            ysize=36,
        )

        for day in range(1, 31 + 1):
            __add_day_page(
                doc,
                year,
                mon,
                day,
                links,
                events,
                time_block_line_width=time_block_line_width,
                time_block_line_color=time_block_line_color,
            )
