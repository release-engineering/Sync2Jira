
<b>Pattern 1: Add explicit unit tests for each early-exit/guard branch introduced in a PR (especially for None/empty config values), so behavior is specified and regressions are caught.
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

<b>Pattern 6: Cache stable identifiers (e.g., Jira issue key/ID) rather than ORM/resource objects, and refresh/fetch the current object when needed to avoid stale data.
</b>

Example code before:
```
cache[url] = jira_issue_obj  # mutable/stale ORM object

def get_issue(url):
    return cache.get(url)
```

Example code after:
```
cache[url] = jira_issue_key  # stable identifier

def get_issue(client, url):
    key = cache.get(url)
    return client.issue(key) if key else None
```

<details><summary>Examples for relevant past discussions:</summary>

- https://github.com/release-engineering/Sync2Jira/pull/398#discussion_r2569771392
</details>


___

<b>Pattern 7: Keep tests focused and maintainable: assert the right behavior (not incidental implementation details), mock helper functions instead of re-testing internals, prefer consistent patching patterns (e.g., decorators/patch.dict), and improve readability by using local variables when formatting tools create noise.
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
