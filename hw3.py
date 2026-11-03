#!/usr/bin/env python3
"""FTEC5660 HW3 student starter: an agent that applies 3 of Fisher's 15 points using tools."""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import sqlite3
import threading
import zlib
from pathlib import Path
from typing import Any


MODEL_NAME = "deepseek-v4-flash"
INTERVIEW_LIMIT = 10
MAX_SQL_ROWS = 50

# Philip Fisher, "Common Stocks and Uncommon Profits", Part One, Chapter 3.
# For every point, PASS means the company looks good on it. You choose 3
# points and decide yourself what PASS means for each of them.
FISHER_POINTS = {
    1: "Does the company have products or services with sufficient market potential to make possible a sizable increase in sales for at least several years?",
    2: "Does the management have a determination to continue to develop products or processes that will still further increase total sales potentials when the growth potentials of currently attractive product lines have largely been exploited?",
    3: "How effective are the company's research and development efforts in relation to its size?",
    4: "Does the company have an above-average sales organization?",
    5: "Does the company have a worthwhile profit margin?",
    6: "What is the company doing to maintain or improve profit margins?",
    7: "Does the company have outstanding labor and personnel relations?",
    8: "Does the company have outstanding executive relations?",
    9: "Does the company have depth to its management?",
    10: "How good are the company's cost analysis and accounting controls?",
    11: "Are there other aspects of the business, somewhat peculiar to the industry involved, which will give the investor important clues as to how outstanding the company may be in relation to its competition?",
    12: "Does the company have a short-range or long-range outlook in regard to profits?",
    13: "In the foreseeable future will the growth of the company require sufficient equity financing so that the larger number of shares then outstanding will largely cancel the existing stockholders' benefit from this anticipated growth?",
    14: "Does the management talk freely to investors about its affairs when things are going well but 'clam up' when troubles and disappointments occur?",
    15: "Does the company have a management of unquestionable integrity?",
}
VERDICTS = ("PASS", "FAIL")


def load_env_file(path: Path = Path(".env")) -> None:
    """Load the simple KEY=VALUE entries used by this homework."""
    if not path.is_file():
        return
    import os

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


# ---------------------------------------------------------------------------
# Student implementation: a Fisher agent for points 1, 2 and 5.
#
# Design (the README report describes it in full):
#   * routing: every chosen point is routed to the source that can answer it.
#     Points 1, 2 and 5 are all database points, so evidence comes from the
#     sql_query tool only; no interviews are spent.
#   * tool use: every sum, ratio and comparison is computed in SQL or Python,
#     never by the model.
#   * prompt chaining: the model turns the computed evidence into a written
#     summary, and a second model call reflects on the draft and fixes it if
#     a verdict or number is misstated. Verdicts themselves never come from
#     the model.
#   * parallelism and isolation: companies are analysed concurrently and one
#     company's failure cannot affect the others.
# ---------------------------------------------------------------------------

# PASS rules, written down so the prompt, the code and the README cannot drift.
POINT_RULES = {
    1: "PASS when the company's revenue growth over the last two full fiscal "
       "years is at least the industry median 2-year revenue growth "
       "(industry_medians.revenue_growth_2y_pct); FAIL when it is below.",
    2: "PASS when products launched since the start of the order history "
       "(about the last three years) make up a share of revenue since the "
       "start of the last full fiscal year that is at least the industry "
       "median new-product share (industry_medians.new_product_share_pct); "
       "FAIL when it is below.",
    5: "PASS when the operating margin of the last full fiscal year, "
       "(revenue - cost of sales - selling and admin - R&D) / revenue, is at "
       "least the industry median operating margin "
       "(industry_medians.operating_margin_pct); FAIL when it is below.",
}

MAX_PARALLEL_COMPANIES = 5

