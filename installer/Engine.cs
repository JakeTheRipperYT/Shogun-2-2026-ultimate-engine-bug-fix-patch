using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Web.Script.Serialization;

namespace S2UltimatePatch {

public static class J {
    public static Dictionary<string, object> Obj(object x) { return (Dictionary<string, object>)x; }
    public static object[] Arr(object x) { return x is object[] a ? a : ((System.Collections.ArrayList)x).ToArray(); }
    public static string S(Dictionary<string, object> d, string k) { return Convert.ToString(d[k]); }
    public static long N(Dictionary<string, object> d, string k) { return Convert.ToInt64(d[k]); }
    public static byte[] B(Dictionary<string, object> d, string k) { return Convert.FromBase64String(S(d, k)); }
    public static JavaScriptSerializer Json() { return new JavaScriptSerializer { MaxJsonLength = 64 * 1024 * 1024, RecursionLimit = 100 }; }
    public static Dictionary<string, object> Parse(string s) { return Obj(Json().DeserializeObject(s)); }
}

/// <summary>Fixed names shared by the installer, launcher and release tooling.</summary>
public static class GameLayout {
    public const string Product = "Shogun 2 Ultimate Bug Fix Patch";
    public const string SteamAppId = "34330";
    public const string GameExe = "shogun2.exe";
    public const string GameEngine = "empire.retail.dll";
    public const string Folder = "UltimatePatch";                    // managed folder inside the game root
    public const string Bootstrap = "Shogun2_UB.exe";   // patched bootstrap, lives in the game root. Must avoid Windows installer-detection words (patch, upgrade, setup, install, update), which force a UAC prompt on 32-bit exes without a manifest.
    public const string Launcher = "Launch_Shogun2_Ultimate_Patch.exe";
    public const string StateFile = "install-state.json";
    public const string LockFile = ".ultimatepatch-install.lock";
    public const string StagingPrefix = Folder + ".staging_";
    public const string PreviousPrefix = Folder + ".previous_";
    public const string PackageMagic = "S2UBPKG1";
    public const string DataPack = "data/data.pack";
    public const string StreamDeltaMinimum = "0.1.8-traits-test";
    // The only files a schema-1 release may produce inside the managed folder.
    public static readonly string[] Destinations = { GameEngine, Bootstrap };
    public static bool AllowedDestination(string path, long schema) {
        return Destinations.Contains(path, StringComparer.Ordinal) || (schema == 2 && path == DataPack);
    }
    // Files published from the managed folder into the game root.
    public static readonly string[] RootFiles = { Bootstrap, Launcher };
}

public sealed class Release {
    public Dictionary<string, object> Manifest;
    public byte[] LauncherExe;
    public string PackageHash;
    public string Version { get { return J.S(Manifest, "version"); } }

    public static byte[] Resource(string name) {
        using (var s = Assembly.GetExecutingAssembly().GetManifestResourceStream(name)) {
            if (s == null) throw new InvalidDataException("Missing application resource: " + name);
            using (var m = new MemoryStream()) { s.CopyTo(m); return m.ToArray(); }
        }
    }

    public static bool HasEmbedded() { return Assembly.GetExecutingAssembly().GetManifestResourceNames().Contains("release"); }

    public static Release Load(string path) { return Parse(String.IsNullOrEmpty(path) ? Resource("release") : File.ReadAllBytes(path), Encoding.UTF8.GetString(Resource("publicKey"))); }

