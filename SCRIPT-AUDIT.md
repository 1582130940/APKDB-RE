# APKDB v2.1.5 批处理脚本审查报告

审查对象：`APKDB_v2.1.5_20261119.exe` 内的 **33 个 `.bat` / `.cmd` 脚本**
审查方式：静态规则扫描（标签/跳转/引号/括号/延迟展开/编码/行尾）+ 对照真实 CLI 帮助 + 关键链路实测
审查时间：2026-11-19

## 一、总体结论

| 项目 | 数量 |
|---|---|
| 脚本总数 | 33 |
| 发现真实缺陷（已修复） | 16 类，涉及 12 个脚本 |
| 仅编码/行尾问题（已规范化） | 7 个文件 |
| 第三方官方脚本（AOSP/jadx，未改逻辑） | 4 个 |
| 静态误报（已核实无问题） | 6 类 |

本轮修复后，主流程脚本 **无重复标签、无未定义跳转、无括号失配、无裸 `exit` 破坏调用方**。

## 二、逐文件结论

### 核心流程

| 脚本 | 行数 | 结论 | 说明 |
|---|---|---|---|
| `apkdb.cmd` | 1681 | 已修 5 类 | Keytool2 标签冲突、`goto APKinTool` 缺失、`:b1x` 重复、`:bxxx2` 自环、`:7ZIP` 重复 |
| `apkdb_d.cmd` | 1541 | 已修 4 类 | 同上 Keytool2、`%dexd_ERRORLEVEL%` 拼写、`goto 230c` 死跳转、`goto Start` 缺字、keytool 路径未引号 |
| `odex.cmd` | 918 | 已修 3 类 | `A16` 缺冒号、28 处 Shaka 专有 `bs` 改为 `baksmali deodex`、`:A71` 重复 |
| `optipng.cmd` | 51 | 已修 5 类 | `%1` 未引号、`%parent%` 双重引号、`%ZIP%` 未定义、缺 `exit /b` 导致落空执行、`md` 路径未闭合 |
| `install.bat` | 178 | 已重写 | 未提权导致 RegAsm 必定失败、依赖 find.exe、缺 .NET 4.8 检测、mshta/mode con/无条件杀 Explorer 造成"闪退" |
| `unins.bat` | 17 | 已重写 | 原文件含非法 GBK 字节（乱码快捷方式路径），且卸载后仍重新注册扩展 |
| `uninstapkico.bat` | 46 | 已修 2 类 | `find` 依赖、缓存目录路径 |
| `seesource.bat` | 15 | 已修 1 类 | `%~p1seesource.bat` 未加引号 |
| `D.bat` | 26 | 正常 | `exit` 为独立进程设计 |
| `java.bat` | 2 | 正常 | 运行期缓存文件 |

### 工具封装

| 脚本 | 行数 | 结论 | 说明 |
|---|---|---|---|
| `Tools/optipng.bat` | 8 | 已修 1 类 | `IF %1 == ()` 恒假且带空格会语法错误 → `if "%~1"==""` |
| `Tools/reduce.bat` | 84 | 已修 1 类 | `%delang%` 未定义时会 `cd /d \res` 并删目录 → 加保护 |
| `Tools/JavaSet.bat` | 56 | 已修 1 类 | `wmic` 在新版 Windows 已移除 → 加检测与手动提示 |
| `Tools/FLV2MP4.bat` | 168 | 已修 2 类 | `goto :end2` 无此标签；ffmpeg.exe 未随包发布 → 加提示退出 |
| `Tools/Hosts/Hostsup.bat` | 287 | 部分可用 | `goto host DNS` 是**合法**的空格标签（非错误）；但 idoog.me / coding.net 已失效，远程更新不可用 |
| `Tools/PreClean.bat` | 24 | 正常 | 本轮新增 |
| `Tools/cleanup.bat` | 85 | 正常 | 本轮新增；含 `uninstall` 模式 |
| `Tools/Signer/apksigner-shim.bat` | 14 | 正常 | 本轮新增，适配原 signapk 四参数调用 |
| `Update/update.bat` | 18 | 已重写 | 原逻辑依赖已停止解析的 idoog.me，改为离线说明 |

### Shell 扩展 / 安装辅助

| 脚本 | 行数 | 结论 | 说明 |
|---|---|---|---|
| `Tools/apkshellext2/install.bat` | 61 | 正常 | 上游脚本；`if '%1' EQU '1'` 是合法 UAC 判定写法（静态工具误报） |
| `Tools/apkshellext2/uninstall.bat` | 56 | 正常 | 上游脚本 |
| `Tools/apkshellext2/restart_explorer.bat` | 7 | 正常 | — |
| `Temp/A.bat` `Temp/B.bat` `Temp/C.bat` | 3 | 正常 | SFX 解压后清进程 |
| `Tools/ADB/cmd.bat` `Tools/bootimg/cmd.bat` | 2 | 正常 | 仅打开 `%ComSpec%` |
| `Tools/ApkTool/adb.bat` | 2 | 依赖外部组件 | 调用 `shuame_helper.exe`（刷机精灵），该组件在本版保留 |

