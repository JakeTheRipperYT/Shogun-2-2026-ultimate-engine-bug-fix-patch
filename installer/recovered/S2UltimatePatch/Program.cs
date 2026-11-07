using System;
using System.Drawing;
using System.IO;
using System.Windows.Forms;

namespace S2UltimatePatch;

internal static class Program
{
	[STAThread]
	private static int Main(string[] args)
	{
		if (args.Length != 0)
		{
			string log = "installer-error.txt";
			try
			{
				if (args[0] == "--preview" && args.Length == 2)
				{
					Application.EnableVisualStyles();
					using (MainForm mainForm = new MainForm(preview: true))
					{
						mainForm.Show();
						Application.DoEvents();
						using Bitmap bitmap = new Bitmap(mainForm.Width, mainForm.Height);
						mainForm.DrawToBitmap(bitmap, new Rectangle(0, 0, mainForm.Width, mainForm.Height));
						bitmap.Save(args[1]);
					}
					return 0;
				}
				if (args[0] == "--self-test")
				{
					SelfTests.Run((args.Length > 1) ? args[1] : "installer-selftest.txt");
					return 0;
				}
				if (args[0] == "--build-only" && args.Length == 4)
				{
					string fullPath = Path.GetFullPath(args[3]);
					log = fullPath + ".log";
					if (Directory.Exists(fullPath))
					{
						throw new IOException("Build-only output already exists.");
					}
					Release r = Release.Load((args[2] == ":embedded") ? null : args[2]);
					Engine engine = new Engine();
					engine.Progress = (string s, int p) =>
					{
						File.AppendAllText(log, p + "% " + s + Environment.NewLine);
					};
					engine.Build(r, args[1], fullPath);
					File.AppendAllText(log, "SUCCESS" + Environment.NewLine);
					return 0;
				}
				if ((args[0] == "--install" || args[0] == "--uninstall") && args.Length == 2)
				{
					log = "installer-" + args[0].Substring(2) + ".log";
					Engine engine2 = new Engine
					{
						Progress = (string s, int p) =>
						{
							File.AppendAllText(log, p + "% " + s + Environment.NewLine);
						}
					};
					if (args[0] == "--install")
					{
						engine2.Install(Release.Load(null), args[1]);
					}
					else
					{
						engine2.Uninstall(args[1]);
					}
					File.AppendAllText(log, "SUCCESS" + Environment.NewLine);
					return 0;
				}
				if (args[0] == "--game")
				{
					return UnifiedLauncher.Run(args);
				}
				if ((args[0] == "--preview-unified" || args[0] == "--preview-install") && args.Length == 3)
				{
					Application.EnableVisualStyles();
					Application.SetCompatibleTextRenderingDefault(defaultValue: false);
					using (UnifiedForm unifiedForm = new UnifiedForm(args[1], null, previewMode: true, args[0] == "--preview-unified"))
					{
						unifiedForm.StartPosition = FormStartPosition.Manual;
						unifiedForm.Location = new Point(-20000, -20000);
						unifiedForm.ShowInTaskbar = false;
						unifiedForm.Show();
						Application.DoEvents();
						using Bitmap bitmap2 = new Bitmap(unifiedForm.Width, unifiedForm.Height);
						unifiedForm.DrawToBitmap(bitmap2, new Rectangle(Point.Empty, unifiedForm.Size));
						bitmap2.Save(args[2]);
					}
					return 0;
				}
				throw new ArgumentException("Unknown installer command.");
			}
			catch (Exception ex)
			{
				File.AppendAllText(log, "FAILED: " + ex?.ToString() + Environment.NewLine);
				return 1;
			}
		}
		return UnifiedLauncher.Run(args);
	}
}
