# 护眼计时：打包与跨平台

这份说明只谈两件事：怎样做成 Windows 上的 exe，以及以后怎样放到 macOS 和 Linux 上。计时规则仍然在 `eyeguard/engine.py`，不随系统变化。

## 程序现在分成三层

| 层 | 位置 | 是否依赖系统 |
| --- | --- | --- |
| 计时 | `eyeguard/engine.py` | 否。只接收时间戳 |
| 界面 | `float_window.py`、`rest_overlay.py`、`dialogs.py`、`app.py` | 只用 Tk，三套系统都能跑 |
| 系统能力 | `eyeguard/platform.py` | 是。现在只接了 Windows |

`platform.py` 是唯一的系统入口。`app.py` 已经从这里取空闲检测、全屏判断、伽马、热键、关屏和开机启动。换系统时改这个入口后面的实现，不要把 `ctypes` 再写进界面。

## 打包成 exe

推荐先做 **目录版**，不要一上来做单文件。

| 方案 | 适合 | 取舍 |
| --- | --- | --- |
| PyInstaller 目录版 | 现在的 Windows 程序 | 启动快，缺文件时能直接看到。体积大约几十 MB，因为里面带一份 Python |
| PyInstaller 单文件 | 只想发一个 exe | 每次启动要先解压到临时目录，杀毒软件更容易误报 |
| Nuitka | 想要更接近普通程序的启动速度 | 编译久，Windows 上要装 C 编译器 |
| cx_Freeze | 和 PyInstaller 同类 | 生态小一些，没有明显好处 |
| Briefcase | 以后要同时出 macOS 和 Windows 安装包 | 现在用它会把 Tk 程序重新套一层，先不采用 |

仓库里已经放了目录版规格：

```powershell
cd F:\yanyue404\eyefoo
powershell -ExecutionPolicy Bypass -File packaging\build_windows.ps1
```

产物是 `dist\EyeGuard\EyeGuard.exe`。这个 exe 没有黑色控制台窗口。配置仍然写在 exe 旁边的运行目录时并不自动成立：现在的配置路径是源码目录下的 `data\`。打包之后应改成 exe 所在目录，这一步还没做，列在下面的阶段里。

开机启动已经区分两种启动方式。源码运行时写 `pythonw.exe` 加 `run.py`。PyInstaller 打出来的程序写 exe 自己的路径。

## 跨平台要补的能力

同一套界面在三个系统上需要下面这些能力。空着的格子就是还没写的后端。

| 能力 | Windows（已有） | macOS | Linux |
| --- | --- | --- | --- |
| 亮度和暖色 | `SetDeviceGammaRamp` | `CGSetDisplayTransferByTable` | X11 用 `XRRSetCrtcGamma`；Wayland 用合成器的 gamma 协议，各家桌面不一样 |
| 空闲时间 | `GetLastInputInfo` | `IOHIDSystem` 的空闲时间 | X11 用屏保扩展；Wayland 没有统一接口，只能先做“不暂停” |
| 全屏判断 | 前台窗口是否铺满屏幕 | 前台窗口 bounds | 同样比窗口和屏幕，Wayland 上经常拿不到前台窗口 |
| 全局热键 | `RegisterHotKey` | 全局监视需要辅助功能权限 | X11 可以抢键；Wayland 默认不给普通程序抢键 |
| 关闭显示器 | `SC_MONITORPOWER` | `IOKit` 睡眠显示器 | `xset dpms force off`，Wayland 上用 logind |
| 托盘 | `pystray` | `pystray` | `pystray`，需要 AppIndicator |
| 开机启动 | 当前用户的 Run 项 | `SMAppService` 登录项 | `~/.config/autostart/*.desktop` |

Tk 界面、柠檬片皮肤、休息倒计时、方案和密码可以原样复用。不要在 `engine.py` 里写系统分支。

## 建议的实现顺序

1. Windows 功能收稳。右键菜单每次点击只执行这一次，皮肤大小可调，设置能保存。这一步正在做。
2. 把配置目录改成“源码运行用项目里的 `data`，打包运行用 exe 旁边的 `data`”。
3. 在 `platform.py` 后面加 `platform_mac.py`，先做伽马、空闲和托盘，热键放到辅助功能权限提示之后。
4. 再加 `platform_linux.py`，先只保证 X11。Wayland 单独开，缺能力时界面保持可用，只是亮度或热键提示不可用。
5. macOS 用 PyInstaller 打 `.app`。Linux 先提供 PyInstaller 目录，再考虑发行版包。

新增一个系统时，实现 `platform.py` 里 `__all__` 的那些函数，并让 `platform.py` 按 `sys.platform` 转到新文件。界面代码不用改。
