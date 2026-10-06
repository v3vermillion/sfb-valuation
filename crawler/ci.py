"""Single entry point for GitHub Actions (and for Claude Code). Decides what to do next.

  python -m crawler.ci --plan continue|core|full|approve|identify|status [--budget-min 300]

continue  resume the current crawl if one is unfinished; otherwise process/QA/publish if a crawl
          finished; otherwise nothing (safe to run any time — this is what "continue" means)
core      start a refresh of core departments (food, health, personal care, baby, pets, household)
full      start a full crawl of every in-scope department
approve   publish the current candidate after human review of its report
identify  refresh the Open Food Facts identification data and equivalent prices
status    print progress only
Writes `next=<plan>` to $GITHUB_OUTPUT when another run should be chained immediately.
"""
import argparse, os, subprocess

from . import crawl, process, qa, identify, store


def out(key, val):
    p = os.environ.get("GITHUB_OUTPUT")
    if p:
        with open(p, "a") as f:
            f.write(f"{key}={val}\n")


def summary(text):
    p = os.environ.get("GITHUB_STEP_SUMMARY")
    if p:
        with open(p, "a") as f:
            f.write(text + "\n")
    print(text)


def compact_store():
    """Replace data-store history with a single commit so the branch never grows."""
    if os.environ.get("SFB_NO_COMMIT") or not (store.ROOT / ".git").exists():
        return
    g = lambda *a: subprocess.run(["git", "-C", str(store.ROOT), *a], check=True, capture_output=True, text=True)
    g("checkout", "-q", "--orphan", "compact")
    g("add", "-A")
    g("commit", "-q", "-m", "compacted snapshot")
    g("push", "-q", "-f", "origin", "HEAD:data-store")


def finish_if_crawled(plan):
    state = store.read_json(crawl.STATE)
    if not state or state["status"] != "crawled":
        return
    process.build()
    status = qa.check()
    store.checkpoint(f"{state['run_id']} built: {status}")
    report = (qa.CAND / "report.md").read_text()
    summary(report)
    if status == "ready" and qa.publish():
        store.checkpoint(f"{state['run_id']} published")
        compact_store()
        if state["plan"] == "full":
            out("next", "identify")
    elif status == "awaiting_approval":
        summary("**First snapshot ready for review.** Read the report above, then run the workflow with plan=approve.")
    else:
        summary("**Gates failed.** The previous snapshot stays live. Review the report above.")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", default="continue", choices=["continue", "core", "full", "approve", "identify", "status"])
    ap.add_argument("--budget-min", type=float, default=300)
    a = ap.parse_args(argv)

    if a.plan == "status":
        crawl.status(); return
    if a.plan == "approve":
        if qa.publish(approve=True):
            store.checkpoint("approved snapshot published")
            compact_store()
            out("next", "identify")
        return
    if a.plan == "identify":
        identify.fetch(); identify.match()
        store.checkpoint("identification data refreshed")
        return

    state = store.read_json(crawl.STATE)
    if a.plan in ("core", "full") and not (state and state["status"] == "crawling"):
        crawl.start(a.plan)
    state = store.read_json(crawl.STATE)
    if state and state["status"] == "crawling":
        outcome = crawl.run(a.budget_min)
        if outcome == "budget":
            out("next", "continue")
        elif outcome == "throttled":
            summary("Paused by Walmart rate limiting; the 12-hourly schedule resumes automatically.")
    finish_if_crawled(a.plan)
    crawl.status()


if __name__ == "__main__":
    main()
