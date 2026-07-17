<#
.SYNOPSIS
Start the Jekyll docs server with debugging output.

.DESCRIPTION
This script installs the required Jekyll gems from docs/Gemfile and runs
`jekyll serve` with tracing enabled so you can debug site generation issues.
#>

param(
    [string]$BaseUrl = '/finance-mosaix',
    [string]$ServerHost = '127.0.0.1',
    [int]$Port = 4000
)

$ErrorActionPreference = 'Stop'

Push-Location -Path $PSScriptRoot

Write-Host "Checking Ruby availability..."
if (-not (Get-Command ruby -ErrorAction SilentlyContinue)) {
    throw "Ruby is not available in the current shell. Install Ruby and retry."
}

Write-Host "Installing bundler if missing..."
ruby -S gem install bundler --no-document | Out-Null

Write-Host "Installing Jekyll dependencies from Gemfile..."
ruby -S bundle install

Write-Host "Building Jekyll site..."
ruby -S bundle exec jekyll build --trace --force --baseurl $BaseUrl

Write-Host "Starting Jekyll with trace enabled in the background..."
$serveArgs = "-S bundle exec jekyll serve --watch --trace --host $ServerHost --port $Port --baseurl $BaseUrl --force"
$process = Start-Process -FilePath "ruby" -ArgumentList $serveArgs -WorkingDirectory $PSScriptRoot -NoNewWindow -PassThru

Start-Sleep -Seconds 4
$url = "http://$($ServerHost):$($Port)$($BaseUrl)/"
Write-Host "Opening docs in browser: $url"
Start-Process $url

Write-Host "Jekyll is running in the background with PID $($process.Id)."
Write-Host "Use the terminal to stop it when you are finished."

Pop-Location
