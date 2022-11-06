# Tootify Azure Function

This Azure Function uses a file share to store the config and syncronisation status. Create `config.yaml` and mount the file share:

```powershell
$path = New-AzWebAppAzureStoragePath -MountPath /tootify
Set-AzWebApp -Name tootify -ResourceGroupName tootify -AzureStoragePath $path
```