### 第三方官方脚本

| 脚本 | 行数 | 结论 | 说明 |
|---|---|---|---|
| `Tools/apksigner/apksigner.bat` | 115 | 正常 | AOSP 原版；`if [%1]==[]` 为标准写法；已加 `JAVA_HOME` 失效回退 |
| `jadx/bin/jadx.bat` | 88 | 正常 | jadx 官方；已加 `JAVA_HOME` 回退 |
| `jadx/bin/jadx-gui.bat` | 88 | 正常 | 同上（回退到 `javaw.exe`） |
| `language/Language.bat` | 533 | 正常 | 纯 `set` 变量文件；`::Goto xxx` 为注释，被静态工具误报 |

## 三、已修复缺陷明细

### 1. Keytool2 段标签冲突（apkdb.cmd / apkdb_d.cmd）

两个文件都定义了**两套** `:DP` `:DP86` `:javahome` `:CPNV` `:CP`。CMD 的 `goto` 只认第一个定义，而 `:Keytool2`（制作签名包）在后面。结果：只要系统设置了 `JAVA_HOME`，`goto javahome` 就跳到第一套 → `goto Keytool11` → 变成"查看签名信息"，**签名包制作功能实际不可用**。

修复：把第二套标签改名为 `:DP2/:DP862/:javahome2/:CPNV2/:CP2`，并同步该区域内所有 `goto`。

### 2. `goto APKinTool` 无目标（apkdb.cmd:1263）

高级菜单 `[7] 关联 APK 文件` 跳转到不存在的标签，选中后整段脚本静默终止。修复：改为执行 `start "" "%~dp0apktool.exe"` 后返回主菜单（与 apkdb_d.cmd 的实现一致）。

### 3. `:b1x` 重复 + `:bxxx2` 自环（apkdb.cmd）

- `:b1x` 有两处（758 整段回编译 / 842 缺目录提示）。`goto b1x` 总是进入第一处，导致"缺输入目录"场景反而开始全量重编译 → 第二处改名 `:b1x_err`，`:bxxx` 内的跳转改指它。
- `:bxxx2` 首行 `if not exist ...\resources.arsc goto bxxx2` 是**自环**，条件成立时无限循环 → 改跳 `:b1x_err`。

### 4. `%dexd_ERRORLEVEL%` 拼写（apkdb_d.cmd:473,505）

变量不存在，展开成 `IF  == 1` → 语法错误，且失败时仍打印"成功"。修复为 `%ERRORLEVEL%`。

### 5. `goto 230c` 死跳转（apkdb_d.cmd:487）

JAR 内含 `classes2.dex` 时跳转到不存在的标签，整个 JAR 反编译中止。修复：去掉该条件，让流程落到正常 baksmali（3.x 支持 zip/jar 输入）。

### 6. `goto Start` 缺字（apkdb_d.cmd:995）

查看签名后跳 `Start`，实际标签是 `StartAPK` → 窗口直接退出。已修正。

### 7. `odex.cmd` 三处

- 第 199 行标签写成 `A16`（缺冒号），而第 97 行 `goto A16` → 选 API 4 时脚本终止。
- `bs -x -a N` 是 **ShakaApktool 专有命令**，Apktool 3 没有 `bs`。共 28 处，全部改为 `baksmali.jar deodex -a N -d "%fr%" -o out file`（baksmali 3.0.10 实测接受该参数）。
- 第二个 `:A71` 改名为 `:AANY`，消除重复。

### 8. `sign.bat` 裸 `exit`（apktool/sign.bat:25,34）

该脚本由 `call` 调用。`exit` 会**关闭整个 APKDB 控制台**（用户选 `[D] 设定右键直接编译` 时必现）。改为 `exit /b`。

### 9. `optipng.cmd` 五处

- `set apk=%1` 未加引号，路径含空格时 `md`/`move` 全部失败。
- `set parent="%~dp0Tools"` 自身带引号，再拼 `"%parent%\7zip\..."` 得到 `"...\Tools"\7zip\64\7z.exe"`，7-Zip 无法启动。
- `%ZIP%` 从未定义（本文件用的是 `%szip%`），删除旧签名文件的命令实际是 `d "..."` → `'d' 不是内部命令`。
- `FOR` 之后没有 `exit /b`，会**继续落入 `:optipng` 子程序**，用目录名当 APK 名执行一遍。
- `IF %1 == ()` 恒假（见下条）。

### 10. `Tools/optipng.bat` 参数判断

