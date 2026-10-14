param(
    [Parameter(Mandatory=$true)][string]$Servidor,
    [Parameter(Mandatory=$true)][string]$Chave,
    [ValidateSet('Terminal','Tunel')][string]$Modo = 'Terminal',
    [ValidateRange(1024,65535)][int]$PortaLocal = 15433,
    [string]$UsuarioSsh = 'ubuntu'
)
$ErrorActionPreference = 'Stop'
if ($Servidor -notmatch '^[a-zA-Z0-9.-]+$' -or $UsuarioSsh -notmatch '^[a-zA-Z0-9_-]+$') {
    throw 'Servidor ou usuário SSH inválido.'
}
$sshPath = Join-Path $env:WINDIR 'System32\OpenSSH\ssh.exe'
if (!(Test-Path -LiteralPath $sshPath)) { throw 'Instale o cliente OpenSSH do Windows.' }
$sourceKey = (Resolve-Path -LiteralPath $Chave).Path
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$privateDir = Join-Path $projectRoot ('tmp/oci/acesso-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $privateDir | Out-Null
$temporaryKey = Join-Path $privateDir 'access.key'
try {
    # Restrict the directory before copying the key. Never modify the original.
    $identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().User
    $directoryAcl = New-Object System.Security.AccessControl.DirectorySecurity
    $directoryAcl.SetOwner($identity)
    $directoryAcl.SetAccessRuleProtection($true,$false)
    $directoryAcl.AddAccessRule((New-Object System.Security.AccessControl.FileSystemAccessRule($identity,'FullControl','ContainerInherit,ObjectInherit','None','Allow')))
    Set-Acl -LiteralPath $privateDir -AclObject $directoryAcl
    Copy-Item -LiteralPath $sourceKey -Destination $temporaryKey
    $keyAcl = New-Object System.Security.AccessControl.FileSecurity
    $keyAcl.SetOwner($identity)
    $keyAcl.SetAccessRuleProtection($true,$false)
    $keyAcl.AddAccessRule((New-Object System.Security.AccessControl.FileSystemAccessRule($identity,'FullControl','Allow')))
    Set-Acl -LiteralPath $temporaryKey -AclObject $keyAcl
    # Reuse the server identity verified during installation; unknown hosts prompt.
    $knownHosts = Join-Path $projectRoot 'tmp/oci/known_hosts'
    $options = @('-F','NUL','-i',$temporaryKey,'-o','ConnectTimeout=10','-o','StrictHostKeyChecking=ask','-o',"UserKnownHostsFile=$knownHosts")
    $destination = "$UsuarioSsh@$Servidor"
    if ($Modo -eq 'Terminal') {
        & $sshPath @options -t $destination 'sudo -n docker exec -it peticas-oci-db-1 psql -U peticas -d peticas'
    } else {
        $databaseIp = & $sshPath @options $destination 'sudo -n docker inspect --format ''{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'' peticas-oci-db-1'
        if ($LASTEXITCODE -ne 0) { throw 'Não foi possível localizar o banco na VM.' }
        $databaseIp = ($databaseIp -join '').Trim()
        $parsedIp = $null
        if (![System.Net.IPAddress]::TryParse($databaseIp,[ref]$parsedIp) -or $parsedIp.AddressFamily -ne 'InterNetwork') {
            throw 'O banco não retornou um endereço IPv4 válido.'
        }
        Write-Host "Túnel em 127.0.0.1:$PortaLocal. Banco: peticas. Usuário: peticas."
        Write-Host 'Mantenha esta janela aberta. A senha está em POSTGRES_PASSWORD no .env de produção da VM.'
        & $sshPath @options -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -L "127.0.0.1:${PortaLocal}:${databaseIp}:5432" $destination
    }
    if ($LASTEXITCODE -ne 0) { throw 'A conexão SSH foi encerrada com erro.' }
} finally {
    if (Test-Path -LiteralPath $temporaryKey) { Remove-Item -LiteralPath $temporaryKey -Force }
    # Only this empty, explicitly created directory is removed; never recursively.
    if (Test-Path -LiteralPath $privateDir) { Remove-Item -LiteralPath $privateDir }
}
