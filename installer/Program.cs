using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using System.Security.Cryptography;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;
using Microsoft.Win32;

[assembly: System.Reflection.AssemblyCompany("JakeTheRipper")]
[assembly: System.Reflection.AssemblyCopyright("JakeTheRipper")]
[assembly: System.Reflection.AssemblyProduct("Shogun 2 Ultimate Bug Fix Patch")]
[assembly: System.Reflection.AssemblyTitle("Shogun 2 Ultimate Bug Fix Patch by JakeTheRipper")]

namespace S2UltimatePatch {

static class Program {
    [STAThread]
    static int Main(string[] args) {
        if (args.Length > 0) {
            string log = "installer-error.txt";
            try {
                if (args[0] == "--preview" && args.Length == 2) {
                    Application.EnableVisualStyles();
                    using (var form = new MainForm(true)) {
                        form.Show(); Application.DoEvents();
                        using (var bitmap = new Bitmap(form.Width, form.Height)) { form.DrawToBitmap(bitmap, new Rectangle(0, 0, form.Width, form.Height)); bitmap.Save(args[1]); }
                    }
                    return 0;
                }
                if (args[0] == "--self-test") { SelfTests.Run(args.Length > 1 ? args[1] : "installer-selftest.txt"); return 0; }
                // --build-only <game> <package|:embedded> <output>: builds into an empty folder without touching the game.
                if (args[0] == "--build-only" && args.Length == 4) {
                    string dest = Path.GetFullPath(args[3]);
                    log = dest + ".log";
                    if (Directory.Exists(dest)) throw new IOException("Build-only output already exists.");
                    var release = Release.Load(args[2] == ":embedded" ? null : args[2]);
                    new Engine { Progress = (s, p) => File.AppendAllText(log, p + "% " + s + Environment.NewLine) }.Build(release, args[1], dest);
                    File.AppendAllText(log, "SUCCESS" + Environment.NewLine);
                    return 0;
                }
                // --install <game> / --uninstall <game>: unattended equivalents of the buttons, used for testing.
                if ((args[0] == "--install" || args[0] == "--uninstall") && args.Length == 2) {
                    log = "installer-" + args[0].Substring(2) + ".log";
                    var engine = new Engine { Progress = (s, p) => File.AppendAllText(log, p + "% " + s + Environment.NewLine) };
                    if (args[0] == "--install") engine.Install(Release.Load(null), args[1]); else engine.Uninstall(args[1]);
                    File.AppendAllText(log, "SUCCESS" + Environment.NewLine);
                    return 0;
                }
                throw new ArgumentException("Unknown installer command.");
            } catch (Exception ex) {
                File.AppendAllText(log, "FAILED: " + ex + Environment.NewLine);
                return 1;
            }
        }
        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);
        Application.Run(new MainForm());
        return 0;
    }
}

public sealed class MainForm : Form {
    readonly TextBox game = new TextBox(), package = new TextBox(), log = new TextBox();
    readonly Button install = new Button(), launch = new Button(), choosePackage = new Button(), cancel = new Button(), uninstall = new Button(), github = new Button();
    readonly ProgressBar progress = new ProgressBar();
    readonly Label state = new Label();
    CancellationTokenSource cancellation;
    bool busy;
    readonly string settings = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Shogun2UltimatePatch", "installer-settings.json");

    public MainForm(bool preview = false) {
        try { Icon = Icon.ExtractAssociatedIcon(Application.ExecutablePath); } catch (Exception) { }
        Text = GameLayout.Product;
        ClientSize = new Size(810, 570); MinimumSize = new Size(820, 610);
        StartPosition = FormStartPosition.CenterScreen;
        Font = new Font("Segoe UI", 10);
        BackColor = Color.FromArgb(27, 23, 22); ForeColor = Color.FromArgb(240, 235, 230);
        AutoScaleMode = AutoScaleMode.Dpi;
        Controls.Add(new Label { Text = "SHOGUN 2 ULTIMATE PATCH", Font = new Font("Segoe UI Semibold", 22), AutoSize = true, Location = new Point(28, 24) });
        Controls.Add(new Label { Text = "By JakeTheRipper · Preview " + OnlineUpdates.AppVersion.Replace("-preview", ""), AutoSize = true, ForeColor = Color.FromArgb(181, 163, 158), Location = new Point(31, 73) });

        FolderRow("Total War: SHOGUN 2 installation", game, 122);
        Controls.Add(new Label { Text = "Release package", AutoSize = true, Location = new Point(30, 204) });
        StyleBox(package); package.Location = new Point(30, 230); package.Size = new Size(505, 29); package.ReadOnly = true; Controls.Add(package);
        ButtonStyle(github, "GitHub", new Rectangle(547, 228, 108, 33));
        github.Click += (s, e) => UseGitHub();
        ButtonStyle(choosePackage, "Offline…", new Rectangle(667, 228, 113, 33));
        var localMenu = new ContextMenuStrip();
        localMenu.Items.Add("Choose a downloaded " + OnlineUpdates.PackageExtension + " file…", null, (s, e) => ChoosePackageFile());
        if (Release.HasEmbedded()) localMenu.Items.Add("Use included release (offline)", null, (s, e) => { package.Tag = ":embedded"; package.Text = "Included release (offline)"; });
        choosePackage.Click += (s, e) => localMenu.Show(choosePackage, new Point(0, choosePackage.Height));
        UseGitHub();

        ButtonStyle(install, "Install / Update", new Rectangle(30, 285, 325, 47));
        install.BackColor = Color.FromArgb(140, 38, 32);
        install.Click += async (s, e) => await Install();
        ButtonStyle(launch, "Launch Ultimate Patch", new Rectangle(369, 285, 260, 47));
        launch.Click += (s, e) => Launch();
        ButtonStyle(cancel, "Cancel", new Rectangle(643, 285, 137, 47));
        cancel.Enabled = false;
        cancel.Click += (s, e) => { if (cancellation != null) cancellation.Cancel(); };
        state.Text = "Your vanilla game files are never changed. Steam must be running to play.";
        state.AutoSize = false; state.Location = new Point(30, 347); state.Size = new Size(520, 42); state.ForeColor = Color.FromArgb(181, 163, 158);
        Controls.Add(state);
        ButtonStyle(uninstall, "Uninstall", new Rectangle(562, 347, 218, 36));
        uninstall.Click += async (s, e) => await Uninstall();
        progress.Location = new Point(30, 396); progress.Size = new Size(750, 9); Controls.Add(progress);
        StyleBox(log); log.Multiline = true; log.ReadOnly = true; log.ScrollBars = ScrollBars.Vertical;
        log.Location = new Point(30, 421); log.Size = new Size(750, 120);
        log.Anchor = AnchorStyles.Left | AnchorStyles.Right | AnchorStyles.Bottom | AnchorStyles.Top;
        Controls.Add(log);

        game.Text = FindGame();
        LoadSettings();
        if (preview) game.Text = @"C:\Program Files (x86)\Steam\steamapps\common\Total War SHOGUN 2";
        game.TextChanged += (s, e) => ShowInstalled();
        if (Release.HasEmbedded()) {
            try { Append("Included release " + Release.Load(null).Version + ". Patched files are built locally from your own game; no game files are distributed."); }
            catch (Exception ex) { Append("The included release could not be read: " + ex.Message); }
        }
        ShowInstalled();
        FormClosing += (s, e) => {
            if (busy) { e.Cancel = true; MessageBox.Show(this, "Wait for the current operation to finish before closing.", Text, MessageBoxButtons.OK, MessageBoxIcon.Information); }
        };
    }