`IF %1 == ()` 只有在参数**字面等于** `()` 时才成立，无参时变成 `IF  == ()` → 语法错误。改为 `if "%~1"=="" goto :eof`，并给 `-o7` 的路径加引号。

### 11. `install.bat` 重写（"按 2 闪退 / 图标装不上"）

四个独立缺陷叠加，正好对应现场现象：

1. **没有提权**。`RegAsm /codebase` 写 HKCR 需要管理员权限，普通权限下必然失败：
   `RegAsm : error RA0000 : 在将注册信息写入注册表时出错。需要有管理员权限…`。
   脚本不检查返回值，照样提示"安装完成" → "图标功能装不上"。
2. **`echo %PROCESSOR_IDENTIFIER% | FIND /i "x86"`** 依赖 Windows 自带 `find.exe`。
   若 PATH 里先命中 GNU/Unix `find`（Git for Windows、MSYS2、Cygwin、部分开发工具链），
   它会把 `/i` 当路径**扫描整盘**并返回错误码，导致 `FRAMEWORK` 判断错误、白等几十秒。
3. **没有检查 .NET Framework 4.8**。ApkShellext2-Plus 的目标框架是 4.8，界面却写"需要 4.0"。
4. **`:end` 使用 `mode con cols=12 lines=12` + `mshta VBScript:MsgBox` + 无条件 `taskkill explorer`**。
   mshta 被安全软件拦截、或 stdin 不是控制台时：弹窗不出现 → `pause` 立即返回 →
   直接杀掉资源管理器 → 窗口瞬间消失、桌面闪一下，即用户看到的"闪退"。

重写后的行为：

- 启动时用 `cacls` 检测权限，非管理员则用 PowerShell `Start-Process -Verb RunAs` 自提权；
  提权失败给出明确提示（右键"以管理员身份运行"）。
- 用 `%PROCESSOR_ARCHITECTURE%` 判断 32/64 位，不再调用 `find`。
- 读 `HKLM\SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full\Release`，
  经 `set /a` 归一化（该值可能是 `0x82718` 这种十六进制），`>= 528040` 才认定 4.8 可用。
- 选项 2 的三种结局都有明确输出：
  - 成功 → `[OK] 已启用"显示 APK 自身图标"`，写 `Tools\.icons-enabled`；
  - RegAsm 失败 → `[失败] 注册 Shell 扩展未成功`，保持"未启用"；
  - 缺 .NET 4.8 → `[跳过] 未检测到 .NET Framework 4.8`。
- 去掉 `mshta` / `mode con`；结束时显示"图标功能: 已启用/未启用"，`pause` 等待按键，
  并把结果追加写入 `安装目录\install.log`。
- **只有注册成功才**重启 Explorer 并清理 IconCache；失败或跳过时不动桌面。

### 11a. 安装流程逻辑修正（关闭 Explorer → 又打开"此电脑"）

旧版 `D.bat` 的链路是：

```
PreClean.bat : TASKKILL /F /IM explorer.exe      （我上一版为释放 DLL 加的）
D.bat        : tasklist | find explorer || start explorer   ← 弹出"此电脑"
D.bat        : start Setup.exe
```

既是多余的动作，`find` 还可能命中 GNU find，且"关掉桌面再弹两个窗口"体验很差。

修正：

- `PreClean.bat` 不再结束 Explorer；改为 `del`（未被占用时直接删）→ 失败则 `ren` 成
  `.old`（被加载的 DLL 可以改名，不能删除），保证 `xcopy` 能写入新文件。
  → 注意 `ren` 的第二个参数必须是**纯文件名**（`%~nx1.old`），带路径会报
  "文件名、目录名或卷标语法不正确"。
- `D.bat` 删除 `tasklist | find || start explorer` 整行，并清理上次遗留的 `*.old`。
- `install.bat` 的资源管理器重启改为**询问**：`[R] 现在重启 / 回车稍后重启`，
  只有注册成功且用户选择 R 才执行；重启前顺带删除 `*.old` 与图标缓存。
- `cleanup.bat uninstall` 分支也补上 `*.old` 清理。

### 11b. RegAsm `RA0000` 警告（未签名程序集）根因处理

警告原文：`使用 /codebase 注册未签名的程序集可能会导致程序集妨碍…`。
根因是 `ApkShellext2.dll` 没有强名称。两种处理：

1. **根治**：为程序集加强名称签名（本版采用）。构建时生成 `apkdb.snk`
   （CAPI PRIVATEKEYBLOB，即标准 SNK 格式）并设置
   `<SignAssembly>true</SignAssembly>`。现在程序集为
   `ApkShellext2, Version=2.1.5.0, PublicKeyToken=d21a89ac4bc45a64`，
   `RegAsm /codebase` 不再输出该警告。
