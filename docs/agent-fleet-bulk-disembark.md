# Fleet agents follow bulk army disembarkation

User-authorized behavior: when the transported army disembarks, bring the fleet's agents with it. Their prior attachment to an army is irrelevant. Preserve the three-agent capacity of a fleet, army or town. Fertility work is deferred until this issue is resolved.

The original embark action transfers the army's attached characters to the fleet using native `105FF5D0`. The unload action detaches the carried army with `105F2990`, leaving those transferred characters on the fleet. The correction performs the native transfer in the opposite direction before the original unload.

Original bytes establish that the carrier's `+BCh` reference pairs with its carried army's `+DCh` reference (`105F82B0` -> `105CC670`), and that `103E5960` dereferences these handles. The adapter gets the actual carried army from this pair; it does not infer it from the currently selected agent or a unit record.

The sole hook is the `CALL 105F2990` at `108A7A52` in `navy_disembark` action `108A7A10`. It calls a 91-byte handwritten x86 adapter at `11D8D800`, inside verified zero padding in the existing mapped executable `.ubfix` section. No PE layout/section-size change or compiler is used. Relative branches/native calls preserve ASLR compatibility.

The adapter preserves all general registers and EFLAGS, dereferences the existing carried-army link, rejects null/self destinations, and checks that both counts and their total are at most three. It calls native `105FF5D0` with ECX=destination army and one stack argument=source fleet (native RET 4), then restores the caller state and tail-calls unchanged `105F2990` (no stack arguments). The native helper handles unlinking/relinking, position updates and notifications. No passenger record is manually spliced or destroyed. A rejected/capacity-inconsistent transfer leaves vanilla unloading behavior in place rather than exceeding the limit.

Agent-only manual disembarkation remains unchanged. Landing eligibility, movement/pathfinding, hostile landing resolution and army movement itself remain the original implementation. This hook is specifically the bulk army-unload action; independent assault-action routes have not been claimed as verified by this trial.

Static verification compares the complete candidate DLL with the current accepted engine and permits only the five-byte call-site plus the 91-byte adapter. Byte-decoded execution with native contract stubs checks 480 cases covering zero to three agents, invalid/over-capacity counts, existing army agents, null/self destinations, preserved registers/flags/stack, and relocated call addresses. These are ABI/emulation checks, not live engine or gameplay tests.

Files: `tools/emit-agent-fleet-disembark.py`, `tools/verify-agent-fleet-disembark.py`, `tools/install-agent-fleet-disembark.py`, and `patches/engine/232-agent-fleet-bulk-disembark.json`. The release recipe remains disabled for packaging pending gameplay verification; the explicit local installation overlays the existing managed DLL without reconstructing the historical source baseline.

Before installation the installer makes and verifies a complete backup of the current managed build and root launcher/bootstrap under this project's `build/backups`. It preserves all earlier engine and fear-data changes, records the previous engine overlay as `previousOverlay`, and leaves the signed base package unchanged. Receipt: `outputs/agent-fleet-disembark-installed.json`.

Required gameplay comparison: bulk-land fleets with one, two and three agents in Shogun 2 and FOTS; include agents boarded independently and agents boarded with the army. Confirm passengers leave the fleet, appear ashore, can move, and can re-embark without duplication. Also test no-agent landing and manual single-agent landing. These remain pending user testing.
