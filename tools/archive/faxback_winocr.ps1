# SPDX-FileCopyrightText: 2026 Michael A. Hall
# SPDX-License-Identifier: GPL-3.0-or-later
param(
    [Parameter(Mandatory)][string]$Directory,
    [Parameter(Mandatory)][string]$Language
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
[void][Windows.Storage.StorageFile,Windows.Storage,ContentType=WindowsRuntime]
[void][Windows.Storage.Streams.IRandomAccessStreamWithContentType,Windows.Storage.Streams,ContentType=WindowsRuntime]
[void][Windows.Graphics.Imaging.BitmapDecoder,Windows.Graphics.Imaging,ContentType=WindowsRuntime]
[void][Windows.Graphics.Imaging.SoftwareBitmap,Windows.Graphics.Imaging,ContentType=WindowsRuntime]
[void][Windows.Media.Ocr.OcrEngine,Windows.Foundation,ContentType=WindowsRuntime]
[void][Windows.Media.Ocr.OcrResult,Windows.Foundation,ContentType=WindowsRuntime]
[void][Windows.Globalization.Language,Windows.Globalization,ContentType=WindowsRuntime]
$asTask = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.IsGenericMethod -and $_.GetParameters().Count -eq 1 -and
    $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
} | Select-Object -First 1

function Receive-WinRt($Operation, [type]$ResultType) {
    $task = $asTask.MakeGenericMethod($ResultType).Invoke($null, @($Operation))
    if (-not $task.Wait(15000)) { throw 'WinRT operation timed out' }
    $task.Result
}

$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage([Windows.Globalization.Language]::new($Language))
if ($null -eq $engine) { throw "Windows OCR language unavailable: $Language" }
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
foreach ($png in Get-ChildItem -LiteralPath $Directory -Filter '*.png' -File) {
    $file = Receive-WinRt ([Windows.Storage.StorageFile]::GetFileFromPathAsync($png.FullName)) ([Windows.Storage.StorageFile])
    $stream = Receive-WinRt ($file.OpenReadAsync()) ([Windows.Storage.Streams.IRandomAccessStreamWithContentType])
    try {
        $decoder = Receive-WinRt ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
        $bitmap = Receive-WinRt ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
        try {
            $result = Receive-WinRt ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
            [pscustomobject]@{
                name = $png.BaseName
                language = $engine.RecognizerLanguage.LanguageTag
                lines = @($result.Lines | ForEach-Object { $_.Text })
            } | ConvertTo-Json -Compress -Depth 4
        } finally { $bitmap.Dispose() }
    } finally { $stream.Dispose() }
}
