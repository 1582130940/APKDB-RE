# APKDB v2.1.5 重制版（2026-11-19）

APKDB（安卓逆手）是一个 Windows 下的 Android 反编译工具包，把 Apktool、jadx、smali/baksmali 等工具
整合进资源管理器右键菜单。本项目在 **v2.1.4 (20210702)** 基础上做原位替换与修复：
目录结构、右键菜单、批处理入口全部保持原样，只更新组件和修 bug。

> 本仓库只做打包整合与脚本修复，各工具版权归原作者所有。

## 下载

- 安装包：见本仓库 **Releases** 页 → `APKDB_v2.1.5_20261119.exe`

## 组件版本

| 组件 | 原版 | 本版 |
|---|---|---|
| Apktool | 2.5.0 / 2.5.1 / Shaka 2.2.2 | **3.0.3** |
| smali / baksmali | 2.5.2 | **3.0.10** |
| jadx | 1.2.0 | **1.5.7** |
| adb / fastboot | 31.0.2 | **platform-tools 37.0.1** |
| aapt / zipalign / apksigner | 旧版 / 无 | **build-tools 37.0.0** |
| 7-Zip | 16.04 | **26.06** |
| OptiPNG | 0.7.6 | **0.7.8** |
| wget | 1.10.2（2005） | **1.25.0** |
| APK 图标扩展 | ApkShellext2 0.2.0.7 | **ApkShellext2-Plus 2.1.5**（强名称签名） |
| boot.img 工具 | bootimg 2015 | 保留旧版 + **MagiskBoot 27.0** |

签名从只支持 v1 的 `signapk` 换成 **apksigner**（v1+v2+v3），批量回编译改为先 zipalign 再签名。

## 环境要求

- **Java 8+**（Apktool 3 最低要求）
- **64 位 Java 11+**（jadx 1.5.7 要求）
- .NET Framework 4.8（仅"显示 APK 自身图标"功能需要，缺失不影响其它功能）
- **64 位 Windows**：Apktool 3 不再支持 32 位平台

## 安装

运行 `APKDB_v2.1.5_20261119.exe`，选择安装路径，解压后自动进入安装向导。

- 会请求管理员权限（写注册表、注册 Shell 扩展需要）
- 图标功能可选，安装结果写入安装目录的 `install.log`
- 覆盖安装前会先清理旧版本，不需要手动卸载

卸载：运行安装目录下的 `Uninstall.exe`。

## 旧版清理

新增 `Tools/PreClean.bat` 与 `Tools/cleanup.bat`，覆盖安装/卸载时自动执行：

- 注销旧的 Shell 扩展，删除旧版文件与 `apktool200~241.jar`、旧 jadx 依赖
- 清理 1350 个旧注册表项（CLSID / Record / ProgID）
- 重建 `.apk/.arsc/.dex/.odex` 关联与右键菜单
- 被 Explorer 占用的 DLL 用重命名方式替换，安装过程不再结束资源管理器

## 脚本修复

33 个批处理脚本已全部审查，修复 16 类真实缺陷，主要包括：

- Keytool2 段标签冲突（2.1.4 里"制作签名包"实际走了"查看签名"分支）
- 死跳转 / 自环 / 重复标签：`goto APKinTool`、`goto 230c`、`:bxxx2`、`:b1x`
- 未定义变量：`%dexd_ERRORLEVEL%`、`%ZIP%`
- 裸 `exit` 破坏 `call` 调用方、路径未加引号
- `install.bat` 逻辑缺陷：无提权导致 RegAsm 必失败、依赖 `find.exe`、缺 .NET 4.8 检测

详见 [SCRIPT-AUDIT.md](SCRIPT-AUDIT.md)。

## 已验证

- apktool 3.0.3 反编译 → `b --copy-original` 回编译成功
- smali/baksmali 3.0.10 往返成功
- 完整链路：aapt2 构建 → zipalign → apksigner 签名 → `apksigner verify` 显示 **v1/v2/v3 全通过**
- OptiPNG 压缩 + 重打包 + 签名（路径含空格）通过
- 各工具版本号逐个确认

## 已知限制

1. Apktool 3 仅支持 64 位，且已移除 aapt1。
2. 脚本为 **GBK + CRLF**，系统若启用"UTF-8 全球语言支持"会出现中文乱码。
3. 工作目录建议不含空格/中文（原版同样要求）。
4. `Update/update.bat` 的在线更新源（idoog.me）已失效，本版改为离线说明。
5. `Tools/Hosts/Hostsup.bat` 的远程 HOSTS 源已失效，手动模式仍可用。
6. 本包不内置 JRE、`d8`、`android.jar`。
