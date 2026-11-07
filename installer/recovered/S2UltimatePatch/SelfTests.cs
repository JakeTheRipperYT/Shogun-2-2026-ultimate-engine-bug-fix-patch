using System;
using System.Collections.Generic;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Threading;

namespace S2UltimatePatch;

internal static class SelfTests
{
	private static void Expect<T>(Action action, string failure) where T : Exception
	{
		try
		{
			action();
		}
		catch (T)
		{
			return;
		}
		throw new Exception(failure);
	}

	public static void Run(string path)
	{
		List<string> list = new List<string>();
		using (RSACryptoServiceProvider rSACryptoServiceProvider = new RSACryptoServiceProvider())
		{
			rSACryptoServiceProvider.FromXmlString(Encoding.UTF8.GetString(Release.Resource("publicKey")));
			if (!rSACryptoServiceProvider.PublicOnly)
			{
				throw new Exception("Application embeds a private signing key.");
			}
		}
		list.Add("PASS: executable contains a valid public-only release verification key");
		Expect<InvalidDataException>(() =>
		{
			Engine.Under(Path.GetTempPath(), "../escape");
		}, "Path traversal accepted.");
		list.Add("PASS: path traversal rejected");
		string[] array = new string[6] { "install", "setup", "update", "patch", "upgrade", "uninst" };
		foreach (string text in array)
		{
			if ("Shogun2_UB.exe".ToLowerInvariant().Contains(text))
			{
				throw new Exception("Bootstrap name triggers installer detection: " + text);
			}
		}
		list.Add("PASS: bootstrap name avoids Windows installer-detection elevation");
		byte[] source = Encoding.ASCII.GetBytes("abcdefgh");
		Dictionary<string, object> spec = new Dictionary<string, object>
		{
			{ "destination", "x" },
			{ "length", 10 },
			{
				"writes",
				new object[2]
				{
					new Dictionary<string, object>
					{
						{ "offset", 2 },
						{
							"data",
							Convert.ToBase64String(Encoding.ASCII.GetBytes("XY"))
						}
					},
					new Dictionary<string, object>
					{
						{ "offset", 8 },
						{
							"data",
							Convert.ToBase64String(Encoding.ASCII.GetBytes("ZZ"))
						}
					}
				}
			}
		};
		spec["sha256"] = Engine.Hash(Encoding.ASCII.GetBytes("abXYefghZZ"));
		if (Encoding.ASCII.GetString(Engine.Patch(source, spec)) != "abXYefghZZ")
		{
			throw new Exception("Patch writes failed.");
		}
		spec["sha256"] = Engine.Hash(source);
		Expect<InvalidDataException>(() =>
		{
			Engine.Patch(source, spec);
		}, "Unverified patch output accepted.");
		list.Add("PASS: byte writes, file growth and output verification");
		StreamTests(list);
		ComposeTests(list);
		ModManagerTests(list);
		if (Release.HasEmbedded())
		{
			Release release = Release.Load(null);
			list.Add("PASS: embedded release signature (" + release.Version + ")");
			byte[] array2 = Release.Resource("release");
			array2[array2.Length - 1] ^= 1;
			string temp = Path.Combine(Path.GetTempPath(), "S2UB-tampered-" + Guid.NewGuid().ToString("N") + ".s2ub");
			File.WriteAllBytes(temp, array2);
			try
			{
				Expect<InvalidDataException>(() =>
				{
					Release.Load(temp);
				}, "Tampered package accepted.");
			}
			finally
			{
				File.Delete(temp);
			}
			list.Add("PASS: tampered release rejected");
			string packageTest = Path.Combine(Path.GetTempPath(), "S2UB-version-test-" + Guid.NewGuid().ToString("N") + ".s2ub");
			File.WriteAllBytes(packageTest, Release.Resource("release"));
			try
			{
				Expect<InvalidDataException>(() =>
				{
					OnlineUpdates.ValidatePackage(packageTest, new OnlineRelease
					{
						Version = "9.9.9"
					});
				}, "Mismatched signed release version accepted.");
			}
			finally
			{
				File.Delete(packageTest);
			}
			list.Add("PASS: updater rejects a signed package that differs from the advertised version");
		}
		string root = Path.Combine(Path.GetTempPath(), "S2UB-publication-test-" + Guid.NewGuid().ToString("N"));
		Directory.CreateDirectory(root);
		try
		{
			string text2 = Engine.Under(root, "UltimatePatch");
			string stage = Engine.Under(root, "UltimatePatch.staging_test");
			string previous = Engine.Under(root, "UltimatePatch.previous_test");
			Directory.CreateDirectory(text2);
			Directory.CreateDirectory(stage);
			File.WriteAllText(Engine.Under(text2, "old.txt"), "old installation");
			Directory.CreateDirectory(Engine.Under(text2, "mods"));
			File.WriteAllText(Engine.Under(text2, "mods/user.pack"), "user mod");
			File.WriteAllText(Engine.Under(root, "Launch_Shogun2_Ultimate_Patch.exe"), "old launcher");
			File.WriteAllText(Engine.Under(root, "Shogun2_UB.exe"), "old bootstrap");
			File.WriteAllText(Engine.Under(stage, "Shogun2_UB.exe"), "new bootstrap");
			Expect<FileNotFoundException>(() =>
			{
				Engine.PublishVerified(stage, root, previous);
			}, "Incomplete publication succeeded.");
			if (!File.Exists(Engine.Under(text2, "old.txt")) || File.ReadAllText(Engine.Under(root, "Shogun2_UB.exe")) != "old bootstrap" || File.ReadAllText(Engine.Under(root, "Launch_Shogun2_Ultimate_Patch.exe")) != "old launcher")
			{
				throw new Exception("Publication rollback failed.");
			}
			list.Add("PASS: failed update restores the previous folder and already-replaced bootstrap");
			if (File.ReadAllText(Engine.Under(text2, "mods/user.pack")) != "user mod")
			{
				throw new Exception("Rollback lost user mods.");
			}
			list.Add("PASS: failed publication restores the user's mods folder");
			File.WriteAllText(Engine.Under(stage, "Launch_Shogun2_Ultimate_Patch.exe"), "new launcher");
			Engine.PublishVerified(stage, root, previous);
			if (!File.Exists(Engine.Under(previous, "old.txt")) || File.ReadAllText(Engine.Under(root, "Launch_Shogun2_Ultimate_Patch.exe")) != "new launcher" || File.ReadAllText(Engine.Under(root, "Shogun2_UB.exe")) != "new bootstrap")
			{
				throw new Exception("Publication commit failed.");
			}
			list.Add("PASS: verified update publishes and keeps the previous installation");
			if (File.ReadAllText(Engine.Under(text2, "mods/user.pack")) != "user mod" || Directory.Exists(Engine.Under(previous, "mods")))
			{
				throw new Exception("Update did not preserve user mods in the live installation.");
			}
			list.Add("PASS: successful update moves user mods into the new live installation");
		}
		finally
		{
			Cleanup(root, "S2UB-publication-test-");
		}
		root = Path.Combine(Path.GetTempPath(), "S2UB-uninstall-test-" + Guid.NewGuid().ToString("N"));
		Directory.CreateDirectory(root);
		try
		{
			string root2 = Engine.Under(root, "UltimatePatch");
			string path2 = Engine.Under(root2, "install-state.json");
			Directory.CreateDirectory(Engine.Under(root2, "previous-launchers"));
			File.WriteAllText(Engine.Under(root, "shogun2.exe"), "vanilla bootstrap");
			File.WriteAllText(Engine.Under(root, "empire.retail.dll"), "vanilla engine");
			File.WriteAllText(Engine.Under(root2, "empire.retail.dll"), "patched engine");
			array = GameLayout.RootFiles;
			foreach (string text3 in array)
			{
				File.WriteAllText(Engine.Under(root2, text3), text3);
				File.WriteAllText(Engine.Under(root, text3), text3);
				File.WriteAllText(Engine.Under(root2, "previous-launchers/" + text3), "previous");
			}
			string text4 = Engine.Under(root, "UltimatePatch.previous_old");
			Directory.CreateDirectory(text4);
			File.WriteAllText(Engine.Under(text4, "install-state.json"), "{\"schema\":1,\"files\":[]}");
			string text5 = Engine.Under(root, "UltimatePatch.previous_foreign");
			Directory.CreateDirectory(text5);
			File.WriteAllText(Engine.Under(text5, "keep.txt"), "not ours");
			Dictionary<string, object> dictionary = new Dictionary<string, object>
			{
				{ "schema", 1 },
				{ "version", "0.0.1" },
				{
					"files",
					GameLayout.Destinations.Select((string x) => new Dictionary<string, object> { { "file", x } }).ToArray()
				}
			};
			Dictionary<string, object> dictionary2 = new Dictionary<string, object>(dictionary);
			dictionary2["files"] = new Dictionary<string, object>[1]
			{
				new Dictionary<string, object> { { "file", "../empire.retail.dll" } }
			};
			File.WriteAllText(path2, J.Json().Serialize(dictionary2));
			Expect<InvalidDataException>(() =>
			{
				Engine engine2 = new Engine();
				engine2.IgnoreRunningGame = true;
				engine2.Uninstall(root);
			}, "Unsafe uninstall record accepted.");
			if (!File.Exists(Engine.Under(root2, "empire.retail.dll")))
			{
				throw new Exception("Unsafe uninstall removed files.");
			}
			list.Add("PASS: uninstall rejects unexpected file paths before removing anything");
			File.WriteAllText(path2, J.Json().Serialize(dictionary));
			File.WriteAllText(Engine.Under(root, "Launch_Shogun2_Ultimate_Patch.exe"), "unrecognized replacement");
			Expect<IOException>(() =>
			{
				Engine engine2 = new Engine();
				engine2.IgnoreRunningGame = true;
				engine2.Uninstall(root);
			}, "Unrecognized launcher was removed.");
			if (!File.Exists(Engine.Under(root2, "empire.retail.dll")))
			{
				throw new Exception("Uninstall removed files before stopping.");
			}
			list.Add("PASS: uninstall keeps an unrecognized root launcher and stops before deletion");
			File.WriteAllText(Engine.Under(root, "Launch_Shogun2_Ultimate_Patch.exe"), "Launch_Shogun2_Ultimate_Patch.exe");
			File.WriteAllText(Engine.Under(root2, "keep-user-file.txt"), "user file");
			Engine engine = new Engine();
			engine.IgnoreRunningGame = true;
			engine.Uninstall(root);
			if (File.Exists(path2) || File.Exists(Engine.Under(root2, "empire.retail.dll")) || GameLayout.RootFiles.Any((string n) => File.Exists(Engine.Under(root, n))) || Directory.Exists(text4))
			{
				throw new Exception("Uninstall left managed files.");
			}
			if (File.ReadAllText(Engine.Under(root, "shogun2.exe")) != "vanilla bootstrap" || File.ReadAllText(Engine.Under(root, "empire.retail.dll")) != "vanilla engine" || !File.Exists(Engine.Under(root2, "keep-user-file.txt")) || !File.Exists(Engine.Under(text5, "keep.txt")))
			{
				throw new Exception("Uninstall removed unrelated files.");
			}
			list.Add("PASS: uninstall removes managed files and launchers; keeps vanilla files, user files and unrecognized folders");
		}
		finally
		{
			Cleanup(root, "S2UB-uninstall-test-");
		}
		if (!OnlineUpdates.NeedsUpdate("0.1.9-preview", "0.1.10-preview") || OnlineUpdates.NeedsUpdate("0.1.10-preview", "0.1.9-preview") || OnlineUpdates.NeedsUpdate("0.1.3-preview", "0.1.3-preview") || ReleaseVersion.Parse("1.0.0-preview.10").CompareTo(ReleaseVersion.Parse("1.0.0-preview.2")) <= 0 || ReleaseVersion.Parse("1.0.0").CompareTo(ReleaseVersion.Parse("1.0.0-preview")) <= 0)
		{
			throw new Exception("Release version ordering failed.");
		}
		list.Add("PASS: updater orders versions numerically and avoids same-version installs and downgrades");
		List<object> list2 = new List<object>();
		array = new string[3] { "0.1.9-preview", "0.1.10-preview", "0.1.11-preview" };
		foreach (string text6 in array)
		{
			string text7 = OnlineUpdates.PackageName(text6);
			list2.Add(new Dictionary<string, object>
			{
				{
					"tag_name",
					"v" + text6
				},
				{
					"draft",
					text6 == "0.1.11-preview"
				},
				{ "prerelease", true },
				{
					"assets",
					new Dictionary<string, object>[1]
					{
						new Dictionary<string, object>
						{
							{ "name", text7 },
							{ "state", "uploaded" },
							{ "size", 123 },
							{
								"browser_download_url",
								"https://github.com/JakeTheRipperYT/Shogun-2-2026-ultimate-engine-bug-fix-patch/releases/download/v" + text6 + "/" + text7
							}
						}
					}
				}
			});
		}
		string json = J.Json().Serialize(list2);
		OnlineRelease selected = OnlineUpdates.Select(json);
		if (selected.Version != "0.1.10-preview")
		{
			throw new Exception("Release selection failed.");
		}
		list.Add("PASS: updater selects the newest published package including prereleases and excludes drafts");
		Expect<InvalidDataException>(() =>
		{
			OnlineUpdates.Select(json.Replace("https://github.com/", "https://untrusted.invalid/"));
		}, "External update URL accepted.");
		list.Add("PASS: updater rejects download addresses outside the release repository");
		Expect<OperationCanceledException>(() =>
		{
			OnlineUpdates.Download(selected, Path.Combine(Path.GetTempPath(), "S2UB-cancelled-download"), new CancellationToken(canceled: true), null);
		}, "Download cancellation failed.");
		list.Add("PASS: cancelled download stops before making a request");
		File.WriteAllLines(path, list);
	}

