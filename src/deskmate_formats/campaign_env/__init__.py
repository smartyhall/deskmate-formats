"""Campaign-scoped Python environments and proven execution identity.

Several research campaigns share this laboratory VM.  Each has a checkout, a
mutable environment and child processes, and on this host every one of them can
resolve ``deskmate_formats`` through the same globally installed wheel unless
something makes it stop.  Naming a checkout, or exporting ``PYTHONPATH``, is
not evidence about what a process executed: ``python -I`` discards
``PYTHONPATH``, the user site directory and ``PYTHON*`` variables, so an
isolated child of a campaign runs whatever the *interpreter that launched it*
has installed.

The submodules keep three separate facts separate:

``identity``
    a checkout's Git revision and a package tree's content digest, recorded
    separately from which module a running interpreter actually imported;
``environment``
    a campaign-owned interpreter, and this source installed into it;
``launch``
    isolated child argument vectors built from an explicitly chosen
    interpreter, with a receipt for what ran;
``probe``
    the child-side entry point that reports its own resolution as JSON;
``preflight``
    compares the request against the observation and refuses to qualify a
    measurement whose identity is unknown or mismatched;
``inventory``
    read-only inventory of interpreters, environments and ``-I`` launch sites;
``receipts``
    durable receipts, plus a redacted projection that is safe to publish.

Only the standard library is used.  Nothing here changes global Python
configuration, another campaign's environment, an existing installation, or
the production isolation flags.

This module deliberately re-exports nothing: ``probe`` is imported by an
isolated child whose only job is to report its own resolution, so importing the
package must stay cheap.
"""

__all__ = [
    "cli",
    "environment",
    "identity",
    "inventory",
    "launch",
    "preflight",
    "probe",
    "receipts",
]
