"""Tarikh ingestion pipeline CLI.

Usage:
    python -m pipeline ingest                          # all sources
    python -m pipeline ingest --source "0310Tabari..." # one source
    python -m pipeline ingest --source "..." --force   # re-ingest
    python -m pipeline ingest --rules-only             # skip LLM (stage 1+2 only)
    python -m pipeline remove --source "..."           # remove source + events
    python -m pipeline status                          # progress report
"""

import argparse
import asyncio
import glob as globmod
import logging
import time
from pathlib import Path

from pipeline.extractors.rules import ah_to_ce, extract_rules
from pipeline.gazetteer import lookup as geo_lookup
from pipeline.normalize import generate_event_id, normalize_type
from pipeline.parsers.openiti import OpenITIParser
from pipeline.registry import SourceConfig, load_sources
from pipeline.seeder import (
    clear_source_events,
    ensure_source,
    get_pool,
    get_status,
    remove_source,
    seed_events,
)

log = logging.getLogger(__name__)


def _resolve_file(source: SourceConfig, base_dir: str = ".") -> str | None:
    """Find the source file via glob pattern."""
    pattern = f"{base_dir}/{source.repo}/{source.glob}"
    matches = globmod.glob(pattern, recursive=True)
    return sorted(matches)[0] if matches else None


def _get_parser(source: SourceConfig):
    """Instantiate parser for a source."""
    if source.parser == "openiti":
        return OpenITIParser(source_uri=source.uri, from_hijra=source.from_hijra)
    raise ValueError(f"Unknown parser: {source.parser}")


def _as_int(v):
    """Coerce LLM/rule values (often strings) to int for INTEGER columns."""
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _process_section(section, rules_result, llm_events=None):
    """Merge rule results + optional LLM results into final event dicts."""
    events = []

    if llm_events:
        for llm_ev in llm_events:
            event_type = normalize_type(llm_ev.get("event_type", rules_result.event_type))
            date_ah = _as_int(llm_ev.get("date_ah") or rules_result.date_ah)
            date_ce = _as_int(llm_ev.get("date_ce") or rules_result.date_ce) or ah_to_ce(date_ah)
            sort_key = date_ce
            title_en = llm_ev.get("title_en", "")

            # Geocode
            loc = llm_ev.get("location") or {}
            loc_lat = loc.get("lat")
            loc_lng = loc.get("lng")
            if not loc_lat and loc.get("name_ar"):
                coords = geo_lookup(loc["name_ar"])
                if coords:
                    loc_lat, loc_lng = coords

            event_id = generate_event_id(section.source_uri, date_ce, title_en)

            data = {
                "title_ar": llm_ev.get("title_ar", ""),
                "title_en": title_en,
                "summary_ar": llm_ev.get("summary_ar", ""),
                "summary_en": llm_ev.get("summary_en", ""),
                "people": llm_ev.get("people", []),
                "location": loc,
                "date_precision": llm_ev.get("date_precision", "year"),
                "section_id": section.section_id,
            }

            events.append(
                {
                    "id": event_id,
                    "event_type": event_type,
                    "importance": _as_int(llm_ev.get("importance")) or 3,
                    "sort_key": sort_key,
                    "date_ah": date_ah,
                    "date_ce": date_ce,
                    "loc_lat": loc_lat,
                    "loc_lng": loc_lng,
                    "data": data,
                }
            )
    else:
        # Rules-only mode: one event per section
        title_preview = " ".join(section.parent_headers) if section.parent_headers else section.arabic_text[:60]
        event_id = generate_event_id(section.source_uri, rules_result.date_ce, title_preview)
        data = {
            "title_ar": title_preview,
            "title_en": "",
            "summary_ar": section.arabic_text[:200],
            "summary_en": "",
            "people": [],
            "section_id": section.section_id,
        }
        events.append(
            {
                "id": event_id,
                "event_type": normalize_type(rules_result.event_type),
                "importance": 3,
                "sort_key": rules_result.sort_key,
                "date_ah": rules_result.date_ah,
                "date_ce": rules_result.date_ce,
                "loc_lat": None,
                "loc_lng": None,
                "data": data,
            }
        )

    return events