    void UseGitHub() { package.Tag = null; package.Text = "GitHub — latest release"; }

    void ChoosePackageFile() {
        using (var dialog = new OpenFileDialog { Filter = GameLayout.Product + " release (*" + OnlineUpdates.PackageExtension + ")|*" + OnlineUpdates.PackageExtension, Title = "Choose a signed " + GameLayout.Product + " release" }) {
            if (dialog.ShowDialog() != DialogResult.OK) return;
            try {
                var r = Release.Load(dialog.FileName);
                package.Tag = dialog.FileName; package.Text = Path.GetFileName(dialog.FileName);
                Append("Selected " + r.Version + "; signature verified.");
            } catch (Exception ex) { ShowError(ex); }
        }
    }

    void ShowInstalled() {
        string v = Directory.Exists(game.Text.Trim()) ? Engine.InstalledVersion(game.Text.Trim()) : null;
        launch.Enabled = !busy && v != null;
        if (!busy) state.Text = v != null ? "Installed · " + v + ". Vanilla game files are unchanged." : "Not installed. Your vanilla game files are never changed.";
    }

    void Launch() {
        try {
            string file = Engine.Under(game.Text.Trim(), GameLayout.Launcher);
            if (!File.Exists(file)) throw new FileNotFoundException("Install the " + GameLayout.Product + " first.");
            Process.Start(new ProcessStartInfo(file) { WorkingDirectory = Path.GetFullPath(game.Text.Trim()), UseShellExecute = true });
        } catch (Exception ex) { ShowError(ex); }
    }

    void FolderRow(string label, TextBox box, int y) {
        Controls.Add(new Label { Text = label, AutoSize = true, Location = new Point(30, y) });
        StyleBox(box); box.Location = new Point(30, y + 27); box.Size = new Size(625, 29); Controls.Add(box);
        var browse = new Button();
        ButtonStyle(browse, "Browse…", new Rectangle(667, y + 25, 113, 33));
        browse.Click += (s, e) => {
            using (var dialog = new FolderBrowserDialog { Description = label, SelectedPath = Directory.Exists(box.Text) ? box.Text : "" })
                if (dialog.ShowDialog() == DialogResult.OK) box.Text = dialog.SelectedPath;
        };
    }

    void ButtonStyle(Button b, string text, Rectangle bounds) {
        b.Text = text; b.Bounds = bounds; b.FlatStyle = FlatStyle.Flat;
        b.FlatAppearance.BorderColor = Color.FromArgb(92, 74, 70); b.BackColor = Color.FromArgb(48, 40, 38); b.ForeColor = ForeColor;
        Controls.Add(b);
    }

    void StyleBox(TextBox t) { t.BackColor = Color.FromArgb(38, 33, 31); t.ForeColor = ForeColor; t.BorderStyle = BorderStyle.FixedSingle; }

    void Append(string s) { log.AppendText(DateTime.Now.ToString("HH:mm:ss") + "  " + s + Environment.NewLine); }

    void ShowError(Exception ex) {
        string message = ex is UnauthorizedAccessException ? "Windows denied access to the game folder. Close the game and, if this folder requires it, run this installer as administrator." : ex.Message;
        Append(message);
        MessageBox.Show(this, message, Text, MessageBoxButtons.OK, MessageBoxIcon.Warning);
    }

    void SetBusy(bool value, bool cancellable) {
        busy = value;
        foreach (var c in new Control[] { install, uninstall, choosePackage, github }) c.Enabled = !value;
        game.ReadOnly = value;
        cancel.Enabled = value && cancellable;
        launch.Enabled = !value;
    }

