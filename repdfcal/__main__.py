"""Generate calendar in PDF format."""

import argparse
import datetime
import locale
import logging
from collections import defaultdict
from typing import cast, DefaultDict, Dict, List, Tuple

from .events import DailyEvent
from .holidays import collect_french_holidays

from fpdf import FPDF

LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.StreamHandler())
LOGGER.setLevel(logging.INFO)

FONT = "dejavu"

# close to a4 sizes in mm, but matching the remarkable 2
PAGE_WIDTH = 210
PAGE_HEIGTH = 280

# clear the remarkable tool bar
LEFT_MARGIN = 20
RIGHT_MARGIN = 20
TOP_MARGIN = 20
BOTTOM_MARGIN = 20

MONTH_COLOR: List[Tuple[int, int, int]] = [
    (-1, -1, -1),  # month 0
    (211, 211, 211),
    (128, 0, 128),
    (0, 128, 0),
    (155, 255, 100),
    (255, 192, 203),
    (0, 0, 255),
    (255, 0, 0),
    (255, 215, 0),
    (80, 200, 212),
    (255, 165, 0),
    (0, 0, 0),
    (178, 34, 34),
]

locale.setlocale(locale.LC_ALL, "")
# propagate OS locale

DAYS: List[str] = []
FULLDAYS: List[str] = []

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

MONTHS: List[str] = [
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


def insert_month_overview(
    doc: FPDF,
    year: int,
    mon: int,
    highlight: int,
    size: int,
    x: int,
    y: int,
    links_mapping: Dict[str, int],
    events: Dict[str, Dict[str, List[DailyEvent]]],
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
        link = links_mapping["%04d" % (year)]
    else:
        link = links_mapping["%04d-%02d" % (year, mon)]

    doc.set_xy(x, y)
    doc.cell(w=7 * size, h=1.5 * size, text=header, align="C", fill=True, link=link)

    y += int(size * 1.5)

    # draw the days of the week above the table
    doc.set_fill_color(180)
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
        link = links_mapping[ymd]

        if weekday == 0 and day != 1:
            week += 1

        day_x = x + weekday * size
        day_y = y + week * ysize

        if border:
            doc.rect(day_x, day_y, size, ysize)
        if day == highlight:
            doc.rect(day_x, day_y, size, ysize, style="F")

        doc.set_xy(day_x, day_y)
        doc.set_font(FONT, "", day_font)
        doc.cell(
            w=size,
            h=day_font / 2 + 1.5,
            text="%d" % (day),
            align="R",
            link=link,
            # fill = day == highlight,
            # border = border,
        )

        if not border:
            continue
        if not (day_events := events.get(ymd)):
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


def add_day_page(
    doc: FPDF,
    year: int,
    mon: int,
    day: int,
    links_mapping: Dict[str, int],
    events: Dict[str, Dict[str, List[DailyEvent]]],
    *,
    time_block_line_width: int,
    time_block_line_color: int,
):
    """A full-page view on the given day.

    It contains an overview for the corresponding month, see
    ``insert_month_overview()``."""
    try:
        date = datetime.date(year, mon, day)
    except Exception:
        return

    ymd = "%04d-%02d-%02d" % (year, mon, day)
    doc.add_page()
    doc.set_link(links_mapping[ymd])

    cal_size = 8
    date_y = 0
    cal_w = 7 * cal_size
    cal_h = 8 * cal_size
    cal_y = 50
    cal_x = PAGE_WIDTH - cal_w - 4

    insert_month_overview(
        doc,
        year,
        mon,
        day,
        cal_size,
        cal_x,
        cal_y,
        links_mapping,
        events,
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
        link=str(links_mapping["%04d-%02d" % (year, mon)]),
    )

    doc.set_font(FONT, "B", 26)
    doc.set_xy(cal_x, date_y)
    doc.cell(
        text=FULLDAYS[date.weekday()],
        w=cal_w,
        h=15,
        align="C",
        link=str(
            links_mapping["%04d" % (year)],
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


def generate_links(doc: FPDF) -> Dict[str, int]:
    """Create links for every day and month.

    Return a mapping from day or month ids to link numbers.

    As a side-effect, creates title page.
    """
    doc.add_page()

    links_mapping: Dict[str, int] = {}

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


def add_year_page(
    doc: FPDF,
    year: int,
    links: Dict[str, int],
    events: Dict[str, Dict[str, List[DailyEvent]]],
):
    """A full-page view on given year.

    The page contains 12 month overviews, see
    ``insert_month_overview()``."""
    for mon in range(0, 12):
        xsize = 9 * 7
        ysize = 9 * 7
        insert_month_overview(
            doc,
            year,
            mon + 1,
            -1,
            8,
            (mon % 3) * xsize + LEFT_MARGIN,
            (mon // 3) * ysize + 20,
            links,
            events,
            display_year=False,
            ysize=8,
        )


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
    )
    parser.add_argument("-o", "--output", help="output file", required=False)
    parser.add_argument(
        "-y",
        "--year",
        help="year to generate (default to current year)",
        required=False,
        type=int,
        default=datetime.datetime.now().year,
    )
    parser.add_argument(
        "-w",
        "--linewidth",
        help="width of time block lines",
        required=False,
        type=float,
        default=0.1,
    )
    parser.add_argument(
        "-c",
        "--linecolor",
        help="color of time block lines (higher is lighter)",
        required=False,
        type=float,
        default=200,
    )
    parser.add_argument(
        "--school-zone",
        help="zone for French school holidays (default to C)",
        required=False,
        type=str,
    )
    parser.add_argument(
        "--bank-holidays",
        help="zone for French bank holidays (default to Métropole)",
        required=False,
        type=str,
    )
    return parser


if __name__ == "__main__":
    parser = get_parser()
    args = vars(parser.parse_args())

    year = args["year"]

    LOGGER.info(f"Generation of calendar for {year}")

    doc = initialize_document(year)
    links_mapping = generate_links(doc)
    events: Dict[str, Dict[str, List[DailyEvent]]] = defaultdict(
        lambda: defaultdict(list)
    )
    if locale.getlocale()[0] == "fr_FR" and (
        args["school_zone"] or args["bank_holidays"]
    ):
        LOGGER.info("Collecting French holidays")
        collect_french_holidays(
            year,
            cast(DefaultDict[str, DefaultDict[str, List[DailyEvent]]], events),
            school_zone=args["school_zone"],
            bank_zone=args["bank_holidays"],
        )

    add_year_page(doc, year, links_mapping, events)

    time_block_line_width = args["linewidth"]
    time_block_line_color = args["linecolor"]

    for mon in range(1, 12 + 1):
        # month overview page
        doc.add_page()
        doc.set_link(links_mapping["%04d-%02d" % (year, mon)])

        insert_month_overview(
            doc,
            year,
            mon,
            -1,
            (PAGE_WIDTH - LEFT_MARGIN) // 7,
            LEFT_MARGIN,
            0,
            links_mapping,
            events,
            day_font=12,
            border=True,
            full_page=True,
            ysize=36,
        )

        for day in range(1, 31 + 1):
            add_day_page(
                doc,
                year,
                mon,
                day,
                links_mapping,
                events,
                time_block_line_width=time_block_line_width,
                time_block_line_color=time_block_line_color,
            )

    output = args.get("output") or f"agenda-{year}.pdf"
    LOGGER.info(f"Writing {output}")
    doc.output(output)