	private static void Cleanup(string root, string prefix)
	{
		Engine.NoLinks(root);
		if (!Path.GetFileName(root).StartsWith(prefix, StringComparison.Ordinal))
		{
			throw new Exception("Invalid self-test cleanup target.");
		}
		Directory.Delete(root, recursive: true);
	}

	private static Dictionary<string, object> Clone(Dictionary<string, object> value)
	{
		return J.Parse(J.Json().Serialize(value));
	}

	private static Dictionary<string, object> SmallFile(string source, string destination, byte[] original, byte[] output)
	{
		Dictionary<string, object> dictionary = new Dictionary<string, object>();
		dictionary.Add("source", source);
		dictionary.Add("destination", destination);
		dictionary.Add("sourceSha256", Engine.Hash(original));
		dictionary.Add("length", output.Length);
		dictionary.Add("sha256", Engine.Hash(output));
		dictionary.Add("writes", new object[1]
		{
			new Dictionary<string, object>
			{
				{ "offset", 0 },
				{
					"data",
					Convert.ToBase64String(output)
				}
			}
		});
		return dictionary;
	}

	private static byte[] SignedSchemaFixture(RSACryptoServiceProvider rsa, int schema, string minimum, byte[] manager = null, bool wrongHash = false, bool missingManager = false)
	{
		Dictionary<string, object> dictionary = new Dictionary<string, object>
		{
			{ "schema", schema },
			{ "version", "0.1.8-traits-test" }
		};
		if (minimum != null)
		{
			dictionary["minimumInstallerVersion"] = minimum;
		}
		if (manager != null)
		{
			dictionary["modManagerSha256"] = (wrongHash ? new string('0', 64) : Engine.Hash(manager));
		}
		byte[] array;
		using (MemoryStream memoryStream = new MemoryStream())
		{
			using (ZipArchive zipArchive = new ZipArchive(memoryStream, ZipArchiveMode.Create, leaveOpen: true))
			{
				using (StreamWriter streamWriter = new StreamWriter(zipArchive.CreateEntry("manifest.json").Open()))
				{
					streamWriter.Write(J.Json().Serialize(dictionary));
				}
				using (Stream stream = zipArchive.CreateEntry("launcher.exe").Open())
				{
					stream.WriteByte(1);
				}
				if (manager != null && !missingManager)
				{
					using Stream stream2 = zipArchive.CreateEntry("mod-manager.exe").Open();
					stream2.Write(manager, 0, manager.Length);
				}
			}
			array = memoryStream.ToArray();
		}
		byte[] array2 = rsa.SignData(array, CryptoConfig.MapNameToOID("SHA256"));
		using MemoryStream memoryStream2 = new MemoryStream();
		byte[] bytes = Encoding.ASCII.GetBytes("S2UBPKG1");
		memoryStream2.Write(bytes, 0, bytes.Length);
		memoryStream2.Write(BitConverter.GetBytes(array2.Length), 0, 4);
		memoryStream2.Write(array2, 0, array2.Length);
		memoryStream2.Write(array, 0, array.Length);
		return memoryStream2.ToArray();
	}

