# mingw_env_setup.ps1
# 在便携式开发环境中将 MinGW-w64 加入 PATH 并设置编译环境变量
# 用法: . .\scripts\mingw_env_setup.ps1  （注意前面的点，使变量在当前shell生效）

$MINGW64 = "C:\Users\fjzheng\portable-dev-env\tools\mingw64"

# 将 MinGW 加入 PATH（当前会话）
$env:Path = "$MINGW64;$env:Path"

# 设置 C 编译器（Python distutils/setuptools 通过环境变量查找）
$env:CC = "$MINGW64\gcc.exe"
$env:CXX = "$MINGW64\g++.exe"

Write-Host "MinGW-w64 environment configured:"
Write-Host "  GCC: $(gcc --version | Select-Object -First 1)"
Write-Host "  Path added: $MINGW64"
