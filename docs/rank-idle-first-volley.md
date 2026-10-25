# 0.1.7 initial rank-idle trial

This trial is built from the exact 0.1.3-naval-test source baseline, with the existing yari, kneel-movement and naval fixes. The sole new gameplay intervention is initial ranked preparation cancelling named standing idle clips141..157. It includes no reconstructed packs or pack redirect.

The restored-build read-only battle capture confirms two soldiers blocked type-5 STOP_STATE on idle155 STAND_TRAINED_IDLE_4. Movement was finished, requested delay zero, and no movement lock was active. The following transition62 STAND_TRAINED_TO_COMBAT_READY remains untouched. See `rank-fire-live-baseline.md` for timing and sampling limits.

The 90-byte adapter at115A0DA0 detours only10188290. It requires the rank-task vtable, initial cycle, no prior group fire, current group zero and an ordinary preparation call. Only a nonnull clip with ID141..157 is cancelled using native103CA920. The complete original request construction then runs. Readiness, movement completion, loaded/reload routing, aim/stance transitions and later rank cycles retain their original checks.

Support recipe000 explicitly maps through115A0DFF; no reliance on PE page rounding or recipe090. There are no new absolute addresses or relocations. The trial is initial-preparation-scoped per newly created rank task, not globally once per battle.

Build validation includes the installer self-tests, inherited yari/kneel/naval native checks, and1554 original/candidate cases covering every standing-idle ID, excluded reload/stance IDs, task/phase guards, integer boundaries, nonvolatile-register/stack sentinels, and integration with original STOP/START evaluators. These are controlled native fixtures, not a substitute for battle A/B and synchronized later-volley/kneeling observation.

Version0.1.7-rankidle-test is an experimental test candidate. No specific seconds saved, total-delay removal or completed gameplay validation is claimed until the patched battle comparison is captured.