	private static void StreamTests(List<string> results)
	{
		string text = Path.Combine(Path.GetTempPath(), "S2UB-stream-test-" + Guid.NewGuid().ToString("N"));
		Directory.CreateDirectory(text);
		try
		{
			byte[] array = new byte[2097183];
			for (int i = 0; i < array.Length; i++)
			{
				array[i] = (byte)(i * 17 + 3);
			}
			byte[] array2 = (byte[])array.Clone();
			int num = 1048574;
			byte[] array3 = new byte[4] { 160, 177, 194, 211 };
			byte[] array4 = new byte[2] { 228, 245 };
			Buffer.BlockCopy(array3, 0, array2, num, array3.Length);
			Buffer.BlockCopy(array4, 0, array2, array2.Length - array4.Length, array4.Length);
			Dictionary<string, object> spec = new Dictionary<string, object>
			{
				{ "kind", "stream-delta" },
				{ "source", "data/data.pack" },
				{ "destination", "data/data.pack" },
				{
					"length",
					(long)array.Length
				},
				{
					"sourceSha256",
					Engine.Hash(array)
				},
				{
					"sha256",
					Engine.Hash(array2)
				},
				{
					"writes",
					new object[2]
					{
						new Dictionary<string, object>
						{
							{ "offset", num },
							{
								"expect",
								Convert.ToBase64String(array.Skip(num).Take(4).ToArray())
							},
							{
								"data",
								Convert.ToBase64String(array3)
							}
						},
						new Dictionary<string, object>
						{
							{
								"offset",
								array.Length - 2
							},
							{
								"expect",
								Convert.ToBase64String(array.Skip(array.Length - 2).ToArray())
							},
							{
								"data",
								Convert.ToBase64String(array4)
							}
						}
					}
				}
			};
			string source = Path.Combine(text, "source.pack");
			string output = Path.Combine(text, "output.pack");
			File.WriteAllBytes(source, array);
			if (Engine.StreamDeltaHash(source, spec, CancellationToken.None) != Engine.Hash(array2))
			{
				throw new Exception("Streaming hash calculation failed.");
			}
			Engine.PatchStream(source, output, spec, CancellationToken.None);
			if (Engine.FileHash(output) != Engine.Hash(array2) || Engine.FileHash(source) != Engine.Hash(array))
			{
				throw new Exception("Stream reconstruction/source preservation failed.");
			}
			results.Add("PASS: bounded stream copy patches buffer-boundary/end writes, verifies hashes and preserves source");
			File.Delete(output);
			Dictionary<string, object> wrong = Clone(spec);
			J.Obj(J.Arr(wrong["writes"])[0])["offset"] = -1;
			Expect<InvalidDataException>(() =>
			{
				Engine.PatchStream(source, output, wrong, CancellationToken.None);
			}, "Negative stream range accepted.");
			wrong = Clone(spec);
			J.Obj(J.Arr(wrong["writes"])[1])["offset"] = num + 1;
			Expect<InvalidDataException>(() =>
			{
				Engine.PatchStream(source, output, wrong, CancellationToken.None);
			}, "Overlapping stream writes accepted.");
			wrong = Clone(spec);
			J.Obj(J.Arr(wrong["writes"])[0])["data"] = Convert.ToBase64String(new byte[1] { 1 });
			Expect<InvalidDataException>(() =>
			{
				Engine.PatchStream(source, output, wrong, CancellationToken.None);
			}, "Variable-size stream write accepted.");
			wrong = Clone(spec);
			wrong["length"] = array.Length + 1;
			Expect<InvalidDataException>(() =>
			{
				Engine.PatchStream(source, output, wrong, CancellationToken.None);
			}, "Stream length change accepted.");
			if (File.Exists(output))
			{
				throw new Exception("Malformed stream created an output.");
			}
			results.Add("PASS: stream rejects negative/overlapping/variable-size writes and length changes before output creation");
			wrong = Clone(spec);
			J.Obj(J.Arr(wrong["writes"])[0])["expect"] = Convert.ToBase64String(new byte[4]);
			Expect<InvalidDataException>(() =>
			{
				Engine.PatchStream(source, output, wrong, CancellationToken.None);
			}, "Mismatched original bytes accepted.");
			if (File.Exists(output))
			{
				throw new Exception("Failed stream retained partial output.");
			}
			wrong = Clone(spec);
			wrong["sourceSha256"] = new string('0', 64);
			Expect<InvalidDataException>(() =>
			{
				Engine.PatchStream(source, output, wrong, CancellationToken.None);
			}, "Wrong stream source SHA accepted.");
			wrong = Clone(spec);
			wrong["sha256"] = new string('0', 64);
			Expect<InvalidDataException>(() =>
			{
				Engine.PatchStream(source, output, wrong, CancellationToken.None);
			}, "Wrong stream output SHA accepted.");
			Expect<OperationCanceledException>(() =>
			{
				Engine.PatchStream(source, output, spec, new CancellationToken(canceled: true));
			}, "Stream cancellation ignored.");
			if (File.Exists(output) || Engine.FileHash(source) != Engine.Hash(array))
			{
				throw new Exception("Failed/cancelled stream changed source or retained output.");
			}
			File.WriteAllText(output, "foreign output");
			Expect<IOException>(() =>
			{
				Engine.PatchStream(source, output, spec, CancellationToken.None);
			}, "Existing output overwritten.");
			if (File.ReadAllText(output) != "foreign output")
			{
				throw new Exception("Unowned stream output deleted.");
			}
			Expect<InvalidDataException>(() =>
			{
				Engine.PatchStream(source, source, spec, CancellationToken.None);
			}, "Stream source could be overwritten.");
			results.Add("PASS: stream rejects old-byte/hash mismatches, cleans cancelled output and preserves pre-existing/source files");
			string game = Path.Combine(text, "game");
			Directory.CreateDirectory(Engine.Under(game, "data"));
			byte[] bytes = Encoding.ASCII.GetBytes("vanilla exe");
			byte[] bytes2 = Encoding.ASCII.GetBytes("vanilla dll");
			File.WriteAllBytes(Engine.Under(game, "shogun2.exe"), bytes);
			File.WriteAllBytes(Engine.Under(game, "empire.retail.dll"), bytes2);
			File.WriteAllBytes(Engine.Under(game, "data/data.pack"), array);
			Dictionary<string, object> dictionary = SmallFile("empire.retail.dll", "empire.retail.dll", bytes2, Encoding.ASCII.GetBytes("patched dll"));
			Dictionary<string, object> dictionary2 = SmallFile("shogun2.exe", "Shogun2_UB.exe", bytes, Encoding.ASCII.GetBytes("bootstrap"));
			Release release = new Release();
			release.PackageHash = new string('1', 64);
			release.LauncherExe = Encoding.ASCII.GetBytes("launcher");
			release.Manifest = new Dictionary<string, object>
			{
				{ "schema", 1 },
				{ "version", "0.1.7-rankidle-test" },
				{
					"files",
					new object[2] { dictionary, dictionary2 }
				}
			};
			Release release2 = release;
			release = new Release();
			release.PackageHash = new string('2', 64);
			release.LauncherExe = release2.LauncherExe;
			release.Manifest = new Dictionary<string, object>
			{
				{ "schema", 2 },
				{ "version", "0.1.8-traits-test" },
				{ "minimumInstallerVersion", "0.1.8-traits-test" },
				{
					"files",
					new object[3] { dictionary, dictionary2, spec }
				}
			};
			Release release3 = release;
			Engine installer = new Engine
			{
				IgnoreRunningGame = true
			};
			installer.Install(release2, game);
			installer.Install(release3, game);
			string root = Engine.Under(game, "UltimatePatch");
			string text2 = Engine.Under(root, "data/data.pack");
			if (Engine.FileHash(text2) != Engine.Hash(array2) || J.N(J.Parse(File.ReadAllText(Engine.Under(root, "install-state.json"))), "schema") != 2)
			{
				throw new Exception("Schema-1 to schema-2 install failed.");
			}
			results.Add("PASS: schema-1 baseline upgrades to a verified schema-2 managed data pack");
			Release badRelease = new Release
			{
				PackageHash = release3.PackageHash,
				LauncherExe = release3.LauncherExe,
				Manifest = Clone(release3.Manifest)
			};
			J.Obj(J.Arr(J.Obj(J.Arr(badRelease.Manifest["files"])[2])["writes"])[0])["expect"] = Convert.ToBase64String(new byte[4]);
			Expect<InvalidDataException>(() =>
			{
				installer.Install(badRelease, game);
			}, "Bad stream update published.");
			if (Engine.FileHash(text2) != Engine.Hash(array2) || Engine.InstalledVersion(game) != release3.Version || Directory.GetDirectories(game, "UltimatePatch.staging_*").Length != 0)
			{
				throw new Exception("Failed stream update changed the live installation.");
			}
			string stage = Engine.Under(game, "UltimatePatch.staging_stream-rollback");
			string previous = Engine.Under(game, "UltimatePatch.previous_stream-rollback");
			Directory.CreateDirectory(Engine.Under(stage, "data"));
			File.WriteAllText(Engine.Under(stage, "Shogun2_UB.exe"), "incomplete bootstrap");
			File.WriteAllText(Engine.Under(stage, "data/data.pack"), "incomplete pack");
			Expect<FileNotFoundException>(() =>
			{
				Engine.PublishVerified(stage, game, previous);
			}, "Incomplete stream publication succeeded.");
			if (Engine.FileHash(text2) != Engine.Hash(array2) || File.ReadAllBytes(Engine.Under(game, "Shogun2_UB.exe")).Length != Encoding.ASCII.GetBytes("bootstrap").Length)
			{
				throw new Exception("Publication rollback did not restore the managed pack/bootstrap.");
			}
			results.Add("PASS: failed stream build/publication preserves the previous pack and restores root launchers");
			File.WriteAllText(text2, "unrecognized replacement");
			Expect<IOException>(() =>
			{
				installer.Uninstall(game);
			}, "Modified managed data pack deleted.");
			if (!File.Exists(Engine.Under(game, "Launch_Shogun2_Ultimate_Patch.exe")))
			{
				throw new Exception("Ownership rejection removed root files.");
			}
			File.WriteAllBytes(text2, array2);
			installer.Uninstall(game);
			if (File.Exists(text2) || File.Exists(Engine.Under(root, "install-state.json")) || Engine.FileHash(Engine.Under(game, "data/data.pack")) != Engine.Hash(array))
			{
				throw new Exception("Schema-2 uninstall/source preservation failed.");
			}
			results.Add("PASS: schema-2 uninstall checks ownership and removes only managed data, keeping vanilla pack");
			RSACryptoServiceProvider rsa = new RSACryptoServiceProvider(2048);
			try
			{
				string key = rsa.ToXmlString(includePrivateParameters: false);
				Release.Parse(SignedSchemaFixture(rsa, 1, "0.1.0-preview"), key);
				Expect<InvalidDataException>(() =>
				{
					Release.Parse(SignedSchemaFixture(rsa, 4, "0.1.8-traits-test"), key);
				}, "Unknown release schema accepted.");
				Expect<InvalidDataException>(() =>
				{
					Release.Parse(SignedSchemaFixture(rsa, 2, null), key);
				}, "Schema-2 compatibility guard omitted.");
				Expect<InvalidDataException>(() =>
				{
					Release.Parse(SignedSchemaFixture(rsa, 2, "0.1.0-preview"), key);
				}, "Schema-2 old installer guard accepted.");
				if (ReleaseVersion.Parse("0.1.45-graphics-unlock").CompareTo(ReleaseVersion.Parse("0.1.8-traits-test")) >= 0)
				{
					Release.Parse(SignedSchemaFixture(rsa, 2, "0.1.8-traits-test"), key);
				}
				else
				{
					Expect<InvalidDataException>(() =>
					{
						Release.Parse(SignedSchemaFixture(rsa, 2, "0.1.8-traits-test"), key);
					}, "Old installer accepted streaming package.");
				}
				results.Add("PASS: signed schema compatibility accepts legacy releases and enforces schema-2 installer minimum");
			}
			finally
			{
				if (rsa != null)
				{
					((IDisposable)rsa).Dispose();
				}
			}
		}
		finally
		{
			Cleanup(text, "S2UB-stream-test-");
		}
	}

