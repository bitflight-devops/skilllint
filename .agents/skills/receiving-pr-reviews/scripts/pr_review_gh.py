"""`gh`-backed GitHub I/O and result assembly for `pr_review_threads.py`.

Every function here shells out to `gh` (GitHub CLI) rather than talking to the GitHub API
directly, relying on `gh`'s own authentication. `build_fetch_result` is the one function the CLI
layer (`pr_review_threads.py`) calls directly — it composes the seven independent `gh` calls below
into one `FetchResult` snapshot, fresh every time it runs. `build_checks_result` is its
counterpart for CI state — two `gh` calls composed into one `ChecksResult`. `run_gh` is
exported too: the CLI layer's `reply`/`resolve` commands call it directly for their own
single-shot `gh` invocations.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Literal, NamedTuple

from pr_review_models import (
    CheckContext,
    CheckRunContext,
    ChecksResult,
    FetchResult,
    ForcePushEvent,
    IssueComment,
    PullRequestHeadState,
    Reaction,
    RepoIdentity,
    Reviewability,
    ReviewNode,
    ReviewsConnection,
    ReviewThreadsConnection,
    UnresolvedThread,
)
from pydantic import TypeAdapter

_UNRESOLVED_THREADS_QUERY = """
query($endCursor: String, $o: String!, $r: String!, $pr: Int!) {
  repository(owner: $o, name: $r) {
    pullRequest(number: $pr) {
      reviewThreads(first: 100, after: $endCursor) {
        totalCount
        pageInfo { hasNextPage endCursor }
        nodes {
          id isResolved path
          comments(first: 100) {
            totalCount
            pageInfo { hasNextPage }
            nodes { databaseId body line originalLine author { login } }
          }
        }
      }
    }
  }
}
"""

_REVIEWS_QUERY = """
query($endCursor: String, $o: String!, $r: String!, $pr: Int!) {
  repository(owner: $o, name: $r) {
    pullRequest(number: $pr) {
      reviews(first: 100, after: $endCursor) {
        totalCount
        pageInfo { hasNextPage endCursor }
        nodes { id author { login } state body submittedAt lastEditedAt url }
      }
    }
  }
}
"""

RESOLVE_THREAD_MUTATION = """
mutation($threadId: ID!) {
  resolveReviewThread(input: { threadId: $threadId }) {
    thread { isResolved }
  }
}
"""

_LATEST_FORCE_PUSH_QUERY = """
query($o: String!, $r: String!, $pr: Int!) {
  repository(owner: $o, name: $r) {
    pullRequest(number: $pr) {
      timelineItems(last: 1, itemTypes: [HEAD_REF_FORCE_PUSHED_EVENT]) {
        nodes { ... on HeadRefForcePushedEvent { createdAt } }
      }
    }
  }
}
"""

# One query for every PR-level field this script reads off the head: the three reviewability
# fields, the head commit's date, and its check rollup. They all live on the same `pullRequest`
# object, so asking for them together costs one round trip instead of two, and `build_fetch_result`
# already makes seven `gh` calls per snapshot.
#
# The rollup used to be fetched by a second query with its own `commits(last: 1)`. Neither query
# selected `oid` and nothing compared them, so a push landing between the two calls produced a
# `ChecksResult` pairing one head's checks with a different head's PR state. Selecting both from a
# single `pullRequest` snapshot removes the race outright — cheaper than selecting `oid` in two
# queries and comparing, and it deletes a `gh` call from `checks` rather than adding a retry.
#
# `isRequired(pullRequestNumber:)` is GitHub's own server-side answer to "does this check gate
# merging this PR", computed from whatever branch protection rule or ruleset covers the base
# branch. Asking for it here is what keeps `build_checks_result` free of a hardcoded check-name
# list, and it needs none of the admin permission the branch-protection REST endpoint requires.
# Verified against this repository's own API (2026-08-31): PR #166 returns `isRequired: true` for
# exactly the six contexts this repo's branch protection requires, and `false` for the eight it
# does not. Verified the same day that `mergeStateStatus` needs no preview `Accept` header on
# `gh api graphql`.
#
# `statusCheckRollup` is null on a head commit with no checks at all, and `contexts` is a
# connection — `build_checks_result` surfaces its `hasNextPage` as `contexts_truncated` rather
# than paginating, so a caller is told when a verdict is incomplete instead of being handed a
# silently partial one.
_HEAD_STATE_QUERY = """
query($o: String!, $r: String!, $pr: Int!) {
  repository(owner: $o, name: $r) {
    pullRequest(number: $pr) {
      isDraft
      mergeable
      mergeStateStatus
      commits(last: 1) {
        nodes {
          commit {
            committedDate
            statusCheckRollup {
              contexts(first: 100) {
                totalCount
                pageInfo { hasNextPage }
                nodes {
                  __typename
                  ... on CheckRun { name status conclusion isRequired(pullRequestNumber: $pr) }
                  ... on StatusContext { context state isRequired(pullRequestNumber: $pr) }
                }
              }
            }
          }
        }
      }
    }
  }
}
"""


# Absolute `gh` path, resolved once at import time — ruff's start-process-with-partial-path (S607)
# requires a resolved path rather than a bare command name. Falls back to the literal "gh" when
# `shutil.which` can't find it, so a missing binary still surfaces as a normal FileNotFoundError
# from the exec call itself rather than a custom error path.
_GH = shutil.which("gh") or "gh"

# `gh` calls are bounded by the caller, not by a constant here. A single fixed cap would have to
# cover a whole `gh api --paginate` run — every page requested sequentially inside one subprocess —
# on an arbitrarily large PR over an arbitrarily slow link, and `build_fetch_result` now makes
# seven such calls per snapshot rather than the two it made when the old 30-second cap was written.
# This repository has no source for that number (CLAUDE.md, "No invented constraints"), so `fetch`
# and `watch` expose `--gh-timeout-seconds` instead, unbounded by default, and `watch` additionally
# bounds each *poll* by its own `--timeout-seconds` deadline, which the caller chose.

# GitHub: "Required status checks must have a `successful`, `skipped`, or `neutral` status before
# collaborators can make changes to a protected branch."
# https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches
# (cached under .claude/vendor/sources/, accessed 2026-08-31). That one sentence is the only source
# for both sets below: a check run's conclusion satisfies a required check iff it is one of these
# three, and a commit status satisfies it iff it is `SUCCESS`.
_PASSING_CHECK_CONCLUSIONS = frozenset({"SUCCESS", "SKIPPED", "NEUTRAL"})
# A commit status that has not reached a verdict yet, as opposed to one that reached a failing one:
# `EXPECTED` is a status GitHub knows to expect but has not received, `PENDING` one still running.
_UNFINISHED_STATUS_STATES = frozenset({"EXPECTED", "PENDING"})


_ISSUE_COMMENT_ADAPTER: TypeAdapter[list[IssueComment]] = TypeAdapter(list[IssueComment])
_REACTION_ADAPTER: TypeAdapter[list[Reaction]] = TypeAdapter(list[Reaction])

# GraphQL's `author.login` and the REST reactions API's `user.login` return this bot's account
# name without a `[bot]` suffix and with one respectively (confirmed against this repo's own PR
# #3318 and #3306 history — see `_fetch_pr_reactions`) — an exact-match set covers both known
# shapes without a prefix check, which would also match an unrelated account whose login merely
# starts with the same text (e.g. a public PR's `chatgpt-codex-connector-imposter`).
_CODEX_REACTOR_LOGINS = frozenset({"chatgpt-codex-connector", "chatgpt-codex-connector[bot]"})


def run_gh(args: list[str], *, timeout: float | None = None) -> str:
    """Run a `gh` command and return its captured stdout.

    `gh` spawns no child processes of its own, so a plain timeout is enough to bound it — no
    process-group cleanup is needed the way it would be for a command that forks descendants.

    Args:
        args: Full `gh` argv, excluding the executable itself (e.g. `["api", "graphql", ...]`).
        timeout: Seconds to allow before killing the process, or `None` for no bound. `watch`
            passes the time left before its own deadline so one slow call near the end of a poll
            window can't push the whole command past `--timeout-seconds`.

    Returns:
        The command's stdout, decoded as text.

    Raises:
        FileNotFoundError: `gh` (GitHub CLI) is not on PATH.
        subprocess.CalledProcessError: `gh` exited non-zero. stderr is left connected to this
            process's own stderr (not captured) so the diagnostic reaches the caller directly.
        subprocess.TimeoutExpired: the command exceeded `timeout`.
    """
    result = subprocess.run([_GH, *args], stdout=subprocess.PIPE, text=True, timeout=timeout, check=True)
    return result.stdout


def detect_repo_identity(*, gh_timeout: float | None = None) -> tuple[str, str]:
    """Detect this checkout's own GitHub `(owner, repo)` via `gh repo view`.

    Relies entirely on `gh`'s own remote resolution (the same one `gh pr view`, `gh pr comment`
    etc. use for this checkout) -- this function adds no guessing of its own. A wrong owner/repo
    would send a reply to the wrong repository, so a caller unable to detect must stop rather than
    fall back to a default (CLAUDE.md, "No invented constraints").

    Args:
        gh_timeout: Seconds to bound the `gh` call to, or `None` for no bound -- see `run_gh`.

    Returns:
        The `(owner, repo)` pair `gh` reports for this checkout.

    Raises:
        FileNotFoundError: `gh` is not on PATH.
        subprocess.CalledProcessError: `gh` could not resolve a repository for this checkout --
            no remote, not a git repository, or `gh` is unauthenticated.
        subprocess.TimeoutExpired: the command exceeded `gh_timeout`.
        pydantic.ValidationError: `gh`'s output does not match the expected shape.
    """
    raw = run_gh(["repo", "view", "--json", "nameWithOwner"], timeout=gh_timeout)
    identity = RepoIdentity.model_validate(json.loads(raw))
    owner, repo = identity.nameWithOwner.split("/", 1)
    return owner, repo


def _fetch_pages(owner: str, repo: str, pr: int, *, gh_timeout: float | None) -> list[ReviewThreadsConnection]:
    """Fetch and validate every paginated page of a PR's review threads.

    Args:
        owner: Repository owner login.
        repo: Repository name.
        pr: Pull request number.
        gh_timeout: Seconds to bound the underlying `gh` call to, or `None` for no bound — see
            `run_gh`.

    Returns:
        One validated `reviewThreads` connection per page `gh api graphql --paginate` returned.
    """
    raw = run_gh(
        [
            "api",
            "graphql",
            "--paginate",
            "--slurp",
            "-f",
            f"query={_UNRESOLVED_THREADS_QUERY}",
            "-f",
            f"o={owner}",
            "-f",
            f"r={repo}",
            "-F",
            f"pr={pr}",
        ],
        timeout=gh_timeout,
    )
    return [
        ReviewThreadsConnection.model_validate(page["data"]["repository"]["pullRequest"]["reviewThreads"])
        for page in json.loads(raw)
    ]


def _fetch_review_pages(owner: str, repo: str, pr: int, *, gh_timeout: float | None) -> list[ReviewsConnection]:
    """Fetch and validate every paginated page of a PR's top-level reviews.

    A separate `gh` invocation from `_fetch_pages`: `gh api graphql --paginate` follows exactly
    one `pageInfo.endCursor` per call, so reviews and reviewThreads — independent connections —
    each need their own query and their own paginated `gh` call.

    Args:
        owner: Repository owner login.
        repo: Repository name.
        pr: Pull request number.
        gh_timeout: Seconds to bound the underlying `gh` call to, or `None` for no bound — see
            `run_gh`.

    Returns:
        One validated `reviews` connection per page `gh api graphql --paginate` returned.
    """
    raw = run_gh(
        [
            "api",
            "graphql",
            "--paginate",
            "--slurp",
            "-f",
            f"query={_REVIEWS_QUERY}",
            "-f",
            f"o={owner}",
            "-f",
            f"r={repo}",
            "-F",
            f"pr={pr}",
        ],
        timeout=gh_timeout,
    )
    return [
        ReviewsConnection.model_validate(page["data"]["repository"]["pullRequest"]["reviews"])
        for page in json.loads(raw)
    ]


def _fetch_issue_comments(owner: str, repo: str, pr: int, *, gh_timeout: float | None) -> list[IssueComment]:
    """Fetch every PR-level (issue) comment's timestamp and author, auto-paginated and flattened.

    A PR-level comment — `gh pr comment`, or any comment posted through the Issues REST API
    rather than as an inline review comment — is the mechanism the receiving-pr-reviews skill's
    own workflow already uses to answer a `reviews_with_body` entry (SKILL.md step 6: "A decision
    spanning threads... goes on the PR itself via `gh pr comment`"). The newest one of these
    authored by the currently-authenticated `gh` identity (see `_fetch_authenticated_login`) is
    exactly the signal `build_fetch_result` needs to tell whether a review's top-level feedback
    has since been followed up on by this workflow — not by an unrelated bystander, bot, or CI
    notification also commenting on the PR in the meantime.

    Args:
        owner: Repository owner login.
        repo: Repository name.
        pr: Pull request number.
        gh_timeout: Seconds to bound the underlying `gh` call to, or `None` for no bound — see
            `run_gh`.

    Returns:
        Every PR-level comment, flattened across all pages. `--slurp` is used even though this is
        a plain REST array response (not GraphQL): without it, a multi-page result would print as
        several bare JSON arrays concatenated back to back, which `json.loads` cannot parse as one
        document — `--slurp` wraps each page in an outer array first, same as the GraphQL calls
        above.
    """
    raw = run_gh(["api", f"repos/{owner}/{repo}/issues/{pr}/comments", "--paginate", "--slurp"], timeout=gh_timeout)
    return [comment for page in json.loads(raw) for comment in _ISSUE_COMMENT_ADAPTER.validate_python(page)]


def _fetch_pr_reactions(owner: str, repo: str, pr: int, *, gh_timeout: float | None) -> list[Reaction]:
    """Fetch every reaction left on the PR itself (not on any individual comment), flattened.

    Confirmed empirically against this repository's own review history (PR #3318, #3306): Codex's
    own review text states "If Codex has suggestions, it will comment; otherwise it will react
    with :+1:" — on both PRs checked, that reaction landed here, `GET
    repos/{owner}/{repo}/issues/{pr}/reactions`, as a `content: "+1"` entry from
    `chatgpt-codex-connector[bot]`, with no accompanying review or comment at all. This is a
    reaction on the PR (issue) itself, distinct from a reaction on any individual review comment —
    `reviews`/`reviews_with_body` never carries it, and this script does not check per-comment
    reactions.

    Args:
        owner: Repository owner login.
        repo: Repository name.
        pr: Pull request number.
        gh_timeout: Seconds to bound the underlying `gh` call to, or `None` for no bound — see
            `run_gh`.

    Returns:
        Every reaction on the PR itself, flattened across all pages — see `_fetch_issue_comments`
        for why `--slurp` is used on this plain REST array endpoint.
    """
    raw = run_gh(["api", f"repos/{owner}/{repo}/issues/{pr}/reactions", "--paginate", "--slurp"], timeout=gh_timeout)
    return [reaction for page in json.loads(raw) for reaction in _REACTION_ADAPTER.validate_python(page)]


def _fetch_authenticated_login(*, gh_timeout: float | None) -> str:
    """Fetch the GitHub login `gh` is currently authenticated as.

    Repo-independent (unlike every other `_fetch_*` helper here): the authenticated identity is
    the same regardless of which PR or repository is being watched, so this call takes no
    `owner`/`repo`/`pr` arguments.

    Args:
        gh_timeout: Seconds to bound the underlying `gh` call to, or `None` for no bound — see
            `run_gh`.

    Returns:
        The authenticated user's login, e.g. `"jane-doe"`.
    """
    return run_gh(["api", "user", "--jq", ".login"], timeout=gh_timeout).strip()


def _fetch_head_state(owner: str, repo: str, pr: int, *, gh_timeout: float | None) -> PullRequestHeadState:
    """Fetch the PR's head-commit date and its three reviewability fields in one GraphQL query.

    The commit date is read via GraphQL's `commits(last: 1)` rather than the REST
    `GET /repos/{owner}/{repo}/pulls/{pr}/commits` endpoint: that endpoint is documented as listing
    a maximum of 250 commits total regardless of pagination, so `--paginate` cannot retrieve a
    commit beyond that hard cap — on a PR with more than 250 commits, its last element would not
    reliably be the actual head. GraphQL's `commits` connection has no such flat cap; requesting
    `last: 1` asks the server directly for the tail element regardless of how many commits the PR
    has.

    `build_fetch_result` compares a Codex approval reaction's timestamp against the later of that
    date and `_fetch_latest_force_push_at`'s result — this call alone is not sufficient on its own:
    a force-push that creates a brand-new commit (the overwhelmingly common case — a rebase or
    amend) refreshes that commit's own committed date to the time of the push, but a force-push
    that resets the branch back onto a pre-existing commit object (reusing its original, older
    committed date) would not, which is exactly what `_fetch_latest_force_push_at`'s
    server-recorded event timestamp covers instead.

    Args:
        owner: Repository owner login.
        repo: Repository name.
        pr: Pull request number.
        gh_timeout: Seconds to bound the underlying `gh` call to, or `None` for no bound — see
            `run_gh`.

    Returns:
        The PR's draft/mergeable/merge-state fields plus its head commit.

    Raises:
        IndexError: the PR has no commits at all — not possible for a real, open pull request, so
            this is an acceptable boundary failure for an invariant this script does not control.
    """
    raw = run_gh(
        ["api", "graphql", "-f", f"query={_HEAD_STATE_QUERY}", "-f", f"o={owner}", "-f", f"r={repo}", "-F", f"pr={pr}"],
        timeout=gh_timeout,
    )
    return PullRequestHeadState.model_validate(json.loads(raw)["data"]["repository"]["pullRequest"])


def _latest_revision_at(head_state: PullRequestHeadState, force_push_at: datetime | None) -> datetime:
    """The moment the PR's current revision came into being.

    Neither input is sufficient alone. A force-push that creates a brand-new commit — a rebase or
    amend, the overwhelmingly common case — refreshes that commit's own committed date, so the head
    commit carries it. A force-push that resets the branch back onto a pre-existing commit object
    reuses that commit's original, older date, and only the server-recorded event timestamp from
    `_fetch_latest_force_push_at` reflects the push.

    Args:
        head_state: The PR head state from `_fetch_head_state`.
        force_push_at: The most recent force-push timestamp, or `None` if never force-pushed.

    Returns:
        The later of the head commit's date and the force-push timestamp.
    """
    head_commit_date = head_state.commits.nodes[-1].commit.committedDate
    return max(head_commit_date, force_push_at or head_commit_date)


def _reviewability(head_state: PullRequestHeadState) -> Reviewability:
    """Derive whether this PR can be reviewed at all, and say what is stopping it if not.

    Only two conditions produce a blocker, because only these two stop reviews from happening:
    a draft PR does not get reviewers requested, and a conflicting one does not get review runs.
    `mergeStateStatus` is reported as data but drives no blocker of its own — its `DRAFT` and
    `DIRTY` values restate `isDraft` and `mergeable` respectively, and its remaining values
    (`BLOCKED`, `BEHIND`, `UNSTABLE`, `HAS_HOOKS`) describe merge readiness, not reviewability.

    `mergeable: "UNKNOWN"` yields no blocker on purpose — see `Reviewability`.

    Args:
        head_state: The PR-level fields from `_fetch_head_state`.

    Returns:
        The three fields as reported, plus a plain-sentence blocker per condition present.
    """
    blockers = []
    if head_state.isDraft:
        blockers.append("draft: reviewers are not requested until the PR is marked ready for review")
    if head_state.mergeable == "CONFLICTING":
        blockers.append("conflicting: reviews will not run until the merge conflicts are resolved")
    return Reviewability(
        is_draft=head_state.isDraft,
        mergeable=head_state.mergeable,
        merge_state_status=head_state.mergeStateStatus,
        blockers=blockers,
    )


def checks_blocked(reviewability: Reviewability) -> bool:
    """Whether the PR's own state stops CI from running at all.

    Only one of `Reviewability`'s two blockers does. A conflicting PR has no mergeable state for
    GitHub to build `refs/pull/N/merge` from, so a `pull_request`-triggered workflow has nothing to
    check out and no run is created — waiting on such a PR observes nothing, forever.

    A **draft** PR does not stop workflows. `pull_request` fires on a draft for its default
    activity types; a workflow skips drafts only when it opts out itself, by filtering
    `types: [ready_for_review]` or guarding on `github.event.pull_request.draft`. This repository's
    own `.github/workflows/test.yml` and `benchmark.yml` do neither — both trigger on a bare
    `pull_request` with no `types:` filter and no draft guard (verified 2026-08-31) — so their runs
    do start on a draft PR. The draft blocker is about *reviewers*, who are not requested until the
    PR is marked ready, which is what `fetch` reads `blockers` for. Treating it as a checks blocker
    made `checks` return the first snapshot instantly on every draft PR.

    Args:
        reviewability: The PR state derived by `_reviewability`.

    Returns:
        `True` when no check can start until the PR itself is fixed.
    """
    return reviewability.mergeable == "CONFLICTING"


def _fetch_latest_force_push_at(owner: str, repo: str, pr: int, *, gh_timeout: float | None) -> datetime | None:
    """Fetch the timestamp of the PR's most recent force-push, if it has ever had one.

    A `HeadRefForcePushedEvent` is a server-recorded timeline entry created at the moment of the
    force-push itself, independent of any commit's own embedded author/committer metadata — the
    signal `_fetch_head_state` cannot provide on its own for a force-push that resets the
    branch back onto a pre-existing commit object (see that function's docstring).

    Args:
        owner: Repository owner login.
        repo: Repository name.
        pr: Pull request number.
        gh_timeout: Seconds to bound the underlying `gh` call to, or `None` for no bound — see
            `run_gh`.

    Returns:
        The most recent force-push's timestamp, or `None` if this PR's head has never been
        force-pushed.
    """
    raw = run_gh(
        [
            "api",
            "graphql",
            "-f",
            f"query={_LATEST_FORCE_PUSH_QUERY}",
            "-f",
            f"o={owner}",
            "-f",
            f"r={repo}",
            "-F",
            f"pr={pr}",
        ],
        timeout=gh_timeout,
    )
    nodes = json.loads(raw)["data"]["repository"]["pullRequest"]["timelineItems"]["nodes"]
    events = [ForcePushEvent.model_validate(node) for node in nodes]
    return events[-1].createdAt if events else None


def _review_effective_timestamp(review: ReviewNode) -> datetime:
    """The timestamp representing the newest content this review's body currently carries.

    A review's `submittedAt` never changes once set, but its `body` can be edited afterward —
    GitHub's `lastEditedAt` reflects that edit. Whichever of the two is later is the review's
    effective timestamp for `unresponded_reviews`'s "has this workflow responded since" comparison
    in `build_fetch_result` — using `submittedAt` alone would let a post-response edit go unnoticed
    forever, since the original submission time already predates the response.

    Args:
        review: A review already known to have been submitted (`submittedAt is not None`) — see
            `build_fetch_result`, the only caller, which filters not-yet-submitted reviews first.

    Returns:
        The later of `submittedAt` and `lastEditedAt`.

    Raises:
        TypeError: `review.submittedAt` is `None` — the caller must exclude not-yet-submitted
            reviews before calling this, since they have no meaningful timestamp to compare.
    """
    if review.submittedAt is None:
        message = "_review_effective_timestamp requires an already-submitted review"
        raise TypeError(message)
    if review.lastEditedAt is None:
        return review.submittedAt
    return max(review.submittedAt, review.lastEditedAt)


def _references_review(comment_body: str, review_url: str) -> bool:
    """Whether `comment_body` quotes `review_url` as a complete permalink, not a mere id prefix.

    A review's `url` ends in its own numeric database id (`#pullrequestreview-<id>`), and plain
    substring containment does not enforce a boundary at the end of that id: id `123` is itself a
    substring of id `1234`, so a comment quoting only the longer permalink would also satisfy a
    naive `review.url in comment_body` check for the shorter, unrelated review. Requiring the
    character immediately after the match (if any) to not be a digit rules that out while still
    matching the common case of the URL followed by punctuation, whitespace, or the end of the
    comment.

    Args:
        comment_body: One PR-level comment's body text.
        review_url: The specific review's own canonical permalink to look for.

    Returns:
        `True` when `review_url` appears in `comment_body` with no trailing digit immediately
        after it.
    """
    return re.search(re.escape(review_url) + r"(?!\d)", comment_body) is not None


def _unresponded_reviews(reviews_with_body: list[ReviewNode], own_comments: list[IssueComment]) -> list[ReviewNode]:
    """Which of `reviews_with_body` this workflow has not yet explicitly responded to.

    A review counts as responded only when at least one of this workflow's own PR-level comments
    both quotes that review's own `url` (its canonical GitHub permalink, matched as a complete id —
    see `_references_review`) *and* postdates the review's effective timestamp — the later of
    `submittedAt`/`lastEditedAt`, see `_review_effective_timestamp`. Requiring an explicit
    reference, rather than inferring a match purely from chronological order, prevents an unrelated
    administrative comment — e.g. a cross-thread sequencing decision, explicitly sanctioned by the
    receiving-pr-reviews skill's own workflow step 6 — from being mistaken for a response to
    whatever review happens to be newest at the time it is posted. Requiring the reference to also
    postdate the review's effective timestamp still catches an editor adding new feedback to an
    already-referenced review after the fact. One comment referencing multiple reviews' URLs
    correctly clears all of them; no review is limited to being "claimed" by only one comment. A
    review with no `submittedAt` (not yet actually submitted) is excluded rather than treated as
    always-unresponded.

    Args:
        reviews_with_body: Every review whose summary text is non-empty, in any order.
        own_comments: Every PR-level comment authored by the currently-authenticated `gh` identity,
            in any order.

    Returns:
        Every unresponded review, in `reviews_with_body`'s original order.
    """
    return [
        review
        for review in reviews_with_body
        if review.submittedAt is not None
        and not any(
            _references_review(comment.body, review.url) and comment.created_at >= _review_effective_timestamp(review)
            for comment in own_comments
        )
    ]


def _is_codex_thumbs_up(reaction: Reaction) -> bool:
    """Whether `reaction` is Codex's approval signal — a "+1" from its bot account.

    Args:
        reaction: One reaction fetched by `_fetch_pr_reactions`.

    Returns:
        `True` when `reaction` is a thumbs-up left by exactly the Codex bot's known login (either
        GraphQL or REST shape — see `_CODEX_REACTOR_LOGINS`), not merely a login that starts with
        the same text.
    """
    return (
        reaction.content == "+1" and reaction.user is not None and reaction.user.login.lower() in _CODEX_REACTOR_LOGINS
    )


def _latest_codex_approval_at(reactions: list[Reaction]) -> datetime | None:
    """The timestamp of Codex's most recent approval reaction on the PR, if it has left one.

    Separated from the "is it still current" comparison in `build_fetch_result` because those are
    two independent questions, and collapsing them into a single boolean is what made a push that
    invalidated an approval indistinguishable from Codex never having looked at the PR — opposite
    situations calling for opposite actions.

    `max` rather than "any": a PR accumulates a reaction per revision Codex approves, and they are
    never removed, so only the most recent one can possibly still apply to what is on the branch.

    Args:
        reactions: Every reaction on the PR itself, from `_fetch_pr_reactions`.

    Returns:
        When Codex last left its "+1", or `None` if it never has.
    """
    return max((reaction.created_at for reaction in reactions if _is_codex_thumbs_up(reaction)), default=None)


def gh_timeout_budget(deadline: float | None, gh_timeout: float | None) -> float | None:
    """Choose the timeout for one `gh` call.

    `deadline` is `None` for a plain `fetch` and for `watch`'s mandatory first fetch: neither has a
    window to respect, so the caller's `--gh-timeout-seconds` applies unchanged (`None` = no
    bound). `watch` passes its own `deadline` for each *poll*, so all seven of
    `build_fetch_result`'s `gh` calls -- issued concurrently, so each is budgeted from
    approximately the same moment rather than from a progressively later one -- are bounded by
    whatever is actually left in that poll's window, rather than by a fixed reservation subtracted
    from every poll regardless of how fast GitHub responds.

    Args:
        deadline: A `time.monotonic()` timestamp to respect, or `None` for no deadline.
        gh_timeout: The caller's own per-call bound, used when there is no deadline.

    Returns:
        Seconds to pass as `run_gh`'s `timeout`, or `None` for no bound.
    """
    if deadline is None:
        return gh_timeout
    return max(0.0, deadline - time.monotonic())


class _ConcurrentFetch(NamedTuple):
    """The typed result of `_fetch_concurrently`'s seven independent `gh` calls.

    A plain tuple (or a list gathered in a loop) would force every element to the same union type
    under static type checking, since nothing about a bare sequence records which position held
    which call's result. A `NamedTuple` keeps each field's own type -- `list[ReviewThreadsConnection]`
    for `thread_pages`, `str` for `authenticated_login`, and so on -- exactly as if each had been
    assigned from its own sequential call, which is what `build_fetch_result` used to do before
    these seven moved onto a thread pool.
    """

    thread_pages: list[ReviewThreadsConnection]
    review_pages: list[ReviewsConnection]
    issue_comments: list[IssueComment]
    reactions: list[Reaction]
    authenticated_login: str
    head_state: PullRequestHeadState
    latest_force_push_at: datetime | None


def _fetch_concurrently(
    owner: str, repo: str, pr: int, *, deadline: float | None, gh_timeout: float | None
) -> _ConcurrentFetch:
    """Run `build_fetch_result`'s seven independent `gh` calls on a thread pool and gather them.

    Split out of `build_fetch_result` itself so the pool's bookkeeping (one `Future` per call)
    stays local to this function instead of adding seven more names to a function already busy
    assembling the result. Each call is a blocking `subprocess` invocation, not native async I/O,
    hence a thread pool rather than asyncio -- and none of the seven consumes another's output, so
    there is no reason to pay the sum of seven round-trip latencies instead of the max.

    Args:
        owner: Repository owner login.
        repo: Repository name.
        pr: Pull request number.
        deadline: A `time.monotonic()` timestamp each call should respect — see `gh_timeout_budget`.
        gh_timeout: Per-call bound applied when `deadline` is `None`.

    Returns:
        All seven calls' results, gathered in a fixed field order so a failure raises the same
        call's exception a sequential run would have raised first.

    A failing call is reported the moment its own `.result()` raises -- it does not wait for
    still-running siblings. `executor.shutdown()` always runs with `wait=False`: on the success
    path every future is already done by the time its `.result()` returns, so `wait=False` costs
    nothing; on a failure path it is what stops the pool from blocking the exception behind
    whichever sibling call happens to be slowest (the old `with ThreadPoolExecutor(...) as
    executor:` form called the default `shutdown(wait=True)` on exit, which did exactly that).
    """
    executor = ThreadPoolExecutor(max_workers=7)
    try:
        thread_pages_future = executor.submit(
            _fetch_pages, owner, repo, pr, gh_timeout=gh_timeout_budget(deadline, gh_timeout)
        )
        review_pages_future = executor.submit(
            _fetch_review_pages, owner, repo, pr, gh_timeout=gh_timeout_budget(deadline, gh_timeout)
        )
        issue_comments_future = executor.submit(
            _fetch_issue_comments, owner, repo, pr, gh_timeout=gh_timeout_budget(deadline, gh_timeout)
        )
        reactions_future = executor.submit(
            _fetch_pr_reactions, owner, repo, pr, gh_timeout=gh_timeout_budget(deadline, gh_timeout)
        )
        authenticated_login_future = executor.submit(
            _fetch_authenticated_login, gh_timeout=gh_timeout_budget(deadline, gh_timeout)
        )
        head_state_future = executor.submit(
            _fetch_head_state, owner, repo, pr, gh_timeout=gh_timeout_budget(deadline, gh_timeout)
        )
        latest_force_push_at_future = executor.submit(
            _fetch_latest_force_push_at, owner, repo, pr, gh_timeout=gh_timeout_budget(deadline, gh_timeout)
        )

        return _ConcurrentFetch(
            thread_pages=thread_pages_future.result(),
            review_pages=review_pages_future.result(),
            issue_comments=issue_comments_future.result(),
            reactions=reactions_future.result(),
            authenticated_login=authenticated_login_future.result(),
            head_state=head_state_future.result(),
            latest_force_push_at=latest_force_push_at_future.result(),
        )
    finally:
        # `cancel_futures=True` drops any of the seven not yet started (none, in practice, since
        # `max_workers=7` covers all seven submissions at once); `wait=False` is what keeps a
        # raised exception from waiting on the rest -- see the docstring above.
        executor.shutdown(wait=False, cancel_futures=True)


def build_fetch_result(
    owner: str, repo: str, pr: int, *, deadline: float | None = None, gh_timeout: float | None = None
) -> FetchResult:
    """Fetch and assemble one PR's full outstanding-work snapshot: threads, reviews, and approval.

    Shared by `fetch` (prints the result once, `deadline=None`) and `watch` (calls this repeatedly
    on a polling interval, passing its own deadline) so both subcommands assemble a `FetchResult`
    identically. Makes seven `gh` calls concurrently (a thread pool, since each is a blocking
    `subprocess` call rather than native async I/O) -- none consumes another's output, so there is
    no reason to pay the sum of seven round-trip latencies instead of the max. Each is
    independently bounded by `gh_timeout_budget(deadline)`:
    the paginated review-threads query, the paginated reviews query, every PR-level issue comment
    (for `unresponded_reviews`), every reaction on the PR itself (for `codex_approved`), the
    currently-authenticated `gh` identity (also for `unresponded_reviews`), and the PR's head
    commit date plus its most recent force-push timestamp, if any (both also for `codex_approved`
    — see `_fetch_head_state` and `_fetch_latest_force_push_at`). Every one of the seven is
    a fresh snapshot taken by this call alone — nothing here is compared against an earlier call's
    result, which is what makes two `watch` calls back to back, or a `watch` call issued right
    after a `fetch`, incapable of missing or double-counting activity that happened in between (the
    failure mode a per-invocation in-memory baseline used to have).

    `unresponded_reviews` is every `reviews_with_body` entry `_unresponded_reviews` cannot find an
    explicit, postdating reference to among the currently-authenticated `gh` identity's own
    PR-level comments — see that function for why a review's own `url` must be quoted in a comment
    that postdates the review's effective timestamp (the later of `submittedAt`/`lastEditedAt`),
    rather than inferring a match purely from chronological order: an unrelated administrative
    comment that merely postdates a review (e.g. a cross-thread sequencing decision this skill's
    own workflow sanctions) is not evidence it addressed that review's feedback, and a plain
    chronological cutover cannot tell the two apart. Comments from any other account are ignored
    for the same reason a comment without any reference is. A review with no `submittedAt` (not
    yet actually submitted) is excluded rather than treated as always-unresponded.

    `codex_approved` is `True` when a "+1" reaction from exactly the Codex bot's known login (not
    merely one that starts with the same text — see `_CODEX_REACTOR_LOGINS`) exists on the PR
    itself at the moment of this call *and* that reaction's own timestamp is at or after the later
    of the PR's current head commit's date and its most recent force-push timestamp, if any — see
    `_fetch_pr_reactions`, `_fetch_head_state`, and `_fetch_latest_force_push_at`. Neither
    date alone is sufficient: a reaction left approving an earlier revision would otherwise keep
    reporting as approval indefinitely, even after a later push the reaction never actually saw,
    including a force-push that resets the branch back onto a pre-existing commit object whose own
    embedded date predates the reaction.

    A reaction that fails only that timestamp test is reported as `codex_approval_stale` rather
    than being silently folded into `codex_approved: False`: Codex did approve, but a later push
    replaced the code it approved, so the caller has to re-request a review instead of waiting for
    one. `codex_approved_at` and `latest_revision_at` carry the two timestamps the verdict was
    computed from, so a caller can say *how* stale rather than only *that* it is — see
    `FetchResult`.

    Args:
        owner: Repository owner login.
        repo: Repository name.
        pr: Pull request number.
        deadline: A `time.monotonic()` timestamp the caller wants this call's seven `gh`
            invocations to respect — see `gh_timeout_budget`. `None` means no deadline.
        gh_timeout: Per-call bound applied when `deadline` is `None`; `None` means no bound.

    Returns:
        Totals plus every currently-unresolved thread, every unresponded review, and whether
        Codex's approval reaction is present right now for the current revision, for an older one,
        or not at all.
    """
    fetched = _fetch_concurrently(owner, repo, pr, deadline=deadline, gh_timeout=gh_timeout)
    latest_revision_at = _latest_revision_at(fetched.head_state, fetched.latest_force_push_at)

    all_threads = [node for page in fetched.thread_pages for node in page.nodes]
    all_reviews = [node for page in fetched.review_pages for node in page.nodes]
    unresolved = [
        UnresolvedThread(
            id=node.id,
            path=node.path,
            comments=node.comments.nodes,
            comments_truncated=node.comments.pageInfo.hasNextPage,
        )
        for node in all_threads
        if not node.isResolved
    ]
    reviews_with_body = [review for review in all_reviews if review.body.strip()]

    own_comments = [
        comment
        for comment in fetched.issue_comments
        if comment.user is not None and comment.user.login == fetched.authenticated_login
    ]
    unresponded_reviews = _unresponded_reviews(reviews_with_body, own_comments)
    codex_approved_at = _latest_codex_approval_at(fetched.reactions)

    return FetchResult(
        reviews_count=fetched.review_pages[0].totalCount,
        reviews_with_body=reviews_with_body,
        unresponded_reviews=unresponded_reviews,
        threads_count=fetched.thread_pages[0].totalCount,
        unresolved=unresolved,
        unresolved_count=len(unresolved),
        # Present and at/after the current revision vs. present and before it: two conditions over
        # the same timestamp, written out rather than derived from each other so the mutual
        # exclusion `FetchResult` documents is visible here instead of inferred.
        codex_approved=codex_approved_at is not None and codex_approved_at >= latest_revision_at,
        codex_approval_stale=codex_approved_at is not None and codex_approved_at < latest_revision_at,
        codex_approved_at=codex_approved_at,
        latest_revision_at=latest_revision_at,
        reviewability=_reviewability(fetched.head_state),
    )


def _check_outcome(context: CheckContext) -> Literal["passed", "failed", "pending"]:
    """Grade one check against the rule GitHub applies to a required check.

    A check run is graded in two steps because GitHub splits its lifecycle from its verdict: it is
    unfinished until `status` reaches `COMPLETED`, and only then does its `conclusion` decide.
    A `COMPLETED` run whose conclusion is not one of the three GitHub accepts — including a value
    this script has never seen — is `"failed"`: it has finished, and it does not satisfy the rule.
    A commit status carries a single `state` instead, so it is graded in one step.

    Args:
        context: One check run or commit status from the head commit's rollup.

    Returns:
        `"passed"`, `"failed"`, or `"pending"` — see `_PASSING_CHECK_CONCLUSIONS` for the source of
        the passing set.
    """
    if isinstance(context, CheckRunContext):
        if context.status != "COMPLETED":
            return "pending"
        return "passed" if context.conclusion in _PASSING_CHECK_CONCLUSIONS else "failed"
    if context.state in _UNFINISHED_STATUS_STATES:
        return "pending"
    return "passed" if context.state == "SUCCESS" else "failed"


def build_checks_result(
    owner: str, repo: str, pr: int, *, deadline: float | None = None, gh_timeout: float | None = None
) -> ChecksResult:
    """Fetch and assemble one PR's CI verdict, plus whether the PR can run checks at all.

    Makes one `gh` call, bounded by `gh_timeout_budget(deadline)` exactly as
    `build_fetch_result`'s seven are. The head commit's check rollup and the PR-level fields
    `_reviewability` reads come out of the same `pullRequest` snapshot, so the verdict and the
    state explaining it can never describe two different heads — see `_HEAD_STATE_QUERY` for the
    race that split queries allowed.

    Only the checks GitHub marks required for this PR are graded when any is marked required: a
    failing check that does not gate the merge is not a failure of the PR. When none is marked
    required there is no smaller set to grade, so every reported check is, and `required_only` says
    which of the two happened.

    Args:
        owner: Repository owner login.
        repo: Repository name.
        pr: Pull request number.
        deadline: A `time.monotonic()` timestamp the caller wants both `gh` invocations to respect
            — see `gh_timeout_budget`. `None` means no deadline.
        gh_timeout: Per-call bound applied when `deadline` is `None`; `None` means no bound.

    Returns:
        The verdict over the graded checks, the names of any that failed or are still running, and
        the PR's reviewability.
    """
    head_state = _fetch_head_state(owner, repo, pr, gh_timeout=gh_timeout_budget(deadline, gh_timeout))
    rollup = head_state.commits.nodes[-1].commit.statusCheckRollup
    reported = rollup.contexts.nodes if rollup is not None else []
    required = [context for context in reported if context.isRequired]
    graded = required or reported
    # A list of pairs rather than a dict: two workflows may report a check of the same name, and a
    # dict would silently drop one of them from the verdict.
    outcomes = [(context.name, _check_outcome(context)) for context in graded]
    failed = [name for name, outcome in outcomes if outcome == "failed"]
    pending = [name for name, outcome in outcomes if outcome == "pending"]
    status: Literal["passed", "failed", "pending", "none"]
    if not graded:
        status = "none"
    elif failed:
        status = "failed"
    elif pending:
        status = "pending"
    else:
        status = "passed"
    return ChecksResult(
        status=status,
        required_only=bool(required),
        total=len(graded),
        failed=failed,
        pending=pending,
        contexts_truncated=rollup is not None and rollup.contexts.pageInfo.hasNextPage,
        reviewability=_reviewability(head_state),
    )
