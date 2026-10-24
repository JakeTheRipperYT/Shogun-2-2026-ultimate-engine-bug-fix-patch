<#
.SYNOPSIS
  Builds the Shogun 2 Ultimate Bug Fix Patch launcher, a signed release package and the installer.

.DESCRIPTION
  1. Compiles the native launcher (MSVC, no C runtime).
  2. Compiles the developer ReleaseTool.
  3. Builds a signed .s2ub release from your local vanilla game + patches/engine/*.json.
  4. Compiles Shogun2UltimatePatch_Setup.exe with that release embedded, runs its self-tests
     and zips it into dist/.

  Needs Visual Studio (C++ workload) and .NET Framework 4.8 reference assemblies.
  First time only: .\build.ps1 -Keygen   (creates the signing key outside the repo).
#>
param(
    [string]$Version,
    [string]$GameDir,
    [switch]$Keygen,
    [switch]$SkipTests
)
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$build = Join-Path $root 'build'
$dist = Join-Path $root 'dist'
New-Item -ItemType Directory -Force $build, $dist | Out-Null

function Step($text) { Write-Host "==> $text" -ForegroundColor Cyan }
function Run($exe, [string[]]$arguments) {
    & $exe @arguments
    if ($LASTEXITCODE -ne 0) { throw "$([IO.Path]::GetFileName($exe)) failed with exit code $LASTEXITCODE" }
}

# --- Toolchain -------------------------------------------------------------------------------
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
$vs = & $vswhere -latest -prerelease -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $vs) { throw 'Visual Studio with the C++ workload was not found.' }
$vcvars = Join-Path $vs 'VC\Auxiliary\Build\vcvarsall.bat'
$csc = Join-Path $vs 'MSBuild\Current\Bin\Roslyn\csc.exe'
$refs = Join-Path ${env:ProgramFiles(x86)} 'Reference Assemblies\Microsoft\Framework\.NETFramework\v4.8'
if (-not (Test-Path $refs)) { throw '.NET Framework 4.8 reference assemblies were not found (install the .NET Framework 4.8 targeting pack).' }
$netRefs = 'mscorlib', 'System', 'System.Core', 'System.Drawing', 'System.Windows.Forms', 'System.Web.Extensions',
           'System.IO.Compression', 'System.Net.Http' | ForEach-Object { "/reference:$refs\$_.dll" }
$cscCommon = @('/nologo', '/noconfig', '/nostdlib', '/platform:anycpu', '/optimize+', '/langversion:7.3', '/warnaserror-') + $netRefs

if (-not $Version) {
    $Version = (Select-String -Path (Join-Path $root 'installer\OnlineUpdates.cs') -Pattern 'AppVersion\s*=\s*"([^"]+)"').Matches[0].Groups[1].Value
}
if (-not $GameDir) {
    $steam = (Get-ItemProperty 'HKCU:\Software\Valve\Steam' -ErrorAction SilentlyContinue).SteamPath
    $libraries = @($steam)
    $vdf = Join-Path "$steam" 'steamapps\libraryfolders.vdf'
    if (Test-Path $vdf) { $libraries += [regex]::Matches((Get-Content $vdf -Raw), '"path"\s+"([^"]+)"') | ForEach-Object { $_.Groups[1].Value -replace '\\\\', '\' } }
    $GameDir = $libraries | Where-Object { $_ } | ForEach-Object { Join-Path $_ 'steamapps\common\Total War SHOGUN 2' } |
               Where-Object { Test-Path (Join-Path $_ 'shogun2.exe') } | Select-Object -First 1
    if (-not $GameDir) { throw 'Total War: SHOGUN 2 was not found. Pass -GameDir.' }
}
$acf = Join-Path (Split-Path (Split-Path $GameDir)) 'appmanifest_34330.acf'
$gameBuild = if (Test-Path $acf) { [regex]::Match((Get-Content $acf -Raw), '"buildid"\s+"(\d+)"').Groups[1].Value } else { '' }

# --- Launcher --------------------------------------------------------------------------------
Step 'Launcher'
$launcher = Join-Path $build 'Launch_Shogun2_Ultimate_Patch.exe'
$cmd = "`"$vcvars`" x64 >nul && cd /d `"$build`" && rc /nologo /fo launcher.res `"$root\launcher\launcher.rc`" && " +
       "cl /nologo /O1 /GS- /W4 /WX /c `"$root\launcher\launcher.c`" /Fo:launcher.obj && " +
       "link /nologo /MANIFEST:EMBED /MANIFESTUAC:`"level='asInvoker' uiAccess='false'`" /NODEFAULTLIB /ENTRY:entry /SUBSYSTEM:WINDOWS /OUT:`"$launcher`" launcher.obj launcher.res kernel32.lib user32.lib advapi32.lib"
$env:PATH = "$(Split-Path $vswhere);$env:PATH"   # vcvarsall looks for vswhere on PATH
cmd /c $cmd | Out-Host
if ($LASTEXITCODE -ne 0) { throw 'Launcher build failed.' }

# --- Release tool ----------------------------------------------------------------------------
Step 'Release tool'
$publicKey = Join-Path $root 'installer\release-public.xml'
$tool = Join-Path $build 'ReleaseTool.exe'
Push-Location $root
try {
    if ($Keygen) {
        # Compile without the public key resource so keygen can create it.
        Run $csc ($cscCommon + @('/target:exe', "/out:$tool", 'tools\ReleaseTool.cs', 'installer\Engine.cs', 'installer\OnlineUpdates.cs'))
        Run $tool @('keygen')
    }
    if (-not (Test-Path $publicKey)) { throw 'No signing key yet. Run .\build.ps1 -Keygen once.' }
    Run $csc ($cscCommon + @('/target:exe', "/out:$tool", "/resource:$publicKey,publicKey", 'tools\ReleaseTool.cs', 'installer\Engine.cs', 'installer\OnlineUpdates.cs'))

    # --- Release package ---------------------------------------------------------------------
    Step "Release $Version from $GameDir (Steam build $gameBuild)"
    $package = Join-Path $build "Shogun2UltimatePatch-$Version.s2ub"
    $makeArgs = @('make', '--game', $GameDir, '--version', $Version, '--launcher', $launcher,
                  '--patches', (Join-Path $root 'patches\engine'), '--out', $package, '--dev-output', (Join-Path $build 'dev'))
    if ($gameBuild) { $makeArgs += @('--game-build', $gameBuild) }
    Run $tool $makeArgs
    Run $tool @('verify', $package)

    # --- Installer ---------------------------------------------------------------------------
    Step 'Installer'
    $setup = Join-Path $build 'Shogun2UltimatePatch_Setup.exe'
    Run $csc ($cscCommon + @('/target:winexe', "/out:$setup", "/win32manifest:installer\app.manifest",
              "/resource:$package,release", "/resource:$publicKey,publicKey",
              'installer\Program.cs', 'installer\Engine.cs', 'installer\OnlineUpdates.cs'))
} finally { Pop-Location }

if (-not $SkipTests) {
    Step 'Self-tests'
    $report = Join-Path $build 'self-test.txt'
    Remove-Item $report -ErrorAction SilentlyContinue
    $p = Start-Process $setup -ArgumentList '--self-test', "`"$report`"" -Wait -PassThru -WindowStyle Hidden -WorkingDirectory $build
    if ($p.ExitCode -ne 0 -or -not (Test-Path $report)) { throw "Self-tests failed; see $build\installer-error.txt" }
    Get-Content $report
}

if (-not $SkipTests -and (Get-Content (Join-Path $root 'patches\engine\050-yari-wall-movement.json') -Raw | ConvertFrom-Json).enabled) {
    Step 'Yari wall native x86 branch checks'
    $branchTest = Join-Path $build 'test-yari-branch.exe'
    $cmd = "`"$vcvars`" x86 >nul && cl /nologo /TP /O2 /W4 /WX `"$root\tools\test-yari-branch.c`" " +
           "/Fo:`"$build\test-yari-branch.obj`" /Fe:`"$branchTest`""
    cmd /c $cmd | Out-Host
    if ($LASTEXITCODE -ne 0) { throw 'Native branch-test build failed.' }
    & $branchTest (Join-Path $GameDir 'empire.retail.dll') (Join-Path $build 'dev\empire.retail.dll') |
        Tee-Object -FilePath (Join-Path $build 'yari-branch-tests.txt') | Out-Host
    if ($LASTEXITCODE -ne 0) { throw 'Native branch tests failed.' }
}

if (-not $SkipTests -and (Get-Content (Join-Path $root 'patches\engine\060-kneel-fire-movement.json') -Raw | ConvertFrom-Json).enabled) {
    Step 'Kneel fire native x86 eligibility checks'
    $kneelTest = Join-Path $build 'test-kneel-eligibility.exe'
    $cmd = "`"$vcvars`" x86 >nul && cl /nologo /TP /O2 /W4 /WX `"$root\tools\test-kneel-eligibility.c`" " +
           "/Fo:`"$build\test-kneel-eligibility.obj`" /Fe:`"$kneelTest`""
    cmd /c $cmd | Out-Host
    if ($LASTEXITCODE -ne 0) { throw 'Kneel eligibility-test build failed.' }
    & $kneelTest (Join-Path $GameDir 'empire.retail.dll') (Join-Path $build 'dev\empire.retail.dll') |
        Tee-Object -FilePath (Join-Path $build 'kneel-eligibility-tests.txt') | Out-Host
    if ($LASTEXITCODE -ne 0) { throw 'Kneel eligibility tests failed.' }
}

Step 'Package'
$zip = Join-Path $dist 'Shogun2UltimatePatch_Installer.zip'
Remove-Item $zip -ErrorAction SilentlyContinue
Compress-Archive -Path $setup -DestinationPath $zip
Copy-Item $package $dist -Force
Write-Host "Done:`n  $zip`n  $(Join-Path $dist (Split-Path $package -Leaf))" -ForegroundColor Green