	private static void ModManagerTests(List<string> results)
	{
		byte[] payload = Encoding.ASCII.GetBytes("manager fixture");
		RSACryptoServiceProvider rsa = new RSACryptoServiceProvider(2048);
		try
		{
			string key = rsa.ToXmlString(includePrivateParameters: false);
			Release release = Release.Parse(SignedSchemaFixture(rsa, 3, "0.1.44-unified-launcher", payload), key);
			if (!release.ModManagerExe.SequenceEqual(payload) || release.PackageBytes == null || Engine.Hash(release.PackageBytes) != release.PackageHash)
			{
				throw new Exception("Manager or original package bytes not preserved.");
			}
			Expect<InvalidDataException>(() =>
			{
				Release.Parse(SignedSchemaFixture(rsa, 3, "0.1.44-unified-launcher", payload, wrongHash: true), key);
			}, "Manager hash mismatch accepted.");
			Expect<InvalidDataException>(() =>
			{
				Release.Parse(SignedSchemaFixture(rsa, 3, "0.1.44-unified-launcher", payload, wrongHash: false, missingManager: true), key);
			}, "Missing manager payload accepted.");
			Expect<InvalidDataException>(() =>
			{
				Release.Parse(SignedSchemaFixture(rsa, 3, "0.1.11-collection-test", payload), key);
			}, "Manager old installer minimum accepted.");
			Expect<InvalidDataException>(() =>
			{
				Release.Parse(SignedSchemaFixture(rsa, 1, "0.1.44-unified-launcher", payload), key);
			}, "Manager old schema accepted.");
		}
		finally
		{
			if (rsa != null)
			{
				((IDisposable)rsa).Dispose();
			}
		}
		results.Add("PASS: signed manager payload verifies hash, presence, schema and minimum installer");
		string root = Path.Combine(Path.GetTempPath(), "S2UB-manager-test-" + Guid.NewGuid().ToString("N"));
		Directory.CreateDirectory(root);
		try
		{
			byte[] bytes = Encoding.ASCII.GetBytes("vanilla");
			byte[] bytes2 = Encoding.ASCII.GetBytes("patched");
			File.WriteAllBytes(Engine.Under(root, "shogun2.exe"), bytes);
			File.WriteAllBytes(Engine.Under(root, "empire.retail.dll"), bytes);
			Release release2 = new Release
			{
				PackageHash = new string('4', 64),
				LauncherExe = bytes2,
				ModManagerExe = payload,
				Manifest = new Dictionary<string, object>
				{
					{ "schema", 3 },
					{ "version", "0.1.44-unified-launcher" },
					{ "minimumInstallerVersion", "0.1.44-unified-launcher" },
					{
						"modManagerSha256",
						Engine.Hash(payload)
					},
					{
						"files",
						new object[2]
						{
							SmallFile("empire.retail.dll", "empire.retail.dll", bytes, bytes2),
							SmallFile("shogun2.exe", "Shogun2_UB.exe", bytes, bytes2)
						}
					}
				}
			};
			release2.PackageBytes = Encoding.ASCII.GetBytes("offline signed-package ownership fixture");
			release2.PackageHash = Engine.Hash(release2.PackageBytes);
			Engine installer = new Engine
			{
				IgnoreRunningGame = true
			};
			installer.Install(release2, root);
			string root2 = Engine.Under(root, "UltimatePatch");
			string path = Engine.Under(root2, "UltimatePatch_Launcher.exe");
			string path2 = Engine.Under(root2, "mods/player.pack");
			File.WriteAllText(path2, "user mod");
			Dictionary<string, object> dictionary = J.Parse(File.ReadAllText(Engine.Under(root2, "install-state.json")));
			if (!J.Arr(dictionary["files"]).Select(J.Obj).Any((Dictionary<string, object> f) => J.S(f, "file") == "UltimatePatch_Launcher.exe" && J.S(f, "sha256") == Engine.Hash(payload)))
			{
				throw new Exception("Manager ownership omitted.");
			}
			string path3 = Engine.Under(root2, "release.s2ub");
			if (!File.ReadAllBytes(path3).SequenceEqual(release2.PackageBytes) || !J.Arr(dictionary["files"]).Select(J.Obj).Any((Dictionary<string, object> f) => J.S(f, "file") == "release.s2ub" && J.S(f, "sha256") == release2.PackageHash))
			{
				throw new Exception("Offline package ownership omitted.");
			}
			results.Add("PASS: original verified package is installed byte-exactly and recorded for offline reinstall");
			installer.Install(release2, root);
			if (File.ReadAllText(path2) != "user mod")
			{
				throw new Exception("Update removed user mod.");
			}
			File.WriteAllText(path, "foreign manager");
			Expect<IOException>(() =>
			{
				installer.Uninstall(root);
			}, "Modified manager removed.");
			File.WriteAllBytes(path, payload);
			File.WriteAllText(path3, "foreign offline release");
			Expect<IOException>(() =>
			{
				installer.Uninstall(root);
			}, "Modified offline package removed.");
			File.WriteAllBytes(path3, release2.PackageBytes);
			installer.Uninstall(root);
			if (File.Exists(path3))
			{
				throw new Exception("Owned offline package retained.");
			}
			results.Add("PASS: uninstall protects edited offline package and removes only its verified owned copy");
			if (File.Exists(path) || File.ReadAllText(path2) != "user mod" || !File.Exists(Engine.Under(root, "empire.retail.dll")))
			{
				throw new Exception("Manager uninstall ownership failed.");
			}
			results.Add("PASS: manager installed and recorded; updates preserve user mods; uninstall protects modified manager and retains mods/vanilla");
		}
		finally
		{
			Cleanup(root, "S2UB-manager-test-");
		}
	}