SUMMARY_PROMPT = """\
You are an investment analyst applying Philip Fisher's "fifteen points to look \
for in a common stock" (Common Stocks and Uncommon Profits). The evidence \
below was gathered from the company's database and the verdicts were computed \
from it with fixed rules; they are final and must not be changed.

{evidence}

Write a short analyst summary (2 or 3 sentences) that explains the verdicts \
in plain English, quoting the key figures. Do not output JSON, do not repeat \
the questions, and do not contradict the verdicts."""

REFLECTION_PROMPT = """\
Below is the evidence for a Fisher analysis of a company and a draft summary \
of it.

{evidence}

Draft summary:
\"\"\"{draft}\"\"\"

Check the draft against the evidence: every PASS/FAIL verdict and every \
figure must match. If anything is misstated, rewrite the summary correctly; \
otherwise return the draft unchanged. Return only the summary text (2 or 3 \
sentences, no JSON, no commentary)."""


def _rows(text: str) -> list[dict[str, str]]:
    """Parse the pipe-separated output of the sql_query tool into dicts."""
    lines = [line for line in str(text).splitlines() if line.strip()]
    if not lines:
        return []
    header = [cell.strip() for cell in lines[0].split("|")]
    rows = []
    for line in lines[1:]:
        if line.startswith("...") or line.startswith("(no rows"):
            continue
        rows.append(dict(zip(header, (cell.strip() for cell in line.split("|")))))
    return rows


def _num(value: Any) -> float:
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return 0.0


def _message_text(message: Any) -> str:
    """Return the text of a LangChain message (content may be str or blocks)."""
    content = getattr(message, "content", message)
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = [b.get("text", "") if isinstance(b, dict) else str(b) for b in content]
        return "".join(parts).strip()
    return str(content).strip()


def _gather_metrics(tools: list[Any]) -> dict[str, Any]:
    """Collect every figure the rules need, through the sql_query tool only."""
    sql = next(tool for tool in tools if tool.name == "sql_query")

    def query(statement: str) -> list[dict[str, str]]:
        return _rows(sql.invoke({"query": statement}))

    medians = query(
        "SELECT c.industry AS industry, "
        "m.revenue_growth_2y_pct AS med_growth, "
        "m.new_product_share_pct AS med_new_share, "
        "m.operating_margin_pct AS med_margin "
        "FROM company c JOIN industry_medians m ON m.industry = c.industry"
    )[0]
    span = query("SELECT MIN(order_date) AS dmin, MAX(order_date) AS dmax FROM orders")[0]
    revenue = {
        row["yr"]: _num(row["rev"])
        for row in query(
            "SELECT substr(order_date, 1, 4) AS yr, SUM(amount) AS rev "
            "FROM orders GROUP BY yr"
        )
    }

    first_year = int(str(span["dmin"])[:4])
    # The last full fiscal year: the latest order year if it reaches December,
    # otherwise the year before it.
    last_full_year = int(str(span["dmax"])[:4]) - (0 if str(span["dmax"])[5:7] == "12" else 1)
    window = max(last_full_year - first_year, 1)

    # Point 1: revenue growth over the window, normalised to a 2-year figure
    # so it stays comparable to industry_medians.revenue_growth_2y_pct.
    rev_first, rev_last = revenue[str(first_year)], revenue[str(last_full_year)]
    growth = (rev_last / rev_first - 1) * 100
    if window != 2:
        growth = ((1 + growth / 100) ** (2.0 / window) - 1) * 100

    # Point 2: revenue share of products launched since first_year, measured
    # on all revenue from the start of the last full fiscal year onward.
    share_row = query(
        "SELECT 100.0 * SUM(CASE WHEN p.launch_date >= "
        f"'{first_year}-01-01' THEN o.amount ELSE 0 END) / SUM(o.amount) AS share "
        "FROM orders o JOIN products p ON p.product = o.product "
        f"WHERE o.order_date >= '{last_full_year}-01-01'"
    )[0]

    # Point 5: operating margin of the last full fiscal year.
    costs = query(
        "SELECT SUM(cost_of_sales) AS cos, SUM(selling_admin) AS sa, "
        "SUM(research_development) AS rd FROM monthly_costs "
        f"WHERE month >= '{last_full_year}-01' AND month <= '{last_full_year}-12'"
    )[0]
    margin = (rev_last - _num(costs["cos"]) - _num(costs["sa"]) - _num(costs["rd"])) / rev_last * 100

    return {
        "industry": medians["industry"],
        "first_year": first_year,
        "last_full_year": last_full_year,
        "growth_2y_pct": growth,
        "med_growth_2y_pct": _num(medians["med_growth"]),
        "new_product_share_pct": _num(share_row["share"]),
        "med_new_product_share_pct": _num(medians["med_new_share"]),
        "operating_margin_pct": margin,
        "med_operating_margin_pct": _num(medians["med_margin"]),
        "revenue_last_musd": rev_last / 1000,
    }


