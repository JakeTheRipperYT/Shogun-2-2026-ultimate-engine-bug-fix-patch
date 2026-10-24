using System;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;

namespace S2UltimatePatch {

public sealed class ReleaseVersion : IComparable<ReleaseVersion> {
    readonly int[] numbers;
    readonly string suffix;
    ReleaseVersion(int[] n, string s) { numbers = n; suffix = s; }

    public static ReleaseVersion Parse(string value) {
        var m = Regex.Match(value ?? "", @"^v?(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-([0-9A-Za-z]+(?:[.-][0-9A-Za-z]+)*))?$");
        int a, b, c;
        if (!m.Success || !Int32.TryParse(m.Groups[1].Value, out a) || !Int32.TryParse(m.Groups[2].Value, out b) || !Int32.TryParse(m.Groups[3].Value, out c))
            throw new InvalidDataException("Unrecognized release version: " + value);
        return new ReleaseVersion(new[] { a, b, c }, m.Groups[4].Value);
    }

    public int CompareTo(ReleaseVersion other) {
        for (int i = 0; i < 3; i++) { int d = numbers[i].CompareTo(other.numbers[i]); if (d != 0) return d; }
        if (suffix == other.suffix) return 0;
        if (suffix.Length == 0) return 1;
        if (other.suffix.Length == 0) return -1;
        var a = suffix.Split('.'); var b = other.suffix.Split('.');
        for (int i = 0; i < Math.Min(a.Length, b.Length); i++) {
            if (a[i] == b[i]) continue;
            bool an = a[i].All(Char.IsDigit), bn = b[i].All(Char.IsDigit);
            if (an != bn) return an ? -1 : 1;
            if (an) { int d = a[i].Length.CompareTo(b[i].Length); if (d != 0) return d; }
            return String.CompareOrdinal(a[i], b[i]);
        }
        return a.Length.CompareTo(b.Length);
    }
}

public sealed class OnlineRelease { public string Version, DownloadUrl; public long Size; }

public static class OnlineUpdates {
    public const string AppVersion = "0.1.2-kneel-test";
    public const string Repository = "JakeTheRipperYT/Shogun-2-2026-ultimate-engine-bug-fix-patch";
    public const string ApiUrl = "https://api.github.com/repos/" + Repository + "/releases?per_page=100";
    public const string DownloadPrefix = "https://github.com/" + Repository + "/releases/download/";
    public const string PackagePrefix = "Shogun2UltimatePatch-";
    public const string PackageExtension = ".s2ub";
    const int MaxPackage = 128 * 1024 * 1024;

    public static string PackageName(string version) { return PackagePrefix + version + PackageExtension; }

    public static OnlineRelease Select(string json) {
        OnlineRelease best = null;
        foreach (object item in J.Arr(J.Json().DeserializeObject(json))) {
            var r = J.Obj(item);
            if (Convert.ToBoolean(r["draft"])) continue;
            string tag = J.S(r, "tag_name");
            if (!tag.StartsWith("v", StringComparison.Ordinal)) continue;
            ReleaseVersion version;
            try { version = ReleaseVersion.Parse(tag); } catch (InvalidDataException) { continue; }
            string text = tag.Substring(1), name = PackageName(text);
            foreach (object asset in J.Arr(r["assets"])) {
                var a = J.Obj(asset);
                if (J.S(a, "name") != name || J.S(a, "state") != "uploaded") continue;
                long size = J.N(a, "size");
                string url = J.S(a, "browser_download_url");
                if (size <= 0 || size > MaxPackage || url != DownloadPrefix + Uri.EscapeDataString(tag) + "/" + Uri.EscapeDataString(name)) continue;
                if (best == null || version.CompareTo(ReleaseVersion.Parse(best.Version)) > 0) best = new OnlineRelease { Version = text, DownloadUrl = url, Size = size };
            }
        }
        if (best == null) throw new InvalidDataException("No " + GameLayout.Product + " release package is published on GitHub yet.");
        return best;
    }