async def _ingest_source(source, base_dir, rules_only, max_sections, pool, source_id, fresh):
    """Run full pipeline for one source, seeding incrementally per batch.

    Crash-safe: each batch is seeded (idempotent upsert) before its sections are
    marked done, so a resumed run re-does only unfinished batches. Returns count seeded.
    """
    filepath = _resolve_file(source, base_dir)
    if not filepath:
        log.error("File not found for %s (glob: %s)", source.uri, source.glob)
        return 0

    log.info("Parsing: %s", filepath)
    parser = _get_parser(source)
    sections = parser.parse(filepath, max_sections=max_sections)
    log.info("%d sections", len(sections))

    # Stage 1: Rules
    rules_results = [extract_rules(section) for section in sections]

    if rules_only:
        events = []
        for section, rules in zip(sections, rules_results, strict=True):
            events.extend(_process_section(section, rules))
        return await seed_events(pool, source_id, events)

    # Stage 3: LLM
    from pipeline.extractors.llm import ProgressTracker, call_llm, make_batches

    tracker = ProgressTracker(f".progress_{source.uri}.json")
    if fresh:
        tracker.reset()

    # Prepare items for LLM (skip sections already seeded in a prior run)
    items = []
    for i, (section, rules) in enumerate(zip(sections, rules_results, strict=True)):
        if tracker.is_done(section.section_id):
            continue
        items.append(
            {
                "section_id": section.section_id,
                "arabic_text": section.arabic_text,
                "parent_headers": section.parent_headers,
                "char_count": section.char_count,
                "date_ah": rules.date_ah,
                "event_type": rules.event_type,
                "_index": i,
            }
        )

    if not items:
        log.info("All sections already processed (resuming)")
        return 0

    batches = make_batches(items)
    log.info("%d LLM batches", len(batches))

    total = 0
    for bi, batch in enumerate(batches):
        log.info("Batch %d/%d (%d sections)...", bi + 1, len(batches), len(batch))
        llm_events = call_llm(batch, model_index=bi)

        # Distribute LLM events back to sections via the 1-based `section` field.
        # Out-of-range / missing section numbers fall back to the batch's first section.
        batch_events = []
        for llm_ev in llm_events:
            sec_no = _as_int(llm_ev.get("section")) or 1
            pos = min(max(sec_no, 1), len(batch)) - 1
            idx = batch[pos]["_index"]
            batch_events.extend(_process_section(sections[idx], rules_results[idx], [llm_ev]))

        # Seed BEFORE marking done so a crash never loses seeded work.
        total += await seed_events(pool, source_id, batch_events)
        tracker.mark_done([item["section_id"] for item in batch])
        log.info("→ %d events (seeded %d total)", len(llm_events), total)
        time.sleep(4)

    return total


async def cmd_ingest(args):
    sources = load_sources()
    if args.source:
        sources = [s for s in sources if args.source in s.uri]
        if not sources:
            log.warning("No source matching '%s'", args.source)
            return

    pool = await get_pool()
    try:
        for source in sources:
            log.info("Ingesting: %s", source.uri)
            source_id = await ensure_source(pool, source.uri, source.corpus, source.repo, source.meta)
            # Fresh run when forced or no prior progress exists; otherwise resume.
            fresh = args.force or not Path(f".progress_{source.uri}.json").exists()
            if fresh:
                await clear_source_events(pool, source_id)
            count = await _ingest_source(
                source, args.base_dir, args.rules_only, args.max_sections, pool, source_id, fresh
            )
            log.info("Seeded %d events", count)
    finally:
        await pool.close()


async def cmd_remove(args):
    if not args.source:
        log.error("--source required for remove")
        return
    pool = await get_pool()
    try:
        count = await remove_source(pool, args.source)
        log.info("Removed %d events for %s", count, args.source)
    finally:
        await pool.close()


async def cmd_status(args):
    pool = await get_pool()
    try:
        status = await get_status(pool)
        log.info("Total events: %d", status["total_events"])
        log.info("Sources:")
        for s in status["sources"]:
            log.info("  %s (%s): %d events", s["uri"], s["corpus"], s["event_count"])
        log.info("Type breakdown:")
        for t in status["type_breakdown"]:
            log.info("  %s (importance=%s): %s", t["event_type"], t["importance"], t["cnt"])
    finally:
        await pool.close()


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    parser = argparse.ArgumentParser(prog="pipeline", description="Tarikh ingestion pipeline")
    sub = parser.add_subparsers(dest="command")

    p_ingest = sub.add_parser("ingest")
    p_ingest.add_argument("--source", default=None)
    p_ingest.add_argument("--force", action="store_true")
    p_ingest.add_argument("--rules-only", action="store_true")
    p_ingest.add_argument("--max-sections", type=int, default=None)
    p_ingest.add_argument("--base-dir", default=".")

    p_remove = sub.add_parser("remove")
    p_remove.add_argument("--source", required=True)

    sub.add_parser("status")

    args = parser.parse_args()

    if args.command == "ingest":
        asyncio.run(cmd_ingest(args))
    elif args.command == "remove":
        asyncio.run(cmd_remove(args))
    elif args.command == "status":
        asyncio.run(cmd_status(args))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