def _apply_rules(metrics: dict[str, Any]) -> dict[int, str]:
    """The PASS/FAIL rules for CHOSEN_POINTS, computed in Python only."""
    return {
        1: "PASS" if metrics["growth_2y_pct"] >= metrics["med_growth_2y_pct"] else "FAIL",
        2: "PASS" if metrics["new_product_share_pct"] >= metrics["med_new_product_share_pct"] else "FAIL",
        5: "PASS" if metrics["operating_margin_pct"] >= metrics["med_operating_margin_pct"] else "FAIL",
    }


def _evidence_text(name: str, metrics: dict[str, Any], verdicts: dict[int, str]) -> str:
    """Render the computed metrics as evidence for the prompt and fallback."""
    return (
        f"Company: {name.replace('_', ' ').title()} (industry: {metrics['industry']}).\n"
        f"Point 1 (market potential for sales growth): revenue grew "
        f"{metrics['growth_2y_pct']:.1f}% over the two full fiscal years "
        f"{metrics['first_year']}-{metrics['last_full_year']}; the industry median "
        f"2-year growth is {metrics['med_growth_2y_pct']:.1f}%. Verdict: {verdicts[1]}.\n"
        f"Point 2 (new products as current lines mature): products launched since "
        f"{metrics['first_year']} account for {metrics['new_product_share_pct']:.1f}% "
        f"of revenue since the start of {metrics['last_full_year']}; the industry "
        f"median new-product share is {metrics['med_new_product_share_pct']:.1f}%. "
        f"Verdict: {verdicts[2]}.\n"
        f"Point 5 (worthwhile profit margin): the operating margin of "
        f"{metrics['last_full_year']} is {metrics['operating_margin_pct']:.1f}% "
        f"(revenue US${metrics['revenue_last_musd']:.0f}m); the industry median is "
        f"{metrics['med_operating_margin_pct']:.1f}%. Verdict: {verdicts[5]}."
    )


def _analyze_company(model: Any, name: str, tools: list[Any]) -> dict[str, Any]:
    """Full pipeline for one company: gather, apply rules, summarise."""
    metrics = _gather_metrics(tools)
    verdicts = _apply_rules(metrics)
    evidence = _evidence_text(name, metrics, verdicts)

    draft = None
    try:
        draft = _message_text(model.invoke(SUMMARY_PROMPT.format(evidence=evidence)))
        summary = _message_text(
            model.invoke(REFLECTION_PROMPT.format(evidence=evidence, draft=draft))
        )
    except Exception:
        summary = None
    if not summary:
        # No API call needed for the verdicts: fall back to the bare evidence.
        summary = draft or evidence

    return {"points": verdicts, "summary": summary}


# Choose any 3 of the 15 points, e.g. CHOSEN_POINTS = [1, 7, 15]. Your agent
# gives a PASS or FAIL verdict on these 3 points only, with your own rule for each.
CHOSEN_POINTS: list[int] = [1, 2, 5]


def build_agent() -> Any:
    """Create and return your model or agent once.

    Suggested imports:
        from langchain_deepseek import ChatDeepSeek
        from langchain.agents import create_agent

    Use the DeepSeek model named by ``MODEL_NAME``. The API key is loaded
    from .env. Each company has its own tools (see ``analyze_companies``), so
    you will probably create one tool-calling agent per company there.
    """
    from langchain_deepseek import ChatDeepSeek

    return ChatDeepSeek(model=MODEL_NAME, temperature=0, max_retries=2)


