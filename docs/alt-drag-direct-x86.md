# Alt-drag: direct original-game x86 patch

Status: local candidate installed on the user's current build on 2026-11-07.
User confirmed R5 works: "perfect it works". Acceptance receipt:
outputs/alt-drag-r5-user-acceptance.json. Recipe remains disabled for release
packaging; this local acceptance does not claim publication or multiplayer tests.
The installed version
is 0.1.45-graphics-unlock+alt-drag-direct-local-r5-ce-sensitivity, preserving the 0.1.45 base fixes.
Receipt: project-root outputs/alt-drag-direct-installation.json.

## Revision 5: exact CE rotation-rate reference

The user replaced the percentage adjustment with a requirement to match CE.
R4's temporary +25% setting was installed before that steering, then superseded
by R5. The user explicitly approved read-only inspection of CE's original DLL
for its coefficient and mouse-coordinate scale. No CE patch project was used.

CE original DLL SHA256:
f1b609dffb95c1fa6b155264fdea0fc73e74c235dfc4e00b0d7e66076937b64e.
CE 181661739 multiplies its UI mouse-X delta by float 182352CA8:
`89 9B D0 42` = 104.30377960205078 native turn units per UI-coordinate unit.
CE 18012A860 rounds using sign-dependent +/-0.5f followed by truncation.

CE UI global 1833667E8 is populated by 18147DC70 from UI dispatcher 181613B70.
OG's corresponding UI stream is 11BBEAB0, populated by 10F938E0 from 110C5560.
R5 uses that OG float stream for previous/current rotation X, retaining normalized
hardware coordinates only for the existing drag threshold. It uses the exact CE
coefficient bits and rounding. No x64 function, register ABI, structure offset or
machine-code body was transplanted into OG.

The verifier checks coefficient bits, three OG UI-X reads and +/-half rounding
instructions, alongside the existing native ABI/branch/stack checks. Reference:
build/ce-rotation-sensitivity-reference.json. Float formula sanity cases:
build/ce-rotation-parity-cases.json. In-game feel comparison remains pending.
Earlier fixes and movement sound remain unchanged. Installation receipt:
outputs/alt-drag-ce-sensitivity-r5.json.

## Revision 3: movement feedback and Ctrl+Alt rotation

The user requested regular movement-order sound and rotation while holding
Ctrl+Alt. The native coordinate writer 10BD4A10 stores normalized FLOAT X/Y in
117ACF84/88, returned by 10BD4D70. The UI coordinate fields used in R2 are also
floats; interpreting their bits as integer pixel deltas made rotation unreliable.
R3 stores normalized floats and converts deltaX * 65536.0 to native turn units.
It samples physical left/right Ctrl AND left/right Alt through 10BD12A0. The
chord works when held at gesture start or added during Alt-left dragging.
Switching back to translation retains the continuity anchor.

R3 calls the ORIGINAL regular movement feedback tail at 102E846B after at least
one target is queued successfully. This unchanged native tail builds the request
and plays UI event 12Eh once. The thunk reproduces its verified F4h local frame
and four saved registers; the original epilogue ends in RET 8. The verifier checks
the tail/epilogue bytes and stack/rejoin depth. No audio file or sound system was
replaced. No feedback is issued for previews, cancellations or clicks without drag.

All R3 changes are confined to Alt-drag's own appended code/constants. Earlier
fixes and unrelated installed files are unchanged. R3 sound/rotation needs the
user's in-game retest. Receipt: outputs/alt-drag-feedback-rotation-r3.json.

## First-use crash and revision 2

The user's first test crashed immediately. The dump records execute access
violation 0xC0000005 at UI + 10Ch, with ESP pointing into the saved PUSHAD frame.
The original DLL's 10436690 takes ECX = multiple selection and one stack argument
= battle model, and ends in RET 4. Its Ghidra declaration omitted that argument.
R1 supplied neither the correct ECX nor the stack argument; RET 4 displaced the
caller return address. R2 uses the exact setup at native call-site 11101E74-79.

The corrected verifier rejects R1's stack imbalance. R2 passes, with reachable
return instructions independently audited for all 26 native call contracts.
Installation changed only 1,693 bytes inside Alt-drag's own appended code.
No rollback occurred. Earlier fixes and unrelated installed assets are unchanged.
The user explicitly said not to restore: fix in place, keep the feature present,
and do not remove it or roll back without another user instruction.
R2 still requires an in-game retest; no successful gesture is claimed yet.

## Source and workflow boundary

The game reference material used is the original 32-bit DLL, its permitted
Ghidra exports, the permitted CE Ghidra exports, and the separately user-approved
CE original-DLL read for exact rotation sensitivity and input scale.
CE supplied behavioural comparisons only. CE's 64-bit machine code, layouts,
register conventions, offsets and command implementation were not transplanted.
No other project's source, dependencies, symbols, mappings or implementation
were used. The previously rejected compiled candidate is not referenced.

`tools/emit-alt-drag-direct.py` writes explicit, handwritten x86 opcode blocks
into a guarded recipe. It invokes neither a compiler nor an assembler. All
native order, projection, footprint and ghost-formation logic remains in OG.
Its only inspection image is under this project's existing `build` directory.

Original DLL SHA-256:
`022fae2e2da92b59b8b1b8ee52887003c624e3c8eca060b209f5d792a7f874f5`.
Previous installed baseline SHA-256:
`a306512f3e571266f810392285b80caa1d15d525ddf9576b229b2fd9a669147d`.
Current managed DLL SHA-256:
`a0a8df960eccc629ebd7b22c7c41071b6762472ef0f094696dce509eb683e631`.
All 25,799,168 previous DLL bytes were compared: only the 43 guarded hook/header
bytes differ, and 18,944 bytes were appended. Existing .ubfix contents are intact.
Only the managed DLL and its install-state metadata were changed. Private packs,
vanilla engine, bootstrap, launcher and signed base package were not changed.

