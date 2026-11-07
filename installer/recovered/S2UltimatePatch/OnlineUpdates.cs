using System;
using System.Collections.Generic;
using System.IO;
using System.Net;
using System.Net.Http;
using System.Text;
using System.Threading;

namespace S2UltimatePatch;

public static class OnlineUpdates
{
	public const string AppVersion = "0.1.46-gameplay-fixes";

	public const string Repository = "JakeTheRipperYT/Shogun-2-2026-ultimate-engine-bug-fix-patch";

	public const string ApiUrl = "https://api.github.com/repos/JakeTheRipperYT/Shogun-2-2026-ultimate-engine-bug-fix-patch/releases?per_page=100";

	public const string DownloadPrefix = "https://github.com/JakeTheRipperYT/Shogun-2-2026-ultimate-engine-bug-fix-patch/releases/download/";

	public const string PackagePrefix = "Shogun2UltimatePatch-";

	public const string PackageExtension = ".s2ub";

	private const int MaxPackage = 134217728;

	public static string PackageName(string version)
	{
		return "Shogun2UltimatePatch-" + version + ".s2ub";
	}

	public static OnlineRelease Select(string json)
	{
		OnlineRelease onlineRelease = null;
		object[] array = J.Arr(J.Json().DeserializeObject(json));
		for (int i = 0; i < array.Length; i++)
		{
			Dictionary<string, object> dictionary = J.Obj(array[i]);
			if (Convert.ToBoolean(dictionary["draft"]))
			{
				continue;
			}
			string text = J.S(dictionary, "tag_name");
			if (!text.StartsWith("v", StringComparison.Ordinal))
			{
				continue;
			}
			ReleaseVersion releaseVersion;
			try
			{
				releaseVersion = ReleaseVersion.Parse(text);
			}
			catch (InvalidDataException)
			{
				continue;
			}
			string version = text.Substring(1);
			string text2 = PackageName(version);
			object[] array2 = J.Arr(dictionary["assets"]);
			for (int j = 0; j < array2.Length; j++)
			{
				Dictionary<string, object> d = J.Obj(array2[j]);
				if (!(J.S(d, "name") != text2) && !(J.S(d, "state") != "uploaded"))
				{
					long num = J.N(d, "size");
					string text3 = J.S(d, "browser_download_url");
					if (num > 0 && num <= 134217728 && !(text3 != "https://github.com/JakeTheRipperYT/Shogun-2-2026-ultimate-engine-bug-fix-patch/releases/download/" + Uri.EscapeDataString(text) + "/" + Uri.EscapeDataString(text2)) && (onlineRelease == null || releaseVersion.CompareTo(ReleaseVersion.Parse(onlineRelease.Version)) > 0))
					{
						onlineRelease = new OnlineRelease
						{
							Version = version,
							DownloadUrl = text3,
							Size = num
						};
					}
				}
			}
		}
		if (onlineRelease == null)
		{
			throw new InvalidDataException("No Shogun 2 Ultimate Bug Fix Patch release package is published on GitHub yet.");
		}
		return onlineRelease;
	}

