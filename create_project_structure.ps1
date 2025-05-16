# PowerShell script for creating project structure

# Set current directory as root
$rootDir = "."

# Create directory structure
$directories = @(
    "static\css",
    "static\js",
    "templates",
    "modules",
    "data"
)

foreach ($dir in $directories) {
    $path = Join-Path -Path $rootDir -ChildPath $dir
    if (-not (Test-Path -Path $path)) {
        New-Item -Path $path -ItemType Directory -Force
        Write-Host "Created directory: $path"
    }
}

# Create empty files
$files = @(
    "app.py",
    "templates\index.html",
    "templates\result.html",
    "modules\downloader.py",
    "modules\parser.py",
    "modules\excel_generator.py",
    "requirements.txt"
)

foreach ($file in $files) {
    $path = Join-Path -Path $rootDir -ChildPath $file
    if (-not (Test-Path -Path $path)) {
        New-Item -Path $path -ItemType File -Force
        Write-Host "Created file: $path"
    }
}

Write-Host "Project structure created successfully!"