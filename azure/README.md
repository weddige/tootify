# Tootify Azure Function

This Azure Function uses a file share to store the config and syncronisation status. Create `config.yaml` and mount the file share:

```powershell
$path = New-AzWebAppAzureStoragePath -MountPath /tootify
Set-AzWebApp -Name tootify -ResourceGroupName tootify -AzureStoragePath $path
```

The name of the config file can be set using the `TOOTIFIER_CONFIG` environment variable. The default is `/tootify/config.yaml`. It's possible to configure multiple files, separated by a colon: `/tootify/account1.yaml:/tootify/account2.yaml`.