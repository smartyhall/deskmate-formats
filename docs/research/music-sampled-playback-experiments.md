# Sampled Music playback experiments

Start with the [retained DAC baseline](pssj-dac-capture-20261118.md) and the
M11, HELD7 and SLOT8 controls. Their observed effects include octave
transposition, signal lasting beyond the source sample, and selection of an
explicitly ranged sample for the two tested notes. Use a disposable clone,
the same RSX/OEM run profile, one newly named DAC file per group of controls,
and the authenticated loopback socket. Record the applied configuration,
input hashes, exact emulated sample spans and start/end transition receipts.

| Step | Change from the previous matched control | Distinguishing observation |
| --- | --- | --- |
| 1. Establish sample regions | Give the three regions of the existing LABINST control distinct clean tones at modest amplitudes. Keep the measured region boundaries at frames 1,100 and 2,200 and preserve the loop metadata. Play once in Sound and save a disposable native copy. | Verify the serialized descriptor and PCM after the save. In Sound playback, the region sequence identifies the boundaries independently of Music. |
| 2. Sustain and release | Play the marked sample as a short C4 and a whole C4 in Music at a fixed tempo and dynamic. If the middle signature repeats, change only one loop boundary and repeat the long note. | The signature order and number of cycles distinguish intro, loop, and release. A boundary shift should move one periodic transition. A tail signature after the loop would identify release playback. |
| 3. Range precedence | Give the two S10 descriptors distinct tones and equal root pitch. First test disjoint ranges with notes just below, on and just above each boundary. Then overlap the ranges and reverse descriptor order in a second file. Include the unset-range control. | Identify the sampled descriptor at endpoints and inside the overlap. Reversing order distinguishes order-dependent resolution from a range-priority rule. Repeat with a single instrument file visible to avoid duplicate-slot effects. |
| 4. Transposition and gating | With only one descriptor, play C4, a nearby non-octave pitch, and C5. Compare a short note, long note, and two tied short notes at fixed tempo, then vary tempo alone. | Compare frequency ratios and region transition times with written pitches. Measure onset, active duration and silence after each gate. For ties, check whether the intro restarts or the same sample position continues. |
| 5. Dynamics and mixing | Measure a single stable note at low, middle and high dynamics, keeping the sample amplitude fixed. Capture each of two distinguishable voices alone and then together, with matched starts and volume. Increase amplitude only after a low-level mix control. | Compare peak and RMS over the same steady-state sample span. Compare the combined capture against the aligned isolated contributions. Note clip limits, any redistribution between voices, and whether a second voice changes the timing of the first. |

Use wide frequency separation in the region markers so transposed tones
remain identifiable. Inspect a short spectral window or correlate against
the known PCM when two components overlap. The crossing estimator in the
DAC analysis utility is intended for a single clean tone. Capture all
transition times on the 48 kHz emulated DAC timeline.

For playback implementation, the first parity target is a one- or
two-voice synthetic score that independently identifies sample selection,
transposition, loop behavior and audibly distinct note gates. Extend that
control with dynamics and mixing before adopting a historical score as a
parity case. The [historical Music inventory](music-control-inventory-20261118.md)
gives separate priorities for accidentals, repeat execution and markers.