    public static Release Parse(byte[] bytes, string publicKeyXml) {
        if (bytes.Length > 128 * 1024 * 1024 || bytes.Length < 16 || Encoding.ASCII.GetString(bytes, 0, 8) != GameLayout.PackageMagic)
            throw new InvalidDataException("This is not a supported " + GameLayout.Product + " package.");
        int siglen = BitConverter.ToInt32(bytes, 8);
        if (siglen < 256 || siglen > 1024 || bytes.Length <= 12 + siglen) throw new InvalidDataException("Invalid package signature length.");
        byte[] sig = new byte[siglen], zip = new byte[bytes.Length - 12 - siglen];
        Buffer.BlockCopy(bytes, 12, sig, 0, siglen);
        Buffer.BlockCopy(bytes, 12 + siglen, zip, 0, zip.Length);
        using (var rsa = new RSACryptoServiceProvider()) {
            rsa.FromXmlString(publicKeyXml);
            if (!rsa.VerifyData(zip, CryptoConfig.MapNameToOID("SHA256"), sig)) throw new InvalidDataException("The package signature is invalid. Nothing was installed.");
        }
        var r = new Release { PackageHash = Engine.Hash(bytes) };
        using (var archive = new ZipArchive(new MemoryStream(zip), ZipArchiveMode.Read)) {
            r.Manifest = J.Parse(Encoding.UTF8.GetString(ReadEntry(archive, "manifest.json", 96 * 1024 * 1024)));
            r.LauncherExe = ReadEntry(archive, "launcher.exe", 1024 * 1024);
        }
        long schema = J.N(r.Manifest, "schema");
        if (schema != 1 && schema != 2) throw new InvalidDataException("This release needs a newer installer. Download the latest installer ZIP from GitHub.");
        if (schema == 2 && (!r.Manifest.ContainsKey("minimumInstallerVersion") || ReleaseVersion.Parse(J.S(r.Manifest, "minimumInstallerVersion")).CompareTo(ReleaseVersion.Parse(GameLayout.StreamDeltaMinimum)) < 0))
            throw new InvalidDataException("Schema-2 releases must specify the streaming installer compatibility requirement.");
        if (r.Manifest.ContainsKey("minimumInstallerVersion") && ReleaseVersion.Parse(OnlineUpdates.AppVersion).CompareTo(ReleaseVersion.Parse(J.S(r.Manifest, "minimumInstallerVersion"))) < 0)
            throw new InvalidDataException("This release needs a newer installer. Download the latest installer ZIP from GitHub.");
        return r;
    }

    static byte[] ReadEntry(ZipArchive zip, string name, int limit) {
        var e = zip.GetEntry(name);
        if (e == null || e.Length > limit) throw new InvalidDataException("Invalid package component: " + name);
        using (var s = e.Open()) using (var m = new MemoryStream()) { s.CopyTo(m); return m.ToArray(); }
    }
}

public sealed class Engine {
    public Action<string, int> Progress;
    public CancellationToken Cancel;
    // Self-tests run against fake game folders and must not depend on whether the real game is open.
    public bool IgnoreRunningGame;

    public void Log(string s, int p) { if (Progress != null) Progress(s, p); Cancel.ThrowIfCancellationRequested(); }

    public static string Hash(byte[] data) { using (var sha = SHA256.Create()) return Hex(sha.ComputeHash(data)); }
    public static string FileHash(string p) { using (var s = File.OpenRead(p)) using (var sha = SHA256.Create()) return Hex(sha.ComputeHash(s)); }
    static string Hex(byte[] b) { return BitConverter.ToString(b).Replace("-", "").ToLowerInvariant(); }

    /// <summary>Resolves a package-relative path, refusing anything that escapes <paramref name="root"/>.</summary>
    public static string Under(string root, string relative) {
        if (String.IsNullOrEmpty(relative) || Path.IsPathRooted(relative)) throw new InvalidDataException("Absolute package paths are forbidden.");
        string r = Path.GetFullPath(root).TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
        string p = Path.GetFullPath(Path.Combine(r, relative.Replace('/', Path.DirectorySeparatorChar)));
        if (!p.StartsWith(r, StringComparison.OrdinalIgnoreCase)) throw new InvalidDataException("Package path escapes its installation folder.");
        return p;
    }

    public static void NoLinks(string path) {
        var d = new DirectoryInfo(Path.GetFullPath(path));
        while (d != null) {
            if (d.Exists && (d.Attributes & FileAttributes.ReparsePoint) != 0) throw new IOException("Linked installation folders are not supported: " + d.FullName);
            d = d.Parent;
        }
    }

