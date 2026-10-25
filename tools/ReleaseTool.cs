// Developer-only release tooling. Not shipped to players.
//   ReleaseTool keygen [--force]
//   ReleaseTool make --game <dir> --version <x.y.z[-tag]> --launcher <exe> --patches <dir> --out <file.s2ub> [--data-patches <dir> | --pack-recipes <dir>] [--dev-output <dir>] [--key <xml>]
//   ReleaseTool verify <file.s2ub>
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Security.Cryptography;
using System.Text;

namespace S2UltimatePatch {

static class ReleaseTool {
    static string DefaultKey { get { return Path.Combine(Environment.CurrentDirectory, "build", "keys", "signing-key.xml"); } }

    static int Main(string[] args) {
        try {
            if (args.Length == 0) throw new ArgumentException("Usage: keygen | make | verify");
            var o = Options(args.Skip(1).ToArray());
            switch (args[0]) {
                case "keygen": Keygen(o); break;
                case "make": Make(o); break;
                case "verify": Verify(args[1]); break;
                default: throw new ArgumentException("Unknown command " + args[0]);
            }
            return 0;
        } catch (Exception ex) {
            Console.Error.WriteLine("ERROR: " + ex.Message);
            return 1;
        }
    }

    static Dictionary<string, string> Options(string[] a) {
        var d = new Dictionary<string, string>();
        for (int i = 0; i < a.Length; i++) {
            if (!a[i].StartsWith("--")) { d["_" + i] = a[i]; continue; }
            d[a[i].Substring(2)] = i + 1 < a.Length && !a[i + 1].StartsWith("--") ? a[++i] : "true";
        }
        return d;
    }

    static string Need(Dictionary<string, string> o, string k) {
        string v;
        if (!o.TryGetValue(k, out v)) throw new ArgumentException("Missing --" + k);
        return v;
    }

    static void Keygen(Dictionary<string, string> o) {
        string key = o.ContainsKey("key") ? o["key"] : DefaultKey;
        string pub = o.ContainsKey("public") ? o["public"] : Path.Combine("installer", "release-public.xml");
        if (File.Exists(key) && !o.ContainsKey("force")) throw new IOException("A signing key already exists at " + key + ". Pass --force to replace it (old releases will stop verifying).");
        using (var rsa = new RSACryptoServiceProvider(3072)) {
            Directory.CreateDirectory(Path.GetDirectoryName(key));
            File.WriteAllText(key, rsa.ToXmlString(true));
            File.WriteAllText(pub, rsa.ToXmlString(false));
        }
        Console.WriteLine("Private key: " + key + " (keep this out of git and backed up)");
        Console.WriteLine("Public key:  " + Path.GetFullPath(pub));
    }

    static void Verify(string path) {
        var r = Release.Parse(File.ReadAllBytes(path), File.ReadAllText(Path.Combine("installer", "release-public.xml")));
        Console.WriteLine("Signature OK. Version " + r.Version + ", package " + r.PackageHash);
        foreach (var f in J.Arr(r.Manifest["files"]).Select(J.Obj))
            Console.WriteLine("  " + J.S(f, "source") + " -> " + J.S(f, "destination") + ": " + OperationCount(f) + ", sha256 " + J.S(f, "sha256"));
    }

