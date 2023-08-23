function Compress-Builds {
    $target = Join-Path -Path $PSScriptRoot -ChildPath "dist"
    @("basic", "banana", "potato") | ForEach-Object {
        Compress-Archive -Path $(Join-Path -Path $target -ChildPath $_) -DestinationPath $(Join-Path -Path $target -ChildPath "${_}.zip") -Force
    } 
}

function Get-Builds {
    @("basic", "banana", "potato") | ForEach-Object {
        pdm run pyinstaller "${_}.spec" --noconfirm
    }  
}

function main {
    Get-Builds

    Compress-Builds
}

if ($MyInvocation.InvocationName -ne '.') { main }