    static void RejectLinkedFile(string path) {
        if (File.Exists(path) && (File.GetAttributes(path) & FileAttributes.ReparsePoint) != 0) throw new IOException("Linked installed files are not supported: " + path);
    }

    public void GameClosed() {
        if (IgnoreRunningGame) return;
        foreach (string n in new[] { "shogun2", Path.GetFileNameWithoutExtension(GameLayout.Bootstrap), Path.GetFileNameWithoutExtension(GameLayout.Launcher) })
            if (Process.GetProcessesByName(n).Length > 0) throw new IOException("Close Shogun 2 and the Upgrade Patch before installing, updating or uninstalling.");
    }

    static void RequireHash(string path, string expected, string what) {
        if (!File.Exists(path)) throw new FileNotFoundException("Missing " + what + ": " + path);
        if (FileHash(path) != expected)
            throw new InvalidDataException("Unsupported or modified " + what + ": " + path + ". This release supports the current Steam build of Total War: SHOGUN 2 only. Verify the game files in Steam and try again.");
    }

    static IEnumerable<Dictionary<string, object>> Files(Release r) { return J.Arr(r.Manifest["files"]).Select(J.Obj); }

    static void ValidateFiles(Release r) {
        long schema = J.N(r.Manifest, "schema");
        if (schema != 1 && schema != 2) throw new InvalidDataException("Unsupported release schema.");
        var destinations = new HashSet<string>(StringComparer.Ordinal);
        foreach (var f in Files(r)) {
            string destination = J.S(f, "destination");
            if (!GameLayout.AllowedDestination(destination, schema) || !destinations.Add(destination))
                throw new InvalidDataException("Unsupported or duplicate release destination: " + destination);
            bool streamed = f.ContainsKey("kind") && J.S(f, "kind") == "stream-delta";
            if (destination == GameLayout.DataPack && (!streamed || schema != 2 || J.S(f, "source") != GameLayout.DataPack))
                throw new InvalidDataException("Only an exact data/data.pack stream delta is supported.");
            if (streamed && destination != GameLayout.DataPack)
                throw new InvalidDataException("Streaming is restricted to the managed data pack.");
            if (f.ContainsKey("kind") && !streamed && J.S(f, "kind") != "byte-delta")
                throw new InvalidDataException("Unsupported release file kind.");
        }
    }

    public void Preflight(Release r, string game) {
        ValidateFiles(r);
        NoLinks(game);
        if (!File.Exists(Under(game, GameLayout.GameExe))) throw new FileNotFoundException("Select the Total War: SHOGUN 2 folder that contains Shogun2.exe.");
        int i = 0;
        foreach (var f in Files(r)) {
            Log("Verifying vanilla " + J.S(f, "source") + "…", 2 + i * 4);
            RequireHash(Under(game, J.S(f, "source")), J.S(f, "sourceSha256"), "game file");
            i++;
        }
    }

    /// <summary>Copies a vanilla file, applies the release's byte writes and verifies the result.</summary>
    public static byte[] Patch(byte[] source, Dictionary<string, object> f) {
        long length = J.N(f, "length");
        if (length <= 0 || length > 256L * 1024 * 1024) throw new InvalidDataException("Invalid output length.");
        byte[] output = new byte[length];
        Buffer.BlockCopy(source, 0, output, 0, (int)Math.Min(source.Length, length));
        foreach (object item in J.Arr(f["writes"])) {
            var op = J.Obj(item);
            long off = J.N(op, "offset");
            byte[] data = J.B(op, "data");
            if (off < 0 || off > output.Length - data.Length) throw new InvalidDataException("Patch range is outside the output file.");
            Buffer.BlockCopy(data, 0, output, (int)off, data.Length);
        }
        if (Hash(output) != J.S(f, "sha256")) throw new InvalidDataException("Patched " + J.S(f, "destination") + " failed verification.");
        return output;
    }

    sealed class StreamWrite {
        public long Offset;
        public byte[] Expected, Data;
    }

