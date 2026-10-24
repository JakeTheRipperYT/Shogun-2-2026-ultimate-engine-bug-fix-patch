# Trait pack byte comparison

Independent streaming comparison of `build/dev/data/data.pack` against original OG `data/data.pack` passed. The comparison read all **2,565,173,720 bytes** from both files in 306 bounded chunks and checked each differing byte against the six authorized float fields in `patches/data/trait-progression.json`.

- Exactly **12 bytes differ**, all within the six intended four-byte float fields. No differences occur outside those fields.
- The complete **1,403,881-byte PFH3 header and index prefix is byte-identical**.
- Both file lengths are unchanged. Source and built file size/modification time remained stable throughout the comparison.
- Each original and replacement float matches its recipe guard and target value.
- Original SHA-256: `6596d4f5e51f3a95c79a90df782d9ef53c850e30c46bbbf9b0d2444f3668670a`.
- Built SHA-256: `73d47046bd097fbec2a1c2013426e573b617b8a6cab0aa084ab651778711c752`.

This establishes preservation of every unrelated archive byte, including all other trait rows and pack entries. It does not constitute campaign gameplay testing. The machine-readable local receipt is `outputs/OG-trait-pack-validation.json` in the task workspace.

## Build and installation checks

The final 0.1.8-traits-test build passed 22 installer self-tests; 10 yari, 192 kneel, 28 naval, 1,554 rank guard/ABI cases plus original STOP/START integration checks; and 2,250 native data-redirect path/access/disposition cases. The final DLL also passed 114 recipe and 114 built-byte emulation cases across three ASLR bases. Installer tests cover bounded streaming, guards, cancellation, cleanup, schema compatibility, upgrade, rollback and uninstall ownership.

The embedded installer reconstructed the full private pack successfully. Installation verified all managed hashes and unchanged vanilla EXE, engine and data.pack. The previous 0.1.7 build was copied and hash-verified on F: before replacement.

- Engine SHA-256: `f85d4c2c4fbab75c1d298e6e1d842f9b136ae67fe7f33ad9ec5cc047fe4ca4f2`.
- Signed package SHA-256: `97257a937c4cac5e470e02bb831d9b88ef3992f9346daa76eb55d4910c89b030`.
- Installer ZIP SHA-256: `1579157315312bb05549c819665bcbedc5637a2dfc7b7d1c7b3d801109e43aaf`.

Startup smoke check passed: the launcher returned zero and the same game process remained responsive with a visible Total War: SHOGUN 2 window for more than three minutes. A read-only host observer confirmed the game-root current directory. An earlier sandbox-scoped process query incorrectly hid this host process; the game had not exited. Campaign trait behavior still requires an in-game check.
