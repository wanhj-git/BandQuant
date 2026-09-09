[CmdletBinding()]
param(
    [string]$JarPath,
    [string]$HostAddress = $(if ($env:IMAGEJ_SERVICE_HOST) { $env:IMAGEJ_SERVICE_HOST } else { '127.0.0.1' }),
    [string]$Port = $(if ($env:IMAGEJ_SERVICE_PORT) { $env:IMAGEJ_SERVICE_PORT } else { '8200' })
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($JarPath)) {
    $JarPath = Join-Path $PSScriptRoot '..\imagej-service\target\imagej-service-1.0.0-SNAPSHOT.jar'
}

if ([string]::IsNullOrWhiteSpace($env:JAVA_HOME)) {
    throw 'JAVA_HOME is required.'
}

$javaExecutable = Join-Path $env:JAVA_HOME 'bin\java.exe'
if (-not (Test-Path -LiteralPath $javaExecutable -PathType Leaf)) {
    throw 'JAVA_HOME\bin\java.exe does not exist.'
}

if ([string]::IsNullOrWhiteSpace($env:IMAGEJ_SERVICE_TOKEN)) {
    throw 'IMAGEJ_SERVICE_TOKEN is required in the current process environment.'
}

$loopback = $false
if ($HostAddress -eq 'localhost') {
    $loopback = $true
} else {
    $parsedAddress = $null
    if ([System.Net.IPAddress]::TryParse($HostAddress, [ref]$parsedAddress)) {
        $loopback = [System.Net.IPAddress]::IsLoopback($parsedAddress)
    }
}
if (-not $loopback) {
    throw 'IMAGEJ_SERVICE_HOST must be a loopback address.'
}

$parsedPort = 0
if (-not [int]::TryParse($Port, [ref]$parsedPort) -or $parsedPort -lt 1 -or $parsedPort -gt 65535) {
    throw 'IMAGEJ_SERVICE_PORT must be an integer from 1 through 65535.'
}

if (-not (Test-Path -LiteralPath $JarPath -PathType Leaf)) {
    throw 'The ImageJ service JAR does not exist.'
}
$resolvedJar = (Resolve-Path -LiteralPath $JarPath -ErrorAction Stop).Path

$env:IMAGEJ_SERVICE_HOST = $HostAddress
$env:IMAGEJ_SERVICE_PORT = [string]$parsedPort

& $javaExecutable '-Xmx1500m' '-Djava.awt.headless=true' '-jar' $resolvedJar
exit $LASTEXITCODE