    static void Make(Dictionary<string, string> o) {
        string game = Need(o, "game"), version = Need(o, "version"), outPath = Need(o, "out");
        ReleaseVersion.Parse(version);
        byte[] launcher = File.ReadAllBytes(Need(o, "launcher"));
        string keyXml = File.ReadAllText(o.ContainsKey("key") ? o["key"] : DefaultKey);

        byte[] exe = File.ReadAllBytes(Path.Combine(game, GameLayout.GameExe));
        byte[] dll = File.ReadAllBytes(Path.Combine(game, GameLayout.GameEngine));
        byte[] bootstrap = Bootstrap.Build(exe);
        var applied = new List<Dictionary<string, object>>();
        byte[] engine = EnginePatches.Apply(dll, Need(o, "patches"), applied);

        var files = new List<Dictionary<string, object>> {
            FileSpec(GameLayout.GameEngine, GameLayout.GameEngine, dll, engine),
            FileSpec(GameLayout.GameExe, GameLayout.Bootstrap, exe, bootstrap),
        };
        bool dataDelta = false;
        if (o.ContainsKey("data-patches") && o.ContainsKey("pack-recipes")) throw new ArgumentException("Use either --data-patches or --pack-recipes, not both.");
        if (o.ContainsKey("data-patches")) foreach (string path in Directory.GetFiles(o["data-patches"], "*.json").OrderBy(x => x, StringComparer.Ordinal)) {
            var recipe = J.Parse(File.ReadAllText(path));
            if (!recipe.ContainsKey("enabled") || !Convert.ToBoolean(recipe["enabled"])) continue;
            if (dataDelta) throw new InvalidDataException("Only one data/data.pack delta recipe may be enabled.");
            files.Add(StreamFileSpec(game, recipe));dataDelta = true;
            applied.Add(new Dictionary<string, object> { { "id", J.S(recipe, "id") }, { "title", J.S(recipe, "title") }, { "description", recipe.ContainsKey("description") ? J.S(recipe, "description") : "" } });
        }
        bool composed = false;
        var composedPacks = new HashSet<string>(StringComparer.Ordinal);
        if (o.ContainsKey("pack-recipes")) foreach (string path in Directory.GetFiles(o["pack-recipes"], "*.json").OrderBy(x => x, StringComparer.Ordinal)) {
            var recipe = J.Parse(File.ReadAllText(path));
            if (recipe.ContainsKey("enabled") && !Convert.ToBoolean(recipe["enabled"])) continue;
            var spec = ComposeFileSpec(game, recipe);
            if (!composedPacks.Add(J.S(spec, "destination"))) throw new InvalidDataException("Duplicate composed pack destination.");
            files.Add(spec);composed = true;
            applied.Add(new Dictionary<string, object> { { "id", J.S(recipe, "id") }, { "title", J.S(recipe, "title") }, { "description", recipe.ContainsKey("description") ? J.S(recipe, "description") : "" } });
        }
        if (o.ContainsKey("pack-recipes") && !composed) throw new InvalidDataException("No enabled pack composition recipes were found.");
        var manifest = new Dictionary<string, object> {
            { "schema", composed ? 3 : dataDelta ? 2 : 1 }, { "version", version }, { "minimumInstallerVersion", composed ? GameLayout.StreamComposeMinimum : dataDelta ? GameLayout.StreamDeltaMinimum : "0.1.0-preview" },
            { "gameBuild", o.ContainsKey("game-build") ? o["game-build"] : "" },
            { "createdUtc", DateTime.UtcNow.ToString("o") },
            { "patches", applied.ToArray() }, { "files", files.ToArray() },
        };
        byte[] zip;
        using (var m = new MemoryStream()) {
            using (var archive = new ZipArchive(m, ZipArchiveMode.Create, true)) {
                Entry(archive, "manifest.json", Encoding.UTF8.GetBytes(J.Json().Serialize(manifest)));
                Entry(archive, "launcher.exe", launcher);
            }
            zip = m.ToArray();
        }
        byte[] sig;
        using (var rsa = new RSACryptoServiceProvider()) { rsa.FromXmlString(keyXml); sig = rsa.SignData(zip, CryptoConfig.MapNameToOID("SHA256")); }
        using (var output = new MemoryStream()) {
            output.Write(Encoding.ASCII.GetBytes(GameLayout.PackageMagic), 0, 8);
            output.Write(BitConverter.GetBytes(sig.Length), 0, 4);
            output.Write(sig, 0, sig.Length);
            output.Write(zip, 0, zip.Length);
            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(outPath)));
            File.WriteAllBytes(outPath, output.ToArray());
        }
        if (o.ContainsKey("dev-output")) {
            // Loose copies for debugging in Ghidra / x32dbg without running the installer.
            string dev = o["dev-output"];
            Directory.CreateDirectory(dev);
            File.WriteAllBytes(Path.Combine(dev, GameLayout.GameEngine), engine);
            File.WriteAllBytes(Path.Combine(dev, GameLayout.Bootstrap), bootstrap);
            foreach (var f in files.Where(x => x.ContainsKey("kind") && (J.S(x, "kind") == "stream-delta" || J.S(x, "kind") == "stream-compose"))) {
                string destination = Engine.Under(dev, J.S(f, "destination"));
                string source = Engine.Under(game, J.S(f, "source"));
                if (String.Equals(Path.GetFullPath(destination), Path.GetFullPath(source), StringComparison.OrdinalIgnoreCase))
                    throw new InvalidDataException("Developer output may not overwrite the vanilla data pack.");
                Directory.CreateDirectory(Path.GetDirectoryName(destination));
                if (File.Exists(destination)) File.Delete(destination);
                if (J.S(f, "kind") == "stream-compose") Engine.PatchCompose(source, destination, f, System.Threading.CancellationToken.None);
                else Engine.PatchStream(source, destination, f, System.Threading.CancellationToken.None);
            }
        }
        Console.WriteLine("Release " + version + " -> " + Path.GetFullPath(outPath));
        Console.WriteLine("  engine patches applied: " + applied.Count);
        foreach (var f in files) Console.WriteLine("  " + J.S(f, "destination") + ": " + OperationCount(f));
    }

    static string OperationCount(Dictionary<string, object> f) {
        bool composed = f.ContainsKey("kind") && J.S(f, "kind") == "stream-compose";
        return J.Arr(f[composed ? "segments" : "writes"]).Length + (composed ? " segment(s)" : " write(s)");
    }

    static Dictionary<string, object> ComposeFileSpec(string game, Dictionary<string, object> recipe) {
        string source = J.S(recipe, "source"), destination = J.S(recipe, "destination");
        if (J.S(recipe, "kind") != "stream-compose" || source != destination || !GameLayout.PrivatePacks.Contains(destination, StringComparer.Ordinal))
            throw new InvalidDataException("Pack recipes may only compose the three supported original packs into matching managed packs.");
        var spec = new Dictionary<string, object> {
            { "kind", "stream-compose" }, { "source", source }, { "destination", destination },
            { "sourceSha256", J.S(recipe, "sourceSha256") }, { "length", recipe["length"] },
            { "sha256", J.S(recipe, "sha256") }, { "segments", J.Arr(recipe["segments"]) }
        };
        Console.WriteLine("Verifying streamed pack composition (bounded memory): " + J.S(recipe, "id"));
        if (Engine.StreamComposeHash(Engine.Under(game, source), spec, System.Threading.CancellationToken.None) != J.S(spec, "sha256"))
            throw new InvalidDataException("Pack recipe output SHA-256 did not match.");
        return spec;
    }

    static void Entry(ZipArchive a, string name, byte[] data) {
        var e = a.CreateEntry(name, CompressionLevel.Optimal);
        using (var s = e.Open()) s.Write(data, 0, data.Length);
    }

    static byte[] HexBytes(string value) {
        string compact = String.Concat(value.Where(c => !Char.IsWhiteSpace(c)));
        if (compact.Length == 0 || compact.Length % 2 != 0) throw new InvalidDataException("A data write needs complete hexadecimal bytes.");
        var bytes = new byte[compact.Length / 2];
        for (int i = 0; i < bytes.Length; i++) bytes[i] = Byte.Parse(compact.Substring(i * 2, 2), NumberStyles.HexNumber, CultureInfo.InvariantCulture);
        return bytes;
    }

    static Dictionary<string, object> StreamFileSpec(string game, Dictionary<string, object> recipe) {
        if (J.S(recipe, "source") != GameLayout.DataPack || J.S(recipe, "destination") != GameLayout.DataPack)
            throw new InvalidDataException("Data recipes may only copy vanilla data/data.pack into the managed data/data.pack.");
        string source = Engine.Under(game, GameLayout.DataPack);
        long length = new FileInfo(source).Length;
        if (recipe.ContainsKey("length") && J.N(recipe, "length") != length) throw new InvalidDataException("Data recipe source length does not match.");
        var writes = new List<object>();
        foreach (var item in J.Arr(recipe["writes"])) {
            var op = J.Obj(item);
            string text = J.S(op, "offset");
            long offset = text.StartsWith("0x", StringComparison.OrdinalIgnoreCase) ? Int64.Parse(text.Substring(2), NumberStyles.HexNumber, CultureInfo.InvariantCulture) : Int64.Parse(text, CultureInfo.InvariantCulture);
            writes.Add(new Dictionary<string, object> {
                { "offset", offset }, { "expect", Convert.ToBase64String(HexBytes(J.S(op, "expect"))) },
                { "data", Convert.ToBase64String(HexBytes(J.S(op, "bytes"))) }
            });
        }
        var spec = new Dictionary<string, object> {
            { "kind", "stream-delta" }, { "source", GameLayout.DataPack }, { "destination", GameLayout.DataPack },
            { "sourceSha256", J.S(recipe, "sourceSha256") }, { "length", length }, { "writes", writes.ToArray() }
        };
        Console.WriteLine("Verifying streamed data pack recipe (bounded memory): " + J.S(recipe, "id"));
        string hash = Engine.StreamDeltaHash(source, spec, System.Threading.CancellationToken.None);
        if (recipe.ContainsKey("sha256") && J.S(recipe, "sha256") != hash) throw new InvalidDataException("Data recipe output SHA-256 did not match.");
        spec["sha256"] = hash;
        return spec;
    }

    /// <summary>Describes <paramref name="patched"/> as byte writes over a copy of <paramref name="vanilla"/>.</summary>
    static Dictionary<string, object> FileSpec(string source, string destination, byte[] vanilla, byte[] patched) {
        var writes = new List<object>();
        int common = Math.Min(vanilla.Length, patched.Length), i = 0;
        while (i < common) {
            if (vanilla[i] == patched[i]) { i++; continue; }
            int start = i, end = i + 1, gap = 0;
            for (int j = end; j < common && gap <= 32; j++) {
                if (vanilla[j] != patched[j]) { end = j + 1; gap = 0; } else gap++;
            }
            writes.Add(Write(patched, start, end - start));
            i = end;
        }
        for (int t = vanilla.Length; t < patched.Length; t += 1 << 20) writes.Add(Write(patched, t, Math.Min(1 << 20, patched.Length - t)));
        var spec = new Dictionary<string, object> {
            { "source", source }, { "destination", destination }, { "sourceSha256", Engine.Hash(vanilla) },
            { "length", (long)patched.Length }, { "writes", writes.ToArray() }, { "sha256", Engine.Hash(patched) },
        };
        // Round-trip through the installer's own code path before signing anything.
        if (Engine.Hash(Engine.Patch(vanilla, J.Parse(J.Json().Serialize(spec)))) != Engine.Hash(patched)) throw new InvalidDataException("Delta round-trip failed for " + destination);
        return spec;
    }

    static Dictionary<string, object> Write(byte[] b, int offset, int length) {
        var d = new byte[length];
        Buffer.BlockCopy(b, offset, d, 0, length);
        return new Dictionary<string, object> { { "offset", (long)offset }, { "data", Convert.ToBase64String(d) } };
    }
}

