# 构建脚本

本目录保存重新打包 `APKDB_v2.1.5_*.exe` 所需的脚本与 Shell 扩展补丁。

## 文件

| 文件 | 作用 |
|---|---|
| `build_apkdb.py` | 主构建脚本：从 v2.1.4 原始安装包出发，原位替换全部工具、打补丁、重新封装 7-Zip SFX |
| `fix_bats.py` | 批处理脚本修复（可重复执行，幂等） |
| `to_utf8.py` | UTF-8 转换实验脚本，**已弃用**（见 SCRIPT-AUDIT.md"四之三"） |
| `lint_bats.py` | 批处理静态检查：标签/跳转/括号/引号/编码/行尾 |
| `test_install.py` | `install.bat` 四个分支的干跑测试（stub 掉注册表与 regasm） |
| `engine/ApkShellext2.csproj` | 打过补丁的 Shell 扩展工程文件 |
| `engine/AssemblyInfo.cs` | 版本号与强名称相关程序集信息 |
| `engine/NonLocalizeResources.resources` | 经典格式（非 System.Resources.Extensions）的图标资源 |
| `engine/apkdb.snk` | 强名称密钥，用于消除 RegAsm 的 `RA0000` 未签名警告 |
| `engine/ApkShellext2.dll` | 已编译好的扩展（2.1.5.0，`PublicKeyToken=d21a89ac4bc45a64`） |

## 重新打包需要准备

`build_apkdb.py` 期望工作目录下有这些路径（脚本里的 `BASE`）：

```
apkdb_extract/APKDB_X/      v2.1.4 安装包解包后的内容
downloads/                  上游原始包（见下表）
stage/                      已解压的上游工具 + 自建 smali/baksmali fat jar
build_apkshellext/bin/Release/ApkShellext2.dll
                            （可直接用本目录 engine/ 下的 DLL）
```

`downloads/` 需要这些文件：

- `apktool_3.0.3.jar` — iBotPeaches/Apktool releases
- `jadx-1.5.7.zip` — skylot/jadx releases
- `platform-tools_r37.0.1-win.zip` — dl.google.com/android/repository
- `build-tools_r37_windows.zip` — 同上
- `7z2606-x64.exe` / `7z2606-x32.exe` — 7-zip.org
- `optipng-0.7.8.zip` — SourceForge（7.9.1 只有源码，无 Windows 二进制）
- `wget-1.25.0-32.exe` — eternallybored.org/misc/wget
- `magiskboot.exe` — deserthouse/magiskboot-build releases

`stage/` 需要：`jadx/`（解压 jadx-1.5.7.zip）、`smali.jar`、`baksmali.jar`
（由 `stage/smali_deps/` 里的 Google Maven 构件合并而成）。

## 重新打包

```bash
python build_apkdb.py
```

产物写在 `build/APKDB_v2.1.5_20261119.exe`，其中 `build/` 每次运行会先被清空。

## 重新编译 Shell 扩展（可选）

`build_apkdb.py` 只在 `build_apkshellext/bin/Release/` 下取现成 DLL，不负责编译。
若需重编译：

1. 取上游源码 `MaterDawn/ApkShellext2-Plus`
2. 用本目录 `engine/` 的 `ApkShellext2.csproj`、`AssemblyInfo.cs`、
   `NonLocalizeResources.resources`、`apkdb.snk` 覆盖对应文件
3. 需要 .NET SDK（`dotnet build ... -c Release`，目标框架 .NET Framework 4.8）

工程里有三处关键补丁，改动时注意别丢：

- `GenerateResourceUsePreserializedResources=false`
  —— 用经典 BinaryFormatter 资源序列化，否则 explorer.exe 内加载会报 0x80131040
- `NonLocalizeResources.resources` 以 `LogicalName` 内嵌，替代 `.resx`
  —— 由 `ResXResourceReader` 转换而来，避免依赖 System.Resources.Extensions
- `SignAssembly=true` + `apkdb.snk`
  —— 消除 `RegAsm : warning RA0000 ... 未签名的程序集`
