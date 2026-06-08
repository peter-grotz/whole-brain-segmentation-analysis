"""Run a neuron-tracing-utils module after registering the jzy3d Maven repo.

Fiji 2.14 transitively depends on ``org.jzy3d:*:2.2.1``, which scijava.public and
Maven Central no longer serve (they live only on https://maven.jzy3d.org/releases).
scyjava bootstraps the JVM via jgo's pure-Python resolver
(``jgo.build(..., resolver=PythonResolver(lenient=True))``), and that resolver only
searches the repositories in ``scyjava.config`` (plus Central). There is no
environment variable or config file for it, so the supported way to add a repo is
``scyjava.config.add_repositories(...)`` *in-process, before* ``scyjava.start_jvm()``.

The pinned neuron-tracing-utils calls ``start_jvm()`` itself and can't be edited
here, so this shim registers the jzy3d repo and then executes the requested module
as ``__main__`` -- the exact equivalent of ``python -m <module> <args...>``.

Usage:  python /code/jvm_repos.py <module> [args...]
"""
import runpy
import sys

try:
    import scyjava.config

    scyjava.config.add_repositories(
        {"jzy3d-releases": "https://maven.jzy3d.org/releases"}
    )
except Exception as exc:  # pragma: no cover - never block the run on this
    print(f"jvm_repos: warning: could not register jzy3d repo: {exc}", file=sys.stderr)

if len(sys.argv) < 2:
    sys.exit("usage: python /code/jvm_repos.py <module> [args...]")

module = sys.argv[1]
# Shift argv so the target module sees args as if launched via `python -m module ...`
# (runpy with alter_sys=True overwrites argv[0] with the module file and keeps argv[1:]).
sys.argv = sys.argv[1:]
# `python -m` puts the current working directory on sys.path; `python script.py`
# puts the script's dir instead. Restore cwd-on-path so behavior matches `-m`.
sys.path.insert(0, "")
runpy.run_module(module, run_name="__main__", alter_sys=True)
