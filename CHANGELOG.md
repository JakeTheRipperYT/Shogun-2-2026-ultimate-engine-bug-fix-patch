# Changelog

## 0.1.8-traits-test

- Port CE progressive general traits to OG: War Is Slaughter enemy morale -1/-2/-3, Brave local morale +1/+2/+3, Cowardly local morale -1/-2/-3. Exactly six level-2/3 floats change; level 1, Cowardly personal security, thresholds and FOTS rows remain unchanged.
- Install / Update builds a private data.pack from the supported vanilla pack using a signed streaming delta. Preserve every pack/table header, index and byte outside the six fields. No game packs are included in release assets.
- Add data.pack-only engine redirection with path, access, argument, stack and ASLR checks. The native launcher requires the generated private pack before launch.
- Retain the existing yari-wall, kneel-movement, naval and ranked-idle fixes. Campaign validation of this trait build is pending.
- Requires the updated installer ZIP for schema 2 packages. Private GitHub releases still require a signed-in download; the credential-free updater cannot access them.
