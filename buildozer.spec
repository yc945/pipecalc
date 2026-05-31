[app]

# 应用名称（显示在手机桌面）
title = 供水水力计算

# 包名（唯一标识，格式: 域名.应用名）
package.name = pipecalc
package.domain = org.water.pipe

# 源码目录（main.py 所在位置）
source.dir = .

# 打包时包含的文件类型
source.include_exts = py,kv,ttf,otf,png,jpg

# 如有 fonts/ 子目录中的字体文件，一并打包
# source.include_patterns = fonts/*.ttf,fonts/*.otf

# 版本号
version = 1.0

# ── 依赖库 ───────────────────────────────────────────────────────────────────
# kivy 必须，其余按需添加
requirements = python3==3.11.0,kivy==2.3.0,pillow

# ── 屏幕方向 & 全屏 ──────────────────────────────────────────────────────────
orientation = portrait
fullscreen = 0

# ── 启动画面（可选，注释掉则用默认黑屏）────────────────────────────────────
# presplash.filename = %(source.dir)s/splash.png
# icon.filename      = %(source.dir)s/icon.png

# ── Android 配置 ─────────────────────────────────────────────────────────────
[app:android]

# 目标 API（Android 13 = 33，建议≥31）
android.api = 33

# 最低 API（Android 5.0 = 21，覆盖绝大多数在用机型）
android.minapi = 21

# NDK 版本（buildozer 会自动下载）
android.ndk = 25b

# 自动接受 SDK 许可
android.accept_sdk_license = True

# CPU 架构：arm64-v8a 覆盖 2017 年以后的绝大多数手机
# 如需同时支持旧手机可改为: arm64-v8a,armeabi-v7a
android.archs = arm64-v8a

# Android 权限（纯本地计算不需要额外权限）
android.permissions =

# 允许调试模式下 adb 连接（打包发布时改为 0）
android.logcat_filters = *:S python:D

# ── iOS 配置（暂不打 iOS 包，保留占位）────────────────────────────────────
[app:ios]
ios.kivy_ios_url = https://github.com/kivy/kivy-ios
ios.kivy_ios_branch = master
ios.ios_deploy_url = https://github.com/phonegap/ios-deploy
ios.ios_deploy_branch = 1.7.0

# ── buildozer 工具配置 ────────────────────────────────────────────────────────
[buildozer]

# 日志等级：0=警告, 1=信息, 2=调试（首次构建建议用 2）
log_level = 2

# 以 root 身份运行时发出警告（建议保持 1）
warn_on_root = 1

# 构建产物输出目录
# bin_dir = ./bin
