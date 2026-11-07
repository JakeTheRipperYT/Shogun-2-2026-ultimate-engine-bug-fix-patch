using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;
using Microsoft.Win32;

namespace S2UltimatePatch;

public sealed class MainForm : Form
{
	private readonly TextBox game = new TextBox();

	private readonly TextBox package = new TextBox();

	private readonly TextBox log = new TextBox();

	private readonly Button install = new Button();

	private readonly Button launch = new Button();

	private readonly Button choosePackage = new Button();

	private readonly Button cancel = new Button();

	private readonly Button uninstall = new Button();

	private readonly Button github = new Button();

	private readonly ProgressBar progress = new ProgressBar();

	private readonly Label state = new Label();

	private CancellationTokenSource cancellation;

	private bool busy;

	private bool compact;

	private readonly string settings = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Shogun2UltimatePatch", "installer-settings.json");

	public bool IsBusy => busy;

	public string GameDirectory => game.Text.Trim();

	public event Action<string> ModsRequested;

	public event Action<string, bool> InstallationChanged;

	public event Action BeforeMutation;

	public event Action<string> GameDirectoryChanged;

	public event Action<bool> BusyChanged;

	public void SetGameDirectory(string path)
	{
		game.Text = path;
	}

	public MainForm(bool preview = false, string initialGame = null)
	{
		try
		{
			Icon = Icon.ExtractAssociatedIcon(Application.ExecutablePath);
		}
		catch (Exception)
		{
		}
		Text = "Shogun 2 Ultimate Bug Fix Patch";
		ClientSize = new Size(810, 570);
		MinimumSize = new Size(820, 610);
		StartPosition = FormStartPosition.CenterScreen;
		Font = new Font("Segoe UI", 10f);
		BackColor = Color.FromArgb(27, 23, 22);
		ForeColor = Color.FromArgb(240, 235, 230);
		AutoScaleMode = AutoScaleMode.Dpi;
		Controls.Add(new Label
		{
			Text = "SHOGUN 2 ULTIMATE PATCH",
			Font = new Font("Segoe UI Semibold", 22f),
			AutoSize = true,
			Location = new Point(28, 24)
		});
		Controls.Add(new Label
		{
			Text = "By JakeTheRipper · Preview " + "0.1.46-gameplay-fixes".Replace("-preview", ""),
			AutoSize = true,
			ForeColor = Color.FromArgb(181, 163, 158),
			Location = new Point(31, 73)
		});
		FolderRow("Total War: SHOGUN 2 installation", game, 122);
		Controls.Add(new Label
		{
			Text = "Release package",
			AutoSize = true,
			Location = new Point(30, 204)
		});
		StyleBox(package);
		package.Location = new Point(30, 230);
		package.Size = new Size(505, 29);
		package.ReadOnly = true;
		Controls.Add(package);
		ButtonStyle(github, "GitHub", new Rectangle(547, 228, 108, 33));
		github.Click += (object s, EventArgs e) =>
		{
			UseGitHub();
		};
		ButtonStyle(choosePackage, "Offline…", new Rectangle(667, 228, 113, 33));
		ContextMenuStrip localMenu = new ContextMenuStrip();
		localMenu.Items.Add("Choose a downloaded .s2ub file…", null, (object s, EventArgs e) =>
		{
			ChoosePackageFile();
		});
		localMenu.Items.Add("Use included or installed release (offline)", null, (object s, EventArgs e) =>
		{
			package.Tag = ":embedded";
			package.Text = "Included / installed release (offline)";
		});
		choosePackage.Click += (object s, EventArgs e) =>
		{
			localMenu.Show(choosePackage, new Point(0, choosePackage.Height));
		};
		UseGitHub();
		ButtonStyle(install, "Install / Update", new Rectangle(30, 285, 325, 47));
		install.BackColor = Color.FromArgb(140, 38, 32);
		install.Click += async (object s, EventArgs e) =>
		{
			await Install();
		};
		ButtonStyle(launch, "Mods / Launch", new Rectangle(369, 285, 260, 47));
		launch.Click += (object s, EventArgs e) =>
		{
			Launch();
		};
		ButtonStyle(cancel, "Cancel", new Rectangle(643, 285, 137, 47));
		cancel.Enabled = false;
		cancel.Click += (object s, EventArgs e) =>
		{
			if (cancellation != null)
			{
				cancellation.Cancel();
			}
		};
		state.Text = "Your vanilla game files are never changed. Steam must be running to play.";
		state.AutoSize = false;
		state.Location = new Point(30, 347);
		state.Size = new Size(520, 42);
		state.ForeColor = Color.FromArgb(181, 163, 158);
		Controls.Add(state);
		ButtonStyle(uninstall, "Uninstall", new Rectangle(562, 347, 218, 36));
		uninstall.Click += async (object s, EventArgs e) =>
		{
			await Uninstall();
		};
		progress.Location = new Point(30, 396);
		progress.Size = new Size(750, 9);
		Controls.Add(progress);
		StyleBox(log);
		log.Multiline = true;
		log.ReadOnly = true;
		log.ScrollBars = ScrollBars.Vertical;
		log.Location = new Point(30, 421);
		log.Size = new Size(750, 120);
		log.Anchor = AnchorStyles.Top | AnchorStyles.Bottom | AnchorStyles.Left | AnchorStyles.Right;
		Controls.Add(log);
		game.Text = FindGame();
		LoadSettings();
		if (!string.IsNullOrEmpty(initialGame))
		{
			game.Text = initialGame;
		}
		if (preview && string.IsNullOrEmpty(initialGame))
		{
			game.Text = "C:\\Program Files (x86)\\Steam\\steamapps\\common\\Total War SHOGUN 2";
		}
		game.TextChanged += (object s, EventArgs e) =>
		{
			ShowInstalled();
			if (GameDirectoryChanged != null)
			{
				GameDirectoryChanged(GameDirectory);
			}
		};
		if (Release.HasEmbedded() || File.Exists(Path.Combine(game.Text, "UltimatePatch", "release.s2ub")))
		{
			try
			{
				Append("Available offline release " + IncludedRelease().Version + ". Patched files are built locally from your own game.");
			}
			catch (Exception ex2)
			{
				Append("The included release could not be read: " + ex2.Message);
			}
		}
		ShowInstalled();
		FormClosing += (object s, FormClosingEventArgs e) =>
		{
			if (busy)
			{
				e.Cancel = true;
				MessageBox.Show(this, "Wait for the current operation to finish before closing.", Text, MessageBoxButtons.OK, MessageBoxIcon.Asterisk);
			}
		};
	}