/// <summary>Minimal PE32 view used by the release tooling.</summary>
sealed class Pe {
    public readonly byte[] B;
    public readonly int Nt, Opt, SectionTable, Count;
    public readonly uint ImageBase;
    public Pe(byte[] b) {
        B = b;
        Nt = BitConverter.ToInt32(b, 0x3c);
        if (BitConverter.ToUInt32(b, Nt) != 0x4550 || BitConverter.ToUInt16(b, Nt + 4) != 0x14c) throw new InvalidDataException("Expected a 32-bit PE image.");
        Opt = Nt + 24;
        Count = BitConverter.ToUInt16(b, Nt + 6);
        SectionTable = Opt + BitConverter.ToUInt16(b, Nt + 20);
        ImageBase = BitConverter.ToUInt32(b, Opt + 28);
    }
    public int Section(string name) {
        for (int i = 0; i < Count; i++) { int s = SectionTable + i * 40; if (Encoding.ASCII.GetString(B, s, 8).TrimEnd('\0') == name) return s; }
        throw new InvalidDataException("Missing section " + name);
    }
    public uint VirtualSize(int s) { return BitConverter.ToUInt32(B, s + 8); }
    public uint Va(int s) { return BitConverter.ToUInt32(B, s + 12); }
    public uint RawSize(int s) { return BitConverter.ToUInt32(B, s + 16); }
    public uint Raw(int s) { return BitConverter.ToUInt32(B, s + 20); }
    public int FileOffset(uint rva) {
        for (int i = 0; i < Count; i++) {
            int s = SectionTable + i * 40;
            if (rva >= Va(s) && rva < Va(s) + Math.Min(Math.Max(VirtualSize(s), RawSize(s)), RawSize(s))) return checked((int)(Raw(s) + rva - Va(s)));
        }
        throw new InvalidDataException("Address is not backed by file data: RVA 0x" + rva.ToString("x"));
    }
    public bool DynamicBase { get { return (BitConverter.ToUInt16(B, Opt + 70) & 0x40) != 0; } }
    public bool HasHighLowReloc(uint rva) {
        uint dir = BitConverter.ToUInt32(B, Opt + 96 + 5 * 8), size = BitConverter.ToUInt32(B, Opt + 96 + 5 * 8 + 4);
        if (dir == 0) return false;
        int p = FileOffset(dir), end = p + (int)size;
        while (p + 8 <= end) {
            uint page = BitConverter.ToUInt32(B, p), block = BitConverter.ToUInt32(B, p + 4);
            if (block < 8) break;
            for (int e = p + 8; e + 2 <= p + block; e += 2) {
                ushort v = BitConverter.ToUInt16(B, e);
                if (v >> 12 == 3 && page + (uint)(v & 0xfff) == rva) return true;
            }
            p += (int)block;
        }
        return false;
    }
}