## Native evidence and contracts

Addresses below describe this exact original DLL; they are not CE addresses.
Targeted disassemblies are `build/alt-drag-direct-*.asm`.

| OG address | Verified role |
| --- | --- |
| `110F81E0` | Left button down, ECX = full battle UI, no stack arguments |
| `110F83E0` | Left button release, ECX = full UI, one cancellation argument, RET 4 |
| `11101E10` | Preview update, ECX = full UI, no stack arguments |
| `110FB980` | Mouse callback, ECX = UI + 18h, three stack arguments, RET 0Ch |
| `110FAB3A` | Key callback detour after native CMP, before PUSH EBX; original flags replayed |
| `101CE380` / `101D10F0` | Clone/destroy OG's 68-byte multiple selection |
| `1042DFD0` | Generate current targets at zero forward displacement; RET 10h |
| `10419B40` | Copy a native target vector; RET 4 |
| `10399F80` | Resolve a 20-byte native path location to world XYZ; RET 4 |
| `1037B430` | Project an OG position finder request to a path location; RET 0Ch |
| `10264600` | Initialize the native 72-byte offset preview proxy; RET 10h |
| `10295A90` | Expand group and individual target vectors into native ghost formations; RET 8 |
| `1029A6F0` / `102E5C30` | Native ghost and full preview validity checks |
| `110EEC30` | Dispose previously submitted native previews through UI + CCCh |
| `1047ED90` / `1047ECA0` | Resolve a target's group handle / individual unit handle |
| `102557E0` | Native width/orientation packet constructor, establishing its layout |
| `102E6F00` | Synchronous native width/orientation packet serialization |
| `1023D220` | Native queue sender for the existing width/orientation command; RET 4 |
| `102A8F60` | Existing command receiver; remains unchanged |

The first output vector of `1042DFD0` contains group handles. The second contains
individual unit interfaces. Each target is 32 bytes: handle at +0, native path
location at +4, 16-bit facing at +18h, and width at +1Ch. Treating an individual
handle as a group handle would call the wrong virtual resolver; the recipe
keeps those vectors separate throughout capture, preview and serialization.

The physical key table independently confirms Escape ID 0, left Ctrl ID 1Ch,
left Shift ID 29h and left Alt ID 37h. Full UI modifier fields are +58Ah Alt,
+58Bh Ctrl and +58Ch Shift. Full UI pointer identity and battle model identity
are checked before using a saved selection.

The footprint rectangle contract comes from OG's `1041CDF0`: its four corner
equations establish the centre and bounds used to find the common pivot.
Translation and rotation operate on captured native targets. Each target's
width is retained. Ctrl transitions reset the translation anchor to avoid a
jump when switching between rotation and translation.

CE registers a separate move-and-rotate-by-offset drag command. OG does not.
This candidate instead emits OG's existing native width/orientation commands,
one per captured group or individual target. It changes no receiver, command
ID, network format or replay schema. Multiplayer/replay compatibility still
requires runtime validation and is not claimed from this static trace.

## Recipe and static validation

Recipe: `patches/engine/231-alt-drag-direct-x86.json` (disabled).
The five detours check exact original bytes and replay complete instructions.
The existing `.ubfix` section is extended for the direct byte stubs and private
gesture state. Its permissions, raw/virtual sizes and image size are updated.
No new DLL import, external engine module or relocation entry is introduced.
All previous baseline bytes outside the guarded writes remain byte-identical.

`tools/verify-alt-drag-direct.py` independently inspects dumpbin's instruction
decode, not a second copy of the intended opcode generator. It checks native
rejoin stack depths, stack balance through branches and loops, native argument
cleanup contracts, branch destinations, hook/relocation exclusion, exact recipe
reconstruction, section bounds and entry addressing under multiple load slides.
Its receipt is `build/alt-drag-direct-x86-static-checks.json`. Passing these
checks is not evidence that the gesture works in the game.

The complete previous managed patch and its installed root bootstrap/launcher
are backed up and hash-verified before any test installation under
`build/backups/0.1.45-before-alt-drag-direct`. No original game files, saves,
mods, profiles, credentials or Steam state are cleanup targets.

## Required runtime checks

Use the existing patched bootstrap with a project-contained temporary profile
and project-contained TEMP/TMP. Do not sign or publish this inspection image.
The game has not been launched. A prompt asking who will run the test is pending;
the old no-launch note in AGENTS.md belongs to a superseded section.

1. Compare normal selection, rectangle selection and right drag with baseline.
2. Select differently sized loose units. Alt-left drag must preview and commit
   a rigid translation without changing facing, frontage or relative spacing.
3. Hold Ctrl+Alt during the gesture to rotate around the common footprint centre.
   Releasing Ctrl must resume translation without a jump.
4. Test locked/unlocked groups, a singleton group and mixed group/loose selection.
5. Check Shift queueing and click-without-drag suppression.
6. Check right-button, Escape, focus loss and selection-change cancellation.
7. Check map boundaries and uneven terrain. Clamping beyond 0.05 world units
   suppresses the whole command instead of deforming the formation.
8. Verify no unintended naval/special placement interception. Those selections
   are declined and use the original handlers.

On a failed case, retain observations under this project and investigate/fix in
place. The user forbids rollback. Do not describe this candidate as a working
feature or update release metadata until the relevant runtime checks pass.
