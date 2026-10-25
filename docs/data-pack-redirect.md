# Single data.pack shadow redirect

This engine adapter selects only `UltimatePatch\data\data.pack`. It does not select a shadow `models.pack`, `local_en.pack`, or any other pack, and does not add or reorder pack entries. Pack construction is a separate signed-manifest operation.

The generator defaults to a disabled recipe. Run `tools/generate-data-pack-redirect.py --engine <original DLL> --enable` to deliberately generate enabled source against the supported vanilla SHA-256. The generator discovers exactly 15 original `call [CreateFileW]` sites and one original `mov ebx,[CreateFileW]` site, validates their HIGHLOW relocation entries, and substitutes relative calls with those old absolute relocations neutralized.

Only read-only `OPEN_EXISTING` requests with the case-insensitive directory-bounded suffix `data\data.pack` are rewritten. Slash variants are accepted. The access mask refuses generic write/all, MAXIMUM_ALLOWED, ACCESS_SYSTEM_SECURITY, delete, DAC/owner changes and file write/append/EA/attribute/delete-child rights. Other names and dispositions pass through. As with the launcher, the game's working directory must be its installation root for the managed relative destination.

Layout:

| Address range | Purpose |
| --- | --- |
| 0x115A0C40..0x115A0C49 | EBX loader for the original MOV site |
| 0x115A0C4A..0x115A0D1B | 210-byte PIC wrapper |
| 0x115A0D78..0x115A0D83 | One 12-byte match-table entry |
| 0x11793AE8..0x11793B21 | One UTF-16 managed path (58 bytes) |

These ranges are disjoint from naval adapter 070 at 0x115A0D20..0x115A0D76 and rank adapter 080 at 0x115A0DA0..0x115A0DF9. The existing 000 support recipe must map the text padding. The 090 recipe expands `.rdata` VirtualSize only within its original raw padding to cover the single string.

`tools/test-data-pack-redirect.py` executes the exact recipe bytes through a Unicorn Win32 stdcall fixture at three load bases. Its 114 cases cover Unicode/absolute/relative paths, models/localization passthrough, rejected write/security/maximum-allowed rights, creation dispositions, the EBX loader, all seven arguments, returned handle, ESP and nonvolatile registers. `--dll <built DLL>` additionally verifies every generated write, rejects live relocations intersecting patched ranges, and repeats the cases using bytes read from that DLL.

`tools/test-data-pack-redirect.c` is the corresponding x86 Windows private-mapping test. It substitutes only the private mapped IAT slot with a recording `__stdcall` fixture and exercises the native adapter at its actual Windows load address. Its 1125 path/access/disposition combinations per mapping also explicitly check returned handle, stack balance, EBX, ESI and EDI; the patched mapping checks the EBX loader. It does not attach to a game or alter a file. Compile and execute it against the original and final built DLL before enabling this adapter in a release. The Python results alone are not evidence of a successful live game launch.