/// <summary>Turns a copy of shogun2.exe into the bootstrap named by GameLayout.Bootstrap, which loads UltimatePatch\empire.retail.dll.</summary>
static class Bootstrap {
    const string Original = "Empire.Retail.dll";
    public const string Replacement = GameLayout.Folder + "\\" + GameLayout.GameEngine;

    public static byte[] Build(byte[] vanilla) {
        byte[] b = (byte[])vanilla.Clone();
        var pe = new Pe(b);
        int rdata = pe.Section(".rdata"), text = pe.Section(".text");
        byte[] needle = Encoding.ASCII.GetBytes(Original + "\0");
        var hits = Find(b, needle, (int)pe.Raw(rdata), (int)pe.RawSize(rdata));
        if (hits.Count != 1) throw new InvalidDataException("Unsupported bootstrap: expected one engine DLL name, found " + hits.Count + ".");
        uint oldVa = pe.ImageBase + pe.Va(rdata) + (uint)(hits[0] - (int)pe.Raw(rdata));
        // The DLL name is pushed as an immediate: 68 <imm32>.
        var pushes = Find(b, new byte[] { 0x68 }.Concat(BitConverter.GetBytes(oldVa)).ToArray(), (int)pe.Raw(text), (int)pe.RawSize(text));
        if (pushes.Count != 1) throw new InvalidDataException("Unsupported bootstrap: expected one reference to the engine DLL name, found " + pushes.Count + ".");
        int immFile = pushes[0] + 1;
        uint immRva = pe.Va(text) + (uint)(immFile - (int)pe.Raw(text));
        if (pe.DynamicBase && !pe.HasHighLowReloc(immRva)) throw new InvalidDataException("Unsupported bootstrap: DLL name reference is not relocated.");

        // The engine load is "push <name>; call [LoadLibraryA]" right after the push.
        uint loadLibraryA = Import(pe, "LoadLibraryA"), getModuleHandleW = Import(pe, "GetModuleHandleW"), getProcAddress = Import(pe, "GetProcAddress");
        int callFile = immFile + 4;
        if (b[callFile] != 0xff || b[callFile + 1] != 0x15 || BitConverter.ToUInt32(b, callFile + 2) != loadLibraryA)
            throw new InvalidDataException("Unsupported bootstrap: engine load is not a direct LoadLibraryA call.");

        // New strings go in the zero padding after .rdata's virtual data.
        var rdataSpace = new Cave(b, pe, rdata, 16);
        uint path = rdataSpace.Add(Encoding.ASCII.GetBytes(Replacement + "\0"));
        uint kernel32 = rdataSpace.Add(Encoding.Unicode.GetBytes("kernel32.dll\0"));
        uint setEnv = rdataSpace.Add(Encoding.ASCII.GetBytes("SetEnvironmentVariableA\0"));
        uint appIdName = rdataSpace.Add(Encoding.ASCII.GetBytes("SteamAppId\0"));
        uint gameIdName = rdataSpace.Add(Encoding.ASCII.GetBytes("SteamGameId\0"));
        uint appId = rdataSpace.Add(Encoding.ASCII.GetBytes(GameLayout.SteamAppId + "\0"));
        Buffer.BlockCopy(BitConverter.GetBytes(path), 0, b, immFile, 4);

        // Without SteamAppId the Steam API fails to initialise when the bootstrap is started directly
        // (outside Steam), leaving the front end unusable. This stub sets it, then tail-jumps to
        // LoadLibraryA with the original stack, so it behaves exactly like the call it replaces.
        var stub = new List<byte>();
        Action<byte[]> emit = x => stub.AddRange(x);
        Func<uint, byte[]> imm = BitConverter.GetBytes;
        emit(new byte[] { 0x68 }); emit(imm(kernel32));                         // push L"kernel32.dll"
        emit(new byte[] { 0xff, 0x15 }); emit(imm(getModuleHandleW));            // call [GetModuleHandleW]
        emit(new byte[] { 0x68 }); emit(imm(setEnv));                           // push "SetEnvironmentVariableA"
        emit(new byte[] { 0x50 });                                              // push eax
        emit(new byte[] { 0xff, 0x15 }); emit(imm(getProcAddress));             // call [GetProcAddress]
        emit(new byte[] { 0x85, 0xc0, 0x74, 0x00 });                            // test eax,eax / jz done
        int jz = stub.Count;
        emit(new byte[] { 0x50 });                                              // push eax (keep fn for both calls)
        foreach (uint name in new[] { appIdName, gameIdName }) {
            emit(new byte[] { 0x68 }); emit(imm(appId));                        // push "34330"
            emit(new byte[] { 0x68 }); emit(imm(name));                         // push name
            emit(new byte[] { 0xff, 0x54, 0x24, 0x08 });                        // call [esp+8]
        }
        emit(new byte[] { 0x58 });                                              // pop eax
        stub[jz - 1] = checked((byte)(stub.Count - jz));                        // done:
        emit(new byte[] { 0xff, 0x25 }); emit(imm(loadLibraryA));               // jmp [LoadLibraryA]
        uint stubVa = new Cave(b, pe, text, 16).Add(stub.ToArray());
        uint callVa = pe.ImageBase + pe.Va(text) + (uint)(callFile - (int)pe.Raw(text));
        b[callFile] = 0xe8;                                                     // call stub
        Buffer.BlockCopy(BitConverter.GetBytes(unchecked(stubVa - (callVa + 5))), 0, b, callFile + 1, 4);
        b[callFile + 5] = 0x90;

        // The stub and strings use absolute addresses without relocation entries, so keep the image at its preferred base.
        int dllCharacteristics = pe.Opt + 70;
        Buffer.BlockCopy(BitConverter.GetBytes((ushort)(BitConverter.ToUInt16(b, dllCharacteristics) & ~0x40)), 0, b, dllCharacteristics, 2);
        return b;
    }

