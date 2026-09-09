[CmdletBinding()]
param(
    [string]$JavaHome = 'C:\Java\jdk1.8.0_351',
    [string]$MavenExecutable = 'C:\Users\hjwan\.workbuddy\binaries\maven\versions\3.9.9\bin\mvn.cmd'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repositoryRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$pomPath = Join-Path $repositoryRoot 'imagej-service\pom.xml'
$sourceJar = Join-Path $repositoryRoot 'imagej-service\target\imagej-service-1.0.0-SNAPSHOT.jar'
$outputDirectory = Join-Path $repositoryRoot 'deploy\artifacts'
$outputJar = Join-Path $outputDirectory 'imagej-service.jar'
$outputChecksum = Join-Path $outputDirectory 'imagej-service.jar.sha256'
$outputEvidence = Join-Path $outputDirectory 'imagej-service.build.json'

if (-not (Test-Path -LiteralPath $MavenExecutable -PathType Leaf)) {
    throw "Maven executable is missing: $MavenExecutable"
}
if (-not (Test-Path -LiteralPath (Join-Path $JavaHome 'bin\java.exe') -PathType Leaf)) {
    throw "Java executable is missing under: $JavaHome"
}

$previousJavaHome = $env:JAVA_HOME
try {
    $env:JAVA_HOME = $JavaHome
    & $MavenExecutable -f $pomPath clean verify
    if ($LASTEXITCODE -ne 0) {
        throw "ImageJ Maven verification failed with exit code $LASTEXITCODE."
    }

    if (-not (Test-Path -LiteralPath $sourceJar -PathType Leaf)) {
        throw "Verified ImageJ JAR is missing: $sourceJar"
    }

    New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null
    Copy-Item -LiteralPath $sourceJar -Destination $outputJar -Force

    $sha256 = (Get-FileHash -LiteralPath $outputJar -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($sha256 -notmatch '^[a-f0-9]{64}$') {
        throw 'Generated ImageJ SHA-256 has an invalid format.'
    }
    [System.IO.File]::WriteAllText(
        $outputChecksum,
        "$sha256`n",
        [System.Text.UTF8Encoding]::new($false)
    )

    $testTotals = [ordered]@{ tests = 0; failures = 0; errors = 0; skipped = 0 }
    Get-ChildItem -LiteralPath (Join-Path $repositoryRoot 'imagej-service\target\surefire-reports') -Filter 'TEST-*.xml' |
        ForEach-Object {
            [xml]$report = Get-Content -LiteralPath $_.FullName
            $suite = $report.testsuite
            $testTotals.tests += [int]$suite.tests
            $testTotals.failures += [int]$suite.failures
            $testTotals.errors += [int]$suite.errors
            $testTotals.skipped += [int]$suite.skipped
        }

    $mavenVersion = (& $MavenExecutable -v | Select-Object -First 1)
    $javaExecutable = Join-Path $JavaHome 'bin\java.exe'
    $savedErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $javaVersionOutput = & $javaExecutable -version 2>&1
        $javaVersionExitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $savedErrorActionPreference
    }
    if ($javaVersionExitCode -ne 0) {
        throw "Java version command failed with exit code $javaVersionExitCode."
    }
    $javaVersion = ($javaVersionOutput | Select-Object -First 1).ToString()
    $evidence = [ordered]@{
        artifact = 'imagej-service.jar'
        sizeBytes = (Get-Item -LiteralPath $outputJar).Length
        sha256 = $sha256
        maven = $mavenVersion
        java = $javaVersion
        tests = $testTotals
    }
    $evidence | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $outputEvidence -Encoding utf8
    $evidence | ConvertTo-Json -Depth 4
}
finally {
    $env:JAVA_HOME = $previousJavaHome
}
