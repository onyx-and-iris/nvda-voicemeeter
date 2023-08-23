@("basic", "banana", "potato") | ForEach-Object {
    pdm run pyinstaller "${_}.spec" --noconfirm
}