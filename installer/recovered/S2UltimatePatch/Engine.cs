using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Threading;

namespace S2UltimatePatch;

public sealed class Engine
{
	private sealed class StreamWrite
	{
		public long Offset;

		public byte[] Expected;

		public byte[] Data;
	}

	private sealed class ComposeSegment
	{
		public long Offset;

		public long Length;

		public byte[] Data;
	}

	public Action<string, int> Progress;

	public CancellationToken Cancel;

	public bool IgnoreRunningGame;

	public void Log(string s, int p)
	{
		if (Progress != null)
		{
			Progress(s, p);
		}
		Cancel.ThrowIfCancellationRequested();
	}

	public static string Hash(byte[] data)
	{
		using SHA256 sHA = SHA256.Create();
		return Hex(sHA.ComputeHash(data));
	}

	public static string FileHash(string p)
	{
		using FileStream inputStream = File.OpenRead(p);
		using SHA256 sHA = SHA256.Create();
		return Hex(sHA.ComputeHash(inputStream));
	}

	private static string Hex(byte[] b)
	{
		return BitConverter.ToString(b).Replace("-", "").ToLowerInvariant();
	}

	public static string Under(string root, string relative)
	{
		if (string.IsNullOrEmpty(relative) || Path.IsPathRooted(relative))
		{
			throw new InvalidDataException("Absolute package paths are forbidden.");
		}
		string text = Path.GetFullPath(root).TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
		string fullPath = Path.GetFullPath(Path.Combine(text, relative.Replace('/', Path.DirectorySeparatorChar)));
		if (!fullPath.StartsWith(text, StringComparison.OrdinalIgnoreCase))
		{
			throw new InvalidDataException("Package path escapes its installation folder.");
		}
		return fullPath;
	}

	public static void NoLinks(string path)
	{
		for (DirectoryInfo directoryInfo = new DirectoryInfo(Path.GetFullPath(path)); directoryInfo != null; directoryInfo = directoryInfo.Parent)
		{
			if (directoryInfo.Exists && (directoryInfo.Attributes & FileAttributes.ReparsePoint) != 0)
			{
				throw new IOException("Linked installation folders are not supported: " + directoryInfo.FullName);
			}
		}
	}

	private static void RejectLinkedFile(string path)
	{
		if (File.Exists(path) && (File.GetAttributes(path) & FileAttributes.ReparsePoint) != 0)
		{
			throw new IOException("Linked installed files are not supported: " + path);
		}
	}

	public static void LogLauncherError(Exception ex)
	{
		try
		{
			string text = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Shogun2UltimatePatch");
			Directory.CreateDirectory(text);
			File.AppendAllText(Path.Combine(text, "launcher-errors.log"), DateTime.UtcNow.ToString("o") + " " + ex?.ToString() + Environment.NewLine);
		}
		catch (IOException)
		{
		}
		catch (UnauthorizedAccessException)
		{
		}
	}

	public void GameClosed()
	{
		if (IgnoreRunningGame)
		{
			return;
		}
		string[] array = new string[5]
		{
			"shogun2",
			Path.GetFileNameWithoutExtension("Shogun2_UB.exe"),
			Path.GetFileNameWithoutExtension("Launch_Shogun2_Ultimate_Patch.exe"),
			Path.GetFileNameWithoutExtension("UltimatePatch_Launcher.exe"),
			Path.GetFileNameWithoutExtension("UltimatePatch_Mod_Manager.exe")
		};
		for (int i = 0; i < array.Length; i++)
		{
			if (Process.GetProcessesByName(array[i]).Any((Process p) => p.Id != Process.GetCurrentProcess().Id))
			{
				throw new IOException("Close Shogun 2 and the Upgrade Patch before installing, updating or uninstalling.");
			}
		}
	}

	private static void RequireHash(string path, string expected, string what)
	{
		if (!File.Exists(path))
		{
			throw new FileNotFoundException("Missing " + what + ": " + path);
		}
		if (FileHash(path) != expected)
		{
			throw new InvalidDataException("Unsupported or modified " + what + ": " + path + ". This release supports the current Steam build of Total War: SHOGUN 2 only. Verify the game files in Steam and try again.");
		}
	}

	private static IEnumerable<Dictionary<string, object>> Files(Release r)
	{
		return J.Arr(r.Manifest["files"]).Select(J.Obj);
	}