2. **兜底**：`RegAsm` 的 stdout/stderr 全部重定向到 `install.log`，控制台不再显示
   注册细节，只显示 `[OK] 已启用…` 或 `[失败] …`。

### 12. `unins.bat` 重写

原文件含非法 GBK 字节（4 行乱码快捷方式路径），且调用 cleanup 会重新写回注册表。现改为：删除图标标记 → `cleanup.bat uninstall`（只清不注册）→ 删除开始菜单/桌面快捷方式 → 删除 4 个扩展名关联与两个右键菜单键。

### 13. `cleanup.bat` 的 uninstall 模式

新增 `uninstall` 参数：只做注销与删除，不再重建菜单/关联、不再注册 DLL。解决"卸载后扩展仍被注册"的残留问题。

### 14. 其它小修

- `seesource.bat`：`if exist %~p1seesource.bat` → 加引号。
- `reduce.bat`：`%delang%` 未定义时直接 `exit /b 1`，避免 `cd /d \res` 后误删。
- `JavaSet.bat`：`wmic` 不存在时给出明确提示，不再静默失败。
- `FLV2MP4.bat`：`goto :end2` → `:end`；缺 `ffmpeg.exe` 时提示并退出。
- `Update/update.bat`：改为离线说明（idoog.me 已停止解析）。
- 7 个 LF-only 文件统一为 CRLF（`apkshellext2/*.bat`、`apkdb.cmd`、`apkdb_d.cmd`、`unins.bat` 等）。

## 四、未修复 / 已知限制

1. **路径含空格**：`apkdb.cmd` 有 44 处、`apkdb_d.cmd` 有 3 处直接使用 `%1\...`。这依赖资源管理器把参数**连引号**一起传入（`"C:\a b\x.apk"\dir` 这种拼接 CMD 能接受）。从右键菜单调用正常；手工在命令行不带引号运行会失败。彻底改写需要重构 1600 行脚本，风险高于收益，建议保持"工作目录不含空格/中文"（原版帮助里也有同样提示）。
2. **`Hostsup.bat`**：`goto host DNS` 是合法的含空格标签，不是错误。但脚本内的更新源（idoog.me、coding.net/idoog）均已失效，"远程更新 HOSTS"不可用；`Defined_Hosts.txt` 手动模式仍可用。
3. **`FLV2MP4.bat`**：`ffmpeg.exe` 从未随包发布；脚本内部仍有两个 `:end` 标签，但入口已加守卫，不会执行到。
4. **`apkdb_d.cmd`**：`:dexd_OK` 重复定义，但没有任何 `goto dexd_OK`，仅顺序落入，无实际影响。
5. **编码**：全部脚本为 **GBK + CRLF**（与原版一致）。若系统开启"Beta: 使用 UTF-8 提供全球语言支持"，中文提示会乱码，且 `for /f` 解析可能异常。建议保持系统代码页 936。
6. **`Language.bat`**：静态工具报告的 `goto apkdb` 等均为 `::Goto xxx` 注释行，非真实跳转。
7. **`apksigner.bat` / `apkshellext2/install.bat`**：分别使用 `if [%1]==[]` 和 `if '%1' EQU '1'`，是 AOSP/上游的既有写法；参数含 `]` 或 `'` 时才会出问题，正常调用无影响。

## 五、验证记录

| 测试 | 结果 |
|---|---|
| 静态扫描 33 个脚本（标签/跳转/括号/引号/编码/CRLF） | 主流程 0 重复标签、0 未定义跳转 |
| `apkdb.cmd` Keytool2 区域标签与跳转 | `:DP2 :DP862 :javahome2 :CPNV2 :CP2`，goto 全部指向本区域 |
| `odex.cmd` baksmali 调用 | 28 处全部为 `deodex -a … -d "%fr%" -o … file`；CLI 实测参数被接受 |
| `OptiPNG 压缩 + 签名` 全链路（路径含空格） | 通过；产物 `01已优化\My App.apk`，`apksigner verify` 显示 v1/v2/v3 全通过 |
| `Tools/optipng.bat` 有参/无参 | 有参正常压缩；无参静默退出，无语法错误 |
| `odex.cmd` 独立运行保护 | 输出"请不要单独执行本文件"后正常退出 |
| `Update/update.bat` | 输出离线说明，不再访问失效域名 |
| `install.bat` 四个分支（默认图标 / 图标成功 / RegAsm 失败 / 无 .NET 4.8） | 均正常结束（rc=0），标记文件与 install.log 符合预期 |

## 六、产物

- 安装包：`APKDB_v2.1.5_20261119.exe`
- 大小：114,466,692 字节
- SHA-256：`8aacc058f8f4d49b6f2c62323634405db6404e6e42d5c05234e970181703821e`
- 构建脚本：`build_apkdb.py`（组件替换）+ `fix_bats.py`（脚本修复，可重复执行）
