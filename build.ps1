function Compress-Builds {
    @("basic", "banana", "potato") | ForEach-Object {
        $target = Join-Path -Path $PSScriptRoot -ChildPath "dist"
        Compress-Archive -Path $(Join-Path -Path $target -ChildPath $_) -DestinationPath $(Join-Path -Path $target -ChildPath "${_}.zip")
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