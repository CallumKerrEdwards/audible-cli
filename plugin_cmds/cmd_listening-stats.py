import asyncio
import json
import logging
import pathlib
from datetime import datetime

import audible
import click
from audible_cli.config import pass_session


logger = logging.getLogger("audible_cli.cmds.cmd_listening-stats")

current_year = datetime.now().year


def ms_to_hms(milliseconds):
    seconds = (int) (milliseconds / 1000) % 60
    minutes = (int) ((milliseconds / (1000*60)) % 60)
    hours   = (int) ((milliseconds / (1000*60*60)) % 24)
    return hours, minutes, seconds


async def _get_stats_year(client, year):
    stats_year = {}
    stats = await client.get(
        "stats/aggregates",
        monthly_listening_interval_duration="12",
        monthly_listening_interval_start_date=f"{year}-01",
        store="Audible"
    )
    #iterate over each month
    for stat in stats['aggregated_monthly_listening_stats']:
        stats_year[stat["interval_identifier"]] = ms_to_hms(stat["aggregated_sum"])
    return stats_year


async def _listening_stats(auth, output, signup_year):
    year_range = [y for y in range(signup_year, current_year+1)]

    async with audible.AsyncClient(auth=auth) as client:

        r = await asyncio.gather(
            *[_get_stats_year(client, y) for y in year_range]
        )

    aggreated_stats = {}
    for i in r:
        for k, v in i.items():
            aggreated_stats[k] = v

    aggreated_stats = json.dumps(aggreated_stats, indent=4)
    output.write_text(aggreated_stats)


@click.command("listening-stats")
@click.option(
    "--output", "-o",
    type=click.Path(path_type=pathlib.Path),
    default=pathlib.Path().cwd() / "listening-stats.json",
    show_default=True,
    help="output file"
)
@click.option(
    "--signup-year", "-s",
    type=click.IntRange(1997, current_year),
    default="2010",
    show_default=True,
    help="start year for collecting listening stats"
)
@pass_session
def cli(session, output, signup_year):
    """get and analyse listening statistics"""
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(
            _listening_stats(session.auth, output, signup_year)
        )
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
        