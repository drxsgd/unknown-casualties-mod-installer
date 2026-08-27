from pathlib import Path
import sys
import os
import shutil
import zipfile
import winreg
import re

# 注意:此程序目前仅适用于windows系统

mod_xz = 0
abc = []

def log(msg):
    abc.append(msg + "\n")

def prlog(nr):
    print(nr)
    log(nr)

# 注意，以下关于获取游戏路径的代码和检测文件的代码是由AI写的，因为我并不知道这一块怎么写

import tkinter as tk
from tkinter import messagebox

def tanchuang(title, message, msg_type="info"):
    """
    弹出一个标准的 Windows 风格提示框
    参数:
        title: 弹窗的标题（显示在标题栏）
        message: 弹窗的主要内容
        msg_type: 弹窗类型，可选 "info", "warning", "error", "question"
    返回值:
        对于 question 类型，返回 True（是）或 False（否）
        对于其他类型，无返回值（None）
    """
    root = tk.Tk()
    root.withdraw()
    
    if msg_type == "info":
        messagebox.showinfo(title, message)
    elif msg_type == "warning":
        messagebox.showwarning(title, message)
    elif msg_type == "error":
        messagebox.showerror(title, message)
    elif msg_type == "question":
        result = messagebox.askyesno(title, message)
        root.destroy()
        return result
    
    root.destroy()


# 调试日志列表

def exit(wy,xs=1):
    # 获取程序所在目录（兼容打包前后）
    log(f"退出的提示:{wy}")
    if getattr(sys, 'frozen', False):
        base_dir = Path(sys.executable).parent
    else:
        base_dir = Path(__file__).parent

    file_path = base_dir / "logabc"

    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(abc)
    except Exception as e:
        prlog(f"错误，无法写入日志文件:{e}")
    print(wy)
    if xs == 1:
        print("最后，如果问题并不出在你，那我建议把与程序同目录下的logabc文件发给开发者，以便开发者快速定位原因，并协助你，谢谢")
    input("请按回车退出(1/2)")
    input("请按回车退出(2/2)")
    sys.exit()