	public void ConfigureCompact()
	{
		compact = true;
		game.ReadOnly = true;
		Button button = Controls.OfType<Button>().Single((Button b) => b.Text.StartsWith("Browse", StringComparison.Ordinal));
		Controls.Clear();
		launch.Visible = false;
		TableLayoutPanel layout = new TableLayoutPanel
		{
			Dock = DockStyle.Fill,
			ColumnCount = 1,
			RowCount = 13,
			Padding = new Padding(18, 12, 18, 16)
		};
		layout.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100f));
		Control[] array = new Control[11]
		{
			game, package, log, install, cancel, uninstall, github, choosePackage, progress, state,
			button
		};
		foreach (Control obj in array)
		{
			obj.Width = 10;
			obj.MinimumSize = Size.Empty;
		}
		float[] array2 = new float[12]
		{
			40f, 24f, 36f, 24f, 32f, 38f, 48f, 40f, 40f, 65f,
			12f, 28f
		};
		foreach (float num2 in array2)
		{
			layout.RowStyles.Add(new RowStyle(SizeType.Absolute, num2));
		}
		layout.RowStyles.Add(new RowStyle(SizeType.Percent, 100f));
		Controls.Add(layout);
		Action<Control> action = (Control c) =>
		{
			c.Dock = DockStyle.Fill;
			c.Margin = new Padding(0, 0, 0, 7);
			layout.Controls.Add(c);
		};
		action(new Label
		{
			Text = "INSTALL / UPDATE",
			Font = new Font("Segoe UI Semibold", 14f),
			ForeColor = ForeColor,
			TextAlign = ContentAlignment.MiddleLeft
		});
		action(new Label
		{
			Text = "Game folder",
			ForeColor = ForeColor,
			TextAlign = ContentAlignment.BottomLeft
		});
		TableLayoutPanel tableLayoutPanel = new TableLayoutPanel
		{
			Dock = DockStyle.Fill,
			ColumnCount = 2,
			RowCount = 1,
			Margin = Padding.Empty
		};
		tableLayoutPanel.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100f));
		tableLayoutPanel.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 88f));
		game.Dock = DockStyle.Fill;
		game.Margin = new Padding(0, 0, 8, 0);
		button.Text = "Browse...";
		button.Dock = DockStyle.Fill;
		button.Margin = Padding.Empty;
		tableLayoutPanel.Controls.Add(game);
		tableLayoutPanel.Controls.Add(button);
		action(tableLayoutPanel);
		action(new Label
		{
			Text = "Release package",
			ForeColor = ForeColor,
			TextAlign = ContentAlignment.BottomLeft
		});
		action(package);
		Func<Control, Control, TableLayoutPanel> func = (Control left, Control right) =>
		{
			TableLayoutPanel tableLayoutPanel2 = new TableLayoutPanel
			{
				ColumnCount = 2,
				RowCount = 1,
				Dock = DockStyle.Fill,
				Margin = Padding.Empty,
				ColumnStyles = 
				{
					new ColumnStyle(SizeType.Percent, 50f),
					new ColumnStyle(SizeType.Percent, 50f)
				}
			};
			DockStyle dock = (right.Dock = DockStyle.Fill);
			left.Dock = dock;
			left.Margin = new Padding(0, 0, 6, 0);
			right.Margin = Padding.Empty;
			tableLayoutPanel2.Controls.Add(left);
			tableLayoutPanel2.Controls.Add(right);
			return tableLayoutPanel2;
		};
		action(func(github, choosePackage));
		action(install);
		action(uninstall);
		action(cancel);
		action(state);
		action(progress);
		action(new Label
		{
			Text = "ACTIVITY",
			Font = new Font("Segoe UI Semibold", 10f),
			ForeColor = ForeColor,
			TextAlign = ContentAlignment.MiddleLeft
		});
		action(log);
	}

	private void UseGitHub()
	{
		package.Tag = null;
		package.Text = "GitHub — latest release";
	}

	private void ChoosePackageFile()
	{
		using OpenFileDialog openFileDialog = new OpenFileDialog
		{
			Filter = "Shogun 2 Ultimate Bug Fix Patch release (*.s2ub)|*.s2ub",
			Title = "Choose a signed Shogun 2 Ultimate Bug Fix Patch release"
		};
		if (openFileDialog.ShowDialog() != DialogResult.OK)
		{
			return;
		}
		try
		{
			Release release = Release.Load(openFileDialog.FileName);
			package.Tag = openFileDialog.FileName;
			package.Text = Path.GetFileName(openFileDialog.FileName);
			Append("Selected " + release.Version + "; signature verified.");
		}
		catch (Exception ex)
		{
			ShowError(ex);
		}
	}

	private void ShowInstalled()
	{
		string text = (Directory.Exists(game.Text.Trim()) ? Engine.InstalledVersion(game.Text.Trim()) : null);
		launch.Enabled = !busy && text != null;
		if (!busy)
		{
			state.Text = ((text != null) ? ("Installed · " + text + ". Vanilla game files are unchanged.") : "Not installed. Your vanilla game files are never changed.");
		}
	}

	private void Launch()
	{
		try
		{
			if (ModsRequested != null)
			{
				ModsRequested(GameDirectory);
				return;
			}
			string text = Engine.Under(game.Text.Trim(), "Launch_Shogun2_Ultimate_Patch.exe");
			if (!File.Exists(text))
			{
				throw new FileNotFoundException("Install the Shogun 2 Ultimate Bug Fix Patch first.");
			}
			Process.Start(new ProcessStartInfo(text)
			{
				WorkingDirectory = Path.GetFullPath(game.Text.Trim()),
				UseShellExecute = true
			});
		}
		catch (Exception ex)
		{
			ShowError(ex);
		}
	}

	private void FolderRow(string label, TextBox box, int y)
	{
		Controls.Add(new Label
		{
			Text = label,
			AutoSize = true,
			Location = new Point(30, y)
		});
		StyleBox(box);
		box.Location = new Point(30, y + 27);
		box.Size = new Size(625, 29);
		Controls.Add(box);
		Button button = new Button();
		ButtonStyle(button, "Browse…", new Rectangle(667, y + 25, 113, 33));
		button.Click += (object s, EventArgs e) =>
		{
			using FolderBrowserDialog folderBrowserDialog = new FolderBrowserDialog
			{
				Description = label,
				SelectedPath = (Directory.Exists(box.Text) ? box.Text : "")
			};
			if (folderBrowserDialog.ShowDialog() == DialogResult.OK)
			{
				box.Text = folderBrowserDialog.SelectedPath;
			}
		};
	}

	private void ButtonStyle(Button b, string text, Rectangle bounds)
	{
		b.Text = text;
		b.Bounds = bounds;
		b.FlatStyle = FlatStyle.Flat;
		b.FlatAppearance.BorderColor = Color.FromArgb(92, 74, 70);
		b.BackColor = Color.FromArgb(48, 40, 38);
		b.ForeColor = ForeColor;
		Controls.Add(b);
	}

	private void StyleBox(TextBox t)
	{
		t.BackColor = Color.FromArgb(38, 33, 31);
		t.ForeColor = ForeColor;
		t.BorderStyle = BorderStyle.FixedSingle;
	}

	private void Append(string s)
	{
		log.AppendText(DateTime.Now.ToString("HH:mm:ss") + "  " + s + Environment.NewLine);
	}

	private void ShowError(Exception ex)
	{
		Engine.LogLauncherError(ex);
		string s = ((ex is UnauthorizedAccessException) ? "Windows denied access to the game folder. Close the game and, if this folder requires it, run this installer as administrator." : ex.Message);
		Append(s);
		MessageBox.Show(this, s, Text, MessageBoxButtons.OK, MessageBoxIcon.Exclamation);
	}

	private void SetBusy(bool value, bool cancellable)
	{
		busy = value;
		Control[] array = new Control[4] { install, uninstall, choosePackage, github };
		for (int i = 0; i < array.Length; i++)
		{
			array[i].Enabled = !value;
		}
		game.ReadOnly = value || compact;
		cancel.Enabled = value & cancellable;
		launch.Enabled = !value;
		if (BusyChanged != null)
		{
			BusyChanged(value);
		}
	}

	private Release IncludedRelease()
	{
		if (Release.HasEmbedded())
		{
			return Release.Load(null);
		}
		string path = Path.Combine(GameDirectory, "UltimatePatch", "release.s2ub");
		if (!File.Exists(path))
		{
			return null;
		}
		return Release.Load(path);
	}

	private async Task Install()
	{
		if (busy)
		{
			return;
		}
		string gamePath = game.Text.Trim();
		string pkg = package.Tag as string;
		if (!Directory.Exists(gamePath))
		{
			ShowError(new IOException("Choose the Total War: SHOGUN 2 folder first."));
			return;
		}
		SetBusy(value: true, cancellable: true);
		cancellation = new CancellationTokenSource();
		progress.Value = 0;
		bool applied = false;
		try
		{
			if (BeforeMutation != null)
			{
				BeforeMutation();
			}
			SaveSettings();
			Release included = ((pkg == null || pkg == ":embedded") ? IncludedRelease() : null);
			if (pkg == null)
			{
				state.Text = "Checking GitHub for the latest release…";
				Append(state.Text);
				OnlineRelease latest = null;
				try
				{
					latest = await Task.Run(() => OnlineUpdates.Latest(cancellation.Token));
				}
				catch (InvalidDataException) when (included != null)
				{
					Append("No release is published on GitHub yet; using the included release.");
				}
				if (latest != null && included != null && !OnlineUpdates.NeedsUpdate(included.Version, latest.Version))
				{
					string text = Engine.InstalledVersion(gamePath);
					if (text != null && !OnlineUpdates.NeedsUpdate(text, included.Version))
					{
						state.Text = "Up to date \ufffd " + text;
						Append("No newer release is available. Your installed files were kept.");
						return;
					}
					Append("Using included " + included.Version + "; published " + latest.Version + " is not newer.");
					latest = null;
				}
				if (latest != null)
				{
					Append("Latest published release: " + latest.Version);
					string text2 = Engine.InstalledVersion(gamePath);
					if (text2 != null && !OnlineUpdates.NeedsUpdate(text2, latest.Version))
					{
						state.Text = "Up to date · " + text2;
						Append("No newer release is available. Your installed files were kept.");
						return;
					}
					Progress<Tuple<long, long>> downloadProgress = new Progress<Tuple<long, long>>((Tuple<long, long> v) =>
					{
						state.Text = "Downloading " + latest.Version + " · " + v.Item1 / 1024 + " KB";
						progress.Value = (int)((v.Item2 > 0) ? Math.Min(100L, v.Item1 * 100 / v.Item2) : 0);
					});
					string folder = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Shogun2UltimatePatch", "downloads");
					pkg = await Task.Run(() => OnlineUpdates.Download(latest, folder, cancellation.Token, (long a, long b) =>
					{
						((IProgress<Tuple<long, long>>)downloadProgress).Report(Tuple.Create(a, b));
					}));
					Append("Downloaded " + latest.Version + "; release signature verified.");
					progress.Value = 0;
				}
			}
			else if (pkg == ":embedded")
			{
				pkg = null;
			}
			Release release = ((pkg == null) ? included : Release.Load(pkg));
			if (release == null)
			{
				throw new IOException("No offline release is available. Choose GitHub or a signed release package.");
			}
			if (ModsRequested != null && release.ModManagerExe == null)
			{
				throw new InvalidDataException("This older release needs its original setup. Choose a release that includes the combined launcher.");
			}
			Append("Installing " + release.Version + ". Any existing installation is kept until the new one is verified.");
			if (release.Manifest.ContainsKey("patches"))
			{
				foreach (Dictionary<string, object> item in J.Arr(release.Manifest["patches"]).Select(J.Obj))
				{
					Append("  • " + J.S(item, "title"));
				}
			}
			Progress<Tuple<string, int>> uiProgress = new Progress<Tuple<string, int>>((Tuple<string, int> v) =>
			{
				state.Text = v.Item1;
				progress.Value = Math.Max(0, Math.Min(100, v.Item2));
				Append(v.Item1);
			});
			Engine engine = new Engine
			{
				Cancel = cancellation.Token,
				Progress = (string s, int p) =>
				{
					((IProgress<Tuple<string, int>>)uiProgress).Report(Tuple.Create(s, p));
				}
			};
			await Task.Run(() =>
			{
				engine.Install(release, gamePath);
			});
			applied = true;
			Append("Installation complete. Mods & Play is ready in this launcher.");
		}
		catch (OperationCanceledException)
		{
			Append("Cancelled. Installed files were preserved.");
		}
		catch (Exception ex3)
		{
			Append("Installation stopped.");
			ShowError(ex3);
		}
		finally
		{
			SetBusy(value: false, cancellable: false);
			cancellation.Dispose();
			cancellation = null;
			ShowInstalled();
			if (InstallationChanged != null)
			{
				InstallationChanged(gamePath, applied);
			}
		}
	}

	private async Task Uninstall()
	{
		if (busy)
		{
			return;
		}
		string gamePath = game.Text.Trim();
		if (!Directory.Exists(gamePath))
		{
			ShowError(new IOException("Choose the Total War: SHOGUN 2 folder first."));
		}
		else
		{
			if (MessageBox.Show(this, "Remove the Shogun 2 Ultimate Bug Fix Patch and its launcher?\n\nVanilla game files, saves and settings are kept.", "Uninstall", MessageBoxButtons.YesNo, MessageBoxIcon.Question, MessageBoxDefaultButton.Button2) != DialogResult.Yes)
			{
				return;
			}
			SetBusy(value: true, cancellable: false);
			progress.Value = 0;
			bool applied = false;
			try
			{
				if (BeforeMutation != null)
				{
					BeforeMutation();
				}
				Progress<Tuple<string, int>> uiProgress = new Progress<Tuple<string, int>>((Tuple<string, int> v) =>
				{
					progress.Value = v.Item2;
					Append(v.Item1);
				});
				Engine engine = new Engine
				{
					Progress = (string s, int p) =>
					{
						((IProgress<Tuple<string, int>>)uiProgress).Report(Tuple.Create(s, p));
					}
				};
				await Task.Run(() =>
				{
					engine.Uninstall(gamePath);
				});
				applied = true;
				Append("Use Steam to launch the vanilla game.");
			}
			catch (Exception ex)
			{
				Append("Uninstall stopped.");
				ShowError(ex);
			}
			finally
			{
				SetBusy(value: false, cancellable: false);
				ShowInstalled();
				if (InstallationChanged != null)
				{
					InstallationChanged(gamePath, applied);
				}
			}
		}
	}

	private void LoadSettings()
	{
		try
		{
			if (File.Exists(settings))
			{
				Dictionary<string, object> d = J.Parse(File.ReadAllText(settings));
				if (Directory.Exists(J.S(d, "game")))
				{
					game.Text = J.S(d, "game");
				}
			}
		}
		catch (Exception)
		{
		}
	}

	private void SaveSettings()
	{
		Directory.CreateDirectory(Path.GetDirectoryName(settings));
		File.WriteAllText(settings, J.Json().Serialize(new Dictionary<string, object> { 
		{
			"game",
			game.Text.Trim()
		} }));
	}

	public static string FindGame()
	{
		List<string> list = new List<string>();
		try
		{
			using RegistryKey registryKey = Registry.CurrentUser.OpenSubKey("Software\\Valve\\Steam");
			if (registryKey != null)
			{
				string text = Convert.ToString(registryKey.GetValue("SteamPath"));
				if (!string.IsNullOrEmpty(text))
				{
					list.Add(text);
				}
			}
		}
		catch (Exception)
		{
		}
		list.Add(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86), "Steam"));
		DriveInfo[] drives = DriveInfo.GetDrives();
		foreach (DriveInfo driveInfo in drives)
		{
			if (driveInfo.DriveType == DriveType.Fixed)
			{
				list.Add(Path.Combine(driveInfo.RootDirectory.FullName, "SteamLibrary"));
			}
		}
		string[] array = list.ToArray();
		for (int i = 0; i < array.Length; i++)
		{
			string path = Path.Combine(array[i], "steamapps", "libraryfolders.vdf");
			try
			{
				if (!File.Exists(path))
				{
					continue;
				}
				foreach (Match item in Regex.Matches(File.ReadAllText(path), "\"path\"\\s+\"([^\"]+)\""))
				{
					list.Add(item.Groups[1].Value.Replace("\\\\", "\\"));
				}
			}
			catch (Exception)
			{
			}
		}
		foreach (string item2 in list.Distinct(StringComparer.OrdinalIgnoreCase))
		{
			string text2 = Path.Combine(item2, "steamapps", "common", "Total War SHOGUN 2");
			if (File.Exists(Path.Combine(text2, "shogun2.exe")))
			{
				return text2;
			}
		}
		return "";
	}
}