	private static void ValidateFiles(Release r)
	{
		long num = J.N(r.Manifest, "schema");
		if (num != 1 && num != 2 && num != 3)
		{
			throw new InvalidDataException("Unsupported release schema.");
		}
		HashSet<string> hashSet = new HashSet<string>(StringComparer.Ordinal);
		foreach (Dictionary<string, object> item in Files(r))
		{
			string text = J.S(item, "destination");
			if (!GameLayout.AllowedDestination(text, num) || !hashSet.Add(text))
			{
				throw new InvalidDataException("Unsupported or duplicate release destination: " + text);
			}
			string text2 = (item.ContainsKey("kind") ? J.S(item, "kind") : "byte-delta");
			if (text == "og11.dll" && (J.S(item, "source") != "empire.retail.dll" || !r.Manifest.ContainsKey("minimumInstallerVersion") || ReleaseVersion.Parse(J.S(r.Manifest, "minimumInstallerVersion")).CompareTo(ReleaseVersion.Parse("0.1.20-atmosphere-test")) < 0))
			{
				throw new InvalidDataException("The private renderer requires its exact original-engine source and compatible installer minimum.");
			}
			if (GameLayout.PrivatePacks.Contains(text, StringComparer.Ordinal))
			{
				if (J.S(item, "source") != text || ((num != 2 || !(text == "data/data.pack") || !(text2 == "stream-delta")) && (num != 3 || !(text2 == "stream-compose"))))
				{
					throw new InvalidDataException("Managed packs require an exact supported source and streaming recipe.");
				}
			}
			else if (text2 != "byte-delta")
			{
				throw new InvalidDataException("Binary files require byte deltas.");
			}
		}
	}

	public void Preflight(Release r, string game)
	{
		ValidateFiles(r);
		NoLinks(game);
		if (!File.Exists(Under(game, "shogun2.exe")))
		{
			throw new FileNotFoundException("Select the Total War: SHOGUN 2 folder that contains Shogun2.exe.");
		}
		int num = 0;
		foreach (Dictionary<string, object> item in Files(r))
		{
			Log("Verifying vanilla " + J.S(item, "source") + "…", 2 + num * 4);
			RequireHash(Under(game, J.S(item, "source")), J.S(item, "sourceSha256"), "game file");
			num++;
		}
	}

	public static byte[] Patch(byte[] source, Dictionary<string, object> f)
	{
		long num = J.N(f, "length");
		if (num <= 0 || num > 268435456)
		{
			throw new InvalidDataException("Invalid output length.");
		}
		byte[] array = new byte[num];
		Buffer.BlockCopy(source, 0, array, 0, (int)Math.Min(source.Length, num));
		object[] array2 = J.Arr(f["writes"]);
		for (int i = 0; i < array2.Length; i++)
		{
			Dictionary<string, object> d = J.Obj(array2[i]);
			long num2 = J.N(d, "offset");
			byte[] array3 = J.B(d, "data");
			if (num2 < 0 || num2 > array.Length - array3.Length)
			{
				throw new InvalidDataException("Patch range is outside the output file.");
			}
			Buffer.BlockCopy(array3, 0, array, (int)num2, array3.Length);
		}
		if (Hash(array) != J.S(f, "sha256"))
		{
			throw new InvalidDataException("Patched " + J.S(f, "destination") + " failed verification.");
		}
		return array;
	}