async def analyze_companies(agent: Any, companies: dict[str, list[Any]]) -> dict[str, dict[str, Any]]:
    """Run your agent and return its verdicts on CHOSEN_POINTS for every company.

    ``companies`` maps each company folder name to its four LangChain tools:

        list_documents()             names and dates of the company's documents
        read_document(name)          the text of one document
        sql_query(query)             one read-only SQLite query on company.db
        interview(role, topic)       one interview answer (INTERVIEW_LIMIT per company)

    Give the tools to a tool-calling agent, e.g.
    ``create_agent(model, tools=companies[name], system_prompt=...)``, or call
    them yourself with ``tool.invoke({...})``. The README explains the
    documents, the database tables and the interview roles and topics.

    Return one dictionary per company folder name, e.g. with
    CHOSEN_POINTS = [1, 7, 15]:

        {
            "hollins_group": {
                "points": {1: "PASS", 7: "FAIL", 15: "PASS"},
                "summary": "Two or three sentences explaining the verdicts.",
            },
            ...
        }

    Each chosen point needs a verdict ("PASS" or "FAIL"; True/False also
    works). Other points are ignored.

    Catch errors per company (e.g. a failed API call) and still return an
    entry for it: an exception here means no results.csv, which scores zero.
    You may analyse companies in parallel (e.g. ``asyncio.gather``).
    """
    semaphore = asyncio.Semaphore(MAX_PARALLEL_COMPANIES)

    async def run_one(name: str, tools: list[Any]) -> tuple[str, dict[str, Any]]:
        async with semaphore:
            try:
                return name, await asyncio.to_thread(_analyze_company, agent, name, tools)
            except Exception as exc:  # one failure must not crash the run
                return name, {"points": {}, "summary": f"Analysis failed: {exc}"}

    return dict(await asyncio.gather(*(run_one(name, tools) for name, tools in companies.items())))


# Everything below is provided runner/scoring code. No edits are needed.
# Your code must read company data only through these tools: do not open
# company.db or interviews.dat directly.

INTERVIEWS_USED: dict[str, int] = {}


def company_folders(folder: Path) -> list[Path]:
    """Return one sub-folder per company directly inside *folder*, sorted by name."""
    return sorted(p for p in folder.iterdir() if p.is_dir() and not p.name.startswith("."))


