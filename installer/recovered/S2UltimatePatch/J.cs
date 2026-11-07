using System;
using System.Collections;
using System.Collections.Generic;
using System.Web.Script.Serialization;

namespace S2UltimatePatch;

public static class J
{
	public static Dictionary<string, object> Obj(object x)
	{
		return (Dictionary<string, object>)x;
	}

	public static object[] Arr(object x)
	{
		if (!(x is object[] result))
		{
			return ((ArrayList)x).ToArray();
		}
		return result;
	}

	public static string S(Dictionary<string, object> d, string k)
	{
		return Convert.ToString(d[k]);
	}

	public static long N(Dictionary<string, object> d, string k)
	{
		return Convert.ToInt64(d[k]);
	}

	public static byte[] B(Dictionary<string, object> d, string k)
	{
		return Convert.FromBase64String(S(d, k));
	}

	public static JavaScriptSerializer Json()
	{
		return new JavaScriptSerializer
		{
			MaxJsonLength = 67108864,
			RecursionLimit = 100
		};
	}

	public static Dictionary<string, object> Parse(string s)
	{
		return Obj(Json().DeserializeObject(s));
	}
}