    async Task Install() {
        if (busy) return;
        string gamePath = game.Text.Trim(), pkg = package.Tag as string;
        if (!Directory.Exists(gamePath)) { ShowError(new IOException("Choose the Total War: SHOGUN 2 folder first.")); return; }
        SetBusy(true, true);
        cancellation = new CancellationTokenSource();
        progress.Value = 0;
        try {
            SaveSettings();
            if (pkg == null) {
                state.Text = "Checking GitHub for the latest release…"; Append(state.Text);
                OnlineRelease latest = null;
                try { latest = await Task.Run(() => OnlineUpdates.Latest(cancellation.Token)); }
                catch (InvalidDataException) when (Release.HasEmbedded()) { Append("No release is published on GitHub yet; using the included release."); }
                if (latest != null) {
                    Append("Latest published release: " + latest.Version);
                    string current = Engine.InstalledVersion(gamePath);
                    if (current != null && !OnlineUpdates.NeedsUpdate(current, latest.Version)) {
                        state.Text = "Up to date · " + current; Append("No newer release is available. Your installed files were kept.");
                        return;
                    }
                    var downloadProgress = new Progress<Tuple<long, long>>(v => {
                        state.Text = "Downloading " + latest.Version + " · " + (v.Item1 / 1024) + " KB";
                        progress.Value = v.Item2 > 0 ? (int)Math.Min(100, v.Item1 * 100 / v.Item2) : 0;
                    });
                    string folder = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Shogun2UltimatePatch", "downloads");
                    pkg = await Task.Run(() => OnlineUpdates.Download(latest, folder, cancellation.Token, (a, b) => ((IProgress<Tuple<long, long>>)downloadProgress).Report(Tuple.Create(a, b))));
                    Append("Downloaded " + latest.Version + "; release signature verified.");
                    progress.Value = 0;
                }
            } else if (pkg == ":embedded") pkg = null;
            var release = Release.Load(pkg);
            Append("Installing " + release.Version + ". Any existing installation is kept until the new one is verified.");
            if (release.Manifest.ContainsKey("patches"))
                foreach (var p in J.Arr(release.Manifest["patches"]).Select(J.Obj)) Append("  • " + J.S(p, "title"));
            var uiProgress = new Progress<Tuple<string, int>>(v => { state.Text = v.Item1; progress.Value = Math.Max(0, Math.Min(100, v.Item2)); Append(v.Item1); });
            var engine = new Engine { Cancel = cancellation.Token, Progress = (s, p) => ((IProgress<Tuple<string, int>>)uiProgress).Report(Tuple.Create(s, p)) };
            await Task.Run(() => engine.Install(release, gamePath));
            Append("Installation complete. Use Launch Ultimate Patch, or " + GameLayout.Launcher + " in the game folder.");
        } catch (OperationCanceledException) {
            Append("Cancelled. Installed files were preserved.");
        } catch (Exception ex) {
            Append("Installation stopped.");
            ShowError(ex);
        } finally {
            SetBusy(false, false);
            cancellation.Dispose(); cancellation = null;
            ShowInstalled();
        }
    }

    async Task Uninstall() {
        if (busy) return;
        string gamePath = game.Text.Trim();
        if (!Directory.Exists(gamePath)) { ShowError(new IOException("Choose the Total War: SHOGUN 2 folder first.")); return; }
        if (MessageBox.Show(this, "Remove the " + GameLayout.Product + " and its launcher?\n\nVanilla game files, saves and settings are kept.", "Uninstall", MessageBoxButtons.YesNo, MessageBoxIcon.Question, MessageBoxDefaultButton.Button2) != DialogResult.Yes) return;
        SetBusy(true, false);
        progress.Value = 0;
        try {
            var uiProgress = new Progress<Tuple<string, int>>(v => { progress.Value = v.Item2; Append(v.Item1); });
            var engine = new Engine { Progress = (s, p) => ((IProgress<Tuple<string, int>>)uiProgress).Report(Tuple.Create(s, p)) };
            await Task.Run(() => engine.Uninstall(gamePath));
            Append("Use Steam to launch the vanilla game.");
        } catch (Exception ex) {
            Append("Uninstall stopped.");
            ShowError(ex);
        } finally {
            SetBusy(false, false);
            ShowInstalled();
        }
    }

    void LoadSettings() {
        try {
            if (!File.Exists(settings)) return;
            var d = J.Parse(File.ReadAllText(settings));
            if (Directory.Exists(J.S(d, "game"))) game.Text = J.S(d, "game");
        } catch (Exception) { }
    }

    void SaveSettings() {
        Directory.CreateDirectory(Path.GetDirectoryName(settings));
        File.WriteAllText(settings, J.Json().Serialize(new Dictionary<string, object> { { "game", game.Text.Trim() } }));
    }

    static string FindGame() {
        var roots = new List<string>();
        try {
            using (var key = Registry.CurrentUser.OpenSubKey(@"Software\Valve\Steam")) {
                if (key != null) { string s = Convert.ToString(key.GetValue("SteamPath")); if (!String.IsNullOrEmpty(s)) roots.Add(s); }
            }
        } catch (Exception) { }
        roots.Add(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86), "Steam"));
        foreach (var drive in DriveInfo.GetDrives()) if (drive.DriveType == DriveType.Fixed) roots.Add(Path.Combine(drive.RootDirectory.FullName, "SteamLibrary"));
        foreach (string root in roots.ToArray()) {
            string vdf = Path.Combine(root, "steamapps", "libraryfolders.vdf");
            try {
                if (File.Exists(vdf))
                    foreach (Match m in Regex.Matches(File.ReadAllText(vdf), "\"path\"\\s+\"([^\"]+)\"")) roots.Add(m.Groups[1].Value.Replace("\\\\", "\\"));
            } catch (Exception) { }
        }
        foreach (string root in roots.Distinct(StringComparer.OrdinalIgnoreCase)) {
            string p = Path.Combine(root, "steamapps", "common", "Total War SHOGUN 2");
            if (File.Exists(Path.Combine(p, GameLayout.GameExe))) return p;
        }
        return "";
    }
}

static class SelfTests {
    static void Expect<T>(Action action, string failure) where T : Exception {
        try { action(); } catch (T) { return; }
        throw new Exception(failure);
    }