def make_tools(company_folder: Path) -> list[Any]:
    """Build the four tools for one company."""
    from langchain_core.tools import tool

    name = company_folder.name
    db_uri = f"{(company_folder / 'company.db').resolve().as_uri()}?mode=ro"
    answers = json.loads(zlib.decompress((company_folder / "interviews.dat").read_bytes()))
    documents = {p.name: p for p in sorted(company_folder.glob("*.md"))}
    lock = threading.Lock()
    INTERVIEWS_USED[name] = 0

    @tool
    def list_documents() -> str:
        """List this company's documents (annual letter, earnings calls, news) with their dates."""
        lines = []
        for doc_name, path in documents.items():
            text = path.read_text(encoding="utf-8").splitlines()
            dated = next((line for line in text if line.startswith("Date:")), "")
            lines.append(f"{doc_name}: {text[0].lstrip('# ')} ({dated or 'undated'})")
        return "\n".join(lines)

    @tool
    def read_document(name: str) -> str:
        """Return the full text of one document named by list_documents, e.g. 'annual_letter_2025.md'."""
        path = documents.get(name.strip())
        if path is None:
            return f"No document named {name!r}. Available: {', '.join(documents)}"
        return path.read_text(encoding="utf-8")

    @tool
    def sql_query(query: str) -> str:
        """Run one read-only SQLite query on this company's database and return at most 50 rows.

        Amounts are in USD thousands. Dates are 'YYYY-MM-DD', months 'YYYY-MM', quarters like '2025Q3'.
        Tables:
          company(name, industry)
          industry_medians(industry, revenue_growth_2y_pct, new_product_share_pct, new_product_sales_per_rd, operating_margin_pct)
          orders(order_id, order_date, product, customer, amount, note)
          products(product, launch_date)
          monthly_costs(month, cost_of_sales, selling_admin, research_development)
          quarterly_cash(quarter, operating_cash_flow, capex, cash_end)
          capex_plan(year, planned_capex)
          returns(month, units_shipped, units_returned)
          insider_trades(trade_date, person, title, side, shares, price)
        Use SUM, GROUP BY and WHERE to compute totals rather than reading raw rows.
        """
        try:
            con = sqlite3.connect(db_uri, uri=True)
            try:
                cursor = con.execute(query)
                columns = [c[0] for c in cursor.description or []]
                rows = cursor.fetchmany(MAX_SQL_ROWS + 1)
            finally:
                con.close()
        except sqlite3.Error as exc:
            return f"SQL error: {exc}"
        if not columns:
            return "Query returned no columns."
        fmt = lambda v: f"{v:.2f}" if isinstance(v, float) else str(v)  # noqa: E731
        out = [" | ".join(columns)] + [" | ".join(fmt(v) for v in row) for row in rows[:MAX_SQL_ROWS]]
        if len(rows) > MAX_SQL_ROWS:
            out.append(f"... more rows not shown (limit {MAX_SQL_ROWS}); aggregate or add LIMIT/OFFSET.")
        if not rows:
            out.append("(no rows)")
        return "\n".join(out)

    @tool
    def interview(role: str, topic: str) -> str:
        """Interview one person about the company (at most 10 interviews per company).

        role: customer, current_employee, former_employee, competitor or supplier.
        topic: sales_team, working_conditions, top_management, decision_making or competitive_edge.
        People who would not know about a topic say so; the README lists who knows what.
        """
        role, topic = role.strip().lower(), topic.strip().lower()
        if role not in answers:
            return f"Unknown role {role!r}. Roles: {', '.join(answers)}. (Not counted.)"
        if topic not in answers[role]:
            return f"Unknown topic {topic!r}. Topics: {', '.join(answers[role])}. (Not counted.)"
        with lock:
            if INTERVIEWS_USED[name] >= INTERVIEW_LIMIT:
                return f"Interview limit reached: {INTERVIEW_LIMIT} interviews per company."
            INTERVIEWS_USED[name] += 1
        return answers[role][topic]

    return [list_documents, read_document, sql_query, interview]


def normalize_verdict(value: Any) -> str | None:
    """Accept PASS/FAIL (any case) or a boolean."""
    if isinstance(value, bool):
        return "PASS" if value else "FAIL"
    text = str(getattr(value, "content", value)).strip().upper()
    return text if text in VERDICTS else None


def check_chosen_points(chosen: Any) -> list[int]:
    """CHOSEN_POINTS must name 3 different points between 1 and 15."""
    try:
        points = sorted({int(p) for p in chosen})
    except (TypeError, ValueError):
        points = []
    if len(points) != 3 or len(chosen) != 3 or not all(p in FISHER_POINTS for p in points):
        raise SystemExit("Set CHOSEN_POINTS at the top of hw3.py to 3 different point numbers "
                         f"between 1 and 15, e.g. [1, 7, 15] (now: {chosen!r}).")
    return points


def normalize_points(points: Any, chosen: list[int]) -> dict[int, str | None]:
    """Map each chosen point number to PASS/FAIL, or None when missing/invalid."""
    points = points if isinstance(points, dict) else {}
    by_number: dict[int, Any] = {}
    for key, value in points.items():
        try:
            by_number[int(key)] = value
        except (TypeError, ValueError):
            continue
    return {p: normalize_verdict(by_number.get(p)) for p in chosen}