	private static void ComposeTests(List<string> results)
	{
		string text = Path.Combine(Path.GetTempPath(), "S2UB-compose-test-" + Guid.NewGuid().ToString("N"));
		Directory.CreateDirectory(text);
		try
		{
			byte[] array = new byte[2097183];
			for (int i = 0; i < array.Length; i++)
			{
				array[i] = (byte)(i * 13 + 7);
			}
			byte[] bytes = Encoding.ASCII.GetBytes("new archive index and a resized table");
			byte[] array2 = array.Skip(1048575).Take(1048593).Concat(bytes)
				.Concat(array.Take(53))
				.ToArray();
			Dictionary<string, object> spec = new Dictionary<string, object>
			{
				{ "kind", "stream-compose" },
				{ "source", "data/data.pack" },
				{ "destination", "data/data.pack" },
				{
					"length",
					(long)array2.Length
				},
				{
					"sourceSha256",
					Engine.Hash(array)
				},
				{
					"sha256",
					Engine.Hash(array2)
				},
				{
					"segments",
					new object[3]
					{
						new Dictionary<string, object>
						{
							{ "offset", 1048575 },
							{ "length", 1048593 }
						},
						new Dictionary<string, object> { 
						{
							"data",
							Convert.ToBase64String(bytes)
						} },
						new Dictionary<string, object>
						{
							{ "offset", 0 },
							{ "length", 53 }
						}
					}
				}
			};
			string source = Path.Combine(text, "source.pack");
			string output = Path.Combine(text, "output.pack");
			File.WriteAllBytes(source, array);
			if (Engine.StreamComposeHash(source, spec, CancellationToken.None) != Engine.Hash(array2))
			{
				throw new Exception("Composition hash failed.");
			}
			Engine.PatchCompose(source, output, spec, CancellationToken.None);
			if (Engine.FileHash(output) != Engine.Hash(array2) || Engine.FileHash(source) != Engine.Hash(array))
			{
				throw new Exception("Composition reconstruction changed source or output.");
			}
			results.Add("PASS: variable-length pack composition copies reordered ranges across buffers, inserts literals and preserves source");
			File.Delete(output);
			string[] array3 = new string[11]
			{
				"negative", "outside", "zero", "shape", "empty", "sum", "source", "output", "fraction", "large",
				"segments"
			};
			foreach (string text2 in array3)
			{
				Dictionary<string, object> wrong = Clone(spec);
				Dictionary<string, object> dictionary = J.Obj(J.Arr(wrong["segments"])[0]);
				if (text2 == "negative")
				{
					dictionary["offset"] = -1;
				}
				if (text2 == "outside")
				{
					dictionary["offset"] = array.Length;
				}
				if (text2 == "zero")
				{
					dictionary["length"] = 0;
				}
				if (text2 == "shape")
				{
					dictionary["data"] = "AQ==";
				}
				if (text2 == "empty")
				{
					J.Obj(J.Arr(wrong["segments"])[1])["data"] = "";
				}
				if (text2 == "sum")
				{
					wrong["length"] = array2.Length + 1;
				}
				if (text2 == "source")
				{
					wrong["sourceSha256"] = new string('0', 64);
				}
				if (text2 == "output")
				{
					wrong["sha256"] = new string('0', 64);
				}
				if (text2 == "fraction")
				{
					dictionary["offset"] = 0.5;
				}
				if (text2 == "large")
				{
					wrong["length"] = 8589934593L;
				}
				if (text2 == "segments")
				{
					wrong["segments"] = Enumerable.Repeat((object)dictionary, 200001).ToArray();
				}
				Expect<InvalidDataException>(() =>
				{
					Engine.PatchCompose(source, output, wrong, CancellationToken.None);
				}, "Malformed composition accepted: " + text2);
				if (File.Exists(output))
				{
					throw new Exception("Failed composition kept output: " + text2);
				}
			}
			Expect<OperationCanceledException>(() =>
			{
				Engine.PatchCompose(source, output, spec, new CancellationToken(canceled: true));
			}, "Composition cancellation ignored.");
			File.WriteAllText(output, "foreign output");
			Expect<IOException>(() =>
			{
				Engine.PatchCompose(source, output, spec, CancellationToken.None);
			}, "Existing composition output overwritten.");
			if (File.ReadAllText(output) != "foreign output")
			{
				throw new Exception("Foreign composition output was deleted.");
			}
			Expect<InvalidDataException>(() =>
			{
				Engine.PatchCompose(source, source, spec, CancellationToken.None);
			}, "Composition source overwritten.");
			results.Add("PASS: composition rejects malformed ranges/shapes/lengths/hashes, cleans failed output and protects existing files");
			string game = Path.Combine(text, "game");
			Directory.CreateDirectory(Engine.Under(game, "data"));
			byte[] bytes2 = Encoding.ASCII.GetBytes("vanilla exe");
			byte[] bytes3 = Encoding.ASCII.GetBytes("vanilla dll");
			File.WriteAllBytes(Engine.Under(game, "shogun2.exe"), bytes2);
			File.WriteAllBytes(Engine.Under(game, "empire.retail.dll"), bytes3);
			array3 = GameLayout.PrivatePacks;
			foreach (string relative in array3)
			{
				File.WriteAllBytes(Engine.Under(game, relative), array);
			}
			Dictionary<string, object> dictionary2 = SmallFile("empire.retail.dll", "empire.retail.dll", bytes3, Encoding.ASCII.GetBytes("patched dll"));
			Dictionary<string, object> dictionary3 = SmallFile("shogun2.exe", "Shogun2_UB.exe", bytes2, Encoding.ASCII.GetBytes("bootstrap"));
			List<object> list = new List<object> { dictionary2, dictionary3 };
			array3 = GameLayout.PrivatePacks;
			foreach (string value in array3)
			{
				Dictionary<string, object> dictionary4 = Clone(spec);
				dictionary4["source"] = value;
				dictionary4["destination"] = value;
				list.Add(dictionary4);
			}
			Release release = new Release();
			release.PackageHash = new string('1', 64);
			release.LauncherExe = Encoding.ASCII.GetBytes("launcher");
			release.Manifest = new Dictionary<string, object>
			{
				{ "schema", 2 },
				{ "version", "0.1.10-fear-values-test" },
				{
					"files",
					new object[2] { dictionary2, dictionary3 }
				}
			};
			Release release2 = release;
			Release release3 = new Release
			{
				PackageHash = new string('2', 64),
				LauncherExe = release2.LauncherExe,
				Manifest = new Dictionary<string, object>
				{
					{ "schema", 3 },
					{ "version", "0.1.11-collection-test" },
					{ "minimumInstallerVersion", "0.1.11-collection-test" },
					{
						"files",
						list.ToArray()
					}
				}
			};
			Engine installer = new Engine
			{
				IgnoreRunningGame = true
			};
			installer.Install(release2, game);
			installer.Install(release3, game);
			string root = Engine.Under(game, "UltimatePatch");
			byte[] bytes4 = Encoding.ASCII.GetBytes("independent renderer payload");
			Dictionary<string, object> item = SmallFile("empire.retail.dll", "og11.dll", bytes3, bytes4);
			list.Add(item);
			release3.Manifest["files"] = list.ToArray();
			release3.Manifest["minimumInstallerVersion"] = "0.1.20-atmosphere-test";
			Release invalidRenderer = new Release
			{
				PackageHash = release3.PackageHash,
				LauncherExe = release3.LauncherExe,
				Manifest = Clone(release3.Manifest)
			};
			invalidRenderer.Manifest["minimumInstallerVersion"] = "0.1.11-collection-test";
			Expect<InvalidDataException>(() =>
			{
				installer.Install(invalidRenderer, game);
			}, "Renderer accepted without compatible installer guard.");
			invalidRenderer.Manifest["minimumInstallerVersion"] = "0.1.20-atmosphere-test";
			J.Obj(J.Arr(invalidRenderer.Manifest["files"])[5])["source"] = "shogun2.exe";
			Expect<InvalidDataException>(() =>
			{
				installer.Install(invalidRenderer, game);
			}, "Renderer accepted with unsupported source.");
			installer.Install(release3, game);
			string text3 = Engine.Under(root, "og11.dll");
			if (Engine.FileHash(text3) != Engine.Hash(bytes4) || File.Exists(Engine.Under(game, "og11.dll")))
			{
				throw new Exception("Renderer was not reconstructed exclusively in managed folder.");
			}
			File.WriteAllText(text3, "foreign renderer");
			Expect<IOException>(() =>
			{
				installer.Uninstall(game);
			}, "Modified renderer was removed.");
			File.WriteAllBytes(text3, bytes4);
			results.Add("PASS: private renderer reconstructs in managed folder, enforces source/version guards and protects modified payload on uninstall");
			array3 = GameLayout.PrivatePacks;
			foreach (string relative2 in array3)
			{
				if (Engine.FileHash(Engine.Under(root, relative2)) != Engine.Hash(array2))
				{
					throw new Exception("Composed pack upgrade failed.");
				}
			}
			Release bad = new Release
			{
				PackageHash = release3.PackageHash,
				LauncherExe = release3.LauncherExe,
				Manifest = Clone(release3.Manifest)
			};
			J.Obj(J.Arr(bad.Manifest["files"])[3])["sha256"] = new string('0', 64);
			Expect<InvalidDataException>(() =>
			{
				installer.Install(bad, game);
			}, "Bad composed update published.");
			if (Engine.InstalledVersion(game) != release3.Version || Directory.GetDirectories(game, "UltimatePatch.staging_*").Length != 0)
			{
				throw new Exception("Failed composed update changed live state or retained stage.");
			}
			array3 = GameLayout.PrivatePacks;
			foreach (string relative3 in array3)
			{
				if (Engine.FileHash(Engine.Under(root, relative3)) != Engine.Hash(array2))
				{
					throw new Exception("Failed composed update changed installed pack.");
				}
			}
			results.Add("PASS: schema-2 installation upgrades to three schema-3 packs and a failed composition preserves the previous build");
			string path = Engine.Under(root, "data/models.pack");
			File.WriteAllText(path, "foreign pack");
			Expect<IOException>(() =>
			{
				installer.Uninstall(game);
			}, "Uninstall removed modified composed pack.");
			if (!File.Exists(Engine.Under(game, "Launch_Shogun2_Ultimate_Patch.exe")))
			{
				throw new Exception("Ownership rejection removed root launcher.");
			}
			File.WriteAllBytes(path, array2);
			installer.Uninstall(game);
			if (File.Exists(text3))
			{
				throw new Exception("Uninstall retained owned renderer.");
			}
			array3 = GameLayout.PrivatePacks;
			foreach (string relative4 in array3)
			{
				if (File.Exists(Engine.Under(root, relative4)) || Engine.FileHash(Engine.Under(game, relative4)) != Engine.Hash(array))
				{
					throw new Exception("Composed uninstall modified vanilla or retained managed pack.");
				}
			}
			results.Add("PASS: schema-3 uninstall checks all pack ownership and removes managed packs while retaining originals");
			RSACryptoServiceProvider rsa = new RSACryptoServiceProvider(2048);
			try
			{
				string key = rsa.ToXmlString(includePrivateParameters: false);
				Expect<InvalidDataException>(() =>
				{
					Release.Parse(SignedSchemaFixture(rsa, 3, null), key);
				}, "Schema-3 omitted minimum accepted.");
				Expect<InvalidDataException>(() =>
				{
					Release.Parse(SignedSchemaFixture(rsa, 3, "0.1.8-traits-test"), key);
				}, "Schema-3 old installer minimum accepted.");
				if (ReleaseVersion.Parse("0.1.45-graphics-unlock").CompareTo(ReleaseVersion.Parse("0.1.11-collection-test")) >= 0)
				{
					Release.Parse(SignedSchemaFixture(rsa, 3, "0.1.11-collection-test"), key);
				}
				else
				{
					Expect<InvalidDataException>(() =>
					{
						Release.Parse(SignedSchemaFixture(rsa, 3, "0.1.11-collection-test"), key);
					}, "Old installer accepted composition package.");
				}
			}
			finally
			{
				if (rsa != null)
				{
					((IDisposable)rsa).Dispose();
				}
			}
			results.Add("PASS: signed schema-3 releases require the composition installer version");
		}
		finally
		{
			Cleanup(text, "S2UB-compose-test-");
		}
	}
}