    public static void Run(string path) {
        var results = new List<string>();
        Expect<InvalidDataException>(() => Engine.Under(Path.GetTempPath(), "../escape"), "Path traversal accepted.");
        results.Add("PASS: path traversal rejected");

        // The bootstrap is a 32-bit exe without a UAC manifest; these words make Windows demand elevation to start it.
        foreach (string word in new[] { "install", "setup", "update", "patch", "upgrade", "uninst" })
            if (GameLayout.Bootstrap.ToLowerInvariant().Contains(word)) throw new Exception("Bootstrap name triggers installer detection: " + word);
        results.Add("PASS: bootstrap name avoids Windows installer-detection elevation");

        byte[] source = Encoding.ASCII.GetBytes("abcdefgh");
        var spec = new Dictionary<string, object> {
            { "destination", "x" }, { "length", 10 },
            { "writes", new object[] { new Dictionary<string, object> { { "offset", 2 }, { "data", Convert.ToBase64String(Encoding.ASCII.GetBytes("XY")) } }, new Dictionary<string, object> { { "offset", 8 }, { "data", Convert.ToBase64String(Encoding.ASCII.GetBytes("ZZ")) } } } }
        };
        spec["sha256"] = Engine.Hash(Encoding.ASCII.GetBytes("abXYefghZZ"));
        if (Encoding.ASCII.GetString(Engine.Patch(source, spec)) != "abXYefghZZ") throw new Exception("Patch writes failed.");
        spec["sha256"] = Engine.Hash(source);
        Expect<InvalidDataException>(() => Engine.Patch(source, spec), "Unverified patch output accepted.");
        results.Add("PASS: byte writes, file growth and output verification");
        StreamTests(results);
        ComposeTests(results);

        if (Release.HasEmbedded()) {
            var release = Release.Load(null);
            results.Add("PASS: embedded release signature (" + release.Version + ")");
            byte[] original = Release.Resource("release");
            original[original.Length - 1] ^= 1;
            string temp = Path.Combine(Path.GetTempPath(), "S2UB-tampered-" + Guid.NewGuid().ToString("N") + OnlineUpdates.PackageExtension);
            File.WriteAllBytes(temp, original);
            try { Expect<InvalidDataException>(() => Release.Load(temp), "Tampered package accepted."); } finally { File.Delete(temp); }
            results.Add("PASS: tampered release rejected");
            string packageTest = Path.Combine(Path.GetTempPath(), "S2UB-version-test-" + Guid.NewGuid().ToString("N") + OnlineUpdates.PackageExtension);
            File.WriteAllBytes(packageTest, Release.Resource("release"));
            try { Expect<InvalidDataException>(() => OnlineUpdates.ValidatePackage(packageTest, new OnlineRelease { Version = "9.9.9" }), "Mismatched signed release version accepted."); } finally { File.Delete(packageTest); }
            results.Add("PASS: updater rejects a signed package that differs from the advertised version");
        }

        string root = Path.Combine(Path.GetTempPath(), "S2UB-publication-test-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(root);
        try {
            string live = Engine.Under(root, GameLayout.Folder), stage = Engine.Under(root, GameLayout.StagingPrefix + "test"), previous = Engine.Under(root, GameLayout.PreviousPrefix + "test");
            Directory.CreateDirectory(live); Directory.CreateDirectory(stage);
            File.WriteAllText(Engine.Under(live, "old.txt"), "old installation");
            File.WriteAllText(Engine.Under(root, GameLayout.Launcher), "old launcher");
            File.WriteAllText(Engine.Under(root, GameLayout.Bootstrap), "old bootstrap");
            File.WriteAllText(Engine.Under(stage, GameLayout.Bootstrap), "new bootstrap");
            Expect<FileNotFoundException>(() => Engine.PublishVerified(stage, root, previous), "Incomplete publication succeeded.");
            if (!File.Exists(Engine.Under(live, "old.txt")) || File.ReadAllText(Engine.Under(root, GameLayout.Bootstrap)) != "old bootstrap" || File.ReadAllText(Engine.Under(root, GameLayout.Launcher)) != "old launcher")
                throw new Exception("Publication rollback failed.");
            results.Add("PASS: failed update restores the previous folder and already-replaced bootstrap");
            File.WriteAllText(Engine.Under(stage, GameLayout.Launcher), "new launcher");
            Engine.PublishVerified(stage, root, previous);
            if (!File.Exists(Engine.Under(previous, "old.txt")) || File.ReadAllText(Engine.Under(root, GameLayout.Launcher)) != "new launcher" || File.ReadAllText(Engine.Under(root, GameLayout.Bootstrap)) != "new bootstrap")
                throw new Exception("Publication commit failed.");
            results.Add("PASS: verified update publishes and keeps the previous installation");
        } finally { Cleanup(root, "S2UB-publication-test-"); }

        root = Path.Combine(Path.GetTempPath(), "S2UB-uninstall-test-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(root);
        try {
            string live = Engine.Under(root, GameLayout.Folder), record = Engine.Under(live, GameLayout.StateFile);
            Directory.CreateDirectory(Engine.Under(live, "previous-launchers"));
            File.WriteAllText(Engine.Under(root, GameLayout.GameExe), "vanilla bootstrap");
            File.WriteAllText(Engine.Under(root, GameLayout.GameEngine), "vanilla engine");
            File.WriteAllText(Engine.Under(live, GameLayout.GameEngine), "patched engine");
            foreach (string name in GameLayout.RootFiles) {
                File.WriteAllText(Engine.Under(live, name), name); File.WriteAllText(Engine.Under(root, name), name);
                File.WriteAllText(Engine.Under(live, "previous-launchers/" + name), "previous");
            }
            string previous = Engine.Under(root, GameLayout.PreviousPrefix + "old");
            Directory.CreateDirectory(previous); File.WriteAllText(Engine.Under(previous, GameLayout.StateFile), "{}");
            string foreign = Engine.Under(root, GameLayout.PreviousPrefix + "foreign");
            Directory.CreateDirectory(foreign); File.WriteAllText(Engine.Under(foreign, "keep.txt"), "not ours");
            var state = new Dictionary<string, object> { { "schema", 1 }, { "version", "0.0.1" }, { "files", GameLayout.Destinations.Select(x => new Dictionary<string, object> { { "file", x } }).ToArray() } };
            var wrong = new Dictionary<string, object>(state);
            wrong["files"] = new[] { new Dictionary<string, object> { { "file", "../" + GameLayout.GameEngine } } };
            File.WriteAllText(record, J.Json().Serialize(wrong));
            Expect<InvalidDataException>(() => new Engine { IgnoreRunningGame = true }.Uninstall(root), "Unsafe uninstall record accepted.");
            if (!File.Exists(Engine.Under(live, GameLayout.GameEngine))) throw new Exception("Unsafe uninstall removed files.");
            results.Add("PASS: uninstall rejects unexpected file paths before removing anything");
            File.WriteAllText(record, J.Json().Serialize(state));
            File.WriteAllText(Engine.Under(root, GameLayout.Launcher), "unrecognized replacement");
            Expect<IOException>(() => new Engine { IgnoreRunningGame = true }.Uninstall(root), "Unrecognized launcher was removed.");
            if (!File.Exists(Engine.Under(live, GameLayout.GameEngine))) throw new Exception("Uninstall removed files before stopping.");
            results.Add("PASS: uninstall keeps an unrecognized root launcher and stops before deletion");
            File.WriteAllText(Engine.Under(root, GameLayout.Launcher), GameLayout.Launcher);
            File.WriteAllText(Engine.Under(live, "keep-user-file.txt"), "user file");
            new Engine { IgnoreRunningGame = true }.Uninstall(root);
            if (File.Exists(record) || File.Exists(Engine.Under(live, GameLayout.GameEngine)) || GameLayout.RootFiles.Any(n => File.Exists(Engine.Under(root, n))) || Directory.Exists(previous))
                throw new Exception("Uninstall left managed files.");
            if (File.ReadAllText(Engine.Under(root, GameLayout.GameExe)) != "vanilla bootstrap" || File.ReadAllText(Engine.Under(root, GameLayout.GameEngine)) != "vanilla engine" || !File.Exists(Engine.Under(live, "keep-user-file.txt")) || !File.Exists(Engine.Under(foreign, "keep.txt")))
                throw new Exception("Uninstall removed unrelated files.");
            results.Add("PASS: uninstall removes managed files and launchers; keeps vanilla files, user files and unrecognized folders");
        } finally { Cleanup(root, "S2UB-uninstall-test-"); }

        if (!OnlineUpdates.NeedsUpdate("0.1.9-preview", "0.1.10-preview") || OnlineUpdates.NeedsUpdate("0.1.10-preview", "0.1.9-preview") || OnlineUpdates.NeedsUpdate("0.1.3-preview", "0.1.3-preview")
            || ReleaseVersion.Parse("1.0.0-preview.10").CompareTo(ReleaseVersion.Parse("1.0.0-preview.2")) <= 0 || ReleaseVersion.Parse("1.0.0").CompareTo(ReleaseVersion.Parse("1.0.0-preview")) <= 0)
            throw new Exception("Release version ordering failed.");
        results.Add("PASS: updater orders versions numerically and avoids same-version installs and downgrades");

        var rows = new List<object>();
        foreach (string version in new[] { "0.1.9-preview", "0.1.10-preview", "0.1.11-preview" }) {
            string name = OnlineUpdates.PackageName(version);
            rows.Add(new Dictionary<string, object> {
                { "tag_name", "v" + version }, { "draft", version == "0.1.11-preview" }, { "prerelease", true },
                { "assets", new[] { new Dictionary<string, object> { { "name", name }, { "state", "uploaded" }, { "size", 123 }, { "browser_download_url", OnlineUpdates.DownloadPrefix + "v" + version + "/" + name } } } }
            });
        }
        string json = J.Json().Serialize(rows);
        var selected = OnlineUpdates.Select(json);
        if (selected.Version != "0.1.10-preview") throw new Exception("Release selection failed.");
        results.Add("PASS: updater selects the newest published package including prereleases and excludes drafts");
        Expect<InvalidDataException>(() => OnlineUpdates.Select(json.Replace("https://github.com/", "https://untrusted.invalid/")), "External update URL accepted.");
        results.Add("PASS: updater rejects download addresses outside the release repository");
        Expect<OperationCanceledException>(() => OnlineUpdates.Download(selected, Path.Combine(Path.GetTempPath(), "S2UB-cancelled-download"), new CancellationToken(true), null), "Download cancellation failed.");
        results.Add("PASS: cancelled download stops before making a request");
        File.WriteAllLines(path, results);
    }

    static void Cleanup(string root, string prefix) {
        Engine.NoLinks(root);
        if (!Path.GetFileName(root).StartsWith(prefix, StringComparison.Ordinal)) throw new Exception("Invalid self-test cleanup target.");
        Directory.Delete(root, true);
    }

    static Dictionary<string, object> Clone(Dictionary<string, object> value) { return J.Parse(J.Json().Serialize(value)); }

    static Dictionary<string, object> SmallFile(string source, string destination, byte[] original, byte[] output) {
        return new Dictionary<string, object> {
            { "source", source }, { "destination", destination }, { "sourceSha256", Engine.Hash(original) },
            { "length", output.Length }, { "sha256", Engine.Hash(output) },
            { "writes", new object[] { new Dictionary<string, object> { { "offset", 0 }, { "data", Convert.ToBase64String(output) } } } }
        };
    }

    static byte[] SignedSchemaFixture(RSACryptoServiceProvider rsa, int schema, string minimum) {
        var manifest = new Dictionary<string, object> { { "schema", schema }, { "version", "0.1.8-traits-test" } };
        if (minimum != null) manifest["minimumInstallerVersion"] = minimum;
        byte[] zip;
        using (var buffer = new MemoryStream()) {
            using (var archive = new ZipArchive(buffer, ZipArchiveMode.Create, true)) {
                using (var writer = new StreamWriter(archive.CreateEntry("manifest.json").Open())) writer.Write(J.Json().Serialize(manifest));
                using (var output = archive.CreateEntry("launcher.exe").Open()) output.WriteByte(1);
            }
            zip = buffer.ToArray();
        }
        byte[] signature = rsa.SignData(zip, CryptoConfig.MapNameToOID("SHA256"));
        using (var package = new MemoryStream()) {
            byte[] magic = Encoding.ASCII.GetBytes(GameLayout.PackageMagic);
            package.Write(magic, 0, magic.Length);package.Write(BitConverter.GetBytes(signature.Length), 0, 4);
            package.Write(signature, 0, signature.Length);package.Write(zip, 0, zip.Length);return package.ToArray();
        }
    }

    static void StreamTests(List<string> results) {
        string root = Path.Combine(Path.GetTempPath(), "S2UB-stream-test-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(root);
        try {
            byte[] original = new byte[2 * 1024 * 1024 + 31];
            for (int i = 0; i < original.Length; i++) original[i] = (byte)(i * 17 + 3);
            byte[] expected = (byte[])original.Clone();
            int boundary = 1024 * 1024 - 2;
            byte[] first = { 0xA0, 0xB1, 0xC2, 0xD3 }, last = { 0xE4, 0xF5 };
            Buffer.BlockCopy(first, 0, expected, boundary, first.Length);Buffer.BlockCopy(last, 0, expected, expected.Length - last.Length, last.Length);
            var spec = new Dictionary<string, object> {
                { "kind", "stream-delta" }, { "source", GameLayout.DataPack }, { "destination", GameLayout.DataPack },
                { "length", (long)original.Length }, { "sourceSha256", Engine.Hash(original) }, { "sha256", Engine.Hash(expected) },
                { "writes", new object[] {
                    new Dictionary<string, object> { { "offset", boundary }, { "expect", Convert.ToBase64String(original.Skip(boundary).Take(4).ToArray()) }, { "data", Convert.ToBase64String(first) } },
                    new Dictionary<string, object> { { "offset", original.Length - 2 }, { "expect", Convert.ToBase64String(original.Skip(original.Length - 2).ToArray()) }, { "data", Convert.ToBase64String(last) } }
                } }
            };
            string source = Path.Combine(root, "source.pack"), output = Path.Combine(root, "output.pack");
            File.WriteAllBytes(source, original);
            if (Engine.StreamDeltaHash(source, spec, CancellationToken.None) != Engine.Hash(expected)) throw new Exception("Streaming hash calculation failed.");
            Engine.PatchStream(source, output, spec, CancellationToken.None);
            if (Engine.FileHash(output) != Engine.Hash(expected) || Engine.FileHash(source) != Engine.Hash(original)) throw new Exception("Stream reconstruction/source preservation failed.");
            results.Add("PASS: bounded stream copy patches buffer-boundary/end writes, verifies hashes and preserves source");
            File.Delete(output);
            var wrong = Clone(spec);
            J.Obj(J.Arr(wrong["writes"])[0])["offset"] = -1;
            Expect<InvalidDataException>(() => Engine.PatchStream(source, output, wrong, CancellationToken.None), "Negative stream range accepted.");
            wrong = Clone(spec);J.Obj(J.Arr(wrong["writes"])[1])["offset"] = boundary + 1;
            Expect<InvalidDataException>(() => Engine.PatchStream(source, output, wrong, CancellationToken.None), "Overlapping stream writes accepted.");
            wrong = Clone(spec);J.Obj(J.Arr(wrong["writes"])[0])["data"] = Convert.ToBase64String(new byte[] { 1 });
            Expect<InvalidDataException>(() => Engine.PatchStream(source, output, wrong, CancellationToken.None), "Variable-size stream write accepted.");
            wrong = Clone(spec);wrong["length"] = original.Length + 1;
            Expect<InvalidDataException>(() => Engine.PatchStream(source, output, wrong, CancellationToken.None), "Stream length change accepted.");
            if (File.Exists(output)) throw new Exception("Malformed stream created an output.");
            results.Add("PASS: stream rejects negative/overlapping/variable-size writes and length changes before output creation");
            wrong = Clone(spec);J.Obj(J.Arr(wrong["writes"])[0])["expect"] = Convert.ToBase64String(new byte[4]);
            Expect<InvalidDataException>(() => Engine.PatchStream(source, output, wrong, CancellationToken.None), "Mismatched original bytes accepted.");
            if (File.Exists(output)) throw new Exception("Failed stream retained partial output.");
            wrong = Clone(spec);wrong["sourceSha256"] = new string('0', 64);
            Expect<InvalidDataException>(() => Engine.PatchStream(source, output, wrong, CancellationToken.None), "Wrong stream source SHA accepted.");
            wrong = Clone(spec);wrong["sha256"] = new string('0', 64);
            Expect<InvalidDataException>(() => Engine.PatchStream(source, output, wrong, CancellationToken.None), "Wrong stream output SHA accepted.");
            Expect<OperationCanceledException>(() => Engine.PatchStream(source, output, spec, new CancellationToken(true)), "Stream cancellation ignored.");
            if (File.Exists(output) || Engine.FileHash(source) != Engine.Hash(original)) throw new Exception("Failed/cancelled stream changed source or retained output.");
            File.WriteAllText(output, "foreign output");
            Expect<IOException>(() => Engine.PatchStream(source, output, spec, CancellationToken.None), "Existing output overwritten.");
            if (File.ReadAllText(output) != "foreign output") throw new Exception("Unowned stream output deleted.");
            Expect<InvalidDataException>(() => Engine.PatchStream(source, source, spec, CancellationToken.None), "Stream source could be overwritten.");
            results.Add("PASS: stream rejects old-byte/hash mismatches, cleans cancelled output and preserves pre-existing/source files");

            string game = Path.Combine(root, "game");Directory.CreateDirectory(Engine.Under(game, "data"));
            byte[] exe = Encoding.ASCII.GetBytes("vanilla exe"), dll = Encoding.ASCII.GetBytes("vanilla dll");
            File.WriteAllBytes(Engine.Under(game, GameLayout.GameExe), exe);File.WriteAllBytes(Engine.Under(game, GameLayout.GameEngine), dll);
            File.WriteAllBytes(Engine.Under(game, GameLayout.DataPack), original);
            var engineSpec = SmallFile(GameLayout.GameEngine, GameLayout.GameEngine, dll, Encoding.ASCII.GetBytes("patched dll"));
            var bootstrapSpec = SmallFile(GameLayout.GameExe, GameLayout.Bootstrap, exe, Encoding.ASCII.GetBytes("bootstrap"));
            var legacy = new Release { PackageHash = new string('1', 64), LauncherExe = Encoding.ASCII.GetBytes("launcher"), Manifest = new Dictionary<string, object> {
                { "schema", 1 }, { "version", "0.1.7-rankidle-test" }, { "files", new object[] { engineSpec, bootstrapSpec } }
            } };
            var streamed = new Release { PackageHash = new string('2', 64), LauncherExe = legacy.LauncherExe, Manifest = new Dictionary<string, object> {
                { "schema", 2 }, { "version", "0.1.8-traits-test" }, { "minimumInstallerVersion", GameLayout.StreamDeltaMinimum },
                { "files", new object[] { engineSpec, bootstrapSpec, spec } }
            } };
            var installer = new Engine { IgnoreRunningGame = true };
            installer.Install(legacy, game);installer.Install(streamed, game);
            string live = Engine.Under(game, GameLayout.Folder), livePack = Engine.Under(live, GameLayout.DataPack);
            if (Engine.FileHash(livePack) != Engine.Hash(expected) || J.N(J.Parse(File.ReadAllText(Engine.Under(live, GameLayout.StateFile))), "schema") != 2)
                throw new Exception("Schema-1 to schema-2 install failed.");
            results.Add("PASS: schema-1 baseline upgrades to a verified schema-2 managed data pack");
            var badRelease = new Release { PackageHash = streamed.PackageHash, LauncherExe = streamed.LauncherExe, Manifest = Clone(streamed.Manifest) };
            var badPack = J.Obj(J.Arr(badRelease.Manifest["files"])[2]);J.Obj(J.Arr(badPack["writes"])[0])["expect"] = Convert.ToBase64String(new byte[4]);
            Expect<InvalidDataException>(() => installer.Install(badRelease, game), "Bad stream update published.");
            if (Engine.FileHash(livePack) != Engine.Hash(expected) || Engine.InstalledVersion(game) != streamed.Version || Directory.GetDirectories(game, GameLayout.StagingPrefix + "*").Length != 0)
                throw new Exception("Failed stream update changed the live installation.");
            string stage = Engine.Under(game, GameLayout.StagingPrefix + "stream-rollback"), previous = Engine.Under(game, GameLayout.PreviousPrefix + "stream-rollback");
            Directory.CreateDirectory(Engine.Under(stage, "data"));
            File.WriteAllText(Engine.Under(stage, GameLayout.Bootstrap), "incomplete bootstrap");File.WriteAllText(Engine.Under(stage, GameLayout.DataPack), "incomplete pack");
            Expect<FileNotFoundException>(() => Engine.PublishVerified(stage, game, previous), "Incomplete stream publication succeeded.");
            if (Engine.FileHash(livePack) != Engine.Hash(expected) || File.ReadAllBytes(Engine.Under(game, GameLayout.Bootstrap)).Length != Encoding.ASCII.GetBytes("bootstrap").Length)
                throw new Exception("Publication rollback did not restore the managed pack/bootstrap.");
            results.Add("PASS: failed stream build/publication preserves the previous pack and restores root launchers");
            File.WriteAllText(livePack, "unrecognized replacement");
            Expect<IOException>(() => installer.Uninstall(game), "Modified managed data pack deleted.");
            if (!File.Exists(Engine.Under(game, GameLayout.Launcher))) throw new Exception("Ownership rejection removed root files.");
            File.WriteAllBytes(livePack, expected);installer.Uninstall(game);
            if (File.Exists(livePack) || File.Exists(Engine.Under(live, GameLayout.StateFile)) || Engine.FileHash(Engine.Under(game, GameLayout.DataPack)) != Engine.Hash(original))
                throw new Exception("Schema-2 uninstall/source preservation failed.");
            results.Add("PASS: schema-2 uninstall checks ownership and removes only managed data, keeping vanilla pack");
            using (var rsa = new RSACryptoServiceProvider(2048)) {
                string key = rsa.ToXmlString(false);
                Release.Parse(SignedSchemaFixture(rsa, 1, "0.1.0-preview"), key);
                Expect<InvalidDataException>(() => Release.Parse(SignedSchemaFixture(rsa, 4, GameLayout.StreamDeltaMinimum), key), "Unknown release schema accepted.");
                Expect<InvalidDataException>(() => Release.Parse(SignedSchemaFixture(rsa, 2, null), key), "Schema-2 compatibility guard omitted.");
                Expect<InvalidDataException>(() => Release.Parse(SignedSchemaFixture(rsa, 2, "0.1.0-preview"), key), "Schema-2 old installer guard accepted.");
                if (ReleaseVersion.Parse(OnlineUpdates.AppVersion).CompareTo(ReleaseVersion.Parse(GameLayout.StreamDeltaMinimum)) >= 0)
                    Release.Parse(SignedSchemaFixture(rsa, 2, GameLayout.StreamDeltaMinimum), key);
                else Expect<InvalidDataException>(() => Release.Parse(SignedSchemaFixture(rsa, 2, GameLayout.StreamDeltaMinimum), key), "Old installer accepted streaming package.");
                results.Add("PASS: signed schema compatibility accepts legacy releases and enforces schema-2 installer minimum");
            }
        } finally { Cleanup(root, "S2UB-stream-test-"); }
    }

    static void ComposeTests(List<string> results) {
        string root = Path.Combine(Path.GetTempPath(), "S2UB-compose-test-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(root);
        try {
            byte[] original = new byte[2 * 1024 * 1024 + 31];
            for (int i = 0; i < original.Length; i++) original[i] = (byte)(i * 13 + 7);
            byte[] literal = Encoding.ASCII.GetBytes("new archive index and a resized table");
            byte[] expected = original.Skip(1024 * 1024 - 1).Take(1024 * 1024 + 17).Concat(literal).Concat(original.Take(53)).ToArray();
            var spec = new Dictionary<string, object> {
                { "kind", "stream-compose" }, { "source", GameLayout.DataPack }, { "destination", GameLayout.DataPack },
                { "length", (long)expected.Length }, { "sourceSha256", Engine.Hash(original) }, { "sha256", Engine.Hash(expected) },
                { "segments", new object[] {
                    new Dictionary<string, object> { { "offset", 1024 * 1024 - 1 }, { "length", 1024 * 1024 + 17 } },
                    new Dictionary<string, object> { { "data", Convert.ToBase64String(literal) } },
                    new Dictionary<string, object> { { "offset", 0 }, { "length", 53 } }
                } }
            };
            string source = Path.Combine(root, "source.pack"), output = Path.Combine(root, "output.pack");
            File.WriteAllBytes(source, original);
            if (Engine.StreamComposeHash(source, spec, CancellationToken.None) != Engine.Hash(expected)) throw new Exception("Composition hash failed.");
            Engine.PatchCompose(source, output, spec, CancellationToken.None);
            if (Engine.FileHash(output) != Engine.Hash(expected) || Engine.FileHash(source) != Engine.Hash(original)) throw new Exception("Composition reconstruction changed source or output.");
            results.Add("PASS: variable-length pack composition copies reordered ranges across buffers, inserts literals and preserves source");
            File.Delete(output);
            foreach (string problem in new[] { "negative", "outside", "zero", "shape", "empty", "sum", "source", "output", "fraction", "large", "segments" }) {
                var wrong = Clone(spec);
                var first = J.Obj(J.Arr(wrong["segments"])[0]);
                if (problem == "negative") first["offset"] = -1;
                if (problem == "outside") first["offset"] = original.Length;
                if (problem == "zero") first["length"] = 0;
                if (problem == "shape") first["data"] = "AQ==";
                if (problem == "empty") J.Obj(J.Arr(wrong["segments"])[1])["data"] = "";
                if (problem == "sum") wrong["length"] = expected.Length + 1;
                if (problem == "source") wrong["sourceSha256"] = new string('0', 64);
                if (problem == "output") wrong["sha256"] = new string('0', 64);
                if (problem == "fraction") first["offset"] = 0.5;
                if (problem == "large") wrong["length"] = 8L * 1024 * 1024 * 1024 + 1;
                if (problem == "segments") wrong["segments"] = Enumerable.Repeat((object)first, 200001).ToArray();
                Expect<InvalidDataException>(() => Engine.PatchCompose(source, output, wrong, CancellationToken.None), "Malformed composition accepted: " + problem);
                if (File.Exists(output)) throw new Exception("Failed composition kept output: " + problem);
            }
            Expect<OperationCanceledException>(() => Engine.PatchCompose(source, output, spec, new CancellationToken(true)), "Composition cancellation ignored.");
            File.WriteAllText(output, "foreign output");
            Expect<IOException>(() => Engine.PatchCompose(source, output, spec, CancellationToken.None), "Existing composition output overwritten.");
            if (File.ReadAllText(output) != "foreign output") throw new Exception("Foreign composition output was deleted.");
            Expect<InvalidDataException>(() => Engine.PatchCompose(source, source, spec, CancellationToken.None), "Composition source overwritten.");
            results.Add("PASS: composition rejects malformed ranges/shapes/lengths/hashes, cleans failed output and protects existing files");

            string game = Path.Combine(root, "game");Directory.CreateDirectory(Engine.Under(game, "data"));
            byte[] exe = Encoding.ASCII.GetBytes("vanilla exe"), dll = Encoding.ASCII.GetBytes("vanilla dll");
            File.WriteAllBytes(Engine.Under(game, GameLayout.GameExe), exe);File.WriteAllBytes(Engine.Under(game, GameLayout.GameEngine), dll);
            foreach (string pack in GameLayout.PrivatePacks) File.WriteAllBytes(Engine.Under(game, pack), original);
            var engineSpec = SmallFile(GameLayout.GameEngine, GameLayout.GameEngine, dll, Encoding.ASCII.GetBytes("patched dll"));
            var bootstrapSpec = SmallFile(GameLayout.GameExe, GameLayout.Bootstrap, exe, Encoding.ASCII.GetBytes("bootstrap"));
            var files = new List<object> { engineSpec, bootstrapSpec };
            foreach (string pack in GameLayout.PrivatePacks) {
                var copy = Clone(spec);copy["source"] = pack;copy["destination"] = pack;files.Add(copy);
            }
            var legacy = new Release { PackageHash = new string('1', 64), LauncherExe = Encoding.ASCII.GetBytes("launcher"), Manifest = new Dictionary<string, object> {
                { "schema", 2 }, { "version", "0.1.10-fear-values-test" }, { "files", new object[] { engineSpec, bootstrapSpec } }
            } };
            var composed = new Release { PackageHash = new string('2', 64), LauncherExe = legacy.LauncherExe, Manifest = new Dictionary<string, object> {
                { "schema", 3 }, { "version", GameLayout.StreamComposeMinimum }, { "minimumInstallerVersion", GameLayout.StreamComposeMinimum }, { "files", files.ToArray() }
            } };
            var installer = new Engine { IgnoreRunningGame = true };
            installer.Install(legacy, game);installer.Install(composed, game);
            string live = Engine.Under(game, GameLayout.Folder);
            foreach (string pack in GameLayout.PrivatePacks) if (Engine.FileHash(Engine.Under(live, pack)) != Engine.Hash(expected)) throw new Exception("Composed pack upgrade failed.");
            var bad = new Release { PackageHash = composed.PackageHash, LauncherExe = composed.LauncherExe, Manifest = Clone(composed.Manifest) };
            J.Obj(J.Arr(bad.Manifest["files"])[3])["sha256"] = new string('0', 64);
            Expect<InvalidDataException>(() => installer.Install(bad, game), "Bad composed update published.");
            if (Engine.InstalledVersion(game) != composed.Version || Directory.GetDirectories(game, GameLayout.StagingPrefix + "*").Length != 0)
                throw new Exception("Failed composed update changed live state or retained stage.");
            foreach (string pack in GameLayout.PrivatePacks) if (Engine.FileHash(Engine.Under(live, pack)) != Engine.Hash(expected)) throw new Exception("Failed composed update changed installed pack.");
            results.Add("PASS: schema-2 installation upgrades to three schema-3 packs and a failed composition preserves the previous build");
            string models = Engine.Under(live, "data/models.pack");File.WriteAllText(models, "foreign pack");
            Expect<IOException>(() => installer.Uninstall(game), "Uninstall removed modified composed pack.");
            if (!File.Exists(Engine.Under(game, GameLayout.Launcher))) throw new Exception("Ownership rejection removed root launcher.");
            File.WriteAllBytes(models, expected);installer.Uninstall(game);
            foreach (string pack in GameLayout.PrivatePacks) if (File.Exists(Engine.Under(live, pack)) || Engine.FileHash(Engine.Under(game, pack)) != Engine.Hash(original)) throw new Exception("Composed uninstall modified vanilla or retained managed pack.");
            results.Add("PASS: schema-3 uninstall checks all pack ownership and removes managed packs while retaining originals");
            using (var rsa = new RSACryptoServiceProvider(2048)) {
                string key = rsa.ToXmlString(false);
                Expect<InvalidDataException>(() => Release.Parse(SignedSchemaFixture(rsa, 3, null), key), "Schema-3 omitted minimum accepted.");
                Expect<InvalidDataException>(() => Release.Parse(SignedSchemaFixture(rsa, 3, GameLayout.StreamDeltaMinimum), key), "Schema-3 old installer minimum accepted.");
                if (ReleaseVersion.Parse(OnlineUpdates.AppVersion).CompareTo(ReleaseVersion.Parse(GameLayout.StreamComposeMinimum)) >= 0)
                    Release.Parse(SignedSchemaFixture(rsa, 3, GameLayout.StreamComposeMinimum), key);
                else Expect<InvalidDataException>(() => Release.Parse(SignedSchemaFixture(rsa, 3, GameLayout.StreamComposeMinimum), key), "Old installer accepted composition package.");
            }
            results.Add("PASS: signed schema-3 releases require the composition installer version");
        } finally { Cleanup(root, "S2UB-compose-test-"); }
    }
}
}