def read_ground_truth(folder: Path) -> dict[str, dict[str, Any]]:
    """Read the expected 15 point verdicts per company."""
    path = folder / "ground_truth.json"
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def point_errors(points: dict[int, str | None], expected: dict[str, Any] | None) -> tuple[int, str]:
    """Count correct point verdicts and describe the wrong ones."""
    if expected is None:
        return 0, ""
    wrong = []
    for p in points:
        truth = expected["points"][str(p)]
        if points[p] != truth:
            wrong.append(f"{p}: expected {truth}, predicted {points[p] or 'missing'}")
    if all(v is None for v in points.values()):
        return 0, "all point verdicts missing"
    return len(points) - len(wrong), "; ".join(wrong)


def balanced_point_accuracy(
    analyses: dict[str, Any], truth: dict[str, dict[str, Any]], names: list[str], chosen: list[int]
) -> float:
    """Mean of the accuracy on true-PASS points and on true-FAIL points.

    Most verdicts are PASS, so answering PASS everywhere gets a high plain
    accuracy but only 50% balanced accuracy. Grading uses the balanced number.
    """
    hits = {"PASS": [0, 0], "FAIL": [0, 0]}
    for name in names:
        if name not in truth:
            continue
        entry = analyses.get(name)
        points = normalize_points(entry.get("points") if isinstance(entry, dict) else None, chosen)
        for p in chosen:
            expected = truth[name]["points"][str(p)]
            hits[expected][0] += points[p] == expected
            hits[expected][1] += 1
    rates = [h / n for h, n in hits.values() if n]
    return sum(rates) / len(rates) if rates else 0.0


def write_results(
    names: list[str], analyses: dict[str, Any], truth: dict[str, dict[str, Any]], chosen: list[int]
) -> tuple[Path, int]:
    """Write results.csv and return the number of correct point verdicts."""
    output = Path("results.csv")
    correct_points = 0
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["company", "points", "points_correct", "point_errors", "interviews_used", "summary"])
        for name in names:
            entry = analyses.get(name)
            entry = entry if isinstance(entry, dict) else {}
            points = normalize_points(entry.get("points"), chosen)
            expected = truth.get(name)
            n_points, errors = point_errors(points, expected)
            correct_points += n_points
            writer.writerow([
                name,
                " ".join(f"{p}:{points[p] or 'missing'}" for p in chosen),
                f"{n_points}/{len(chosen)}" if expected else "",
                errors,
                INTERVIEWS_USED.get(name, 0),
                str(entry.get("summary", "")).strip(),
            ])
    return output, correct_points


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run FTEC5660 HW3 on company data folders")
    parser.add_argument(
        "--data-folder",
        required=True,
        type=Path,
        help="folder containing one sub-folder per company",
    )
    return parser.parse_args()


async def run(folder: Path) -> int:
    folders = company_folders(folder)
    if not folders:
        raise SystemExit(f"no company folders found in {folder}")

    chosen = check_chosen_points(CHOSEN_POINTS)
    load_env_file()
    companies = {path.name: make_tools(path) for path in folders}
    agent = build_agent()
    analyses = await analyze_companies(agent, companies)
    if not isinstance(analyses, dict):
        raise TypeError("analyze_companies() must return a dictionary")

    truth = read_ground_truth(folder)
    output, correct_points = write_results(list(companies), analyses, truth, chosen)
    summary = f" Your points: {', '.join(map(str, chosen))}."
    if truth:
        summary += (
            f" Point accuracy: {correct_points}/{len(companies) * len(chosen)}"
            f" (balanced: {balanced_point_accuracy(analyses, truth, list(companies), chosen):.1%})."
        )
    print(f"Processed {len(companies)} compan{'y' if len(companies) == 1 else 'ies'}. Wrote {output}.{summary}")
    return 0


def main() -> int:
    args = parse_args()
    if not args.data_folder.is_dir():
        raise SystemExit(f"not a folder: {args.data_folder}")
    return asyncio.run(run(args.data_folder))


if __name__ == "__main__":
    raise SystemExit(main())
