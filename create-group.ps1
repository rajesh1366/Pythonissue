param (
    [string]$jsonFilePath
)

# Read JSON file
$jsonContent = Get-Content -Raw -Path $jsonFilePath | ConvertFrom-Json

foreach ($group in $jsonContent.groups) {
    $groupName = $group.groupname
    $description = $group.description

    if (-Not (Get-LocalGroup -Name $groupName -ErrorAction SilentlyContinue)) {
        Write-Host "Creating group: $groupName"
        New-LocalGroup -Name $groupName -Description $description
    } else {
        Write-Host "Group $groupName already exists. Skipping."
    }
}
