<# Builds the accepted OG binary recipes and the signed installer/launcher only.
   No engine compilation, collection-project inputs or automatic installation.
   All generated files and temporary files stay under this project on F:.
#>
param(
    [string]$Version = '0.1.46-gameplay-fixes',
    [string]$GameDir = 'C:\Program Files (x86)\Steam\steamapps\common\Total War SHOGUN 2',
    [string]$Python = 'C:\Users\CT-MK2\AppData\Local\Programs\Python\Python313\python.exe',
    [string]$Baseline,
    [switch]$Keygen,
    [switch]$CompareInstalled
)
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$build = Join-Path $root 'build\release-current'
$dist = Join-Path $root 'dist'
$env:TEMP = Join-Path $root 'build\test-temp'
$env:TMP = $env:TEMP
$env:PYTHONDONTWRITEBYTECODE = '1'
New-Item -ItemType Directory -Force $build,$dist,$env:TEMP | Out-Null
$utf8 = [Text.UTF8Encoding]::new($false)
function Run($file, [string[]]$arguments) {
    & $file @arguments
    if ($LASTEXITCODE -ne 0) { throw "$file failed with exit code $LASTEXITCODE" }
}
function Application($file, [string[]]$arguments) {
    $process = Start-Process -FilePath $file -ArgumentList $arguments -WorkingDirectory $build -WindowStyle Hidden -PassThru -Wait
    if ($process.ExitCode -ne 0) { throw "$file failed with exit code $($process.ExitCode); inspect logs in $build" }
}
if (-not $Baseline) {
    $Baseline = Join-Path $root '..\..\outputs\release-0.1.45\assets\Shogun2UltimatePatch-0.1.45-graphics-unlock.s2ub'
    if (-not (Test-Path -LiteralPath $Baseline)) {
        $Baseline = Join-Path $build 'Shogun2UltimatePatch-0.1.45-graphics-unlock.s2ub'
        if (-not (Test-Path -LiteralPath $Baseline)) {
            Run 'gh' @('release','download','v0.1.45-graphics-unlock','--repo','JakeTheRipperYT/Shogun-2-2026-ultimate-engine-bug-fix-patch','--pattern','Shogun2UltimatePatch-0.1.45-graphics-unlock.s2ub','--dir',$build)
        }
    }
}
$keyFile = Join-Path $root 'build\keys\signing-key.xml'
$publicFile = Join-Path $root 'installer\release-public.xml'
if ($Keygen) {
    if (Test-Path -LiteralPath $keyFile) { throw 'Signing key already exists; it will not be replaced.' }
    New-Item -ItemType Directory -Force (Split-Path $keyFile) | Out-Null
    $newKey = [Security.Cryptography.RSA]::Create(3072)
    try {
        [IO.File]::WriteAllText($keyFile,$newKey.ToXmlString($true),$utf8)
        [IO.File]::WriteAllText($publicFile,$newKey.ToXmlString($false),$utf8)
    } finally { $newKey.Dispose() }
}
if (-not (Test-Path -LiteralPath $keyFile)) { throw 'Original signing key required. Do not regenerate an established release key.' }
$rsa = [Security.Cryptography.RSA]::Create()
try {
    $rsa.FromXmlString([IO.File]::ReadAllText($keyFile))
    if ($rsa.ToXmlString($false) -ne [IO.File]::ReadAllText($publicFile)) { throw 'Signing key does not match installer public key.' }
    $vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
    $vs = & $vswhere -latest -prerelease -products * -property installationPath
    $csc = Join-Path $vs 'MSBuild\Current\Bin\Roslyn\csc.exe'
    $references = Join-Path ${env:ProgramFiles(x86)} 'Reference Assemblies\Microsoft\Framework\.NETFramework\v4.8'
    $netRefs = @('mscorlib','System','System.Core','System.Drawing','System.Windows.Forms','System.Web.Extensions','System.IO.Compression','System.Net.Http') | ForEach-Object { '/reference:'+(Join-Path $references ($_.ToString()+'.dll')) }
    $sources = @(Get-ChildItem -LiteralPath (Join-Path $root 'installer\recovered\S2UltimatePatch') -Filter '*.cs' -File | Sort-Object Name | ForEach-Object FullName)
    $sources += Join-Path $root 'installer\recovered\Properties\AssemblyInfo.cs'
    $common = @('/nologo','/noconfig','/nostdlib','/platform:anycpu','/optimize+','/deterministic+','/debug-','/langversion:latest','/target:winexe',('/resource:'+$publicFile+',publicKey'),('/win32manifest:'+(Join-Path $root 'installer\recovered\app.manifest'))) + $netRefs
    $applicationVersion = [regex]::Match([IO.File]::ReadAllText((Join-Path $root 'installer\recovered\S2UltimatePatch\OnlineUpdates.cs')),'AppVersion = "([^"]+)"').Groups[1].Value
    if ($applicationVersion -ne $Version) { throw 'Source application version differs from requested package version.' }
    $manager = Join-Path $build 'UltimatePatch_Launcher.exe'
    Write-Host 'Building installer/launcher application; engine code is not compiled.'
    Run $csc ($common + @('/out:'+$manager) + $sources)
    $prepare = @('-B',(Join-Path $root 'tools\prepare-current-release.py'),'--game',$GameDir,'--baseline',$Baseline,'--version',$Version,'--out',$build,'--managed-launcher',$manager)
    if ($CompareInstalled) { $prepare += '--compare-installed' }
    Run $Python $prepare
    $payload = [IO.File]::ReadAllBytes((Join-Path $build 'package-payload.zip'))
    $signature = $rsa.SignData($payload,[Security.Cryptography.HashAlgorithmName]::SHA256,[Security.Cryptography.RSASignaturePadding]::Pkcs1)
    if (-not $rsa.VerifyData($payload,$signature,[Security.Cryptography.HashAlgorithmName]::SHA256,[Security.Cryptography.RSASignaturePadding]::Pkcs1)) { throw 'Signature verification failed.' }
    $package = Join-Path $dist ('Shogun2UltimatePatch-'+$Version+'.s2ub')
    $stream = [IO.File]::Create($package)
    try {
        $magic = [Text.Encoding]::ASCII.GetBytes('S2UBPKG1')
        $stream.Write($magic,0,$magic.Length)
        $size = [BitConverter]::GetBytes([int]$signature.Length)
        $stream.Write($size,0,$size.Length)
        $stream.Write($signature,0,$signature.Length)
        $stream.Write($payload,0,$payload.Length)
    } finally { $stream.Dispose() }
} finally { $rsa.Dispose() }
$setup = Join-Path $dist 'Shogun2UltimatePatch_Setup.exe'
Run $csc ($common + @(('/out:'+$setup),('/resource:'+$package+',release')) + $sources)
Application $setup @('--self-test',('"'+(Join-Path $build 'installer-self-tests.txt')+'"'))
$zip = Join-Path $dist 'Shogun2UltimatePatch_Installer.zip'
[IO.File]::SetLastWriteTimeUtc($setup,[DateTime]::new(2026,11,7,0,0,0,[DateTimeKind]::Utc))
Compress-Archive -LiteralPath $setup -DestinationPath $zip -Force
$assets = @($package,$setup,$zip)
$hashLines = $assets | ForEach-Object { (Get-FileHash -LiteralPath $_ -Algorithm SHA256).Hash.ToLowerInvariant()+'  '+[IO.Path]::GetFileName($_) }
[IO.File]::WriteAllText((Join-Path $dist 'SHA256SUMS.txt'),($hashLines -join "`n")+"`n",$utf8)
Write-Host ('Signed release built: '+$Version)
Get-Content -LiteralPath (Join-Path $build 'installer-self-tests.txt') -Tail 4
Write-Host ('Installer and package: '+$dist)
