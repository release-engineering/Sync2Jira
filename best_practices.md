
<b>Pattern 1: Unit tests should aspire to provide 100% coverage of the code. All normal-execution paths, including early-exit/guard conditionals, should be exercised. While it is not strictly necessary to exercise every error case, all cases which can be reasonably tested should be.

Changes to the code which create new functions or branches should include unit tests which provide coverage for those paths. As a general rule, it should not be the case that a PR causes the overall coverage to be reduced (although, changes which add no uncovered code but which delete more code than they add can have this effect, but these are unusual).
</b>

Example code before:
```
def sync_fields(issue, updates):
    if "github_project_fields" not in updates:
        return
    fields = issue.downstream.get("github_project_fields")
    if fields is None:
        return
    update_fields(fields)
```

Example code after:
```
def sync_fields(issue, updates):
    fields = issue.downstream.get("github_project_fields") or {}
    if "github_project_fields" not in updates or not fields:
        return
    update_fields(fields)

def test_sync_fields_early_exit_no_updates():
    assert sync_fields(issue, updates=[]) is None

def test_sync_fields_early_exit_none_fields():
    issue.downstream["github_project_fields"] = None
    assert sync_fields(issue, updates=["github_project_fields"]) is None

def test_sync_fields_happy_path_updates_fields(mocker):
    issue.downstream["github_project_fields"] = {"priority": "P1"}
    spy = mocker.spy(mod, "update_fields")
    sync_fields(issue, updates=["github_project_fields"])
    spy.assert_called_once()
```

<details><summary>Examples for relevant past discussions:</summary>

- https://github.com/release-engineering/Sync2Jira/pull/405#discussion_r2683208326
- https://github.com/release-engineering/Sync2Jira/pull/405#discussion_r2683211908
- https://github.com/release-engineering/Sync2Jira/pull/404#discussion_r2665584806
</details>


___

<b>Pattern 2: Do not silently continue after failures in critical integration paths (e.g., building Jira field caches, Snowflake connectivity, custom-field resolution); log and re-raise (or raise a clear ValueError) so the run fails loudly and predictably.

There are three parts to emphasize:
- Do not attempt to continue after a critical failure
- Instead, raise an exception which will propagate back to the base of the stack which will cause the tool to discard the current event and continue with the next one: we want the tool to recover and continue running, if possible and reasonable, but we don't want to perform any heroic measures on the part of any single event. (Having the tool hard-crash is generally unuseful, because the infrastructure will restart it, the restart will open a new log, and the original context will be lost.)
- Log information required to understand and address the failure, either at the point of failure or via the raised exception, which will be logged when the stack is unwound.
</b>

Example code before:
```
def build_cache(client):
    try:
        cache.clear()
        cache.update({f["name"]: f["id"] for f in client.fields()})
    except Exception as e:
        log.error("Failed: %s", e)
        return  # continues with partial/bad state
```

Example code after:
```
def build_cache(client):
    cache.clear()
    try:
        for f in client.fields():
            cache[f["name"]] = f["id"]
    except Exception as e:
        log.error("Failed to build field cache: %s", e)
        raise

def resolve_field_id(client, name):
    field_id = cache.get(name)
    if not field_id:
        raise ValueError(f"Could not resolve custom field '{name}' to an ID")
    return field_id
```

<details><summary>Examples for relevant past discussions:</summary>

- https://github.com/release-engineering/Sync2Jira/pull/375#discussion_r2403003292
- https://github.com/release-engineering/Sync2Jira/pull/375#discussion_r2403189630
- https://github.com/release-engineering/Sync2Jira/pull/404#discussion_r2665525408
- https://github.com/release-engineering/Sync2Jira/pull/399#discussion_r2662130914
- https://github.com/release-engineering/Sync2Jira/pull/399#discussion_r2594056370
</details>


___

<b>Pattern 3: Keep try/except blocks minimal and scoped to the single call that can reasonably fail; prefer context managers for resources, and avoid broad excepts that mask unrelated bugs.

The implementation of `try` blocks should be focused on the actions of the `except` clauses: there should be only "one thing" which can go wrong in the body of the `try` block, so that which exceptions are to be caught and what their respective actions should be is clear. Statements which are related to the contents of the `try` block should be placed before or after the block and not included in it, to avoid the possibility of them raising unexpected errors which might trigger erroneous handling.

Similarly, the targets of `except` clauses should be as specific and explicit as reasonably possible. Using hierarchical exception classes is an excellent approach to simplifying exception handling which allows a single clause to handle any of a set of related exceptions.

Context managers can be a superb alternative to `try` blocks.
</b>

Example code before:
```
try:
    conn = connect()
    cur = conn.cursor()
    cur.execute(sql)
    rows = cur.fetchall()
    cur.close()
    conn.close()
except Exception:
    return []
```

Example code after:
```
with connect() as conn:
    cur = conn.cursor()
    cur.execute(sql)
    rows = cur.fetchall()
    cur.close()
return rows
```

<details><summary>Examples for relevant past discussions:</summary>