    static uint Import(Pe pe, string name) {
        byte[] b = pe.B;
        uint dir = BitConverter.ToUInt32(b, pe.Opt + 96 + 8);
        for (int d = pe.FileOffset(dir); BitConverter.ToUInt32(b, d + 12) != 0; d += 20) {
            uint thunks = BitConverter.ToUInt32(b, d) != 0 ? BitConverter.ToUInt32(b, d) : BitConverter.ToUInt32(b, d + 16), iat = BitConverter.ToUInt32(b, d + 16);
            for (int i = 0; ; i++) {
                uint entry = BitConverter.ToUInt32(b, pe.FileOffset(thunks) + i * 4);
                if (entry == 0) break;
                if ((entry & 0x80000000) != 0) continue;
                int at = pe.FileOffset(entry) + 2, end = at;
                while (b[end] != 0) end++;
                if (Encoding.ASCII.GetString(b, at, end - at) == name) return pe.ImageBase + iat + (uint)(i * 4);
            }
        }
        throw new InvalidDataException("Unsupported bootstrap: missing import " + name + ".");
    }

    /// <summary>Appends data into a section's zero padding (between VirtualSize and SizeOfRawData) and grows VirtualSize.</summary>
    sealed class Cave {
        readonly byte[] b; readonly Pe pe; readonly int section; readonly uint align, limit;
        public Cave(byte[] b, Pe pe, int section, uint align) {
            this.b = b; this.pe = pe; this.section = section; this.align = align;
            uint nextVa = Enumerable.Range(0, pe.Count).Select(i => pe.SectionTable + i * 40).Select(pe.Va).Where(v => v > pe.Va(section)).DefaultIfEmpty(uint.MaxValue).Min();
            limit = Math.Min(pe.RawSize(section), nextVa - pe.Va(section));
        }
        public uint Add(byte[] data) {
            uint at = (pe.VirtualSize(section) + align - 1) & ~(align - 1), end = at + (uint)data.Length;
            if (end > limit) throw new InvalidDataException("Unsupported bootstrap: no padding left in its sections.");
            int file = (int)(pe.Raw(section) + at);
            for (int i = file; i < file + data.Length; i++) if (b[i] != 0) throw new InvalidDataException("Unsupported bootstrap: section padding is not empty.");
            Buffer.BlockCopy(data, 0, b, file, data.Length);
            Buffer.BlockCopy(BitConverter.GetBytes(end), 0, b, section + 8, 4);
            return pe.ImageBase + pe.Va(section) + at;
        }
    }

