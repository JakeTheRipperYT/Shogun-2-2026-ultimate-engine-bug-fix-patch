using System;
using System.Collections.Generic;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;

namespace S2UltimatePatch;

public sealed class Release
{
	public Dictionary<string, object> Manifest;

	public byte[] LauncherExe;

	public byte[] ModManagerExe;

	public byte[] PackageBytes;

	public string PackageHash;

	public string Version => J.S(Manifest, "version");

	public static byte[] Resource(string name)
	{
		using Stream stream = Assembly.GetExecutingAssembly().GetManifestResourceStream(name);
		if (stream == null)
		{
			throw new InvalidDataException("Missing application resource: " + name);
		}
		using MemoryStream memoryStream = new MemoryStream();
		stream.CopyTo(memoryStream);
		return memoryStream.ToArray();
	}

	public static bool HasEmbedded()
	{
		return Assembly.GetExecutingAssembly().GetManifestResourceNames().Contains("release");
	}

	public static Release Load(string path)
	{
		return Parse(string.IsNullOrEmpty(path) ? Resource("release") : File.ReadAllBytes(path), Encoding.UTF8.GetString(Resource("publicKey")));
	}

	public static Release Parse(byte[] bytes, string publicKeyXml)
	{
		if (bytes.Length > 134217728 || bytes.Length < 16 || Encoding.ASCII.GetString(bytes, 0, 8) != "S2UBPKG1")
		{
			throw new InvalidDataException("This is not a supported Shogun 2 Ultimate Bug Fix Patch package.");
		}
		int num = BitConverter.ToInt32(bytes, 8);
		if (num < 256 || num > 1024 || bytes.Length <= 12 + num)
		{
			throw new InvalidDataException("Invalid package signature length.");
		}
		byte[] array = new byte[num];
		byte[] array2 = new byte[bytes.Length - 12 - num];
		Buffer.BlockCopy(bytes, 12, array, 0, num);
		Buffer.BlockCopy(bytes, 12 + num, array2, 0, array2.Length);
		using (RSACryptoServiceProvider rSACryptoServiceProvider = new RSACryptoServiceProvider())
		{
			rSACryptoServiceProvider.FromXmlString(publicKeyXml);
			if (!rSACryptoServiceProvider.VerifyData(array2, CryptoConfig.MapNameToOID("SHA256"), array))
			{
				throw new InvalidDataException("The package signature is invalid. Nothing was installed.");
			}
		}
		Release release = new Release
		{
			PackageHash = Engine.Hash(bytes),
			PackageBytes = (byte[])bytes.Clone()
		};
		using (ZipArchive zip = new ZipArchive(new MemoryStream(array2), ZipArchiveMode.Read))
		{
			release.Manifest = J.Parse(Encoding.UTF8.GetString(ReadEntry(zip, "manifest.json", 100663296)));
			release.LauncherExe = ReadEntry(zip, "launcher.exe", 1048576);
			if (release.Manifest.ContainsKey("modManagerSha256"))
			{
				if (J.N(release.Manifest, "schema") != 3)
				{
					throw new InvalidDataException("Mod manager requires schema 3.");
				}
				release.ModManagerExe = ReadEntry(zip, "mod-manager.exe", 2097152);
				if (Engine.Hash(release.ModManagerExe) != J.S(release.Manifest, "modManagerSha256") || !release.Manifest.ContainsKey("minimumInstallerVersion") || ReleaseVersion.Parse(J.S(release.Manifest, "minimumInstallerVersion")).CompareTo(ReleaseVersion.Parse("0.1.44-unified-launcher")) < 0)
				{
					throw new InvalidDataException("Invalid mod-manager payload or installer compatibility requirement.");
				}
			}
		}
		long num2 = J.N(release.Manifest, "schema");
		if (num2 != 1 && num2 != 2 && num2 != 3)
		{
			throw new InvalidDataException("This release needs a newer installer. Download the latest installer ZIP from GitHub.");
		}
		if (num2 == 2 && (!release.Manifest.ContainsKey("minimumInstallerVersion") || ReleaseVersion.Parse(J.S(release.Manifest, "minimumInstallerVersion")).CompareTo(ReleaseVersion.Parse("0.1.8-traits-test")) < 0))
		{
			throw new InvalidDataException("Schema-2 releases must specify the streaming installer compatibility requirement.");
		}
		if (num2 == 3 && (!release.Manifest.ContainsKey("minimumInstallerVersion") || ReleaseVersion.Parse(J.S(release.Manifest, "minimumInstallerVersion")).CompareTo(ReleaseVersion.Parse("0.1.11-collection-test")) < 0))
		{
			throw new InvalidDataException("Schema-3 releases must specify the pack composition installer compatibility requirement.");
		}
		if (release.Manifest.ContainsKey("minimumInstallerVersion") && ReleaseVersion.Parse("0.1.46-gameplay-fixes").CompareTo(ReleaseVersion.Parse(J.S(release.Manifest, "minimumInstallerVersion"))) < 0)
		{
			throw new InvalidDataException("This release needs a newer installer. Download the latest installer ZIP from GitHub.");
		}
		return release;
	}

	private static byte[] ReadEntry(ZipArchive zip, string name, int limit)
	{
		ZipArchiveEntry entry = zip.GetEntry(name);
		if (entry == null || entry.Length > limit)
		{
			throw new InvalidDataException("Invalid package component: " + name);
		}
		using Stream stream = entry.Open();
		using MemoryStream memoryStream = new MemoryStream();
		stream.CopyTo(memoryStream);
		return memoryStream.ToArray();
	}
}
