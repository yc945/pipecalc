[app]

title = 供水水力计算
package.name = pipecalc
package.domain = org.water.pipe
source.dir = .
source.include_exts = py,kv,ttf,otf,png,jpg
version = 1.0

requirements = python3,kivy==2.3.0,pillow

orientation = portrait
fullscreen = 0

android.api = 33
android.minapi = 21
android.ndk = 25b
android.accept_sdk_license = True
android.archs = arm64-v8a
android.permissions =

[buildozer]
log_level = 2
warn_on_root = 1