	private static byte[] Get(string url, int limit, CancellationToken cancel, Action<long, long> progress)
	{
		cancel.ThrowIfCancellationRequested();
		ServicePointManager.SecurityProtocol |= SecurityProtocolType.Tls12;
		using CancellationTokenSource cancellationTokenSource = CancellationTokenSource.CreateLinkedTokenSource(cancel);
		using HttpClient httpClient = new HttpClient();
		cancellationTokenSource.CancelAfter(TimeSpan.FromMinutes(3.0));
		CancellationToken token = cancellationTokenSource.Token;
		httpClient.DefaultRequestHeaders.UserAgent.ParseAdd("Shogun2UltimatePatch/0.1.46-gameplay-fixes");
		httpClient.DefaultRequestHeaders.Accept.ParseAdd("application/vnd.github+json");
		try
		{
			using HttpResponseMessage httpResponseMessage = httpClient.GetAsync(url, HttpCompletionOption.ResponseHeadersRead, token).GetAwaiter().GetResult();
			if (httpResponseMessage.StatusCode == HttpStatusCode.Forbidden || httpResponseMessage.StatusCode == (HttpStatusCode)429)
			{
				throw new IOException("GitHub is temporarily limiting update checks. Try again later or choose a downloaded package.");
			}
			httpResponseMessage.EnsureSuccessStatusCode();
			long valueOrDefault = httpResponseMessage.Content.Headers.ContentLength.GetValueOrDefault();
			if (valueOrDefault > limit)
			{
				throw new InvalidDataException("Update response exceeds the allowed download size.");
			}
			using Stream stream = httpResponseMessage.Content.ReadAsStreamAsync().GetAwaiter().GetResult();
			using MemoryStream memoryStream = new MemoryStream();
			byte[] array = new byte[65536];
			int result;
			while ((result = stream.ReadAsync(array, 0, array.Length, token).GetAwaiter().GetResult()) > 0)
			{
				if (memoryStream.Length > limit - result)
				{
					throw new InvalidDataException("Update download exceeds the allowed size.");
				}
				memoryStream.Write(array, 0, result);
				progress?.Invoke(memoryStream.Length, valueOrDefault);
			}
			token.ThrowIfCancellationRequested();
			if (valueOrDefault > 0 && memoryStream.Length != valueOrDefault)
			{
				throw new InvalidDataException("The update download was incomplete.");
			}
			return memoryStream.ToArray();
		}
		catch (OperationCanceledException)
		{
			cancel.ThrowIfCancellationRequested();
			throw new IOException("GitHub timed out. Try again or choose a downloaded package.");
		}
		catch (HttpRequestException innerException)
		{
			throw new IOException("Could not reach GitHub. Check the connection, retry, or choose a downloaded package.", innerException);
		}
	}

	public static OnlineRelease Latest(CancellationToken cancel)
	{
		return Select(Encoding.UTF8.GetString(Get("https://api.github.com/repos/JakeTheRipperYT/Shogun-2-2026-ultimate-engine-bug-fix-patch/releases?per_page=100", 8388608, cancel, null)));
	}

	public static void ValidatePackage(string path, OnlineRelease expected)
	{
		if (Release.Load(path).Version != expected.Version)
		{
			throw new InvalidDataException("The signed package version does not match the GitHub release. Nothing was installed.");
		}
	}

	public static string Download(OnlineRelease release, string folder, CancellationToken cancel, Action<long, long> progress)
	{
		string stringToEscape = PackageName(release.Version);
		string text = "https://github.com/JakeTheRipperYT/Shogun-2-2026-ultimate-engine-bug-fix-patch/releases/download/" + Uri.EscapeDataString("v" + release.Version) + "/" + Uri.EscapeDataString(stringToEscape);
		if (release.DownloadUrl != text || release.Size <= 0 || release.Size > 134217728)
		{
			throw new InvalidDataException("Unexpected update download address or size.");
		}
		byte[] array = Get(release.DownloadUrl, 134217728, cancel, progress);
		if (array.LongLength != release.Size)
		{
			throw new InvalidDataException("The downloaded package size does not match the published release.");
		}
		Engine.NoLinks(folder);
		Directory.CreateDirectory(folder);
		string text2 = Engine.Under(folder, "download-" + Guid.NewGuid().ToString("N") + ".part");
		try
		{
			File.WriteAllBytes(text2, array);
			cancel.ThrowIfCancellationRequested();
			ValidatePackage(text2, release);
			string text3 = Engine.Under(folder, "Shogun2UltimatePatch-" + release.Version + "-" + Engine.Hash(array).Substring(0, 16) + ".s2ub");
			if (File.Exists(text3))
			{
				File.Delete(text3);
			}
			File.Move(text2, text3);
			return text3;
		}
		finally
		{
			if (File.Exists(text2))
			{
				File.Delete(text2);
			}
		}
	}

	public static bool NeedsUpdate(string installed, string available)
	{
		return ReleaseVersion.Parse(installed).CompareTo(ReleaseVersion.Parse(available)) < 0;
	}
}
