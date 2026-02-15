"""Run the full analysis pipeline on the GGS corpus and produce results.

Usage:
    uv run python scripts/run_full_analysis.py
"""

from __future__ import annotations

import json
import math
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rich.console import Console
from rich.table import Table

from ggs.analysis.features import (
    FEATURE_DIMENSIONS,
    compute_corpus_features,
)
from ggs.analysis.match import MatchRecord, run_matching
from ggs.lexicon.loader import load_lexicon

console = Console()

PROJECT_ROOT = Path(__file__).parent.parent
CORPUS_PATH = PROJECT_ROOT / "data" / "corpus" / "ggs_lines.jsonl"
CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"
RESULTS_DIR = PROJECT_ROOT / "data" / "derived"
LEXICON_DIR = PROJECT_ROOT / "lexicon"

# Gurmukhi numeral → int
_GNUM = {
    "੧": 1, "੨": 2, "੩": 3, "੪": 4, "੫": 5,
    "੬": 6, "੭": 7, "੮": 8, "੯": 9,
}

GURU_NAMES = {
    1: "Guru Nanak",
    2: "Guru Angad",
    3: "Guru Amar Das",
    4: "Guru Ram Das",
    5: "Guru Arjan",
    9: "Guru Tegh Bahadur",
}

_BHAGAT_HEADERS: list[tuple[str, str]] = [
    ("ਕਬੀਰ", "Kabir"),
    ("ਫਰੀਦ", "Farid"),
    ("ਨਾਮਦੇਵ", "Namdev"),
    ("ਰਵਿਦਾਸ", "Ravidas"),
    ("ਤ੍ਰਿਲੋਚਨ", "Trilochan"),
    ("ਬੇਣੀ", "Beni"),
    ("ਧੰਨਾ", "Dhanna"),
    ("ਜੈਦੇਵ", "Jaidev"),
    ("ਪੀਪਾ", "Pipa"),
    ("ਸੈਣ", "Sain"),
    ("ਪਰਮਾਨੰਦ", "Parmanand"),
    ("ਸੂਰਦਾਸ", "Surdas"),
    ("ਸੁੰਦਰ", "Sundar"),
    ("ਰਾਮਾਨੰਦ", "Ramanand"),
    ("ਭੀਖਨ", "Bhikhan"),
    ("ਸਧਨਾ", "Sadhna"),
]

_MAHALLA_PAT = re.compile(r"ਮਹਲਾ\s*([੧੨੩੪੫੬੭੮੯]|ਪਹਿਲਾ)")


def load_corpus() -> list[dict]:
    records: list[dict] = []
    with CORPUS_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            records.append(json.loads(line))
    return records


def load_config() -> dict:
    import yaml

    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def extract_authors(
    records: list[dict],
) -> dict[str, str]:
    """Extract author for each line based on header patterns.

    Returns mapping of line_uid -> author name.
    """
    uid_to_author: dict[str, str] = {}
    current_author = "Guru Nanak"  # Japji Sahib (angs 1-7)

    for rec in records:
        g = rec.get("gurmukhi", "")
        tokens = rec.get("tokens", [])

        # Check for mahalla header
        m = _MAHALLA_PAT.search(g)
        if m:
            num_str = m.group(1)
            if num_str == "ਪਹਿਲਾ":
                current_author = GURU_NAMES[1]
            elif num_str in _GNUM:
                mahalla = _GNUM[num_str]
                current_author = GURU_NAMES.get(
                    mahalla, f"Mahalla {mahalla}"
                )

        # Check for bhagat header patterns (short lines
        # with bhagat name + ਜੀਉ/ਜੀ/ਕੀ/ਕਾ)
        for gur_name, eng_name in _BHAGAT_HEADERS:
            if gur_name in g and len(tokens) < 12:
                header_markers = {"ਜੀਉ", "ਜੀ", "ਕੀ", "ਕਾ"}
                if header_markers & set(tokens):
                    current_author = eng_name
                    break

        uid_to_author[rec["line_uid"]] = current_author

    return uid_to_author