    static bool Sha256Text(string hash) { return hash != null && hash.Length == 64 && hash.All(c => (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f')); }

    static List<StreamWrite> StreamWrites(Dictionary<string, object> f, long sourceLength) {
        long length = J.N(f, "length");
        if (length <= 0 || length > 8L * 1024 * 1024 * 1024 || length != sourceLength)
            throw new InvalidDataException("Stream deltas must preserve the exact supported source length.");
        if (!Sha256Text(J.S(f, "sourceSha256"))) throw new InvalidDataException("Invalid stream source SHA-256.");
        var result = new List<StreamWrite>();
        long total = 0;
        foreach (var item in J.Arr(f["writes"])) {
            if (result.Count >= 4096) throw new InvalidDataException("Too many stream writes.");
            var op = J.Obj(item);
            var write = new StreamWrite { Offset = J.N(op, "offset"), Expected = J.B(op, "expect"), Data = J.B(op, "data") };
            if (write.Expected.Length == 0 || write.Expected.Length != write.Data.Length || write.Data.Length > 1024 * 1024 || write.Offset < 0 || write.Offset > length - write.Data.Length)
                throw new InvalidDataException("Invalid same-length stream write range.");
            total += write.Data.Length;
            if (total > 16L * 1024 * 1024) throw new InvalidDataException("Stream delta payload exceeds its bounded limit.");
            result.Add(write);
        }
        result.Sort((a, b) => a.Offset.CompareTo(b.Offset));
        long end = 0;
        foreach (var write in result) {
            if (write.Offset < end) throw new InvalidDataException("Overlapping stream writes are forbidden.");
            end = write.Offset + write.Data.Length;
        }
        return result;
    }

    static string StreamDelta(FileStream source, Stream output, Dictionary<string, object> f, CancellationToken cancel) {
        var writes = StreamWrites(f, source.Length);
        byte[] buffer = new byte[1024 * 1024];
        using (var originalHash = SHA256.Create()) using (var outputHash = SHA256.Create()) {
            Action<long> copy = count => {
                while (count > 0) {
                    cancel.ThrowIfCancellationRequested();
                    int got = source.Read(buffer, 0, (int)Math.Min(buffer.Length, count));
                    if (got <= 0) throw new EndOfStreamException("Source ended while copying a stream delta.");
                    originalHash.TransformBlock(buffer, 0, got, buffer, 0);
                    outputHash.TransformBlock(buffer, 0, got, buffer, 0);
                    output.Write(buffer, 0, got);count -= got;
                }
            };
            foreach (var write in writes) {
                copy(write.Offset - source.Position);
                int got = 0;
                while (got < write.Expected.Length) {
                    cancel.ThrowIfCancellationRequested();
                    int n = source.Read(buffer, got, write.Expected.Length - got);
                    if (n <= 0) throw new EndOfStreamException("Source ended at a stream write.");
                    got += n;
                }
                originalHash.TransformBlock(buffer, 0, got, buffer, 0);
                for (int i = 0; i < got; i++) if (buffer[i] != write.Expected[i])
                    throw new InvalidDataException("Original bytes do not match the stream delta at offset " + write.Offset + ".");
                outputHash.TransformBlock(write.Data, 0, write.Data.Length, write.Data, 0);
                output.Write(write.Data, 0, write.Data.Length);
            }
            copy(source.Length - source.Position);
            originalHash.TransformFinalBlock(new byte[0], 0, 0);outputHash.TransformFinalBlock(new byte[0], 0, 0);
            if (Hex(originalHash.Hash) != J.S(f, "sourceSha256")) throw new InvalidDataException("Stream source SHA-256 did not match.");
            return Hex(outputHash.Hash);
        }
    }

    /// <summary>Checks a small recipe and computes its output hash without buffering or distributing the pack.</summary>
    public static string StreamDeltaHash(string source, Dictionary<string, object> f, CancellationToken cancel) {
        using (var input = new FileStream(source, FileMode.Open, FileAccess.Read, FileShare.Read, 1024 * 1024, FileOptions.SequentialScan))
            return StreamDelta(input, Stream.Null, f, cancel);
    }

    /// <summary>Creates a managed copy with same-size writes, verifying both sides; deletes its own partial output on failure.</summary>
    public static void PatchStream(string source, string destination, Dictionary<string, object> f, CancellationToken cancel) {
        if (String.Equals(Path.GetFullPath(source), Path.GetFullPath(destination), StringComparison.OrdinalIgnoreCase))
            throw new InvalidDataException("A stream delta may not overwrite its source.");
        if (!Sha256Text(J.S(f, "sha256"))) throw new InvalidDataException("Invalid stream output SHA-256.");
        bool created = false;
        try {
            using (var input = new FileStream(source, FileMode.Open, FileAccess.Read, FileShare.Read, 1024 * 1024, FileOptions.SequentialScan)) {
                StreamWrites(f, input.Length); // Validate every range/overlap before creating the output.
                using (var output = new FileStream(destination, FileMode.CreateNew, FileAccess.Write, FileShare.None, 1024 * 1024, FileOptions.SequentialScan)) {
                    created = true;
                    if (StreamDelta(input, output, f, cancel) != J.S(f, "sha256")) throw new InvalidDataException("Stream output SHA-256 did not match.");
                    output.Flush(true);
                }
            }
        } catch {
            if (created && File.Exists(destination)) File.Delete(destination);
            throw;
        }
    }

    public void Build(Release r, string game, string stage) {
        Preflight(r, game);
        NoLinks(stage);
        Directory.CreateDirectory(stage);
        var recorded = new List<object>();
        int i = 0, count = Files(r).Count();
        foreach (var f in Files(r)) {
            string destination = J.S(f, "destination");
            if (!GameLayout.AllowedDestination(destination, J.N(r.Manifest, "schema"))) throw new InvalidDataException("Unsupported release destination: " + destination);
            Log("Building " + destination + "…", 20 + 60 * i / Math.Max(1, count));
            string outputPath = Under(stage, destination);
            Directory.CreateDirectory(Path.GetDirectoryName(outputPath));
            if (f.ContainsKey("kind") && J.S(f, "kind") == "stream-delta")
                PatchStream(Under(game, J.S(f, "source")), outputPath, f, Cancel);
            else {
                byte[] patched = Patch(File.ReadAllBytes(Under(game, J.S(f, "source"))), f);
                File.WriteAllBytes(outputPath, patched);
            }
            RequireHash(Under(stage, destination), J.S(f, "sha256"), "generated file");
            recorded.Add(new Dictionary<string, object> { { "file", destination }, { "sha256", J.S(f, "sha256") } });
            i++;
        }
        foreach (string required in new[] { GameLayout.GameEngine, GameLayout.Bootstrap })
            if (!File.Exists(Under(stage, required))) throw new InvalidDataException("This release does not produce " + required + ".");
        File.WriteAllBytes(Under(stage, GameLayout.Launcher), r.LauncherExe);
        var state = new Dictionary<string, object> {
            { "schema", J.N(r.Manifest, "schema") }, { "version", r.Version }, { "packageSha256", r.PackageHash },
            { "gameBuild", r.Manifest.ContainsKey("gameBuild") ? J.S(r.Manifest, "gameBuild") : "" },
            { "installedUtc", DateTime.UtcNow.ToString("o") }, { "files", recorded.ToArray() },
            { "launcherSha256", Hash(r.LauncherExe) }
        };
        File.WriteAllText(Under(stage, GameLayout.StateFile), J.Json().Serialize(state));
        Log("All generated files verified.", 90);
    }

    public void Install(Release r, string game) {
        game = Path.GetFullPath(game);
        NoLinks(game);
        GameClosed();
        string live = Under(game, GameLayout.Folder);
        NoLinks(live);
        using (new FileStream(Under(game, GameLayout.LockFile), FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None, 1, FileOptions.DeleteOnClose)) {
            string stamp = DateTime.UtcNow.ToString("yyyyMMdd_HHmmss") + "_" + Guid.NewGuid().ToString("N").Substring(0, 6);
            string stage = Under(game, GameLayout.StagingPrefix + stamp), previous = Under(game, GameLayout.PreviousPrefix + stamp);
            bool retainStage = false;
            try {
                long needed = Files(r).Sum(f => J.N(f, "length")) + 64L * 1024 * 1024;
                if (new DriveInfo(Path.GetPathRoot(game)).AvailableFreeSpace < needed) throw new IOException("Not enough free disk space to stage this update safely.");
                Build(r, game, stage);
                Cancel.ThrowIfCancellationRequested();
                GameClosed();
                Log("Publishing verified files…", 95);
                PublishVerified(stage, game, previous);
                PrunePrevious(game, previous);
                Log("Installed " + r.Version + ". Vanilla game files were not changed.", 100);
            } catch (AggregateException) {
                retainStage = true;
                throw;
            } finally {
                if (!retainStage && Directory.Exists(stage)) {
                    NoLinks(stage);
                    if (!Path.GetFileName(stage).StartsWith(GameLayout.StagingPrefix, StringComparison.Ordinal)) throw new IOException("Invalid staging cleanup target.");
                    Directory.Delete(stage, true);
                }
            }
        }
    }

    /// <summary>Swaps the staged folder in and replaces the root launchers, rolling everything back if any step fails.</summary>
    public static void PublishVerified(string stage, string game, string previous) {
        string live = Under(game, GameLayout.Folder);
        NoLinks(stage); NoLinks(live); NoLinks(previous);
        if (!Path.GetFullPath(stage).StartsWith(Path.GetFullPath(game).TrimEnd('\\') + "\\", StringComparison.OrdinalIgnoreCase) || !Path.GetFileName(stage).StartsWith(GameLayout.StagingPrefix, StringComparison.Ordinal))
            throw new IOException("Invalid publication staging folder.");
        var existed = new HashSet<string>();
        var replaced = new List<string>();
        bool moved = false, published = false;
        Directory.CreateDirectory(Under(stage, "previous-launchers"));
        foreach (string name in GameLayout.RootFiles)
            if (File.Exists(Under(game, name))) { File.Copy(Under(game, name), Under(stage, "previous-launchers/" + name), true); existed.Add(name); }
        try {
            if (Directory.Exists(live)) { Directory.Move(live, previous); moved = true; }
            Directory.Move(stage, live);
            published = true;
            foreach (string name in GameLayout.RootFiles) {
                string temp = Under(game, name + ".installing");
                File.Copy(Under(live, name), temp, true);
                if (File.Exists(Under(game, name))) File.Replace(temp, Under(game, name), null); else File.Move(temp, Under(game, name));
                replaced.Add(name);
            }
        } catch (Exception original) {
            var failures = new List<Exception> { original };
            foreach (string name in replaced.AsEnumerable().Reverse()) {
                try { if (existed.Contains(name)) File.Copy(Under(live, "previous-launchers/" + name), Under(game, name), true); else File.Delete(Under(game, name)); }
                catch (Exception ex) { failures.Add(ex); }
            }
            try { if (published) Directory.Move(live, stage); if (moved) Directory.Move(previous, live); }
            catch (Exception ex) { failures.Add(ex); }
            if (failures.Count > 1) throw new AggregateException("Update rollback needs attention. Keep the game closed; previous files have been retained.", failures);
            throw;
        } finally {
            foreach (string name in GameLayout.RootFiles) { string temp = Under(game, name + ".installing"); if (File.Exists(temp)) File.Delete(temp); }
        }
    }

    /// <summary>Keeps only the most recent previous installation; older managed copies are removed.</summary>
    static void PrunePrevious(string game, string keep) {
        foreach (string dir in Directory.EnumerateDirectories(game, GameLayout.PreviousPrefix + "*")) {
            if (String.Equals(Path.GetFullPath(dir), Path.GetFullPath(keep), StringComparison.OrdinalIgnoreCase)) continue;
            try { DeleteManagedCopy(dir); } catch (IOException) { } catch (UnauthorizedAccessException) { }
        }
    }

    static void DeleteManagedCopy(string dir) {
        NoLinks(dir);
        if (!Path.GetFileName(dir).StartsWith(GameLayout.PreviousPrefix, StringComparison.Ordinal) || !File.Exists(Path.Combine(dir, GameLayout.StateFile))) return;
        if (Directory.EnumerateFileSystemEntries(dir, "*", SearchOption.AllDirectories).Any(p => (File.GetAttributes(p) & FileAttributes.ReparsePoint) != 0)) return;
        Directory.Delete(dir, true);
    }

    public void Uninstall(string game) {
        game = Path.GetFullPath(game);
        NoLinks(game);
        GameClosed();
        string live = Under(game, GameLayout.Folder);
        NoLinks(live);
        string record = Under(live, GameLayout.StateFile);
        if (!File.Exists(record)) throw new IOException("No installer-managed " + GameLayout.Product + " installation was found in this folder.");
        using (new FileStream(Under(game, GameLayout.LockFile), FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None, 1, FileOptions.DeleteOnClose)) {
            RejectLinkedFile(record);
            var installed = J.Parse(File.ReadAllText(record));
            long installedSchema = J.N(installed, "schema");
            if (installedSchema != 1 && installedSchema != 2) throw new InvalidDataException("Unrecognized installation record; nothing was removed.");
            var files = J.Arr(installed["files"]).Select(J.Obj).Select(x => J.S(x, "file")).ToArray();
            if (files.Any(x => !GameLayout.AllowedDestination(x, installedSchema)) || files.Distinct(StringComparer.Ordinal).Count() != files.Length) throw new InvalidDataException("Unexpected installed file paths; nothing was removed.");
            if (installedSchema == 2) foreach (var file in J.Arr(installed["files"]).Select(J.Obj)) {
                string path = Under(live, J.S(file, "file"));
                RejectLinkedFile(path);NoLinks(Path.GetDirectoryName(path));
                if (!file.ContainsKey("sha256") || !Sha256Text(J.S(file, "sha256")) || (File.Exists(path) && FileHash(path) != J.S(file, "sha256")))
                    throw new IOException("A managed file differs from its installation record; nothing was removed.");
            }
            var owned = files.Select(x => Under(live, x)).ToList();
            foreach (string name in GameLayout.RootFiles) {
                string local = Under(live, name), root = Under(game, name);
                RejectLinkedFile(local); RejectLinkedFile(root);
                if (File.Exists(root)) {
                    if (!File.Exists(local) || FileHash(root) != FileHash(local)) throw new IOException("The root " + name + " differs from the installed copy; nothing was removed.");
                    owned.Add(root);
                }
                owned.Add(local);
                owned.Add(Under(live, "previous-launchers/" + name));
            }
            foreach (string path in owned) { NoLinks(Path.GetDirectoryName(path)); RejectLinkedFile(path); }
            Log("Removing the " + GameLayout.Product + "…", 10);
            GameClosed();
            // Remove only our named files; the record goes last so a failed attempt can be retried.
            foreach (string path in owned) if (File.Exists(path)) File.Delete(path);
            File.Delete(record);
            foreach (string folder in new[] { Under(live, "data"), Under(live, "previous-launchers"), live })
                if (Directory.Exists(folder) && !Directory.EnumerateFileSystemEntries(folder).Any()) Directory.Delete(folder);
            foreach (string dir in Directory.EnumerateDirectories(game, GameLayout.PreviousPrefix + "*").ToArray()) {
                try { DeleteManagedCopy(dir); } catch (IOException) { } catch (UnauthorizedAccessException) { }
            }
            Log(Directory.Exists(live) ? "Uninstalled. Unrecognized files in " + GameLayout.Folder + " were kept." : "Uninstalled. Vanilla game files were never changed.", 100);
        }
    }

    public static string InstalledVersion(string game) {
        try {
            string record = Under(game, GameLayout.Folder + "/" + GameLayout.StateFile);
            return File.Exists(record) ? J.S(J.Parse(File.ReadAllText(record)), "version") : null;
        } catch (Exception) { return null; }
    }
}
}
