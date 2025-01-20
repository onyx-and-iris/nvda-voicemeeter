function Compress-Builds {
    $target = Join-Path -Path $PSScriptRoot -ChildPath "dist"
    @("basic", "banana", "potato") | ForEach-Object {
        Compress-Archive -Path $(Join-Path -Path $target -ChildPath $_) -DestinationPath $(Join-Path -Path $target -ChildPath "${_}.zip") -Force
    }
}

function Get-Builds {
    @("basic", "banana", "potato") | ForEach-Object {
        $specName = $_

        Write-Host "building $specName"

        pdm run pyinstaller --noconfirm --distpath  (Join-Path -Path "dist" -ChildPath $specName) (Join-Path -Path "spec" -ChildPath "${specName}.spec")
    }
}

function main {
    Get-Builds
    Compress-Builds
}

if ($MyInvocation.InvocationName -ne '.') { main }