def get_steam_game_path(game_id):
    """
    根据Steam游戏ID获取其安装目录（调试日志存入外部列表 abc）
    参数: game_id - Steam游戏数字ID（如未知伤亡为4576510）
    返回值: 游戏安装目录的Path对象，未找到则返回None
    """
    log("开始查找游戏路径")
    
    # 获取程序所在目录（兼容打包前后）
    if getattr(sys, 'frozen', False):
        base_dir = Path(sys.executable).parent
    else:
        base_dir = Path(__file__).parent

    log(f"[调试] 程序所在目录: {base_dir}")
    steam_path = None

    # 1. 从注册表读取Steam路径
    reg_locations = [
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Valve\Steam", "SteamPath"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath")
    ]
    log("[调试] 尝试从注册表读取Steam安装路径...")
    for hkey, subkey, value_name in reg_locations:
        try:
            key = winreg.OpenKey(hkey, subkey)
            steam_path, _ = winreg.QueryValueEx(key, value_name)
            winreg.CloseKey(key)
            steam_path = Path(steam_path)
            log(f"[调试] 成功读取注册表: {steam_path}")
            break
        except FileNotFoundError:
            log(f"[调试] 未在 {subkey} 中找到 Steam 路径")
            continue
        except Exception as e:
            log(f"[调试] 读取注册表时发生异常: {e}")
            continue

    if steam_path is None:
        log("[错误] 未在注册表中找到 Steam 安装路径")
        return None

    # 2. 获取所有Steam库文件夹
    libraries = [steam_path]
    vdf_path = steam_path / "steamapps" / "libraryfolders.vdf"
    log(f"[调试] 尝试读取库配置文件: {vdf_path}")
    
    if vdf_path.exists():
        try:
            with open(vdf_path, 'r', encoding='utf-8') as f:
                content = f.read()
            paths = re.findall(r'^\s*"\d*"\s*"([^"]*)"', content, re.MULTILINE)
            log(f"[调试] 从 libraryfolders.vdf 中提取到 {len(paths)} 个额外库路径")
            for p in paths:
                lib_path = Path(p.replace("\\\\", "\\"))
                if lib_path.exists():
                    libraries.append(lib_path)
                    log(f"[调试] 添加有效库路径: {lib_path}")
                else:
                    log(f"[调试] 库路径不存在，跳过: {lib_path}")
        except Exception as e:
            log(f"[调试] 读取或解析 libraryfolders.vdf 时出错: {e}")
    else:
        log(f"[调试] 未找到 libraryfolders.vdf 文件，仅使用默认库: {steam_path}")

    log(f"[调试] 总共将扫描 {len(libraries)} 个库文件夹: {libraries}")

    # 3. 在所有库中查找游戏 ACF 文件
    target_acf = f"appmanifest_{game_id}.acf"
    log(f"[调试] 目标 ACF 文件名: {target_acf}")

    for lib in libraries:
        acf_path = lib / "steamapps" / target_acf
        log(f"[调试] 检查: {acf_path} 是否存在? {acf_path.exists()}")
        if acf_path.exists():
            try:
                with open(acf_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                match = re.search(r'"installdir"\s*"([^"]+)"', content)
                if match:
                    game_folder = match.group(1)
                    log(f"[调试] 从 ACF 中解析到 installdir: {game_folder}")
                    game_path = lib / "steamapps" / "common" / game_folder
                    log(f"[调试] 尝试定位游戏目录: {game_path} 是否存在? {game_path.exists()}")
                    if game_path.exists():
                        log(f"[调试] 找到游戏路径: {game_path}")
                        return game_path
                    else:
                        log(f"[调试] 游戏目录不存在，可能游戏未完整安装或目录名不匹配")
                else:
                    log(f"[调试] 在 ACF 文件中未找到 installdir 字段")
            except Exception as e:
                log(f"[调试] 读取或解析 ACF 文件时出错: {e}")
        else:
            log(f"[调试] 未找到 ACF 文件: {acf_path}")

    log("[调试] 所有库遍历完毕，未找到游戏安装目录")
    return None
    
def find_file(filename):
    # 方式1：开发环境 - 脚本所在目录
    if not getattr(sys, 'frozen', False):
        path = Path(__file__).parent / filename
        if path.exists():
            log(f"当前是开发环境，检测到脚本所在目录有{filename}")
            return path

    # 方式2：打包环境 - 优先读取包内资源（PyInstaller 的 _MEIPASS）
    if hasattr(sys, '_MEIPASS'):
        path = Path(sys._MEIPASS) / filename
        if path.exists():
            log(f"当前是打包环境，已在包内资源检测到{filename}")
            return path

    # 方式3：打包环境 - 降级读取 EXE 同目录
    path = Path(sys.executable).parent / filename
    if path.exists():
        log(f"当前是包内环境，已检测到{filename}")
        return path

    # 所有环境均未找到
    log(f"在这三种环境中，并没有在任何一种路径下检测到{filename}")
    return None
    
# 切换到人工

tanchuang("提示","""未知伤亡mod安装器v2.1.1
注意:
1.此版本没有做过多的兼容，请确保你的mod压缩包里面是"/plugins/......"这样的格式,否则mod不会生效
2.此安装器在安装新mod时将会直接删除之前的mod,不会备份。请知悉

mod安装器作者:享受孤独(qq号:3762239872)

继续使用本程序即表示您已阅读并知悉以上内容。
""","info")

# 检测游戏是否安装
a = get_steam_game_path(4576510)
if a is None:
    print("错误:未找到游戏安装目录，请确认游戏已在steam入库并安装")
    a = input("如果你不是通过steam安装的，而是通过其他方式安装的，请在这里输入你的游戏根目录(注意是根目录，如果你也没有通过其他方式安装，请直接右上角点击叉退出程序):")
    if a == "":
        exit("看起来你输入了空白内容,已默认跳过")
    print("正在检测此目录到底是不是游戏根目录...")
    log(f"用户手动输入了游戏文件夹:{a}，正在检测其是真是假")
    a = str(a)
    a = a.strip().strip('"')
    a = Path(a)
    exe_path = a / "CasualtiesUnknown.exe"
    data_path = a / "CasualtiesUnknown_Data"

    exe_exists = exe_path.is_file()
    data_exists = data_path.is_dir()

    if exe_exists and data_exists:
        log(f"[检测] 验证通过")
        print("验证通过")
    else:
        log(f"[检测] 游戏完整性验证失败")
        if not exe_exists:
            log(f"[检测] 未找到主程序: {exe_path}")
        if not data_exists:
            log(f"[检测] 未找到Data文件夹: {data_path}")
        exit("错误:此目录并不是正确的游戏目录，请检查这是否是游戏目录，或者这是不是游戏根目录")
print(f"已找到游戏目录:{a}")
b = a / "BepInEx"

log("程序已运行到BepInEx这里")
# BepInEx依赖相关代码
if os.path.isdir(b):
    prlog("已检测到BepInEx环境")
else:
    prlog("错误:BepInEx未安装")
    b = find_file("BepInEx.zip")
    if b and b.is_file():
        prlog("检测到BepInEx安装包")
        d = input("是否为你安装BepInEx?(y/n)没有异议或看不懂请输入y:")
        if d == "y" or d == "Y":
            a.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(b, 'r') as zf:
                zf.extractall(a)
                log("用户选择了安装BepInEx安装包")
                prlog("BepInEx依赖安装完成")
        else:
            log("用户选择了取消安装BepInEx安装包")
            print("已取消安装")
            exit("BepInEx是插件运行的依赖，没有它，所有mod都无法运行。所以本程序无法为您继续安装mod",0)
    else:
        prlog("未找到BepInEx安装包")
        exit("BepInEx是插件运行的依赖，没有它，所有mod都无法运行。请手动安装BepInEx或把BepInEx安装文件放在与程序同一目录下。")


log("找用户要mod或者找mod")
# 找用户要mod或者找mod
m = find_file("wzsw_mod.zip")
md = find_file("wzsw_mod114514.zip")

if md and md.is_file():
    log("检测到外部指定mod")
    d = input("检测到外部指定mod,是否选择(y/n)?")
    if d == "y" or d == "Y":
        print("好的，已选择")
        log("用户已选择使用")
        e = md
        mod_xz = 1
    else:
        print("好的，已取消")
        log("用户已取消使用")
if m and m.is_file() and mod_xz == 0:
    e = m
    prlog("检测到指定的mod")
    d = input("是否为你安装指定mod？(y/n)没有异议或看不懂请输入y:")
    if d != "y" and d != "Y":
        d = input("那么，是否由你自己选择mod?(y/n)如果你是需要安装自己的mod,此处请选y:")
        if d != "y" and d != "Y":
            exit("已取消安装mod",0)
        e = input("请将zip压缩格式的mod文件拖入此窗口(或手动输入完整路径)，然后按下回车键：")
else:
    e = input("请将zip压缩格式的mod文件拖入此窗口(或手动输入完整路径)，然后按下回车键：")

e = str(e)
f = e.strip().strip('"')
if not Path(f).is_file():
    exit("错误:找不到该文件，请检查路径是否正确")
else:
    prlog(f"已获取mod文件路径：{f}")
    b = a / "BepInEx"
    
    # 开始验证是否为 zip 压缩包
    if zipfile.is_zipfile(f):
        prlog("zip文件验证完成")
        g = f
    else:
        exit("错误:这不是合法的 zip 压缩包（可能损坏、加密或这根本不是个压缩包）")

# 解压mod文件
prlog("正在安装mod，请稍候...")
h = b / "plugins"
if os.path.isdir(h):
    shutil.rmtree(h)


i = Path(g)      # 压缩包路径
j = Path(b)    # 目标解压目录

j.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(i, 'r') as zf:
    zf.extractall(j)
log("全部安装完成")
print("mod已经全部安装完成，如果后续发生任何问题，建议你把与本程序同目录下的logabc文件发给开发者，以便开发者快速定位原因，而且也可以更好地协助你，谢谢")
if 1==1:
    if getattr(sys, 'frozen', False):
        base_dir = Path(sys.executable).parent
    else:
        base_dir = Path(__file__).parent

    file_path = base_dir / "logabc"

    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(abc)
    except Exception as e:
        prlog(f"错误，无法写入日志文件:{e}")
        print("如果mod安装成功了，那你不必理会这个错误，如果发生问题，需要把日志文件发给开发者，请尝试使用管理员权限重新安装一遍，看是否可以写入成功")
input("请按回车退出(1/2)")
input("请按回车退出(2/2)")