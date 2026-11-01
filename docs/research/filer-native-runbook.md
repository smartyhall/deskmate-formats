# Filer F00–F02: minimal native operator runbook

**Prepared only. No Filer native experiment has run.** This runbook adds sharper
questions without replacing the preserved F00 baseline or its original report.

## Preparation and evidence

A research assistant should verify hashes and prepare a fresh disposable copy
of the existing F00 before installation. Keep
DOSLAB EXPERIMENTS/FILER/F00_baseline/before, run, manifests and sealed evidence
unchanged; use a new clearly named native-control directory for execution.
The existing run copy is evidence too. Do not mount original media or earlier
experiment trees writable.

Before the operator starts: verify all126 source files, save a complete before
snapshot/manifest and working path/size/timestamps, record parent manifest/hash,
and independently check the mounted disposable directory. The operator should
only perform native actions and capture the few decisive screenshots below.
No guessed launch command, menu path or shortcut is supplied: **Filer's entry
point and schema workflow have not been observed**.

Record screenshot filenames and concise actual action descriptions in order.
For each mutation capture the full visible values before its single save.
Never replay an ambiguous save; inspect the resulting state first. Stop on
unexpected destructive/overwrite prompts or inability to establish which copy
is open. Do not “repair” files with a binary editor.

## F00 — no-edit launch/exit

1. Capture F00-00: disposable environment/path before launch. Open Filer using
   the actual available DeskMate control. Record its label and any launch command
   actually used. Capture F00-01: initial screen/title, open filename and count
   if shown; record whether a file picker appears.
2. Inspect only the minimum controls needed to determine opening/creation,
   schema editing (possibly Form Setup) and normal exit. Capture F00-02:
   relevant menu/dialog labels. Do not create/edit data, change layout, save
   a sample or accept an overwrite. If launch requires choosing a file, record
   which shipped file and why; inspect it without editing.
3. Exit normally using the observed control. Capture F00-03: confirmed clean
   exit/DOS prompt. If save is unexpectedly requested, capture it and record
   the decision; preserve that case rather than claiming a clean no-edit control.

After visible clean exit, assistant records working timestamps before copying,
then complete after snapshot/manifest. Compare all files, additions/deletions,
sizes/hashes and exhaustive byte deltas. Timestamp-only changes are distinct
from content changes (ADR A00 demonstrated this). A creation prompt or compulsory
change makes a different control condition and must be reported explicitly.

**Questions answered:** actual entry point, application/form-design relationship,
sample role and incidental launch/exit writes. No-edit byte identity is a result
to measure, not a prerequisite to assume. Explain all unexplained differences
before F01.

## F01 — smallest accepted empty schema

Start from a verified independent copy of F00's clean final installation,
retaining its exact hash lineage. Filer/Form Setup ownership of schema creation
must follow what F00 actually revealed.

1. Select the observed creation/schema control. Propose a new base filename
   FREC01 and one text field FTXT_A of length24 **only if supported**. Capture
   F01-00: actual schema screen with name, type label, length and required
   defaults. Record the actual extension; do not impose .FIL from this plan.
2. Use the minimum schema the native UI accepts. If additional sections/fields,
   form positioning or a Form Setup handoff are mandatory, record them and take
   one screenshot of the resulting schema. Do not invent a shortcut or silently
   accept a larger schema as equivalent to the one-field design.
3. Save once and verify zero user records if a count is displayed. Capture
   F01-01: saved empty database with its title/count. Exit normally; capture
   F01-02: clean exit. If save semantics are unclear, record the actual prompts.

Assistant takes a complete saved snapshot. A read-only reopen should confirm
field definition and zero records; capture F01-03 only if those are visible.
Exit normally, record timestamps and complete after snapshot; compare saved
versus reopened contents as well as F00 parent versus F01. Preserve auxiliary
files even if the schema is not stored in .FIL.

**Questions answered:** native signature, directory grammar, starting DATA/index
blocks, self-schema row consistency, five-versus-six descriptor fields, default
rows and which application writes schema. A nonzero count must be explained
before calling this an empty user database.

## F02 — one distinctive synthetic record

Start from the exact verified successful F01 final state, in a new disposable
copy. Do not derive this experiment from a shipped sample.

1. Invoke the observed record-add control. Enter **F02_VALUE_7Q9** once in the
   FTXT_A field (or the documented actual equivalent). Leave optional fields
   untouched. Capture F02-00: full exact value, field label and any defaults.
   Record actual actions and every nonempty default.
2. Save once using the observed native operation. Capture F02-01: resulting
   record and count1 if available. Exit normally; capture F02-02 clean exit.
   Assistant immediately preserves the complete saved tree before reopening.
3. Read-only reopen: capture F02-03 showing the exact value and single record.
   Exit without editing. Record timestamp inventory and complete final snapshot.

Assistant compares F01→saved and saved→final across the complete installation,
including new/deleted files, full byte deltas and block maps. Search the new value
as literal ASCII but retain evidence if it is encoded differently. Test candidate
row framing and index target/ID; compare count/next-ID-like tokens and actual
field count. Check whether only DATA changed or layout/graphics/default state
also changed. Do not label an unknown number as a counter solely because it
increased. Do not presume ID10 is a control row: ADR's first visible contact
already disproves that cross-application assumption.

**Questions answered:** shared framing/index machinery in a newly native-created
file, literal payload storage, application defaults, counters and save/reopen
stability. Deletion, second-record ordering, long fields and page allocation are
separate future experiments, not extra actions in F02.