    static byte[] Get(string url, int limit, CancellationToken cancel, Action<long, long> progress) {
        cancel.ThrowIfCancellationRequested();
        ServicePointManager.SecurityProtocol |= SecurityProtocolType.Tls12;
        using (var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancel))
        using (var client = new HttpClient()) {
            timeout.CancelAfter(TimeSpan.FromMinutes(3));
            var token = timeout.Token;
            client.DefaultRequestHeaders.UserAgent.ParseAdd("Shogun2UltimatePatch/" + AppVersion);
            client.DefaultRequestHeaders.Accept.ParseAdd("application/vnd.github+json");
            try {
                using (var response = client.GetAsync(url, HttpCompletionOption.ResponseHeadersRead, token).GetAwaiter().GetResult()) {
                    if ((int)response.StatusCode == 403 || (int)response.StatusCode == 429) throw new IOException("GitHub is temporarily limiting update checks. Try again later or choose a downloaded package.");
                    response.EnsureSuccessStatusCode();
                    long total = response.Content.Headers.ContentLength ?? 0;
                    if (total > limit) throw new InvalidDataException("Update response exceeds the allowed download size.");
                    using (var stream = response.Content.ReadAsStreamAsync().GetAwaiter().GetResult())
                    using (var output = new MemoryStream()) {
                        byte[] buffer = new byte[65536];
                        int count;
                        while ((count = stream.ReadAsync(buffer, 0, buffer.Length, token).GetAwaiter().GetResult()) > 0) {
                            if (output.Length > limit - count) throw new InvalidDataException("Update download exceeds the allowed size.");
                            output.Write(buffer, 0, count);
                            if (progress != null) progress(output.Length, total);
                        }
                        token.ThrowIfCancellationRequested();
                        if (total > 0 && output.Length != total) throw new InvalidDataException("The update download was incomplete.");
                        return output.ToArray();
                    }
                }
            } catch (OperationCanceledException) {
                cancel.ThrowIfCancellationRequested();
                throw new IOException("GitHub timed out. Try again or choose a downloaded package.");
            } catch (HttpRequestException ex) {
                throw new IOException("Could not reach GitHub. Check the connection, retry, or choose a downloaded package.", ex);
            }
        }
    }

    public static OnlineRelease Latest(CancellationToken cancel) { return Select(Encoding.UTF8.GetString(Get(ApiUrl, 8 * 1024 * 1024, cancel, null))); }

    public static void ValidatePackage(string path, OnlineRelease expected) {
        if (Release.Load(path).Version != expected.Version) throw new InvalidDataException("The signed package version does not match the GitHub release. Nothing was installed.");
    }

    public static string Download(OnlineRelease release, string folder, CancellationToken cancel, Action<long, long> progress) {
        // Package URLs are restricted to this repository, even when passed by another caller.
        string name = PackageName(release.Version), expected = DownloadPrefix + Uri.EscapeDataString("v" + release.Version) + "/" + Uri.EscapeDataString(name);
        if (release.DownloadUrl != expected || release.Size <= 0 || release.Size > MaxPackage) throw new InvalidDataException("Unexpected update download address or size.");
        byte[] bytes = Get(release.DownloadUrl, MaxPackage, cancel, progress);
        if (bytes.LongLength != release.Size) throw new InvalidDataException("The downloaded package size does not match the published release.");
        Engine.NoLinks(folder);
        Directory.CreateDirectory(folder);
        string part = Engine.Under(folder, "download-" + Guid.NewGuid().ToString("N") + ".part");
        try {
            File.WriteAllBytes(part, bytes);
            cancel.ThrowIfCancellationRequested();
            ValidatePackage(part, release);
            string final = Engine.Under(folder, PackagePrefix + release.Version + "-" + Engine.Hash(bytes).Substring(0, 16) + PackageExtension);
            if (File.Exists(final)) File.Delete(final);
            File.Move(part, final);
            return final;
        } finally {
            if (File.Exists(part)) File.Delete(part);
        }
    }

    public static bool NeedsUpdate(string installed, string available) { return ReleaseVersion.Parse(installed).CompareTo(ReleaseVersion.Parse(available)) < 0; }
}
}
