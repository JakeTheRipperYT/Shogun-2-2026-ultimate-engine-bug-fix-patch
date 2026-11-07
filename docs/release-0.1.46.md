# 0.1.46 — accepted gameplay fixes

This release preserves the original signed 0.1.45 baseline and adds the accepted
local changes:

- Alt-left-drag moves selected formations. Ctrl+Alt rotates them, with the exact
  rotation coefficient and rounding traced from the original CE game. Successful
  movement uses the regular movement-order feedback sound. OG x86 code is
  independently traced; no CE x64 function is transplanted.
- Main-campaign Legendary Menpo and the FOTS Accordion, Prussian Spiked Helmet
  and Legendary Menpo apply -4 fear. FOTS Dread applies -4; Bloodthirsty levels
  apply -4/-5/-6. Existing fear stacking and other earlier changes are retained.
- Fleet agents follow the carried army during bulk disembarkation, using the
  native transfer routine and the existing three-agent capacity.
- FOTS farm building hover cards use contextual farm wealth, including fertility.
  Actual campaign income and settlement multipliers are unchanged.
- Limber can cancel an obstructed unlimber transition through the native packing
  routine. Gun readiness, collision and native limber completion remain intact.

The user confirmed the Alt-drag, agent landing, farm-card and artillery fixes in
game. These confirmations do not establish exhaustive campaign/unit/multiplayer
coverage. Fear changes are the user's requested numeric edits.

## Reconstruction

`build.ps1` compiles only the recovered source of this project's combined
installer/launcher application. `tools/prepare-current-release.py` verifies the
original 0.1.45 package signature, reconstructs its baseline, applies the four
guarded engine recipes named in `patches/release/current.json`, and merges the
eight fear edits into the baseline pack composition. It does not import another
project or regenerate game code through a compiler.

The signed package contains reconstruction recipes and this project's application,
not complete game DLLs or game packs. The installer checks original source hashes
and output hashes. A fresh installer extracted from the release ZIP is tested
with `--build-only` against the original game files. Engine, bootstrap and all
three private packs are compared byte for byte with the tested installation.

Expected engine SHA256:
`0d6e29bdfb3d2d9d35c21cb0cdf36f7a50aee3a7783e2f9af991523d654452ab`.

Expected managed data.pack SHA256:
`a77c9e980635847f24d380e3abc227203d1c660f6f7c62026505b7458d257232`.

The legacy engine recipe `enabled` flags remain disabled for standalone historical
tooling. The explicit current release configuration selects the accepted overlays.
Do not enable old experiments or rebuild from the older historical recipe set.

## Signing-key replacement

The original OG private signing key was lost. With the user's approval, this
release uses a replacement 3072-bit RSA key. Its public half is embedded in the
rebuilt installer and combined launcher. The native launcher, bootstrap and game
payload are preserved. Download this release's installer once; old installers
cannot verify packages signed by the replacement key. No signature checks are
disabled. `installer/recovered/publicKey` retains the old public key solely to
authenticate the original 0.1.45 baseline.

The private key exists only in ignored `build/keys/signing-key.xml` on F:. It must
never enter Git history or release downloads. Install-state timestamps and cached
release/version metadata necessarily differ from the old local-overlay record;
they are not gameplay payloads.
