"""The maintainer published 153.1.0 and added its discussion by hand on github.com, bypassing
the orchestrator (which had already exited after the Gate 2 rejection during the changelog-bug
investigation). This runs the rest of what phase_publish() + _finish_build() would have done -
everything except notify.await_decision and publish.publish_release, since the GitHub side is
already done. Uses the real orchestrator/publish functions so this is exactly what the
pipeline itself would have run, not a reimplementation.
"""
import common
import orchestrator
import publish

state = common.load_state()
logger = common.setup_logging("manual-finish-publish")
config = common.load_config()
ctx = orchestrator.Context(config, logger, state)

assert "build" in state, "no in-progress build in state.json"
version = ctx.build["version"]
assert version == "153.1.0", f"expected 153.1.0, found {version}"

tag = ctx.build["tag"]
repo_dir = config["project"]["repo_dir"]
branch = config["project"]["branch"]

publish.sync_patch_stack(repo_dir, ctx.source_dir, tag, logger=logger)
publish.regenerate_patches_readme(repo_dir, ctx.source_dir, tag, branch, logger=logger)
publish.sync_docs_files(repo_dir, ctx.source_dir, logger=logger)
publish.sync_automation(repo_dir, common.AUTOMATION_DIR, logger=logger)
publish.prepend_changelog(repo_dir, ctx.build["changelog_entry"], logger=logger)
publish.commit_push_tag(repo_dir, version, logger=logger)

orchestrator._record_vt_history(ctx)
orchestrator._finish_build(ctx)

print("done")