def main() -> None:
    t0 = time.monotonic()
    console.print("\n[bold cyan]" + "=" * 70 + "[/bold cyan]")
    console.print("[bold cyan]  GGS Full Analysis Pipeline[/bold cyan]")
    console.print("[bold cyan]" + "=" * 70 + "[/bold cyan]\n")

    # Load corpus
    console.print("[bold]Loading corpus...[/bold]")
    records = load_corpus()
    total_tokens = sum(len(r.get("tokens", [])) for r in records)
    total_angs = len(set(r["ang"] for r in records))
    console.print(
        f"  {len(records)} lines, {total_tokens} tokens, "
        f"{total_angs} angs\n"
    )

    # Load config
    config = load_config()

    # Load lexicon
    console.print("[bold]Loading lexicon...[/bold]")
    lexicon_paths = config.get("lexicon_paths", {})
    index = load_lexicon(lexicon_paths, base_dir=PROJECT_ROOT)
    console.print(
        f"  {index.entity_count} entities, "
        f"{index.alias_count} aliases\n"
    )

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # ===================================================================
    # Author Extraction
    # ===================================================================
    console.print("[bold]Extracting authors...[/bold]")
    uid_to_author = extract_authors(records)
    author_counts = Counter(uid_to_author.values())
    unique_authors = sorted(author_counts.keys())
    console.print(f"  {len(unique_authors)} authors identified\n")

    table = Table(title="Author Distribution")
    table.add_column("Author", style="cyan")
    table.add_column("Lines", justify="right")
    table.add_column("% Corpus", justify="right")
    for auth, cnt in author_counts.most_common():
        table.add_row(
            auth, str(cnt),
            f"{100 * cnt / len(records):.1f}%",
        )
    console.print(table)

    # ===================================================================
    # Phase 1: Matching
    # ===================================================================
    console.print("[bold magenta]" + "-" * 50 + "[/bold magenta]")
    console.print("[bold magenta]  Phase 1: Lexical Matching[/bold magenta]")
    console.print("[bold magenta]" + "-" * 50 + "[/bold magenta]\n")

    matches_path = RESULTS_DIR / "matches.jsonl"
    all_matches = run_matching(
        records, index, output_path=matches_path,
    )

    # Match statistics
    match_by_entity = Counter(m.entity_id for m in all_matches)
    match_by_confidence = Counter(m.confidence for m in all_matches)
    nested_count = sum(1 for m in all_matches if m.nested_in is not None)
    lines_with_matches = len(set(m.line_uid for m in all_matches))

    console.print(f"  Total matches: {len(all_matches)}")
    console.print(f"  Unique entities matched: {len(match_by_entity)}")
    console.print(
        f"  Lines with matches: {lines_with_matches}/{len(records)} "
        f"({100 * lines_with_matches / len(records):.1f}%)"
    )
    console.print(f"  Nested matches: {nested_count}")
    console.print(f"  Confidence: {dict(match_by_confidence)}\n")

    # Top entities table
    table = Table(title="Top 30 Matched Entities")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Entity ID", style="cyan")
    table.add_column("Canonical Form", style="green")
    table.add_column("Register", style="yellow")
    table.add_column("Category")
    table.add_column("Tradition")
    table.add_column("Hits", justify="right", style="bold")
    for i, (eid, count) in enumerate(match_by_entity.most_common(30), 1):
        entity = index.entities.get(eid)
        if entity:
            table.add_row(
                str(i), eid, entity.canonical_form,
                entity.register or "-",
                entity.category or "-",
                entity.tradition or "-",
                str(count),
            )
        else:
            table.add_row(str(i), eid, "?", "-", "-", "-", str(count))
    console.print(table)

    # ===================================================================
    # Phase 2a: Feature Computation
    # ===================================================================
    console.print("\n[bold magenta]" + "-" * 50 + "[/bold magenta]")
    console.print("[bold magenta]  Phase 2a: Feature Computation[/bold magenta]")
    console.print("[bold magenta]" + "-" * 50 + "[/bold magenta]\n")

    features_path = RESULTS_DIR / "features.jsonl"
    feature_records = compute_corpus_features(
        records, all_matches, index, output_path=features_path,
    )

    # Feature dimension stats
    dim_stats: dict[str, dict] = {}
    for dim in FEATURE_DIMENSIONS:
        counts = [f["features"][dim]["count"] for f in feature_records]
        densities = [f["features"][dim]["density"] for f in feature_records]
        nonzero = sum(1 for c in counts if c > 0)
        total_hits = sum(counts)
        avg_density = sum(densities) / len(densities) if densities else 0
        max_density = max(densities) if densities else 0
        dim_stats[dim] = {
            "total_hits": total_hits,
            "lines_with_hits": nonzero,
            "pct_lines": round(100 * nonzero / len(feature_records), 2),
            "avg_density": round(avg_density, 6),
            "max_density": round(max_density, 4),
        }

    table = Table(title="Feature Dimensions Summary")
    table.add_column("Dimension", style="cyan")
    table.add_column("Total Hits", justify="right")
    table.add_column("Lines Hit", justify="right")
    table.add_column("% Lines", justify="right")
    table.add_column("Avg Density", justify="right")
    table.add_column("Max Density", justify="right")
    for dim, stats in dim_stats.items():
        table.add_row(
            dim,
            str(stats["total_hits"]),
            str(stats["lines_with_hits"]),
            f"{stats['pct_lines']}%",
            f"{stats['avg_density']:.6f}",
            f"{stats['max_density']:.4f}",
        )
    console.print(table)

    # ===================================================================
    # Phase 2b: Per-Ang Register Density
    # ===================================================================
    console.print("\n[bold magenta]" + "-" * 50 + "[/bold magenta]")
    console.print("[bold magenta]  Phase 2b: Register Density by Ang[/bold magenta]")
    console.print("[bold magenta]" + "-" * 50 + "[/bold magenta]\n")

    # Build line_uid -> ang map
    uid_to_ang = {r["line_uid"]: r["ang"] for r in records}

    # Group features by ang
    features_by_ang: dict[int, list] = defaultdict(list)
    for fr in feature_records:
        ang = uid_to_ang.get(fr["line_uid"])
        if ang is not None:
            features_by_ang[ang].append(fr)

    # Compute per-ang density
    ang_densities: dict[str, dict[int, float]] = {
        dim: {} for dim in FEATURE_DIMENSIONS
    }
    for ang in sorted(features_by_ang.keys()):
        ang_features = features_by_ang[ang]
        for dim in FEATURE_DIMENSIONS:
            total_count = sum(
                f["features"][dim]["count"] for f in ang_features
            )
            total_tokens = sum(f["token_count"] for f in ang_features)
            density = total_count / total_tokens if total_tokens > 0 else 0
            ang_densities[dim][ang] = density

    # Peak angs per dimension
    table = Table(title="Peak Register Density by Ang (top 3 per dimension)")
    table.add_column("Dimension", style="cyan")
    table.add_column("Ang", justify="right")
    table.add_column("Density", justify="right")
    for dim in FEATURE_DIMENSIONS:
        if not ang_densities[dim]:
            continue
        sorted_angs = sorted(
            ang_densities[dim].items(), key=lambda x: x[1], reverse=True,
        )
        for ang, density in sorted_angs[:3]:
            if density > 0:
                table.add_row(dim, str(ang), f"{density:.4f}")
    console.print(table)

    # ===================================================================
    # Phase 2c: Co-occurrence Analysis
    # ===================================================================
    console.print("\n[bold magenta]" + "-" * 50 + "[/bold magenta]")
    console.print(
        "[bold magenta]  Phase 2c: Co-occurrence (Ang-Level)"
        "[/bold magenta]"
    )
    console.print("[bold magenta]" + "-" * 50 + "[/bold magenta]\n")

    # Build line -> ang mapping for co-occurrence units
    line_to_ang_co = {r["line_uid"]: r["ang"] for r in records}

    # Group matches by ang (as co-occurrence unit)
    matches_by_ang: dict[int, set[str]] = defaultdict(set)
    for m in all_matches:
        if m.nested_in is not None:
            continue
        ang = line_to_ang_co.get(m.line_uid)
        if ang is not None:
            matches_by_ang[ang].add(m.entity_id)

    total_shabads = len(matches_by_ang)
    entity_freq: Counter = Counter()
    pair_freq: Counter = Counter()

    for _ang_id, entities in matches_by_ang.items():
        for eid in entities:
            entity_freq[eid] += 1
        elist = sorted(entities)
        for i in range(len(elist)):
            for j in range(i + 1, len(elist)):
                pair_freq[(elist[i], elist[j])] += 1

    # PMI
    pmi_scores: list[tuple[str, str, float, int]] = []
    for (e1, e2), count in pair_freq.items():
        if count < 5:
            continue
        p_e1 = entity_freq[e1] / total_shabads
        p_e2 = entity_freq[e2] / total_shabads
        p_joint = count / total_shabads
        if p_e1 > 0 and p_e2 > 0 and p_joint > 0:
            pmi = math.log2(p_joint / (p_e1 * p_e2))
            pmi_scores.append((e1, e2, pmi, count))

    pmi_scores.sort(key=lambda x: x[2], reverse=True)

    console.print(f"  Angs analyzed (as co-occurrence units): {total_shabads}")
    console.print(f"  Entity pairs with count >= 5: {len(pmi_scores)}\n")

    table = Table(title="Top 20 Entity Pairs by PMI")
    table.add_column("Entity 1", style="cyan")
    table.add_column("Entity 2", style="cyan")
    table.add_column("PMI", justify="right")
    table.add_column("Co-occur Count", justify="right")
    for e1, e2, pmi, count in pmi_scores[:20]:
        table.add_row(e1, e2, f"{pmi:.3f}", str(count))
    console.print(table)

    table = Table(title="Top 20 Entity Pairs by Frequency")
    table.add_column("Entity 1", style="cyan")
    table.add_column("Entity 2", style="cyan")
    table.add_column("Co-occur Count", justify="right")
    for (e1, e2), count in pair_freq.most_common(20):
        table.add_row(e1, e2, str(count))
    console.print(table)

    # ===================================================================
    # Phase 3: Tagging
    # ===================================================================
    console.print("\n[bold magenta]" + "-" * 50 + "[/bold magenta]")
    console.print("[bold magenta]  Phase 3: Interpretive Tagging[/bold magenta]")
    console.print("[bold magenta]" + "-" * 50 + "[/bold magenta]\n")

    tag_counts: Counter = Counter()
    secondary_tags: Counter = Counter()
    tagged_lines: list[dict] = []

    for fr in feature_records:
        nirgun = fr["features"]["nirgun"]["count"]
        sagun = fr["features"]["sagun_narrative"]["count"]
        ritual = fr["features"]["ritual"]["count"]
        cleric = fr["features"]["cleric"]["count"]
        perso = fr["features"]["perso_arabic"]["count"]
        sanskrit = fr["features"]["sanskritic"]["count"]

        primary = "unmarked"
        if nirgun > 0 and sagun > 0:
            primary = "mixed_nirgun_sagun"
        elif nirgun > 0:
            primary = "nirgun_leaning"
        elif sagun > 0:
            primary = "sagun_narrative"
        elif ritual > 0 and cleric > 0:
            primary = "critique_both"
        elif ritual > 0:
            primary = "ritual_reference"
        elif cleric > 0:
            primary = "cleric_reference"
        elif perso > 0 and sanskrit > 0:
            primary = "mixed_register"
        elif perso > 0:
            primary = "perso_arabic_register"
        elif sanskrit > 0:
            primary = "sanskritic_register"

        tag_counts[primary] += 1

        if ritual > 0:
            secondary_tags["has_ritual"] += 1
        if cleric > 0:
            secondary_tags["has_cleric"] += 1
        if perso > 0:
            secondary_tags["has_perso_arabic"] += 1
        if sanskrit > 0:
            secondary_tags["has_sanskritic"] += 1
        if nirgun > 0:
            secondary_tags["has_nirgun"] += 1
        if sagun > 0:
            secondary_tags["has_sagun_narrative"] += 1

        tagged_lines.append({
            "line_uid": fr["line_uid"],
            "primary_tag": primary,
            "features": {
                d: fr["features"][d]["count"]
                for d in FEATURE_DIMENSIONS
            },
        })

    table = Table(title="Primary Tag Distribution")
    table.add_column("Tag", style="cyan")
    table.add_column("Lines", justify="right")
    table.add_column("% Corpus", justify="right")
    for tag, count in tag_counts.most_common():
        pct = round(100 * count / len(feature_records), 2)
        table.add_row(tag, str(count), f"{pct}%")
    console.print(table)

    table = Table(title="Feature Presence (secondary markers)")
    table.add_column("Marker", style="cyan")
    table.add_column("Lines", justify="right")
    table.add_column("% Corpus", justify="right")
    for tag, count in secondary_tags.most_common():
        pct = round(100 * count / len(feature_records), 2)
        table.add_row(tag, str(count), f"{pct}%")
    console.print(table)

    # ===================================================================
    # Cross-register mixing
    # ===================================================================
    console.print("\n[bold magenta]" + "-" * 50 + "[/bold magenta]")
    console.print("[bold magenta]  Cross-Register Mixing[/bold magenta]")
    console.print("[bold magenta]" + "-" * 50 + "[/bold magenta]\n")

    both = perso_only = sanskrit_only = 0
    for fr in feature_records:
        has_perso = fr["features"]["perso_arabic"]["count"] > 0
        has_sanskrit = fr["features"]["sanskritic"]["count"] > 0
        if has_perso and has_sanskrit:
            both += 1
        elif has_perso:
            perso_only += 1
        elif has_sanskrit:
            sanskrit_only += 1

    total_reg = perso_only + sanskrit_only + both
    console.print(f"  Perso-Arabic only:   {perso_only}")
    console.print(f"  Sanskritic only:     {sanskrit_only}")
    console.print(f"  Both registers:      {both}")
    console.print(
        f"  Mixing rate: {both}/{total_reg} "
        f"({100 * both / max(1, total_reg):.1f}%)\n"
    )

    # Nirgun + Sagun overlap
    nirgun_only = sagun_only = nirgun_sagun_both = 0
    for fr in feature_records:
        has_nirgun = fr["features"]["nirgun"]["count"] > 0
        has_sagun = fr["features"]["sagun_narrative"]["count"] > 0
        if has_nirgun and has_sagun:
            nirgun_sagun_both += 1
        elif has_nirgun:
            nirgun_only += 1
        elif has_sagun:
            sagun_only += 1

    console.print(f"  Nirgun only:         {nirgun_only}")
    console.print(f"  Sagun narrative only: {sagun_only}")
    console.print(f"  Both nirgun+sagun:   {nirgun_sagun_both}")

    # ===================================================================
    # Phase 4: Per-Author Analysis
    # ===================================================================
    console.print("\n[bold magenta]" + "-" * 50 + "[/bold magenta]")
    console.print(
        "[bold magenta]  Phase 4: Per-Author Analysis"
        "[/bold magenta]"
    )
    console.print("[bold magenta]" + "-" * 50 + "[/bold magenta]\n")

    # Group matches and features by author
    matches_by_line: dict[str, list[MatchRecord]] = defaultdict(
        list,
    )
    for m in all_matches:
        if m.nested_in is None:
            matches_by_line[m.line_uid].append(m)

    author_entity_freq: dict[str, Counter] = defaultdict(Counter)
    author_dim_lines: dict[str, dict[str, int]] = defaultdict(
        lambda: {d: 0 for d in FEATURE_DIMENSIONS},
    )
    author_line_counts: Counter = Counter()

    for fr in feature_records:
        uid = fr["line_uid"]
        author = uid_to_author.get(uid, "Unknown")
        author_line_counts[author] += 1

        for m in matches_by_line.get(uid, []):
            author_entity_freq[author][m.entity_id] += 1

        for dim in FEATURE_DIMENSIONS:
            if fr["features"][dim]["count"] > 0:
                author_dim_lines[author][dim] += 1

    # Per-author register density table
    table = Table(
        title="Per-Author Register Profile (% of author's lines)",
    )
    table.add_column("Author", style="cyan")
    table.add_column("Lines", justify="right")
    for dim in FEATURE_DIMENSIONS:
        table.add_column(dim[:8], justify="right")
    for auth, cnt in author_counts.most_common():
        row = [auth, str(cnt)]
        for dim in FEATURE_DIMENSIONS:
            n = author_dim_lines[auth][dim]
            pct = 100 * n / cnt if cnt > 0 else 0
            row.append(f"{pct:.1f}%")
        table.add_row(*row)
    console.print(table)

    # Per-author top entities
    author_profiles: dict[str, dict] = {}
    for auth in unique_authors:
        top = author_entity_freq[auth].most_common(10)
        author_profiles[auth] = {
            "lines": author_line_counts[auth],
            "top_entities": [
                {"entity_id": e, "count": c} for e, c in top
            ],
            "register_pct": {
                dim: round(
                    100 * author_dim_lines[auth][dim]
                    / max(1, author_line_counts[auth]),
                    2,
                )
                for dim in FEATURE_DIMENSIONS
            },
        }

    # ===================================================================
    # Phase 5: Semantic Analysis
    # ===================================================================
    console.print("\n[bold magenta]" + "-" * 50 + "[/bold magenta]")
    console.print(
        "[bold magenta]  Phase 5: Semantic Analysis"
        "[/bold magenta]"
    )
    console.print("[bold magenta]" + "-" * 50 + "[/bold magenta]\n")

    # 5a: RAM semantic behavior — what co-occurs with RAM
    # on the same LINE?
    ram_cooccur: Counter = Counter()
    ram_line_count = 0
    for _uid, line_matches in matches_by_line.items():
        eids = {m.entity_id for m in line_matches}
        if "RAM" in eids:
            ram_line_count += 1
            for e in eids:
                if e != "RAM":
                    ram_cooccur[e] += 1

    ram_nirgun = sum(
        c for e, c in ram_cooccur.items()
        if e in {
            "NIRANKAR", "AKAL", "ALAKH", "AGAM", "NIRANJAN",
            "NIRBHAU", "NIRVAIR", "AJOONI", "NIRAGUN", "AGOCHAR",
        }
    )
    ram_sagun = sum(
        c for e, c in ram_cooccur.items()
        if e in {
            "RAMCHANDRA", "SITA", "DASRATH", "LACHMAN", "RAVAN",
            "KRISHNA", "SHIV", "BRAHMA",
        }
    )
    console.print(f"  RAM appears on {ram_line_count} lines")
    console.print(
        f"  RAM + nirgun marker: {ram_nirgun} co-occurrences"
    )
    console.print(
        f"  RAM + sagun narrative: {ram_sagun} co-occurrences"
    )
    console.print(
        f"  Top RAM co-occurrences: "
        f"{ram_cooccur.most_common(8)}\n"
    )

    # 5b: ALLAH context — what appears on the same line?
    allah_cooccur: Counter = Counter()
    allah_line_count = 0
    allah_with_indic = 0
    for _uid, line_matches in matches_by_line.items():
        eids = {m.entity_id for m in line_matches}
        if "ALLAH" in eids:
            allah_line_count += 1
            indic_entities = {
                "HARI", "RAM", "GOBIND", "PRABH", "BRAHM",
                "NARAYANA", "BISN", "THAKUR",
            }
            if eids & indic_entities:
                allah_with_indic += 1
            for e in eids:
                if e != "ALLAH":
                    allah_cooccur[e] += 1

    console.print(f"  ALLAH appears on {allah_line_count} lines")
    if allah_line_count > 0:
        console.print(
            f"  ALLAH + Indic divine name: "
            f"{allah_with_indic} lines "
            f"({100 * allah_with_indic / allah_line_count:.0f}%)"
        )
    console.print(
        f"  Top ALLAH co-occurrences: "
        f"{allah_cooccur.most_common(8)}\n"
    )

    # 5c: Cross-tradition lines (Hindu + Muslim identity markers)
    cross_trad_lines = 0
    identity_lines = 0
    for fr in feature_records:
        uid = fr["line_uid"]
        eids = {
            m.entity_id for m in matches_by_line.get(uid, [])
        }
        has_indic_id = bool(eids & {"HINDU"})
        has_islamic_id = bool(
            eids & {"MUSALMAN", "TURK"}
        )
        if has_indic_id or has_islamic_id:
            identity_lines += 1
        if has_indic_id and has_islamic_id:
            cross_trad_lines += 1

    console.print(
        f"  Lines with identity markers: {identity_lines}"
    )
    console.print(
        f"  Cross-tradition lines (Hindu+Muslim): "
        f"{cross_trad_lines}"
    )

    # ===================================================================
    # Phase 6: Composite Indices
    # ===================================================================
    console.print("\n[bold magenta]" + "-" * 50 + "[/bold magenta]")
    console.print(
        "[bold magenta]  Phase 6: Composite Indices"
        "[/bold magenta]"
    )
    console.print("[bold magenta]" + "-" * 50 + "[/bold magenta]\n")

    # 6a: Stoic-Bhakti-Advaita triangle per author
    console.print("[bold]Stoic-Bhakti-Advaita Triangle:[/bold]")
    table = Table(
        title=(
            "Per-Author Stoic-Bhakti-Advaita Profile "
            "(% of author's lines)"
        ),
    )
    table.add_column("Author", style="cyan")
    table.add_column("Lines", justify="right")
    table.add_column("Ethical", justify="right", style="yellow")
    table.add_column("Devotion", justify="right", style="green")
    table.add_column("Nirgun", justify="right", style="magenta")
    table.add_column("Oneness", justify="right", style="blue")
    for auth, cnt in author_counts.most_common():
        pct_e = author_dim_lines[auth]["ethical"]
        pct_d = author_dim_lines[auth]["devotional"]
        pct_n = author_dim_lines[auth]["nirgun"]
        pct_o = author_dim_lines[auth]["oneness"]
        table.add_row(
            auth, str(cnt),
            f"{100 * pct_e / cnt:.1f}%",
            f"{100 * pct_d / cnt:.1f}%",
            f"{100 * pct_n / cnt:.1f}%",
            f"{100 * pct_o / cnt:.1f}%",
        )
    console.print(table)

    # 6b: Civilizational Density Index
    sanatan_entities = {
        "HARI", "RAM", "GOBIND", "PRABH", "THAKUR",
        "NARAYANA", "BISN", "BRAHM", "ATMA", "MAYA",
        "KRISHNA", "RAMCHANDRA", "SHIV", "BRAHMA",
        "VED", "PURAN", "SHASTAR",
    }
    islamic_entities = {
        "ALLAH", "KHUDA", "RABB", "MAULA",
        "RAHMAN", "RAHIM", "NOOR",
        "QURAN", "KITAB", "NABI", "PAIGAMBAR",
        "NAMAZ", "ROZA", "HAJI", "MAKKA", "MASJID",
        "QAZI", "MULLAH", "FAQIR",
    }

    sanatan_total = sum(
        match_by_entity.get(e, 0) for e in sanatan_entities
    )
    islamic_total = sum(
        match_by_entity.get(e, 0) for e in islamic_entities
    )
    console.print(
        f"\n  Sanatan marker total: {sanatan_total}"
    )
    console.print(f"  Islamic marker total: {islamic_total}")
    if islamic_total > 0:
        console.print(
            f"  Ratio: {sanatan_total / islamic_total:.1f}:1"
        )

    # ===================================================================
    # Save all results
    # ===================================================================
    console.print("\n[bold]Saving results...[/bold]")

    results = {
        "corpus": {
            "total_lines": len(records),
            "total_tokens": total_tokens,
            "total_angs": total_angs,
            "total_authors": len(unique_authors),
            "author_distribution": {
                a: c for a, c in author_counts.most_common()
            },
        },
        "matching": {
            "total_matches": len(all_matches),
            "unique_entities": len(match_by_entity),
            "lines_with_matches": lines_with_matches,
            "lines_with_matches_pct": round(
                100 * lines_with_matches / len(records), 2,
            ),
            "nested_matches": nested_count,
            "confidence_distribution": dict(match_by_confidence),
            "top_entities": [
                {
                    "entity_id": eid,
                    "canonical_form": (
                        index.entities[eid].canonical_form
                        if eid in index.entities else "?"
                    ),
                    "count": c,
                }
                for eid, c in match_by_entity.most_common(50)
            ],
        },
        "features": {
            dim: dim_stats[dim] for dim in FEATURE_DIMENSIONS
        },
        "tagging": {
            "primary_distribution": dict(tag_counts),
            "secondary_markers": dict(secondary_tags),
        },
        "registers": {
            "perso_arabic_only": perso_only,
            "sanskritic_only": sanskrit_only,
            "both_registers": both,
            "mixing_rate_pct": round(
                100 * both / max(1, total_reg), 2,
            ),
        },
        "nirgun_sagun": {
            "nirgun_only": nirgun_only,
            "sagun_only": sagun_only,
            "both": nirgun_sagun_both,
        },
        "cooccurrence": {
            "total_cooccurrence_units": total_shabads,
            "pairs_with_min_5": len(pmi_scores),
            "top_pmi": [
                {
                    "e1": e1, "e2": e2,
                    "pmi": round(pmi, 3), "count": c,
                }
                for e1, e2, pmi, c in pmi_scores[:30]
            ],
            "top_frequency": [
                {"e1": e1, "e2": e2, "count": c}
                for (e1, e2), c in pair_freq.most_common(30)
            ],
        },
        "author_profiles": author_profiles,
        "semantic": {
            "ram": {
                "line_count": ram_line_count,
                "nirgun_cooccur": ram_nirgun,
                "sagun_cooccur": ram_sagun,
                "top_cooccur": [
                    {"entity": e, "count": c}
                    for e, c in ram_cooccur.most_common(20)
                ],
            },
            "allah": {
                "line_count": allah_line_count,
                "with_indic_divine": allah_with_indic,
                "top_cooccur": [
                    {"entity": e, "count": c}
                    for e, c in allah_cooccur.most_common(20)
                ],
            },
            "cross_tradition_lines": cross_trad_lines,
            "identity_lines": identity_lines,
        },
        "civilizational": {
            "sanatan_total": sanatan_total,
            "islamic_total": islamic_total,
            "ratio": (
                round(sanatan_total / islamic_total, 1)
                if islamic_total > 0 else None
            ),
        },
    }

    results_path = RESULTS_DIR / "analysis_results.json"
    with results_path.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
        f.write("\n")
    console.print(f"  {results_path}")

    # Save tags
    tags_path = RESULTS_DIR / "tags.jsonl"
    with tags_path.open("w", encoding="utf-8") as f:
        for tl in tagged_lines:
            f.write(json.dumps(tl, ensure_ascii=False) + "\n")
    console.print(f"  {tags_path}")

    # Save per-ang density
    density_path = RESULTS_DIR / "ang_densities.json"
    density_export = {
        dim: {str(ang): round(d, 6) for ang, d in densities.items()}
        for dim, densities in ang_densities.items()
    }
    with density_path.open("w", encoding="utf-8") as f:
        json.dump(density_export, f, indent=2, ensure_ascii=False)
        f.write("\n")
    console.print(f"  {density_path}")

    elapsed = time.monotonic() - t0
    console.print(
        f"\n[bold green]Complete in {elapsed:.1f}s[/bold green]\n"
    )


if __name__ == "__main__":
    main()