	private static bool Sha256Text(string hash)
	{
		if (hash != null && hash.Length == 64)
		{
			return hash.All((char c) => (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'));
		}
		return false;
	}

	private static List<StreamWrite> StreamWrites(Dictionary<string, object> f, long sourceLength)
	{
		long num = J.N(f, "length");
		if (num <= 0 || num > 8589934592L || num != sourceLength)
		{
			throw new InvalidDataException("Stream deltas must preserve the exact supported source length.");
		}
		if (!Sha256Text(J.S(f, "sourceSha256")))
		{
			throw new InvalidDataException("Invalid stream source SHA-256.");
		}
		List<StreamWrite> list = new List<StreamWrite>();
		long num2 = 0L;
		object[] array = J.Arr(f["writes"]);
		foreach (object x in array)
		{
			if (list.Count >= 4096)
			{
				throw new InvalidDataException("Too many stream writes.");
			}
			Dictionary<string, object> d = J.Obj(x);
			StreamWrite streamWrite = new StreamWrite
			{
				Offset = J.N(d, "offset"),
				Expected = J.B(d, "expect"),
				Data = J.B(d, "data")
			};
			if (streamWrite.Expected.Length == 0 || streamWrite.Expected.Length != streamWrite.Data.Length || streamWrite.Data.Length > 1048576 || streamWrite.Offset < 0 || streamWrite.Offset > num - streamWrite.Data.Length)
			{
				throw new InvalidDataException("Invalid same-length stream write range.");
			}
			num2 += streamWrite.Data.Length;
			if (num2 > 16777216)
			{
				throw new InvalidDataException("Stream delta payload exceeds its bounded limit.");
			}
			list.Add(streamWrite);
		}
		list.Sort((StreamWrite a, StreamWrite b) => a.Offset.CompareTo(b.Offset));
		long num3 = 0L;
		foreach (StreamWrite item in list)
		{
			if (item.Offset < num3)
			{
				throw new InvalidDataException("Overlapping stream writes are forbidden.");
			}
			num3 = item.Offset + item.Data.Length;
		}
		return list;
	}

	private static string StreamDelta(FileStream source, Stream output, Dictionary<string, object> f, CancellationToken cancel)
	{
		List<StreamWrite> list = StreamWrites(f, source.Length);
		byte[] buffer = new byte[1048576];
		SHA256 originalHash = SHA256.Create();
		try
		{
			SHA256 outputHash = SHA256.Create();
			try
			{
				Action<long> action = (long count) =>
				{
					while (count > 0)
					{
						cancel.ThrowIfCancellationRequested();
						int num4 = source.Read(buffer, 0, (int)Math.Min(buffer.Length, count));
						if (num4 <= 0)
						{
							throw new EndOfStreamException("Source ended while copying a stream delta.");
						}
						originalHash.TransformBlock(buffer, 0, num4, buffer, 0);
						outputHash.TransformBlock(buffer, 0, num4, buffer, 0);
						output.Write(buffer, 0, num4);
						count -= num4;
					}
				};
				foreach (StreamWrite item in list)
				{
					action(item.Offset - source.Position);
					int num;
					int num2;
					for (num = 0; num < item.Expected.Length; num += num2)
					{
						cancel.ThrowIfCancellationRequested();
						num2 = source.Read(buffer, num, item.Expected.Length - num);
						if (num2 <= 0)
						{
							throw new EndOfStreamException("Source ended at a stream write.");
						}
					}
					originalHash.TransformBlock(buffer, 0, num, buffer, 0);
					for (int num3 = 0; num3 < num; num3++)
					{
						if (buffer[num3] != item.Expected[num3])
						{
							throw new InvalidDataException("Original bytes do not match the stream delta at offset " + item.Offset + ".");
						}
					}
					outputHash.TransformBlock(item.Data, 0, item.Data.Length, item.Data, 0);
					output.Write(item.Data, 0, item.Data.Length);
				}
				action(source.Length - source.Position);
				originalHash.TransformFinalBlock(new byte[0], 0, 0);
				outputHash.TransformFinalBlock(new byte[0], 0, 0);
				if (Hex(originalHash.Hash) != J.S(f, "sourceSha256"))
				{
					throw new InvalidDataException("Stream source SHA-256 did not match.");
				}
				return Hex(outputHash.Hash);
			}
			finally
			{
				if (outputHash != null)
				{
					((IDisposable)outputHash).Dispose();
				}
			}
		}
		finally
		{
			if (originalHash != null)
			{
				((IDisposable)originalHash).Dispose();
			}
		}
	}

	public static string StreamDeltaHash(string source, Dictionary<string, object> f, CancellationToken cancel)
	{
		using FileStream source2 = new FileStream(source, FileMode.Open, FileAccess.Read, FileShare.Read, 1048576, FileOptions.SequentialScan);
		return StreamDelta(source2, Stream.Null, f, cancel);
	}

	private static long ComposeInteger(Dictionary<string, object> op, string key)
	{
		if (!op.TryGetValue(key, out var value) || (!(value is int) && !(value is long)))
		{
			throw new InvalidDataException("Pack composition lengths and offsets must be JSON integers.");
		}
		return Convert.ToInt64(value);
	}

	private static List<ComposeSegment> ComposeSegments(Dictionary<string, object> f, long sourceLength)
	{
		long num = ComposeInteger(f, "length");
		long num2 = 0L;
		long num3 = 0L;
		if (num <= 0 || num > 8589934592L || sourceLength <= 0 || sourceLength > 8589934592L || !Sha256Text(J.S(f, "sourceSha256")) || !Sha256Text(J.S(f, "sha256")))
		{
			throw new InvalidDataException("Invalid pack composition length or SHA-256.");
		}
		object[] array = J.Arr(f["segments"]);
		if (array.Length == 0 || array.Length > 200000)
		{
			throw new InvalidDataException("Invalid pack composition segment count.");
		}
		List<ComposeSegment> list = new List<ComposeSegment>();
		object[] array2 = array;
		for (int i = 0; i < array2.Length; i++)
		{
			Dictionary<string, object> dictionary = J.Obj(array2[i]);
			ComposeSegment composeSegment = new ComposeSegment();
			if (dictionary.Count == 1 && dictionary.ContainsKey("data"))
			{
				if (((dictionary["data"] as string) ?? throw new InvalidDataException("Pack composition data must be base64 text.")).Length > (50331648 - num3 + 2) / 3 * 4)
				{
					throw new InvalidDataException("Pack composition payload exceeds its bounded limit.");
				}
				composeSegment.Data = J.B(dictionary, "data");
				composeSegment.Length = composeSegment.Data.LongLength;
				num3 += composeSegment.Length;
				if (num3 > 50331648)
				{
					throw new InvalidDataException("Pack composition payload exceeds its bounded limit.");
				}
			}
			else
			{
				if (dictionary.Count != 2 || !dictionary.ContainsKey("offset") || !dictionary.ContainsKey("length"))
				{
					throw new InvalidDataException("Unknown pack composition segment shape.");
				}
				composeSegment.Offset = ComposeInteger(dictionary, "offset");
				composeSegment.Length = ComposeInteger(dictionary, "length");
				if (composeSegment.Offset < 0 || composeSegment.Length <= 0 || composeSegment.Length > sourceLength || composeSegment.Offset > sourceLength - composeSegment.Length)
				{
					throw new InvalidDataException("Pack composition source range is outside its source.");
				}
			}
			if (composeSegment.Length <= 0 || composeSegment.Length > num - num2)
			{
				throw new InvalidDataException("Pack composition segment length exceeds its output.");
			}
			num2 += composeSegment.Length;
			list.Add(composeSegment);
		}
		if (num2 != num)
		{
			throw new InvalidDataException("Pack composition segments do not match the output length.");
		}
		return list;
	}

	private static void VerifyComposeSource(FileStream source, Dictionary<string, object> f, CancellationToken cancel)
	{
		byte[] array = new byte[1048576];
		using (SHA256 sHA = SHA256.Create())
		{
			int inputCount;
			while ((inputCount = source.Read(array, 0, array.Length)) != 0)
			{
				cancel.ThrowIfCancellationRequested();
				sHA.TransformBlock(array, 0, inputCount, array, 0);
			}
			sHA.TransformFinalBlock(new byte[0], 0, 0);
			if (Hex(sHA.Hash) != J.S(f, "sourceSha256"))
			{
				throw new InvalidDataException("Pack composition source SHA-256 did not match.");
			}
		}
		cancel.ThrowIfCancellationRequested();
	}

	private static string Compose(FileStream source, Stream output, List<ComposeSegment> segments, CancellationToken cancel)
	{
		byte[] array = new byte[1048576];
		using SHA256 sHA = SHA256.Create();
		foreach (ComposeSegment segment in segments)
		{
			cancel.ThrowIfCancellationRequested();
			if (segment.Data == null)
			{
				source.Position = segment.Offset;
			}
			long num = segment.Length;
			long num2 = 0L;
			while (num > 0)
			{
				cancel.ThrowIfCancellationRequested();
				int num3 = (int)Math.Min(array.Length, num);
				if (segment.Data == null)
				{
					num3 = source.Read(array, 0, num3);
					if (num3 == 0)
					{
						throw new EndOfStreamException("Source ended inside a pack composition segment.");
					}
				}
				else
				{
					Buffer.BlockCopy(segment.Data, (int)num2, array, 0, num3);
				}
				sHA.TransformBlock(array, 0, num3, array, 0);
				output.Write(array, 0, num3);
				num2 += num3;
				num -= num3;
			}
		}
		sHA.TransformFinalBlock(new byte[0], 0, 0);
		return Hex(sHA.Hash);
	}

	public static string StreamComposeHash(string source, Dictionary<string, object> f, CancellationToken cancel)
	{
		cancel.ThrowIfCancellationRequested();
		using FileStream fileStream = new FileStream(source, FileMode.Open, FileAccess.Read, FileShare.Read, 1048576);
		List<ComposeSegment> segments = ComposeSegments(f, fileStream.Length);
		VerifyComposeSource(fileStream, f, cancel);
		return Compose(fileStream, Stream.Null, segments, cancel);
	}

	public static void PatchCompose(string source, string destination, Dictionary<string, object> f, CancellationToken cancel)
	{
		if (string.Equals(Path.GetFullPath(source), Path.GetFullPath(destination), StringComparison.OrdinalIgnoreCase))
		{
			throw new InvalidDataException("A pack composition may not overwrite its source.");
		}
		cancel.ThrowIfCancellationRequested();
		bool flag = false;
		try
		{
			using FileStream fileStream = new FileStream(source, FileMode.Open, FileAccess.Read, FileShare.Read, 1048576);
			List<ComposeSegment> segments = ComposeSegments(f, fileStream.Length);
			VerifyComposeSource(fileStream, f, cancel);
			using FileStream fileStream2 = new FileStream(destination, FileMode.CreateNew, FileAccess.Write, FileShare.None, 1048576, FileOptions.SequentialScan);
			flag = true;
			if (Compose(fileStream, fileStream2, segments, cancel) != J.S(f, "sha256"))
			{
				throw new InvalidDataException("Pack composition output SHA-256 did not match.");
			}
			fileStream2.Flush(flushToDisk: true);
		}
		catch
		{
			if (flag && File.Exists(destination))
			{
				File.Delete(destination);
			}
			throw;
		}
	}

	public static void PatchStream(string source, string destination, Dictionary<string, object> f, CancellationToken cancel)
	{
		if (string.Equals(Path.GetFullPath(source), Path.GetFullPath(destination), StringComparison.OrdinalIgnoreCase))
		{
			throw new InvalidDataException("A stream delta may not overwrite its source.");
		}
		if (!Sha256Text(J.S(f, "sha256")))
		{
			throw new InvalidDataException("Invalid stream output SHA-256.");
		}
		bool flag = false;
		try
		{
			using FileStream fileStream = new FileStream(source, FileMode.Open, FileAccess.Read, FileShare.Read, 1048576, FileOptions.SequentialScan);
			StreamWrites(f, fileStream.Length);
			using FileStream fileStream2 = new FileStream(destination, FileMode.CreateNew, FileAccess.Write, FileShare.None, 1048576, FileOptions.SequentialScan);
			flag = true;
			if (StreamDelta(fileStream, fileStream2, f, cancel) != J.S(f, "sha256"))
			{
				throw new InvalidDataException("Stream output SHA-256 did not match.");
			}
			fileStream2.Flush(flushToDisk: true);
		}
		catch
		{
			if (flag && File.Exists(destination))
			{
				File.Delete(destination);
			}
			throw;
		}
	}

	public void Build(Release r, string game, string stage)
	{
		Preflight(r, game);
		NoLinks(stage);
		Directory.CreateDirectory(stage);
		List<object> list = new List<object>();
		int num = 0;
		int val = Files(r).Count();
		foreach (Dictionary<string, object> item in Files(r))
		{
			string text = J.S(item, "destination");
			if (!GameLayout.AllowedDestination(text, J.N(r.Manifest, "schema")))
			{
				throw new InvalidDataException("Unsupported release destination: " + text);
			}
			Log("Building " + text + "…", 20 + 60 * num / Math.Max(1, val));
			string text2 = Under(stage, text);
			Directory.CreateDirectory(Path.GetDirectoryName(text2));
			if (item.ContainsKey("kind") && J.S(item, "kind") == "stream-delta")
			{
				PatchStream(Under(game, J.S(item, "source")), text2, item, Cancel);
			}
			else if (item.ContainsKey("kind") && J.S(item, "kind") == "stream-compose")
			{
				PatchCompose(Under(game, J.S(item, "source")), text2, item, Cancel);
			}
			else
			{
				byte[] bytes = Patch(File.ReadAllBytes(Under(game, J.S(item, "source"))), item);
				File.WriteAllBytes(text2, bytes);
			}
			RequireHash(Under(stage, text), J.S(item, "sha256"), "generated file");
			list.Add(new Dictionary<string, object>
			{
				{ "file", text },
				{
					"sha256",
					J.S(item, "sha256")
				}
			});
			num++;
		}
		string[] array = new string[2] { "empire.retail.dll", "Shogun2_UB.exe" };
		foreach (string text3 in array)
		{
			if (!File.Exists(Under(stage, text3)))
			{
				throw new InvalidDataException("This release does not produce " + text3 + ".");
			}
		}
		File.WriteAllBytes(Under(stage, "Launch_Shogun2_Ultimate_Patch.exe"), r.LauncherExe);
		if (r.ModManagerExe != null)
		{
			if (!r.Manifest.ContainsKey("modManagerSha256") || Hash(r.ModManagerExe) != J.S(r.Manifest, "modManagerSha256"))
			{
				throw new InvalidDataException("Mod manager differs from its signed manifest.");
			}
			File.WriteAllBytes(Under(stage, "UltimatePatch_Launcher.exe"), r.ModManagerExe);
			list.Add(new Dictionary<string, object>
			{
				{ "file", "UltimatePatch_Launcher.exe" },
				{
					"sha256",
					Hash(r.ModManagerExe)
				}
			});
		}
		if (r.ModManagerExe != null && r.PackageBytes != null)
		{
			if (Hash(r.PackageBytes) != r.PackageHash)
			{
				throw new InvalidDataException("Cached release differs from its verified package.");
			}
			File.WriteAllBytes(Under(stage, "release.s2ub"), r.PackageBytes);
			list.Add(new Dictionary<string, object>
			{
				{ "file", "release.s2ub" },
				{ "sha256", r.PackageHash }
			});
		}
		Directory.CreateDirectory(Under(stage, "mods"));
		Dictionary<string, object> obj = new Dictionary<string, object>
		{
			{
				"schema",
				J.N(r.Manifest, "schema")
			},
			{ "version", r.Version },
			{ "packageSha256", r.PackageHash },
			{
				"gameBuild",
				r.Manifest.ContainsKey("gameBuild") ? J.S(r.Manifest, "gameBuild") : ""
			},
			{
				"installedUtc",
				DateTime.UtcNow.ToString("o")
			},
			{
				"files",
				list.ToArray()
			},
			{
				"launcherSha256",
				Hash(r.LauncherExe)
			}
		};
		File.WriteAllText(Under(stage, "install-state.json"), J.Json().Serialize(obj));
		Log("All generated files verified.", 90);
	}

	public void Install(Release r, string game)
	{
		game = Path.GetFullPath(game);
		NoLinks(game);
		GameClosed();
		NoLinks(Under(game, "UltimatePatch"));
		using (new FileStream(Under(game, ".ultimatepatch-install.lock"), FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None, 1, FileOptions.DeleteOnClose))
		{
			string text = DateTime.UtcNow.ToString("yyyyMMdd_HHmmss") + "_" + Guid.NewGuid().ToString("N").Substring(0, 6);
			string text2 = Under(game, "UltimatePatch.staging_" + text);
			string text3 = Under(game, "UltimatePatch.previous_" + text);
			bool flag = false;
			try
			{
				long num = Files(r).Sum((Dictionary<string, object> f) => J.N(f, "length")) + 67108864;
				if (new DriveInfo(Path.GetPathRoot(game)).AvailableFreeSpace < num)
				{
					throw new IOException("Not enough free disk space to stage this update safely.");
				}
				Build(r, game, text2);
				Cancel.ThrowIfCancellationRequested();
				GameClosed();
				Log("Publishing verified files…", 95);
				PublishVerified(text2, game, text3);
				PrunePrevious(game, text3);
				Log("Installed " + r.Version + ". Vanilla game files were not changed.", 100);
			}
			catch (AggregateException)
			{
				flag = true;
				throw;
			}
			finally
			{
				if (!flag && Directory.Exists(text2))
				{
					NoLinks(text2);
					if (!Path.GetFileName(text2).StartsWith("UltimatePatch.staging_", StringComparison.Ordinal))
					{
						throw new IOException("Invalid staging cleanup target.");
					}
					Directory.Delete(text2, recursive: true);
				}
			}
		}
	}

	public static void PublishVerified(string stage, string game, string previous)
	{
		string text = Under(game, "UltimatePatch");
		NoLinks(stage);
		NoLinks(text);
		NoLinks(previous);
		if (!Path.GetFullPath(stage).StartsWith(Path.GetFullPath(game).TrimEnd('\\') + "\\", StringComparison.OrdinalIgnoreCase) || !Path.GetFileName(stage).StartsWith("UltimatePatch.staging_", StringComparison.Ordinal))
		{
			throw new IOException("Invalid publication staging folder.");
		}
		HashSet<string> hashSet = new HashSet<string>();
		List<string> list = new List<string>();
		bool flag = false;
		bool flag2 = false;
		bool flag3 = false;
		Directory.CreateDirectory(Under(stage, "previous-launchers"));
		string[] rootFiles = GameLayout.RootFiles;
		foreach (string text2 in rootFiles)
		{
			if (File.Exists(Under(game, text2)))
			{
				File.Copy(Under(game, text2), Under(stage, "previous-launchers/" + text2), overwrite: true);
				hashSet.Add(text2);
			}
		}
		try
		{
			if (Directory.Exists(text))
			{
				Directory.Move(text, previous);
				flag = true;
			}
			Directory.Move(stage, text);
			flag2 = true;
			string text3 = Under(previous, "mods");
			string text4 = Under(text, "mods");
			if (flag && Directory.Exists(text3))
			{
				NoLinks(text3);
				if (Directory.Exists(text4))
				{
					if (Directory.EnumerateFileSystemEntries(text4).Any())
					{
						throw new IOException("The staged mods folder must be empty.");
					}
					Directory.Delete(text4);
				}
				Directory.Move(text3, text4);
				flag3 = true;
			}
			rootFiles = GameLayout.RootFiles;
			foreach (string text5 in rootFiles)
			{
				string text6 = Under(game, text5 + ".installing");
				File.Copy(Under(text, text5), text6, overwrite: true);
				if (File.Exists(Under(game, text5)))
				{
					File.Replace(text6, Under(game, text5), null);
				}
				else
				{
					File.Move(text6, Under(game, text5));
				}
				list.Add(text5);
			}
		}
		catch (Exception item)
		{
			List<Exception> list2 = new List<Exception> { item };
			foreach (string item4 in list.AsEnumerable().Reverse())
			{
				try
				{
					if (hashSet.Contains(item4))
					{
						File.Copy(Under(text, "previous-launchers/" + item4), Under(game, item4), overwrite: true);
					}
					else
					{
						File.Delete(Under(game, item4));
					}
				}
				catch (Exception item2)
				{
					list2.Add(item2);
				}
			}
			try
			{
				if (flag3)
				{
					Directory.Move(Under(text, "mods"), Under(previous, "mods"));
				}
				if (flag2)
				{
					Directory.Move(text, stage);
				}
				if (flag)
				{
					Directory.Move(previous, text);
				}
			}
			catch (Exception item3)
			{
				list2.Add(item3);
			}
			if (list2.Count > 1)
			{
				throw new AggregateException("Update rollback needs attention. Keep the game closed; previous files have been retained.", list2);
			}
			throw;
		}
		finally
		{
			rootFiles = GameLayout.RootFiles;
			foreach (string text7 in rootFiles)
			{
				string path = Under(game, text7 + ".installing");
				if (File.Exists(path))
				{
					File.Delete(path);
				}
			}
		}
	}

	private static void PrunePrevious(string game, string keep)
	{
		foreach (string item in Directory.EnumerateDirectories(game, "UltimatePatch.previous_*"))
		{
			if (!string.Equals(Path.GetFullPath(item), Path.GetFullPath(keep), StringComparison.OrdinalIgnoreCase))
			{
				try
				{
					DeleteManagedCopy(item);
				}
				catch (IOException)
				{
				}
				catch (UnauthorizedAccessException)
				{
				}
			}
		}
	}

	private static void DeleteManagedCopy(string dir)
	{
		NoLinks(dir);
		if (!Path.GetFileName(dir).StartsWith("UltimatePatch.previous_", StringComparison.Ordinal) || !File.Exists(Path.Combine(dir, "install-state.json")) || Directory.EnumerateFileSystemEntries(dir, "*", SearchOption.AllDirectories).Any((string p) => (File.GetAttributes(p) & FileAttributes.ReparsePoint) != 0))
		{
			return;
		}
		Dictionary<string, object> dictionary;
		try
		{
			dictionary = J.Parse(File.ReadAllText(Path.Combine(dir, "install-state.json")));
		}
		catch (Exception ex) when (ex is InvalidOperationException || ex is ArgumentException || ex is InvalidDataException)
		{
			return;
		}
		try
		{
			if (!dictionary.ContainsKey("schema") || !dictionary.ContainsKey("files"))
			{
				return;
			}
			HashSet<string> owned = new HashSet<string>(StringComparer.OrdinalIgnoreCase) { Path.GetFullPath(Path.Combine(dir, "install-state.json")) };
			long num = J.N(dictionary, "schema");
			if (num != 1 && num != 2 && num != 3)
			{
				return;
			}
			foreach (Dictionary<string, object> item in J.Arr(dictionary["files"]).Select(J.Obj))
			{
				string text = J.S(item, "file");
				if (!GameLayout.AllowedDestination(text, num))
				{
					return;
				}
				owned.Add(Under(dir, text));
			}
			string[] rootFiles = GameLayout.RootFiles;
			foreach (string text2 in rootFiles)
			{
				owned.Add(Under(dir, text2));
				owned.Add(Under(dir, "previous-launchers/" + text2));
			}
			if (Directory.EnumerateFiles(dir, "*", SearchOption.AllDirectories).Any((string p) => !owned.Contains(Path.GetFullPath(p))))
			{
				return;
			}
		}
		catch (Exception ex2) when (ex2 is InvalidCastException || ex2 is FormatException || ex2 is OverflowException || ex2 is ArgumentException || ex2 is InvalidDataException || ex2 is NullReferenceException)
		{
			return;
		}
		Directory.Delete(dir, recursive: true);
	}

	public void Uninstall(string game)
	{
		game = Path.GetFullPath(game);
		NoLinks(game);
		GameClosed();
		string live = Under(game, "UltimatePatch");
		NoLinks(live);
		string path = Under(live, "install-state.json");
		if (!File.Exists(path))
		{
			throw new IOException("No installer-managed Shogun 2 Ultimate Bug Fix Patch installation was found in this folder.");
		}
		using (new FileStream(Under(game, ".ultimatepatch-install.lock"), FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None, 1, FileOptions.DeleteOnClose))
		{
			RejectLinkedFile(path);
			Dictionary<string, object> dictionary = J.Parse(File.ReadAllText(path));
			long installedSchema = J.N(dictionary, "schema");
			if (installedSchema != 1 && installedSchema != 2 && installedSchema != 3)
			{
				throw new InvalidDataException("Unrecognized installation record; nothing was removed.");
			}
			string[] array = (from x in J.Arr(dictionary["files"]).Select(J.Obj)
				select J.S(x, "file")).ToArray();
			if (array.Any((string x) => !GameLayout.AllowedDestination(x, installedSchema)) || array.Distinct(StringComparer.Ordinal).Count() != array.Length)
			{
				throw new InvalidDataException("Unexpected installed file paths; nothing was removed.");
			}
			if (installedSchema >= 2)
			{
				foreach (Dictionary<string, object> item in J.Arr(dictionary["files"]).Select(J.Obj))
				{
					string text = Under(live, J.S(item, "file"));
					RejectLinkedFile(text);
					NoLinks(Path.GetDirectoryName(text));
					if (!item.ContainsKey("sha256") || !Sha256Text(J.S(item, "sha256")) || (File.Exists(text) && FileHash(text) != J.S(item, "sha256")))
					{
						throw new IOException("A managed file differs from its installation record; nothing was removed.");
					}
				}
			}
			List<string> list = array.Select((string x) => Under(live, x)).ToList();
			string[] rootFiles = GameLayout.RootFiles;
			foreach (string text2 in rootFiles)
			{
				string text3 = Under(live, text2);
				string text4 = Under(game, text2);
				RejectLinkedFile(text3);
				RejectLinkedFile(text4);
				if (File.Exists(text4))
				{
					if (!File.Exists(text3) || FileHash(text4) != FileHash(text3))
					{
						throw new IOException("The root " + text2 + " differs from the installed copy; nothing was removed.");
					}
					list.Add(text4);
				}
				list.Add(text3);
				list.Add(Under(live, "previous-launchers/" + text2));
			}
			foreach (string item2 in list)
			{
				NoLinks(Path.GetDirectoryName(item2));
				RejectLinkedFile(item2);
			}
			Log("Removing the Shogun 2 Ultimate Bug Fix Patch…", 10);
			GameClosed();
			foreach (string item3 in list)
			{
				if (File.Exists(item3))
				{
					File.Delete(item3);
				}
			}
			File.Delete(path);
			rootFiles = new string[3]
			{
				Under(live, "data"),
				Under(live, "previous-launchers"),
				live
			};
			foreach (string path2 in rootFiles)
			{
				if (Directory.Exists(path2) && !Directory.EnumerateFileSystemEntries(path2).Any())
				{
					Directory.Delete(path2);
				}
			}
			rootFiles = Directory.EnumerateDirectories(game, "UltimatePatch.previous_*").ToArray();
			foreach (string dir in rootFiles)
			{
				try
				{
					DeleteManagedCopy(dir);
				}
				catch (IOException)
				{
				}
				catch (UnauthorizedAccessException)
				{
				}
			}
			Log(Directory.Exists(live) ? "Uninstalled. Unrecognized files in UltimatePatch were kept." : "Uninstalled. Vanilla game files were never changed.", 100);
		}
	}

	public static string InstalledVersion(string game)
	{
		try
		{
			string path = Under(game, "UltimatePatch/install-state.json");
			return File.Exists(path) ? J.S(J.Parse(File.ReadAllText(path)), "version") : null;
		}
		catch (Exception)
		{
			return null;
		}
	}
}
