# Engine patches

Each `engine/*.json` file is one patch to `empire.retail.dll` (32-bit, image base `0x10000000`). Files are applied in name order, so prefix them with numbers (`010-…`, `020-…`) when order matters.

```json
{
  "id": "example-fix",
  "title": "Short line shown in the installer",
  "description": "What it fixes and how; Ghidra function names and notes.",
  "enabled": true,
  "writes": [
    {
      "va": "0x1012ABCD",
      "expect": "8B 45 08 85 C0",
      "bytes":  "90 90 90 90 90",
      "note": "why these bytes"
    }
  ]
}
```

- `va` is the virtual address exactly as Ghidra shows it.
- `expect` holds the vanilla bytes at that address. The build fails if they don't match, which catches wrong addresses and a changed Steam build.
- `bytes` replaces `expect` in place and must be the same length. Hex digits only, spaces optional; don't add a `0x` prefix.
- Writes from different patches may not overlap.
- `"enabled": false` keeps a patch in the repo without building it.
- `"offset"` (a raw file offset) replaces `"va"` for writes into the PE headers, such as growing a section's VirtualSize.

### Code caves

New code goes in the zero padding at the end of `.text` (starting at VA `0x115A0C40`, 0x1C0 bytes). `000-text-cave.json` grows `.text` VirtualSize (header file offset `0x260`) so the loader maps it, and lists the current stub layout. When you add a stub, append it after the last one and extend the size there. Keep cave code position-independent (relative calls and jumps only), because the engine DLL can be relocated.

`build.ps1` writes the patched DLL to `build\dev\empire.retail.dll` for checking in Ghidra or x32dbg. The signed release stores only the byte differences against vanilla. The installer re-applies them to each player's own vanilla DLL and verifies the result by SHA-256.


