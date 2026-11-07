using System;
using System.Linq;

namespace S2UltimatePatch;

public static class GameLayout
{
	public const string Product = "Shogun 2 Ultimate Bug Fix Patch";

	public const string SteamAppId = "34330";

	public const string GameExe = "shogun2.exe";

	public const string GameEngine = "empire.retail.dll";

	public const string Folder = "UltimatePatch";

	public const string Bootstrap = "Shogun2_UB.exe";

	public const string Launcher = "Launch_Shogun2_Ultimate_Patch.exe";

	public const string ModManager = "UltimatePatch_Launcher.exe";

	public const string LegacyModManager = "UltimatePatch_Mod_Manager.exe";

	public const string OfflineRelease = "release.s2ub";

	public const string ModManagerMinimum = "0.1.44-unified-launcher";

	public const string Renderer = "og11.dll";

	public const string RendererMinimum = "0.1.20-atmosphere-test";

	public const string StateFile = "install-state.json";

	public const string LockFile = ".ultimatepatch-install.lock";

	public const string StagingPrefix = "UltimatePatch.staging_";

	public const string PreviousPrefix = "UltimatePatch.previous_";

	public const string PackageMagic = "S2UBPKG1";

	public const string DataPack = "data/data.pack";

	public const string StreamDeltaMinimum = "0.1.8-traits-test";

	public const string StreamComposeMinimum = "0.1.11-collection-test";

	public static readonly string[] PrivatePacks = new string[3] { "data/data.pack", "data/models.pack", "data/local_en.pack" };

	public static readonly string[] Destinations = new string[2] { "empire.retail.dll", "Shogun2_UB.exe" };

	public static readonly string[] RootFiles = new string[2] { "Shogun2_UB.exe", "Launch_Shogun2_Ultimate_Patch.exe" };

	public static bool AllowedDestination(string path, long schema)
	{
		if (!Destinations.Contains(path, StringComparer.Ordinal) && (schema != 2 || !(path == "data/data.pack")))
		{
			if (schema == 3)
			{
				switch (path)
				{
				default:
					return PrivatePacks.Contains(path, StringComparer.Ordinal);
				case "og11.dll":
				case "UltimatePatch_Launcher.exe":
				case "UltimatePatch_Mod_Manager.exe":
				case "release.s2ub":
					return true;
				}
			}
			return false;
		}
		return true;
	}
}