- https://github.com/release-engineering/Sync2Jira/pull/404#discussion_r2665550385
- https://github.com/release-engineering/Sync2Jira/pull/399#discussion_r2593928187
- https://github.com/release-engineering/Sync2Jira/pull/375#discussion_r2403189630
- https://github.com/release-engineering/Sync2Jira/pull/399#discussion_r2662130914
</details>


___

<b>Pattern 4: Be intentional about logging volume: remove low-value INFO logs, downgrade noisy logs to DEBUG, and avoid redundant logging before raising exceptions to prevent massive log growth in production.
</b>

Example code before:
```
log.info("About to sync PR %s", pr.url)
log.info("Syncing PR %s", pr.url)
try:
    do_work()
except Exception as e:
    log.error("Failed: %s", e)
    raise
```

Example code after:
```
log.debug("Syncing PR %s", pr.url)
do_work()  # exceptions will be logged by the top-level handler with traceback
```

<details><summary>Examples for relevant past discussions:</summary>

- https://github.com/release-engineering/Sync2Jira/pull/405#discussion_r2683150750
- https://github.com/release-engineering/Sync2Jira/pull/405#discussion_r2683072080
- https://github.com/release-engineering/Sync2Jira/pull/399#discussion_r2593995729
- https://github.com/release-engineering/Sync2Jira/pull/404#discussion_r2665525408
</details>


___

<b>Pattern 5: Use Pythonic truthiness checks and short-circuiting to both simplify code and avoid unnecessary work (e.g., `if mapping:` instead of `len(mapping) > 0`, and check cheap conditions before expensive iterations).
</b>

Example code before:
```
if "github_project_fields" in updates and len(github_project_fields) > 0:
    update(github_project_fields)

if any("transition" in item for item in issue_updates):
    description = issue.status + "\n" + description
```

Example code after:
```
if "github_project_fields" in updates and github_project_fields:
    update(github_project_fields)

if issue.status and any("transition" in item for item in issue_updates):
    description = issue.status + "\n" + description
```

<details><summary>Examples for relevant past discussions:</summary>

- https://github.com/release-engineering/Sync2Jira/pull/405#discussion_r2683003809
- https://github.com/release-engineering/Sync2Jira/pull/405#discussion_r2683011856
- https://github.com/release-engineering/Sync2Jira/pull/298#discussion_r1975579347
</details>


___

<b>Pattern 6: Keep tests focused and maintainable: assert the right behavior (not incidental implementation details), mock helper functions instead of re-testing internals, and prefer consistent patching patterns (e.g., decorators/patch.dict).

This pattern addresses several aspects of writing maintainable tests:
- Unit test assertions should test intended (visible) behaviors and not implementation details. The external behavior is what we care about, and we want to leave the internals free to be refactored or rearchitected.
- We should be conscious of what constitutes the "unit" that we are testing. In most cases, it is simpler to test a single function with its subroutines replaced by mocks. However, this is not always the case, and so the approach should generally reflect whatever is most expedient.
- Be consistent about how we patch things, so that readers and subsequent developers are not surprised and don't have to embrace a new idiom for each test they encounter.
</b>

Example code before:
```
@mock.patch("module.issue_handlers")  # dict patched as attribute
def test_x(self, handlers):
    handlers["k"].return_value = None

self.assertEqual(len(cache), 4)  # incidental, not spec
```

Example code after:
```
@mock.patch.dict("module.issue_handlers", {"k": MagicMock(return_value=None)})
def test_x(self):
    ...

# Assert explicit contents / invariant instead of incidental size
self.assertEqual(cache, {"priority": "priority", "summary": "summary"})
```

<details><summary>Examples for relevant past discussions:</summary>

- https://github.com/release-engineering/Sync2Jira/pull/404#discussion_r2665572801
- https://github.com/release-engineering/Sync2Jira/pull/399#discussion_r2594045631
- https://github.com/release-engineering/Sync2Jira/pull/375#discussion_r2403221096
- https://github.com/release-engineering/Sync2Jira/pull/289#discussion_r1941816872
- https://github.com/release-engineering/Sync2Jira/pull/404#discussion_r2669219878
</details>


___

<b>Pattern 7: When Black makes the code less readable, feel free to use tricks like introducing local variables, using single strings (which Black won't break), or putting breaks in strings (which Python will automatically re-join) to restore readability.
</b>

Example code before:
```
# Black reformats this to be less readable
log.error(
    "Failed to sync %s/%s from %s to JIRA project %s component %s",
    repo_owner,
    repo_name,
    upstream_url,
    jira_project_key,
    jira_component,
)
```

Example code after:
```
# Use a local variable to keep it as a single line
msg = "Failed to sync %s/%s from %s to JIRA project %s component %s"
log.error(msg, repo_owner, repo_name, upstream_url, jira_project_key, jira_component)

# Or use a single string that Black won't break
log.error("Failed to sync %s/%s from %s to JIRA project %s component %s", repo_owner, repo_name, upstream_url, jira_project_key, jira_component)
```


___
