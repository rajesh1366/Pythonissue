param (
    [string]$jsonFilePath
)

# Read JSON file
$jsonContent = Get-Content -Raw -Path $jsonFilePath | ConvertFrom-Json

foreach ($user in $jsonContent.users) {
    $username = $user.username
    $fullname = $user.fullname
    $password = $user.password
    $groups = $user.groups

    if (-Not (Get-LocalUser -Name $username -ErrorAction SilentlyContinue)) {
        Write-Host "Creating user: $username"
        New-LocalUser -Name $username -Password (ConvertTo-SecureString -AsPlainText $password -Force) -FullName $fullname -Description "Created via automation"
    } else {
        Write-Host "User $username already exists. Skipping."
    }

    foreach ($group in $groups) {
        if (Get-LocalGroup -Name $group -ErrorAction SilentlyContinue) {
            Write-Host "Adding $username to group $group"
            Add-LocalGroupMember -Group $group -Member $username
        } else {
            Write-Host "Group $group does not exist. Skipping."
        }
    }
}
