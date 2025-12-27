"""Generate calendar in PDF format."""

import argparse
import datetime
import locale
import logging
from collections import defaultdict
from typing import cast, DefaultDict, Dict, List, Tuple

from .events import DailyEvent
from .generate import (
    initialize_document,
    generate_links,
    add_year_page,
    add_months_pages,
)
from .holidays import collect_french_holidays

from fpdf import FPDF

LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.StreamHandler())
LOGGER.setLevel(logging.INFO)

locale.setlocale(locale.LC_ALL, "")
# propagate OS locale


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
    links_mapping = generate_links(doc, year)
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

    add_months_pages(
        doc,
        year,
        links_mapping,
        events,
        time_block_line_width=time_block_line_width,
        time_block_line_color=time_block_line_color,
    )

    output = args.get("output") or f"agenda-{year}.pdf"
    LOGGER.info(f"Writing {output}")
    doc.output(output)