    static List<int> Find(byte[] b, byte[] n, int start, int length) {
        var r = new List<int>();
        for (int i = start; i + n.Length <= start + length && i + n.Length <= b.Length; i++) {
            int k = 0;
            while (k < n.Length && b[i + k] == n[k]) k++;
            if (k == n.Length) r.Add(i);
        }
        return r;
    }
}

/// <summary>Applies patches/engine/*.json to a copy of the vanilla engine. See patches/README.md for the format.</summary>
static class EnginePatches {
    public static byte[] Apply(byte[] vanilla, string folder, List<Dictionary<string, object>> applied) {
        byte[] b = (byte[])vanilla.Clone();
        var pe = new Pe(b);
        var owner = new Dictionary<int, string>();
        foreach (string file in Directory.Exists(folder) ? Directory.GetFiles(folder, "*.json").OrderBy(x => x, StringComparer.Ordinal).ToArray() : new string[0]) {
            var p = J.Parse(File.ReadAllText(file));
            string id = J.S(p, "id");
            if (p.ContainsKey("enabled") && !Convert.ToBoolean(p["enabled"])) { Console.WriteLine("  skipped (disabled): " + id); continue; }
            foreach (var w in J.Arr(p["writes"]).Select(J.Obj)) {
                // "va" addresses code/data as Ghidra shows it; "offset" is a raw file offset (PE headers).
                string at = w.ContainsKey("va") ? J.S(w, "va") : "file+" + J.S(w, "offset");
                int off;
                if (w.ContainsKey("va")) {
                    uint va = ParseVa(J.S(w, "va"));
                    if (va < pe.ImageBase) throw new InvalidDataException(id + ": VA 0x" + va.ToString("x") + " is below the image base.");
                    off = pe.FileOffset(va - pe.ImageBase);
                } else {
                    off = checked((int)ParseVa(J.S(w, "offset")));
                    if (off >= (int)pe.Raw(pe.Section(".text"))) throw new InvalidDataException(id + " @" + at + ": file-offset writes are only for PE headers; use 'va'.");
                }
                byte[] expect = HexBytes(J.S(w, "expect")), bytes = HexBytes(J.S(w, "bytes"));
                if (expect.Length != bytes.Length || bytes.Length == 0) throw new InvalidDataException(id + " @" + at + ": expect and bytes must be the same non-zero length.");
                for (int i = 0; i < expect.Length; i++) {
                    if (vanilla[off + i] != expect[i]) throw new InvalidDataException(id + " @" + at + ": vanilla bytes differ from 'expect'. Wrong game build or wrong address.");
                    string other;
                    if (owner.TryGetValue(off + i, out other)) throw new InvalidDataException(id + " @" + at + ": overlaps patch " + other + ".");
                    owner[off + i] = id;
                }
                Buffer.BlockCopy(bytes, 0, b, off, bytes.Length);
            }
            applied.Add(new Dictionary<string, object> { { "id", id }, { "title", J.S(p, "title") } });
            Console.WriteLine("  applied: " + id);
        }
        return b;
    }

    static uint ParseVa(string s) {
        s = s.Trim();
        if (s.StartsWith("0x", StringComparison.OrdinalIgnoreCase)) s = s.Substring(2);
        return uint.Parse(s, NumberStyles.HexNumber, CultureInfo.InvariantCulture);
    }

    static byte[] HexBytes(string s) {
        s = new string(s.Where(Uri.IsHexDigit).ToArray());
        if (s.Length % 2 != 0) throw new InvalidDataException("Odd number of hex digits: " + s);
        return Enumerable.Range(0, s.Length / 2).Select(i => Convert.ToByte(s.Substring(i * 2, 2), 16)).ToArray();
    }
}
}
