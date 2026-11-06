# SDK-guided semantic observer verification

The SDK provides semantic names for application-owned objects. The
[Calendar and DMCSR crosswalk](sdk-calendar-dmcsr.md) provides private
allocation evidence for a pinned build, and the
[database crosswalk](sdk-calendar-database.md) identifies what persists
after an application closes. Use these as distinct evidence sources in
the [Observatory v2 semantic diagnostics](observatory-v2-spec.md#f9-semantic-deskmate-diagnostics-p2).

## Observer design

1. **Resolve the loaded identities.** Store an app profile and a DMCSR
   profile keyed by full module digests. A profile records SDK layout
   provenance, verified code anchors, applicable selector family and
   observation limits. Re-establish the launch, reset, task, code and
   data mapping before use. The documented CSR task-vector word is a
   candidate locator to validate against the independent register-derived
   base. A stale mapping yields unknown even if old descriptor bytes match.
2. **Classify live context separately from forms.** Use the mapped window
   pool, parent boundary, record ownership and handle transitions to
   distinguish a held input context from the day baseline. Report
   draw-only, between-run and nested states only after controlled
   calibration. Inspect geometry inside the allocated outer record and
   retain ambiguity when signatures collide. A selected child is evidence
   about dispatch, and its handle can be reused.
3. **Resolve a form within the verified application.** Join the active
   context to an application descriptor through a verified call or owner
   association. Check the frame pointer, extents, counts, pointer bounds
   and expected component types. Use a profile's title-pointer token to
   distinguish Add from Change after verifying that association. Keep
   raw title and text private. Expose the least detailed known semantic
   label, such as editor style, when form identity is still ambiguous.
4. **Attribute focus and events to the same capture.** Read `focus_index`
   only inside the verified form, bound it by the table count and check the
   referenced component. Keep the low focus mirror and event-return bit
   separate in a future diagnostic. Retain the current strict replay gate
   and independently labelled captures while calibrating state. A returned
   command, a transient event and a settled component focus are distinct
   observations. Label event-derived transitions as such. Keep pending
   event-buffer reads out of the first implementation.
5. **Publish reviewed facts from the owner.** Keep the existing
   producer-pushed, read-only boundary. Emit checkpoint identity, guest
   time and freshness, module/profile identity, classification and evidence
   status. Publish unknown for partial or contradictory inputs. Preserve
   raw memory and disk evidence privately. Closed-file data such as saved
   screen mode is useful in an offline trace or persistence test and
   belongs outside the live UI state predicate.

Implement in this order. Extend offline replay with explicit per-stage
evidence and negative cases before introducing a new collector. Keep the
working Calendar decoder bounded to the validated launches and forms.
Then add the two application profiles after independent controls. The
current investigation leaves the observer's behavior intact.

## Experiment priorities

The [controlled Add and Change trial](calendar-live-dialog-identity.md)
completed priority 1. Its scoped offline replay now requires the held
allocation, Calendar descriptor ownership, frame and table association,
and the matching editor title token before emitting a named editor.

The remaining experiments are proposals. Use a separately provisioned disposable
clone with the RSX/DOS 5.00, 86Box, ROM, graphics-mode and module pins in the
[activation report](calendar-dialog-activation.md#repeat-clone-runtime-pins),
or record and explicitly review any changed pin. Copy and hash source
media, configuration and NVRAM. Use the authenticated native loopback
socket with one owner. Prepare each range for separate approval before
collection. Independently label held visual states, recheck relocation-free
anchors, and use normal-view width-one reads. Duplicate reads at a
checkpoint advance **0 ms**. Record exact guest clocks and frames,
timing pads, reset counters and source and final hashes. Preserve the
approved samples privately. Stop on an unexpected label, mapping change
or failed restore. The surviving research checkpoint is outside the plan.

| Priority | Controlled comparison and budget | Predicted result and interpretation |
| --- | --- | --- |
| 1. Add versus Change | From the same E02 selected day, run separate A/B/C trials for Add and Change with Escape, plus Find Date and idle controls. Target the previously validated 1,236 ms open and 604 ms cancel intervals, with timing pads after independent visual settlement. Use the existing two DMCSR anchors, six context bytes and B-only four geometry bytes. Add the two Calendar code anchors and two title bytes described in the [identity report](calendar-dialog-identity.md#add-event-and-change-event). Remap every range for the new clone. | Add and Change should match the 4,500×2,860 frame and predict the same `+3/+10` pattern if the active child has the same allocation shape. The two title offsets at B should be `0536` and `0540`. C can retain them while the window boundary restores. A mismatch in Add depth limits the count rule, while a title mismatch under verified ownership limits the mode rule. Idle and Find Date test false attribution. The final closed disk should equal the E02 source. |
| 2. Sampling and task-context control | Reuse an E02 clone and compare selected day, open Event menu, settled Change, and restored day. Run a matched idle sequence and one bounded opening and unwind sweep with at most 220 and 180 one-ms register stops, respectively. After static review of each checkpoint, compare only the six context bytes and the four bytes at physical `0x0384..0x0387` against register-derived bases. Read optional outer geometry only when the whole outer record is allocated. | The task word should equal the DMCSR context segment at the verified DMCSR stops. The menu may have its own allocations. Draw return and run return should restore their parent boundaries even if a form is still on screen between calls. If held samples miss those intervals, report that sampling limit and retain unknown outside the settled pattern. Establish a separate task-switch test only after this baseline. |
| 3. One-bit Calendar file test | Make sibling E02 disk copies. From the same selected day, open Change on each, leave all text and times untouched, and use identical save/exit sequences from day view. Toggle only Alarm in the trial. Use another cancel control. Check visible input and resulting state, close Calendar before imaging, then diff the whole database and installed-tree hashes. Keep RTC, alarm timing and saved screen mode matched. | Ordinary Protected should be `31` in the control and `71` in the trial at the indexed row. The config screen byte should stay `65`. Extra differences require inspection of alarm service state or DB write behavior. Once confirmed, use distinct disposable tests for blank time, end midnight, reminder and annual occasion. Those are separate parser-profile gates. |
| 4. One modal per additional app | On disposable data, identify the Address Book Add List Name and Filer Print Form routes using their labels. Establish a separate held baseline in each app. Observe one open/cancel cycle and matched idle, using re-mapped six context bytes, B-only outer extents, and a bounded three-byte descriptor prefix read starting at `+3` if independently approved. Verify their app and DMCSR anchors first. Do not accept the name or submit a print job. | Predict the respective static frame extents 3,500×1,540 and 3,000×1,430. Both tables contain three components. Predict `+3/+4` only under the same one-marker, one-outer, one-child and one-small-record-per-control shape as Find Date. Address Book should initialize `+3` within range before use. A different count with matching frame is evidence for a distinct profile. Cancel should restore the baseline and preserve the selected database. |
| 5. Physical DB limits | First use the named read/update/build entry paths to locate the exact on-disk index and allocator consumers offline. Only then design a new differential fixture around one remaining boundary, for example a non-tail replacement sized just below and just above the available slot under the [E19 controls](../experiments/e19-space-pressure.md). Keep schema, record order and close path identical. | The current candidate is that the fitting row can occupy available space without growth and the oversized variant requires a different placement. Record exact page/index/counter deltas. Treat the API record maximum as an input to the test, with allocation behavior decided by the images. |

A help-only watch, a fresh measurement of the two already observed settled
focus indices, and a rerun of the known E01/E02 screen-byte correlation
are lower priority. The SDK and verified static paths now answer those
questions at the level needed for the current profiles. A broader claim
about the event-return bit, nested help, or saved modes across other apps
would need its own controls.
