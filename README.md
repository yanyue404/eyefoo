# 护眼计时

可修改的 Windows 护眼计时程序。工作一段时间后铺满屏幕提醒休息，并可调节显示器亮度和暖色。

`eyefoo_3.0.15.207.exe` 是眼睛护士（EyeFoo）3.0.15.207 的 NSIS 安装包，里面没有源码。本目录里的 `eyeguard` 是按这类软件公开的用法重新写的，方便继续改功能。

## 它怎么工作

程序自己计时，到点盖住屏幕。改画面时不逐个处理窗口，而是改显示器的伽马表，整屏一起变暗或变暖。

| 行为 | 实现 |
| --- | --- |
| 工作 / 休息倒计时 | `eyeguard/engine.py` 用单调时钟推进。暂停时冻结剩余秒数，恢复后继续 |
| 无键鼠时暂停 | `GetLastInputInfo`。默认连续 180 秒没有输入就暂停，设为 0 则关闭 |
| 全屏时暂停 | 前台窗口几乎铺满某块屏幕，且不是本程序，也不是桌面 |
| 休息遮罩 | 每块屏幕一个置顶无边框窗口，显示倒计时和眼保健动作 |
| 紧急推迟 | 工作中延长本轮；休息中结束休息，只再给一段推迟时间。默认每轮 3 次，用完后要密码 |
| 结束休息、改设置、退出 | 设置了密码才询问。密码以 PBKDF2 存在配置里 |
| 亮度 | `SetDeviceGammaRamp`，三通道一起按比例缩小。退出或恢复 100% 时写回启动时读到的原表 |
| 暖色 | 同一张伽马表里少压红、多压蓝。这是色温的简化做法 |
| 关灯 | 纯黑遮罩。`Ctrl+Alt+T` 开关，双击发 `SC_MONITORPOWER` 让显示器休眠 |
| 推迟热键 | `Ctrl+Alt+D`，用 `RegisterHotKey` 注册，不挂键盘钩子 |
| 提示音 | 配置里的 wav；留空则播放系统提示音。自然结束休息时连响两次 |
| 定时关机 | 调用 Windows 的 `shutdown /s`，对话框里可以 `shutdown /a` 取消 |
| 开机启动 | 当前用户的 `Run` 注册表项，指向 `pythonw.exe` 和 `run.py` |

计时状态：

1. 工作中。剩余时间少于“提前提示”时，悬浮窗变橙色并响一声。
2. 到点进入休息。遮罩盖住所有屏幕，空闲和全屏检测不再打断休息。
3. 休息结束，开始下一轮完整的工作时间。
4. 工作中如果无操作、遇到全屏程序，或手动暂停，剩余时间停住；条件消失后从停住的秒数继续。

保存方案后，当前这一轮会按新的时长重新计算。

## 运行

需要 Windows 和 Python 3.11 及以上。

```powershell
cd eyefoo
pip install -r requirements.txt
python run.py
```

不想看到控制台窗口时，用 `pythonw run.py`。

右键柠檬片可以休息、推迟、暂停、关灯、切换皮肤、放大缩小、打开设置或退出。皮肤有青柠和橙片。滚轮或设置里的“大小”可以调整柠檬片，范围是 160 到 360。这些都会记在 `data/config.json`。

打包和 macOS、Linux 的做法写在 `DESIGN.md`。Windows 目录版可以用 `packaging\build_windows.ps1` 打出来。

菜单打开期间，倒计时不会去改这个菜单。之前每 0.2 秒刷新一次置顶，菜单按钮会跟着闪，点不中。

自检：

```powershell
python -m unittest discover -s tests
python run.py --smoke
```

`--smoke` 会打开悬浮窗并马上退出，不注册热键，也不改伽马表。

## 二次开发时改哪里

| 想改的东西 | 文件 |
| --- | --- |
| 计时规则、推迟之后怎么继续 | `eyeguard/engine.py` |
| 默认方案、配置字段 | `eyeguard/config.py`、`data/config.json` |
| 亮度算法、热键、全屏判断、关屏 | `eyeguard/platform_win.py` |
| 悬浮窗外观、青柠 / 橙片 | `eyeguard/skins.py`、`eyeguard/float_window.py` |
| 休息页文案和按钮 | `eyeguard/rest_overlay.py` |
| 设置项 | `eyeguard/dialogs.py` |
| 把上面这些串起来 | `eyeguard/app.py` |

加一种新的屏幕效果时，在 `platform_win.apply_display` 里改三通道增益，设置界面已经把亮度和暖色传进来了。

换一套休息交互时，保持 `Engine.tick` 仍返回 `warn`、`rest_start`、`rest_end`、`paused`、`resumed`，`app.py` 的 `_handle_event` 不用跟着改状态机。

热键目前固定为推迟 `Ctrl+Alt+D`、关灯 `Ctrl+Alt+T`。要换键，改 `platform_win.py` 里的 `VK_D` / `VK_T` 和对应修饰键。如果眼睛护士或其他程序已经注册了同一热键，日志 `data/eyeguard.log` 会记下占用。

## 使用时要注意

伽马表能不能写成功取决于显卡驱动。笔记本有时只接受硬件亮度，函数会失败并写进日志，悬浮窗和休息提醒仍然可用。

系统“夜间模式”可能在本程序之后再次改色温。两边同时开时，以最后写入的一方为准。

休息窗口会反复置顶，避免被普通软件挡住。它不锁定任务管理器，也不阻止注销。需要强制结束时，在任务管理器里结束 Python 进程即可。

定时关机是真实的系统关机。点“开始计时关机”之后，可以用同一对话框里的“取消关机”撤回。
